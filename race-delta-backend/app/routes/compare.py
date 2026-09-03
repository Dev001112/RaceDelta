# app/routes/compare.py
"""L1 season analytics, driver-vs-driver comparison, and the Compare Lab (feature store only)."""
from flask import jsonify, request, current_app

from scripts.driver_comparison_timeline import build_driver_comparison_timeline

from app.routes import api_bp
from app.routes._common import cached_openf1_get, resolve_request_season
from app.services import compare_lab, compare_verdict, track_map
from app.services.driver_comparison_fastf1 import compare_drivers_season
from app.services.f1_service import get_season_drivers
from app.services.l1_season_fastf1 import get_driver_season_metrics, get_teammate_code
from app.services.radar_normalization import normalize_radar


@api_bp.route("/l1/season", methods=["GET"])
def l1_season():
    driver_code = request.args.get("driver_code")
    season = request.args.get("season", type=int)

    if not driver_code or not season:
        return jsonify({"error": "driver_code and season required"}), 400

    # ---- driver metadata (OpenF1 - identity only)
    driver_meta = {
        "code": driver_code,
        "name": None,
        "team": None,
        "image": None
    }

    try:
        drivers_data = get_season_drivers(year=season)
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

    # ---- main driver: season metrics
    metrics = get_driver_season_metrics(season, driver_code)
    total_races = len(metrics["points_by_race"])
    radar = normalize_radar(metrics, total_races)

    # ---- teammate overlay (same car, same normalization)
    teammate_block = None
    teammate_code = get_teammate_code(season, driver_code)

    if teammate_code:
        teammate_metrics = get_driver_season_metrics(season, teammate_code)
        teammate_radar = normalize_radar(
            teammate_metrics,
            len(teammate_metrics["points_by_race"])
        )

        teammate_meta = {
            "code": teammate_code,
            "name": None
        }

        try:
            drivers = cached_openf1_get("drivers") or []
            for d in drivers:
                if d.get("name_acronym") == teammate_code:
                    teammate_meta["name"] = (
                        f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                    )
                    break
        except Exception as e:
            current_app.logger.warning(f"Teammate name lookup failed for {teammate_code}: {e}")

        teammate_block = {
            "driver": teammate_meta,
            "metrics": teammate_metrics,
            "radar": teammate_radar
        }

    # ---- final response (L1 schema - frozen)
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


# ---------------------------------------------------------------- Compare Lab
@api_bp.route("/compare/races", methods=["GET"])
def compare_races():
    """Every ingested race with the metadata the Compare page filters on."""
    return jsonify({"races": compare_lab.list_races()})


@api_bp.route("/compare/drivers/races", methods=["GET"])
def compare_drivers_on_races():
    """?driver1&driver2&races=2026-1,2025-8 -> per-race lines plus aggregates."""
    d1, d2, spec = request.args.get("driver1"), request.args.get("driver2"), request.args.get("races", "")
    if not d1 or not d2 or not spec:
        return jsonify({"error": "driver1, driver2 and races are required"}), 400
    try:
        races = [tuple(int(x) for x in item.split("-")) for item in spec.split(",") if item]
    except ValueError:
        return jsonify({"error": "races must look like 2026-1,2025-8"}), 400
    return jsonify(compare_lab.compare_on_races(d1, d2, races))


def _no_store_while_pending(payload):
    """A 'still building' answer must not sit in the browser cache, or the page's polling never sees the result."""
    resp = jsonify(payload)
    if payload.get("pending"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@api_bp.route("/compare/verdict", methods=["GET"])
def compare_verdict_route():
    """?driver1&driver2&races=2026-1,2025-8[&context=] -> who is better and how (rules, model prose when configured)."""
    d1, d2, spec = request.args.get("driver1"), request.args.get("driver2"), request.args.get("races", "")
    context = (request.args.get("context") or "")[:80]
    if not d1 or not d2 or not spec:
        return jsonify({"error": "driver1, driver2 and races are required"}), 400
    try:
        races = [tuple(int(x) for x in item.split("-")) for item in spec.split(",") if item]
    except ValueError:
        return jsonify({"error": "races must look like 2026-1,2025-8"}), 400
    return _no_store_while_pending(compare_verdict.for_races(d1, d2, races, context))


@api_bp.route("/compare/track-map", methods=["GET"])
def compare_track_map():
    """?rounds=2026-9,2025-12 (visits of one circuit, latest first) -> outline split into sectors,
    {'pending': true} while it is first built, or 'unavailable' when no visit's telemetry can be read."""
    spec = request.args.get("rounds", "")
    try:
        candidates = [tuple(int(x) for x in item.split("-")) for item in spec.split(",") if item]
    except ValueError:
        candidates = []
    if not candidates:
        return jsonify({"error": "rounds must look like 2026-9,2025-12"}), 400
    return _no_store_while_pending(track_map.get(candidates))


@api_bp.route("/compare/drivers/laps", methods=["GET"])
def compare_drivers_laps():
    d1, d2 = request.args.get("driver1"), request.args.get("driver2")
    season, round_num = request.args.get("season", type=int), request.args.get("round", type=int)
    if not d1 or not d2 or not season or not round_num:
        return jsonify({"error": "driver1, driver2, season and round are required"}), 400
    return jsonify(compare_lab.laps_for_race(d1, d2, season, round_num))
