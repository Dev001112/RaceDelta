# app/routes.py

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import requests
from fastf1.ergast import Ergast

from scripts.team_meta import get_team_meta
from scripts.driver_comparison_timeline import build_driver_comparison_timeline
from scripts.ergast_teams import get_f1_teams
from scripts.ergast_standings import (
    get_driver_standings,
    get_constructor_standings,
)

from app.services.f1_service import get_season_drivers, normalize_team
from app.services import cache_store
from app.services.driver_comparison_fastf1 import compare_drivers_season
from app.services.l1_season_fastf1 import (
    get_driver_season_metrics,
    get_teammate_code
)
from app.services.radar_normalization import normalize_radar
from app.services.season_aggregator import build_l1_season
from app.utils.season_resolver import resolve_seasons, get_season_for_drivers

# ==================================================
# BLUEPRINT
# ==================================================

api_bp = Blueprint("api", __name__)

# ==================================================
# CONSTANTS & CLIENTS
# ==================================================

ergast = Ergast()

# ==================================================
# HELPERS
# ==================================================

def get_openf1_base():
    """Get OpenF1 API base URL from Flask config"""
    return current_app.config.get("OPENF1_BASE", "https://api.openf1.org/v1")


def cached_openf1_get(path, params=None, ttl=60 * 60 * 6):
    openf1_base = get_openf1_base()
    timeout = min(current_app.config.get("OPENF1_TIMEOUT", 10), 4)
    url = f"{openf1_base.rstrip('/')}/{path.lstrip('/')}"
    normalized_params = dict(sorted((params or {}).items()))
    cache_key = f"{url}:{normalized_params}"
    cached = cache_store.get("openf1", cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException:
        return None

    if not resp.ok:
        return None
    data = resp.json()
    cache_store.set("openf1", cache_key, data, ttl)
    return data


def resolve_request_season(raw_season):
    if not raw_season or raw_season == "current":
        return resolve_seasons()["display_season"]
    return int(raw_season)

# ==================================================
# HEALTH CHECK
# ==================================================

@api_bp.route("/", methods=["GET"])
@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "RaceDelta API",
        "version": "1.0.0"
    })

# ==================================================
# SEASONS ENDPOINT
# ==================================================

@api_bp.route("/seasons", methods=["GET"])
def seasons_info():
    """
    Get season resolution information.
    Returns calendar_season, active_season, last_completed_season,
    is_offseason, and a frontend-ready dropdown array.
    """
    try:
        seasons_data = resolve_seasons()
        return jsonify(seasons_data)
    except Exception as e:
        logger = current_app.logger
        logger.error(f"Error resolving seasons: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to resolve seasons",
            "message": str(e)
        }), 500

# ==================================================
# DRIVERS LIST (OpenF1 - Roster-based)
# ==================================================

