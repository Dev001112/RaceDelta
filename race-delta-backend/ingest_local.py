"""One-off: build data/racedelta.db locally so the free container ships with real data.
Render's free tier has no persistent disk, so on-demand ingestion is lost on every restart."""
import os, sys, time
os.environ.setdefault("RACEDELTA_WARM_CACHE", "0")
# create_app() calls load_dotenv(override=True) unless FLASK_ENV is production, which would
# let .env's postgres DATABASE_URL clobber the sqlite path set below.
os.environ["FLASK_ENV"] = "production"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "racedelta.db").replace("\\", "/")
from app import create_app
app = create_app()
with app.app_context():
    from app.services.ingestor import DataIngestor as D
    t0 = time.time()
    print("schedule:", D.ingest_season_schedule(2026), flush=True)
    rounds = D.completed_rounds(2026)
    print("completed rounds:", rounds, flush=True)
    for r in rounds:
        t = time.time()
        try:
            s = D.ingest_race_telemetry(2026, r)
            print(f"  round {r:2} OK  {s['event'][:28]:28} drivers={s['drivers']:3} laps={s['laps']:5}  {time.time()-t:.0f}s", flush=True)
        except Exception as e:
            print(f"  round {r:2} FAIL {str(e)[:90]}  {time.time()-t:.0f}s", flush=True)
    print(f"TOTAL {time.time()-t0:.0f}s", flush=True)
