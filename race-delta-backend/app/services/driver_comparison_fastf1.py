# app/services/driver_comparison_fastf1.py
"""Driver-vs-driver comparison for the latest completed race, served from the Phase-2 feature store."""
import os
from datetime import datetime

import fastf1

import app.fastf1_setup  # noqa: F401  (enables the shared FastF1 cache)
from app.services import cache_store
from app.services.feature_store import ensure_race_features, features_for_race

DERIVED_CACHE_TTL = int(os.getenv("FASTF1_DERIVED_CACHE_TTL", "21600"))


def _completed_events(year: int):
    schedule = fastf1.get_event_schedule(year)
    schedule = schedule[schedule["RoundNumber"] > 0]
    if "EventFormat" in schedule.columns:
        schedule = schedule[schedule["EventFormat"] != "testing"]
    dates = schedule["EventDate"]
    if dates.dt.tz is not None:
        dates = dates.dt.tz_convert(None)
    return schedule[dates < datetime.utcnow()]


def get_latest_completed_event(year: int):
    completed = _completed_events(year)
    return None if completed.empty else completed.iloc[-1]["EventName"]


def get_latest_completed_round(year: int):
    completed = _completed_events(year)
    if completed.empty:
        return None, None
    last = completed.iloc[-1]
    return int(last["RoundNumber"]), str(last["EventName"])


def compare_drivers_season(driver1: str, driver2: str, season: int):
    """
    Compare two drivers in the latest completed race of `season`.

    Returns the legacy keys (avg_lap_time / best_lap_time / laps) plus the full
    engineered feature vector for each driver under `features`.
    """
    return cache_store.cached("derived", f"compare_latest:v3:{season}:{driver1.upper()}:{driver2.upper()}",
                              cache_store.season_ttl(season), lambda: _build_comparison(driver1, driver2, season))


def _build_comparison(driver1: str, driver2: str, season: int):
    completed = _completed_events(season)
    if completed.empty:
        raise RuntimeError("No completed race found")

    # The newest round has laps within hours of the flag but its classification can lag; use the
    # latest round that can actually be ingested.
    error = None
    for _, ev in completed.iloc[::-1].head(2).iterrows():
        round_num, event_name = int(ev["RoundNumber"]), str(ev["EventName"])
        try:
            ensure_race_features(season, round_num)
            break
        except Exception as e:  # ResultsPending or a FastF1 hiccup: step back one round
            error = e
    else:
        raise RuntimeError(f"Latest races could not be ingested: {error}")
    rows = {r["driver_code"]: r for r in features_for_race(season, round_num)}
    a, b = rows.get(driver1.upper()), rows.get(driver2.upper())
    if not a or not b:
        raise RuntimeError("Missing lap data for one or both drivers")

    def block(r):
        return {"avg_lap_time": r["avg_pace_s"], "best_lap_time": r["best_lap_s"],
                "laps": r["total_laps"], "features": r}

    payload = {
        "season": season,
        "round": round_num,
        "event": event_name,
        "drivers": {driver1: block(a), driver2: block(b)},
        "source": "feature_store",
    }
    return payload
