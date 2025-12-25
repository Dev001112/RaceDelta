import fastf1
from datetime import datetime
import os

# --------------------------------------------------
# FASTF1 CACHE SETUP (SAFE, IDEMPOTENT)
# --------------------------------------------------

CACHE_DIR = os.path.join(os.path.expanduser("~"), "fastf1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

try:
    fastf1.Cache.enable_cache(CACHE_DIR)
except Exception:
    pass  # cache already enabled

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

    event_name = get_latest_completed_event(season)
    if not event_name:
        raise RuntimeError("No completed race found")

    session = fastf1.get_session(season, event_name, "RACE")
    session.load()

    laps = session.laps

    a = laps.pick_driver(driver1)
    b = laps.pick_driver(driver2)

    if a.empty or b.empty:
        raise RuntimeError("Missing lap data for one or both drivers")

    def metrics(df):
        return {
            "avg_lap_time": round(df["LapTime"].dt.total_seconds().mean(), 3),
            "best_lap_time": round(df["LapTime"].dt.total_seconds().min(), 3),
            "laps": int(len(df))
        }

    return {
        "season": season,
        "event": event_name,
        "drivers": {
            driver1: metrics(a),
            driver2: metrics(b)
        },
        "source": "fastf1"
    }
