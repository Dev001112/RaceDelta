import fastf1
from datetime import datetime
import os
import math
from app.services import cache_store

# --------------------------------------------------
# FASTF1 CACHE SETUP (SAFE, IDEMPOTENT)
# --------------------------------------------------

CACHE_DIR = os.path.join(os.path.expanduser("~"), "fastf1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

try:
    fastf1.Cache.enable_cache(CACHE_DIR)
except Exception:
    pass  # cache already enabled

DERIVED_CACHE_TTL = int(os.getenv("FASTF1_DERIVED_CACHE_TTL", "21600"))

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def get_latest_completed_event(year: int):
    schedule = fastf1.get_event_schedule(year)

    event_dates = schedule["EventDate"]
    if event_dates.dt.tz is not None:
        event_dates = event_dates.dt.tz_convert(None)

    now = datetime.utcnow()
    completed = schedule[event_dates < now]

    if completed.empty:
        return None

    return completed.iloc[-1]["EventName"]

# --------------------------------------------------
# MAIN COMPARISON
# --------------------------------------------------

def compare_drivers_season(driver1: str, driver2: str, season: int):
    """
    Compare two drivers in the latest completed race
    Uses FastF1 only (NO Ergast)
    """

    cache_key = f"compare_latest:v2:{season}:{driver1.upper()}:{driver2.upper()}"
    cached = cache_store.get("derived", cache_key)
    if cached is not None:
        return cached

    event_name = get_latest_completed_event(season)
    if not event_name:
        raise RuntimeError("No completed race found")

    session = fastf1.get_session(season, event_name, "RACE")
    session.load(laps=True, telemetry=False, weather=False, messages=False)

    laps = session.laps

    a = laps.pick_driver(driver1)
    b = laps.pick_driver(driver2)

    if a.empty or b.empty:
        raise RuntimeError("Missing lap data for one or both drivers")

    def safe_float(value):
        try:
            value = float(value)
            return round(value, 3) if math.isfinite(value) else None
        except Exception:
            return None

    def metrics(df):
        lap_seconds = df["LapTime"].dt.total_seconds().dropna()
        return {
            "avg_lap_time": safe_float(lap_seconds.mean()),
            "best_lap_time": safe_float(lap_seconds.min()),
            "laps": int(len(lap_seconds))
        }

    payload = {
        "season": season,
        "event": event_name,
        "drivers": {
            driver1: metrics(a),
            driver2: metrics(b)
        },
        "source": "fastf1"
    }
    cache_store.set("derived", cache_key, payload, DERIVED_CACHE_TTL)
    return payload
