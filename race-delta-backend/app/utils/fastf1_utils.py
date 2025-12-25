from datetime import datetime
import fastf1

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