@api_bp.route("/drivers", methods=["GET"])
def drivers_list():
    """
    Get current season drivers from OpenF1 driver index (roster-based).
    Does NOT depend on completed races.
    Includes season and is_offseason metadata.
    """
    try:
        # Get season information
        seasons_data = resolve_seasons()
        requested_season = request.args.get("season")
        
        season_for_drivers = resolve_request_season(requested_season)
            
        # If requesting a historical season that is not the current calendar or display season,
        # skip OpenF1's current roster index and use the historical service directly.
        is_historical = season_for_drivers not in [seasons_data["calendar_season"], seasons_data["display_season"]]
        if is_historical:
            # Use fallback system for historical data
            drivers_data = get_season_drivers(year=season_for_drivers)
            drivers_data["season"] = season_for_drivers
            drivers_data["is_offseason"] = False
            return jsonify(drivers_data)
        
        # Get drivers from OpenF1 (roster-based, not race-dependent)
        # Fetch drivers from OpenF1 driver index
        openf1_drivers = cached_openf1_get("drivers")
        
        if openf1_drivers is None:
            # Fallback to existing service if OpenF1 fails
            drivers_data = get_season_drivers(year=int(season_for_drivers))
            drivers_data["season"] = season_for_drivers
            drivers_data["is_offseason"] = seasons_data["is_offseason"]
            return jsonify(drivers_data)
        
        # Filter and normalize drivers
        # OpenF1 driver index contains current season roster
        # We filter to ensure we have valid driver data
        drivers = []
        seen_codes = set()
        
        for driver in openf1_drivers:
            code = driver.get("name_acronym")
            if not code or code in seen_codes:
                continue
            
            # Only include drivers with essential info
            first_name = driver.get("first_name", "").strip()
            last_name = driver.get("last_name", "").strip()
            if not first_name or not last_name:
                continue
            
            seen_codes.add(code)
            
            drivers.append({
                "driver_code": code,
                "driver_name": f"{first_name} {last_name}".strip(),
                "driver_number": driver.get("driver_number"),
                "team": normalize_team(driver.get("team_name", "")),
                "country_code": driver.get("country_code", ""),
                "headshot_url": driver.get("headshot_url"),
            })
        
        # Sort by driver number (nulls last)
        drivers.sort(key=lambda d: d["driver_number"] if d["driver_number"] is not None else 999)
        
        if not drivers:
            raise ValueError("OpenF1 returned empty roster")
        
        return jsonify({
            "source": "openf1_roster",
            "season": season_for_drivers,
            "is_offseason": seasons_data["is_offseason"],
            "active_season": seasons_data["active_season"],
            "last_completed_season": seasons_data["last_completed_season"],
            "count": len(drivers),
            "drivers": drivers
        })
        
    except Exception as e:
        logger = current_app.logger
        logger.error(f"Error fetching drivers: {e}", exc_info=True)
        
        # Fallback to existing service
        try:
            drivers_data = get_season_drivers(year=season_for_drivers)
            
            # If the fallback is also empty (e.g. because there are no completed races yet),
            # and we are in the current or future season, use the previous season's roster.
            if not drivers_data.get("drivers") and season_for_drivers >= seasons_data["calendar_season"]:
                drivers_data = get_season_drivers(year=season_for_drivers - 1)
                
            drivers_data["season"] = season_for_drivers
            drivers_data["is_offseason"] = seasons_data["is_offseason"]
            return jsonify(drivers_data)
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}", exc_info=True)
            return jsonify({
                "error": "Failed to fetch drivers",
                "message": str(fallback_error),
                "source": "error",
                "drivers": []
            }), 500

# ==================================================
# TEAMS LIST
# ==================================================

@api_bp.route("/teams", methods=["GET"])
def teams_list():
    season = request.args.get("season")
    season = resolve_request_season(season)
    return jsonify(get_f1_teams(season=season))

# ==================================================
# DRIVER STANDINGS
# ==================================================

@api_bp.route("/standings/drivers", methods=["GET"])
def driver_standings():
    season = request.args.get("season")
    season = resolve_request_season(season)
    return jsonify(get_driver_standings(season=season))

# ==================================================
# CONSTRUCTOR STANDINGS
# ==================================================

@api_bp.route("/standings/constructors", methods=["GET"])
def constructor_standings():
    season = request.args.get("season")
    season = resolve_request_season(season)
    return jsonify(get_constructor_standings(season=season))

# ==================================================
# TEAM DETAIL PAGE
# ==================================================

