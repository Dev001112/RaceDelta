# app/routes/admin.py
"""Data ingestion triggers. All require X-Admin-Token (see _common.admin_only)."""
from flask import jsonify

from app.routes import api_bp
from app.routes._common import admin_only


@api_bp.route("/admin/ingest/schedule/<int:year>", methods=["POST"])
@admin_only
def ingest_schedule(year):
    """Trigger schedule ingestion for a season"""
    try:
        from app.services.ingestor import DataIngestor
        count = DataIngestor.ingest_season_schedule(year)
        return jsonify({"message": f"Ingested {count} races for {year}", "success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/ingest/results/<int:year>/<int:round_num>", methods=["POST"])
@admin_only
def ingest_results(year, round_num):
    """Trigger result ingestion for a specific race"""
    try:
        from app.services.ingestor import DataIngestor
        count = DataIngestor.ingest_race_results(year, round_num)
        return jsonify({"message": f"Ingested {count} results", "success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/ingest/telemetry/<int:year>/<int:round_num>", methods=["POST"])
@admin_only
def ingest_telemetry(year, round_num):
    """(Re)ingest laps, stints and features for one race."""
    try:
        from app.services.ingestor import DataIngestor
        return jsonify({"success": True, **DataIngestor.ingest_race_telemetry(year, round_num)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/ingest/telemetry/<int:year>", methods=["POST"])
@admin_only
def ingest_telemetry_season(year):
    """Backfill laps, stints and features for every completed round of a season."""
    try:
        from app.services.ingestor import DataIngestor
        report = DataIngestor.ingest_season_telemetry(year)
        return jsonify({"success": all(r["ok"] for r in report), "season": year, "rounds": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
