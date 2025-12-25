# app/routes/l1_season.py

from flask import Blueprint, request, jsonify
from app.services.season_aggregator import build_l1_season

l1_bp = Blueprint("l1", __name__)


@l1_bp.route("/l1/season", methods=["GET"])
def l1_season():
    driver_code = request.args.get("driver_code")
    season = request.args.get("season", type=int)

    if not driver_code or not season:
        return jsonify({"error": "driver_code and season are required"}), 400

    data = build_l1_season(driver_code, season)
    return jsonify(data)
