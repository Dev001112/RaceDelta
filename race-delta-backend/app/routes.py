# app/routes.py

from flask import Blueprint, jsonify, request
import requests
from fastf1.ergast import Ergast
from scripts.team_meta import TEAM_META
from app.services.l1_season_fastf1 import get_driver_season_metrics
import requests
from datetime import datetime
from app.services.radar_normalization import normalize_radar
from flask import Blueprint
from scripts.driver_comparison_timeline import (
    build_driver_comparison_timeline
)
from app.services.f1_service import get_current_season_drivers
from app.services.driver_comparison_fastf1 import compare_drivers_season


from app.services.l1_season_fastf1 import (
    get_driver_season_metrics,
    get_teammate_code
)
from app.services.radar_normalization import normalize_radar


# ==================================================
# BLUEPRINT
# ==================================================

api_bp = Blueprint("api", __name__)

# ==================================================
# CONSTANTS & CLIENTS
# ==================================================

ergast = Ergast()
OPENF1_BASE = "https://api.openf1.org/v1"

TEAM_ID_TO_NAME = {
    "mercedes": "Mercedes",
    "ferrari": "Ferrari",
    "red_bull": "Red Bull",
    "mclaren": "McLaren",
    "aston_martin": "Aston Martin",
    "alpine": "Alpine",
    "williams": "Williams",
    "haas": "Haas",
    "rb": "RB",
    "sauber": "Sauber"
}

# ==================================================
# IMPORT EXTERNAL LOGIC (KEEP SEPARATE)
# ==================================================

from scripts.ergast_teams import get_current_f1_teams
from scripts.ergast_standings import (
    get_current_driver_standings,
    get_current_constructor_standings,
)
from scripts.team_meta import TEAM_META

# L1 Season Analytics service
from app.services.season_aggregator import build_l1_season

# ==================================================
# HELPERS
# ==================================================

