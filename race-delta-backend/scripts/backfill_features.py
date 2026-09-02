"""
Backfill the Phase-2 feature store (laps, stints, driver_race_features) for a season.

Usage (from race-delta-backend, with the venv active):
    python scripts/backfill_features.py 2025            # every completed round
    python scripts/backfill_features.py 2025 1 2 3      # specific rounds
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.ingestor import DataIngestor


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    year = int(argv[1])
    rounds = [int(r) for r in argv[2:]] or None

    app = create_app()
    with app.app_context():
        for r in DataIngestor.ingest_season_telemetry(year, rounds):
            status = "ok " if r["ok"] else "ERR"
            detail = r.get("event") or r.get("error")
            print(f"[{status}] {year} R{r['round']:02d}  {detail}  "
                  f"drivers={r.get('drivers', '-')} laps={r.get('laps', '-')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
