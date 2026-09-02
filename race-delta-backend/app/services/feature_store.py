# app/services/feature_store.py
"""Read side of the Phase-2 feature store (driver_race_features), plus lazy ingestion."""
import numpy as np

from models import RaceSession, DriverRaceFeature
from app.services.ingestor import DataIngestor

FEATURE_COLUMNS = [
    "grid_position", "finish_position", "status", "points", "total_laps", "clean_laps",
    "avg_pace_s", "best_lap_s", "s1_avg_s", "s2_avg_s", "s3_avg_s",
    "lap_consistency_s", "race_pace_trend_s_per_lap", "tyre_degradation_s_per_lap",
    "avg_stint_length", "pit_stop_count", "pit_laps",
    "position_changes", "overtake_count", "avg_gap_ahead_s", "avg_gap_behind_s", "penalties",
    "avg_air_temp", "avg_track_temp", "rainfall",
]
MEAN_COLUMNS = [
    "avg_pace_s", "best_lap_s", "s1_avg_s", "s2_avg_s", "s3_avg_s", "lap_consistency_s",
    "race_pace_trend_s_per_lap", "tyre_degradation_s_per_lap", "avg_stint_length",
    "position_changes", "avg_gap_ahead_s", "avg_gap_behind_s", "grid_position", "finish_position",
]
SUM_COLUMNS = ["points", "pit_stop_count", "overtake_count", "penalties", "clean_laps", "total_laps"]


def row_to_dict(f: DriverRaceFeature) -> dict:
    d = {c: getattr(f, c) for c in FEATURE_COLUMNS}
    d.update({
        "season": f.season, "round": f.round, "driver_code": f.driver_code,
        "driver_id": f.driver_id, "constructor_id": f.constructor_id,
        "session_id": f.session_id, "race_id": f.race_id,
    })
    return d


def _session(season, round_num, session_type="R"):
    return RaceSession.query.filter_by(season=season, round=round_num, session_type=session_type).first()


def ensure_race_features(season: int, round_num: int, session_type: str = "R"):
    """Return the RaceSession for a round, ingesting it from FastF1 on first request."""
    rs = _session(season, round_num, session_type)
    if rs and DriverRaceFeature.query.filter_by(session_id=rs.session_id).count() > 0:
        return rs
    DataIngestor.ingest_race_telemetry(season, round_num, session_type)
    return _session(season, round_num, session_type)


def features_for_race(season: int, round_num: int, session_type: str = "R") -> list:
    rs = _session(season, round_num, session_type)
    if not rs:
        return []
    rows = (DriverRaceFeature.query.filter_by(session_id=rs.session_id)
            .order_by(DriverRaceFeature.finish_position.asc().nulls_last(),
                      DriverRaceFeature.driver_code)
            .all())
    out = [row_to_dict(r) for r in rows]
    for d in out:
        d["event"] = rs.event_name
    return out


def features_for_driver(driver_code: str, season: int) -> dict:
    """All ingested per-race feature rows for a driver in a season, plus season aggregates."""
    rows = (DriverRaceFeature.query.filter_by(driver_code=driver_code.upper(), season=season)
            .order_by(DriverRaceFeature.round).all())
    races = [row_to_dict(r) for r in rows]

    agg = {}
    for c in MEAN_COLUMNS:
        vals = [r[c] for r in races if r.get(c) is not None]
        agg[c] = round(float(np.mean(vals)), 3) if vals else None
    for c in SUM_COLUMNS:
        vals = [r[c] for r in races if r.get(c) is not None]
        agg[c] = round(float(np.sum(vals)), 1) if vals else 0
    agg["races"] = len(races)
    agg["rainfall_races"] = sum(1 for r in races if r.get("rainfall"))

    return {"driver_code": driver_code.upper(), "season": season,
            "races": races, "aggregates": agg, "source": "feature_store"}