@api_bp.route("/teams/<constructor_id>", methods=["GET"])
def team_detail(constructor_id):
    try:
        seasons_data = resolve_seasons()
        requested_season = request.args.get("season")
        if not requested_season:
            season = seasons_data["display_season"]
        else:
            season = int(requested_season)
        # Load teams list securely with OpenF1 fallback logic automatically
        from scripts.ergast_teams import get_f1_teams
        teams_list = get_f1_teams(season=season)
        
        team = next((t for t in teams_list if t.get("constructor_id") == constructor_id), None)
        
        if not team:
            return jsonify({"error": "Team not found"}), 404

        team_name = team.get("team_name")
        nationality = team.get("nationality")

        # ---- Headshot Logic & Driver Loading (Unified)
        # Use our robust service that handles caching and fallbacks (via OpenF1/FastF1 roster)
        headshot_map = {}
        all_drivers_data = {}
        try:
            target_year = season
            # Fetch all drivers for the specific season using our service
            all_drivers_data = get_season_drivers(year=target_year)
            
            # Create a map: Code -> Headshot URL
            if "drivers" in all_drivers_data:
                 for d in all_drivers_data["drivers"]:
                     c = d.get("driver_code") or d.get("code")
                     url = d.get("headshot_url")
                     if c and url:
                         headshot_map[c] = url
                         
        except Exception as e:
             current_app.logger.warning(f"Failed to fetch headshots via service: {e}")

        # ---- Team drivers
        drivers = []
        seen = set()

        if "drivers" in all_drivers_data:
            for row in all_drivers_data["drivers"]:
                team_check = row.get("team", "")
                
                # Match driver's team to the current team requested
                if team_check.lower() == team_name.lower():
                    code = row.get("driver_code") or row.get("code", "")
                    
                    if not code or code in seen:
                        continue
                    seen.add(code)
                    
                    drivers.append({
                        "name": row.get("driver_name") or row.get("full_name", ""),
                        "driver_number": row.get("driver_number"),
                        "headshot_url": headshot_map.get(code)
                    })
                    
                    if len(drivers) == 2:
                        break

        meta = get_team_meta(constructor_id, season)

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
            "car": meta.get("car"),
            "car_image": meta.get("car_image")
        })

    except Exception as e:
        logger = current_app.logger
        logger.error(f"Team detail error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500

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
        # Use robust service to find driver
        # We need to find the driver in the resolved season context
        # First try the requested season, if that fails, maybe try current?
        # Actually, get_season_drivers handles logic.
        
        # We need to look up this specific driver_code in the season list
        drivers_data = get_season_drivers(year=season)
        
        # If not allowed or empty, try default season?
        # get_season_drivers usually handles fallbacks if configured, but let's just search
        
        found_driver = None
        if "drivers" in drivers_data:
            for d in drivers_data["drivers"]:
                if d.get("driver_code") == driver_code:
                    found_driver = d
                    break
        
        if found_driver:
             driver_meta["name"] = found_driver.get("driver_name")
             driver_meta["team"] = found_driver.get("team")
             driver_meta["image"] = found_driver.get("headshot_url")
             
    except Exception as e:
        current_app.logger.warning(f"Metadata lookup failed in l1_season: {e}")

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
            drivers = cached_openf1_get("drivers") or []
            if drivers:
                for d in drivers:
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

    if not driver1 or not driver2:
        return jsonify({"error": "driver1 and driver2 required"}), 400

    season = resolve_request_season(season)

    try:
        return jsonify(compare_drivers_season(driver1, driver2, season))
    except ValueError as e:
        return jsonify({"error": "Invalid input", "message": str(e)}), 400
    except Exception as e:
        logger = current_app.logger
        logger.error(f"Driver comparison failed: {e}", exc_info=True)
        return jsonify({"error": "Driver comparison failed", "message": str(e)}), 500

@api_bp.route("/compare/drivers/timeline", methods=["GET"])
def compare_drivers_timeline():
    driver1 = request.args.get("driver1")
    driver2 = request.args.get("driver2")
    season = request.args.get("season", "current")

    season = resolve_request_season(season)

    if not driver1 or not driver2:
        return jsonify({"error": "driver1 and driver2 required"}), 400

    try:
        data = build_driver_comparison_timeline(
            driver1=driver1,
            driver2=driver2,
            season=season
        )
        return jsonify(data)

    except ValueError as e:
        return jsonify({
            "error": "Invalid input",
            "message": str(e)
        }), 400
    except Exception as e:
        logger = current_app.logger
        logger.error(f"Driver comparison timeline failed: {e}", exc_info=True)
        return jsonify({
            "error": "Driver comparison timeline failed",
            "message": str(e),
            "type": type(e).__name__
        }), 500

# ==================================================
# DATA INGESTION (ADMIN)
# ==================================================

@api_bp.route("/admin/ingest/schedule/<int:year>", methods=["POST"])
def ingest_schedule(year):
    """Trigger schedule ingestion for a season"""
    try:
        from app.services.ingestor import DataIngestor
        
        count = DataIngestor.ingest_season_schedule(year)
        return jsonify({"message": f"Ingested {count} races for {year}", "success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/admin/ingest/results/<int:year>/<int:round_num>", methods=["POST"])
def ingest_results(year, round_num):
    """Trigger result ingestion for a specific race"""
    try:
        from app.services.ingestor import DataIngestor
        
        count = DataIngestor.ingest_race_results(year, round_num)
        return jsonify({"message": f"Ingested {count} results", "success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