def normalize_team(name: str) -> str:
    if not name:
        return ""
    return (
        name.lower()
        .replace("racing", "")
        .replace("formula one team", "")
        .replace("f1 team", "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )

# ==================================================
# DRIVERS LIST (OpenF1)
# ==================================================

@api_bp.route("/drivers", methods=["GET"])
def drivers_list():
    return jsonify(get_current_season_drivers())

# ==================================================
# TEAMS LIST
# ==================================================

@api_bp.route("/teams", methods=["GET"])
def teams_list():
    return jsonify(get_current_f1_teams())

# ==================================================
# DRIVER STANDINGS
# ==================================================

@api_bp.route("/standings/drivers", methods=["GET"])
def driver_standings():
    return jsonify(get_current_driver_standings())

# ==================================================
# CONSTRUCTOR STANDINGS
# ==================================================

@api_bp.route("/standings/constructors", methods=["GET"])
def constructor_standings():
    return jsonify(get_current_constructor_standings())

# ==================================================
# TEAM DETAIL PAGE
# ==================================================

@api_bp.route("/teams/<constructor_id>", methods=["GET"])
def team_detail(constructor_id):
    try:
        standings = ergast.get_constructor_standings(
            season="current",
            round="last"
        )

        if not standings.content or standings.content[0].empty:
            return jsonify({"error": "No constructor data"}), 404

        df_teams = standings.content[0]
        team_row = df_teams[df_teams["constructorId"] == constructor_id]

        if team_row.empty:
            return jsonify({"error": "Team not found"}), 404

        team = team_row.iloc[0]

        team_name = team.get("constructorName")
        nationality = team.get("constructorNationality")

        # ---- OpenF1 headshots (single request)
        try:
            openf1_resp = requests.get(f"{OPENF1_BASE}/drivers", timeout=10)
            openf1_data = openf1_resp.json()
            headshot_map = {
                d.get("name_acronym"): d.get("headshot_url")
                for d in openf1_data
                if d.get("name_acronym")
            }
        except Exception:
            headshot_map = {}

        # ---- Team drivers
        drivers = []
        seen = set()

        driver_standings = ergast.get_driver_standings(
            season="current",
            round="last"
        )

        if driver_standings.content and not driver_standings.content[0].empty:
            df_drivers = driver_standings.content[0]

            constructor_ids = df_drivers["constructorIds"].apply(
                lambda x: x[0] if isinstance(x, list) and x else None
            )

            team_drivers_df = df_drivers[constructor_ids == constructor_id]

            for _, row in team_drivers_df.iterrows():
                code = row.get("driverCode")

                if not code or code in seen:
                    continue
                seen.add(code)

                drivers.append({
                    "name": f"{row['givenName']} {row['familyName']}".strip(),
                    "driver_number": row.get("driverNumber"),
                    "headshot_url": headshot_map.get(code)
                })

                if len(drivers) == 2:
                    break

        meta = TEAM_META.get(constructor_id, {})

        return jsonify({
            "team_name": team_name,
            "constructor_id": constructor_id,
            "nationality": nationality,
            "position": int(team["position"]),
            "points": float(team["points"]),
            "wins": int(team["wins"]),
            "drivers": drivers,
            "team_principal": meta.get("principal"),
            "engine": meta.get("engine"),
            "car": meta.get("car")
        })

    except Exception as e:
        print("Team detail error:", e)
        return jsonify({"error": "Internal server error"}), 500

# ==================================================
# L1 – SEASON ANALYTICS (FASTF1)
# ==================================================

@api_bp.route("/l1/season", methods=["GET"])
def l1_season():
    driver_code = request.args.get("driver_code")
    season = request.args.get("season", type=int)

    if not driver_code or not season:
        return jsonify({"error": "driver_code and season required"}), 400

    # ==================================================
    # DRIVER METADATA (OpenF1 – identity only)
    # ==================================================
    driver_meta = {
        "code": driver_code,
        "name": None,
        "team": None,
        "image": None
    }

    try:
        resp = requests.get("https://api.openf1.org/v1/drivers", timeout=10)
        if resp.ok:
            for d in resp.json():
                if d.get("name_acronym") == driver_code:
                    driver_meta["name"] = (
                        f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                    )
                    driver_meta["team"] = d.get("team_name")
                    driver_meta["image"] = d.get("headshot_url")
                    break
    except Exception:
        pass

    # ==================================================
    # MAIN DRIVER – SEASON METRICS
    # ==================================================
    metrics = get_driver_season_metrics(season, driver_code)
    total_races = len(metrics["points_by_race"])
    radar = normalize_radar(metrics, total_races)

    # ==================================================
    # TEAMMATE OVERLAY (SAME CAR, SAME NORMALIZATION)
    # ==================================================
    teammate_block = None
    teammate_code = get_teammate_code(season, driver_code)

    if teammate_code:
        teammate_metrics = get_driver_season_metrics(season, teammate_code)
        teammate_radar = normalize_radar(
            teammate_metrics,
            len(teammate_metrics["points_by_race"])
        )

        # Optional: teammate identity (lightweight)
        teammate_meta = {
            "code": teammate_code,
            "name": None
        }

        try:
            if resp.ok:
                for d in resp.json():
                    if d.get("name_acronym") == teammate_code:
                        teammate_meta["name"] = (
                            f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                        )
                        break
        except Exception:
            pass

        teammate_block = {
            "driver": teammate_meta,
            "metrics": teammate_metrics,
            "radar": teammate_radar
        }

    # ==================================================
    # FINAL RESPONSE (L1 SCHEMA – FROZEN)
    # ==================================================
    return jsonify({
        "driver": driver_meta,
        "season": season,
        "metrics": metrics,
        "radar": radar,
        "teammate": teammate_block
    })

@api_bp.route("/compare/drivers", methods=["GET"])
def compare_drivers():
    driver1 = request.args.get("driver1")
    driver2 = request.args.get("driver2")
    season = request.args.get("season")

    if season == "current":
        season = datetime.now().year
    else:
        season = int(season)

    try:
        return jsonify(compare_drivers_season(driver1, driver2, season))
    except Exception as e:
        print("COMPARE ERROR:", e)
        return jsonify({"error": "Driver comparison failed"}), 500

@api_bp.route("/compare/drivers/timeline", methods=["GET"])
def compare_drivers_timeline():
    driver1 = request.args.get("driver1")
    driver2 = request.args.get("driver2")
    season = request.args.get("season", "current")

    if not driver1 or not driver2:
        return jsonify({"error": "driver1 and driver2 required"}), 400

    try:
        data = build_driver_comparison_timeline(
            driver1=driver1,
            driver2=driver2,
            season=season
        )
        return jsonify(data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500
