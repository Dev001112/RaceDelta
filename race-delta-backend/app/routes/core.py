# app/routes/core.py
"""Health, seasons, driver roster, teams, standings, team detail."""
from flask import jsonify, request, current_app

from scripts.team_meta import get_team_meta
from scripts.ergast_teams import get_f1_teams
from scripts.ergast_standings import get_driver_standings, get_constructor_standings

from app.routes import api_bp
from app.routes._common import cached_openf1_get, resolve_request_season
from app.services.f1_service import get_season_drivers, normalize_team
from app.utils.season_resolver import resolve_seasons


@api_bp.route("/", methods=["GET"])
@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "RaceDelta API",
        "version": "1.0.0"
    })


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
            first_name = (driver.get("first_name") or "").strip()
            last_name = (driver.get("last_name") or "").strip()
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


@api_bp.route("/teams", methods=["GET"])
def teams_list():
    season = request.args.get("season")
    season = resolve_request_season(season)
    return jsonify(get_f1_teams(season=season))


@api_bp.route("/standings/drivers", methods=["GET"])
def driver_standings():
    season = request.args.get("season")
    season = resolve_request_season(season)
    return jsonify(get_driver_standings(season=season))


@api_bp.route("/standings/constructors", methods=["GET"])
def constructor_standings():
    season = request.args.get("season")
    season = resolve_request_season(season)
    return jsonify(get_constructor_standings(season=season))


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
