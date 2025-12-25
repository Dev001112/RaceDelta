# create_tables_final.py
import sys
from pathlib import Path
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the app factory and the db instance
from app import create_app, db

# **Important**: import the module that defines the models so SQLAlchemy metadata is populated.
# This file should be at D:\RaceDelta\race-delta-backend\models.py
import models  # ensures model classes (Driver, Constructor, etc.) are registered

app = create_app()

# Initialize db with app if not already done in create_app()
if not getattr(app, "extensions", None) or "sqlalchemy" not in app.extensions:
    db.init_app(app)

with app.app_context():
    print("Creating tables (final) in:", app.config.get("SQLALCHEMY_DATABASE_URI"))
    # This will create all tables based on models' metadata
    db.create_all()

    # Verify creation: list all non-system tables
    q = text("""
      SELECT table_schema, table_name
      FROM information_schema.tables
      WHERE table_schema NOT IN ('pg_catalog','information_schema')
      ORDER BY table_schema, table_name;
    """)
    rows = db.session.execute(q).fetchall()
    if not rows:
        print("No user tables found after create_all() (0 rows).")
    else:
        print("Tables created / existing:")
        for schema, name in rows:
            print(f" - {schema}.{name}")

    cnt = db.session.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar_one()
    print("public table count:", cnt)
