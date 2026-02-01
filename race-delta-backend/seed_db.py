from app import create_app, db
from app.services.ingestor import DataIngestor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = create_app()

with app.app_context():
    print("Starting Ingestion for 2025...")
    try:
        # verify connection
        print("Checking DB connection...")
        db.session.execute(db.text("SELECT 1"))
        print("DB Connection OK.")
        
        # Ingest Schedule
        print("Ingesting Schedule...")
        count = DataIngestor.ingest_season_schedule(2025)
        print(f"Ingested {count} races.")
        
        # Ingest One Race Results (e.g. Round 1) to test
        print("Ingesting Round 1 Results (if completed)...")
        results = DataIngestor.ingest_race_results(2025, 1)
        print(f"Ingested {results} results.")
        
    except Exception as e:
        print(f"ERROR: {e}")
