"""
Warms the current season's caches once at startup, on a daemon thread, so the first visitor
never waits for FastF1 or OpenF1. Disable with RACEDELTA_WARM_CACHE=0.
"""
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)


def start(app) -> None:
    if app.config.get("TESTING") or os.getenv("RACEDELTA_WARM_CACHE", "1") != "1":
        return
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return  # reloader parent process; the child does the work
    threading.Thread(target=_warm, args=(app,), daemon=True, name="cache-warmer").start()


def _warm(app) -> None:
    t0 = time.time()
    client = app.test_client()
    try:
        with app.app_context():
            from app.utils.season_resolver import resolve_seasons
            season = resolve_seasons()["display_season"]
        urls = [
            "/api/seasons",
            f"/api/drivers?season={season}",
            f"/api/teams?season={season}",
            f"/api/standings/drivers?season={season}",
            f"/api/standings/constructors?season={season}",
            f"/api/meetings?year={season}",
            f"/api/strategy/races?season={season}",
            f"/api/ai/rating?season={season}",
            f"/api/ai/clusters?season={season}&method=kmeans&k=4",
        ]
        for url in urls:
            client.get(url)
        drivers = (client.get(f"/api/drivers?season={season}").get_json() or {}).get("drivers") or []
        for d in drivers:
            client.get(f"/api/l1/season?driver_code={d['driver_code']}&season={season}")
        # Strategy Lab contexts live in process memory (XGBoost fit per race); only rounds already ingested
        races = (client.get(f"/api/strategy/races?season={season}").get_json() or {}).get("races") or []
        for r in races:
            if r.get("ingested"):
                client.get(f"/api/strategy/race?season={season}&round={r['round']}")
        logger.info("cache warm-up for %s finished in %.0fs", season, time.time() - t0)
    except Exception as e:
        logger.warning("cache warm-up aborted: %s", e)
