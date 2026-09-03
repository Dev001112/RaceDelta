# app/routes/lab.py
"""Phases 2-5: feature store, driver intelligence, Strategy Lab, AI Race Analyst."""
import time
from collections import defaultdict, deque

from flask import jsonify, request, current_app

from app.routes import api_bp
from app.services import race_analyst, strategy_lab
from app.services.driver_intelligence import rating_for_season, dna_for_season, clusters_for_season
from app.services.feature_store import ensure_race_features, features_for_race, features_for_driver


# ---------------------------------------------------------------- Phase 2: feature store
@api_bp.route("/features/race", methods=["GET"])
def features_race():
    """Per-driver engineered features for one race. Ingests from FastF1 on first request."""
    season = request.args.get("season", type=int)
    round_num = request.args.get("round", type=int)
    if not season or not round_num:
        return jsonify({"error": "season and round are required"}), 400
    try:
        rs = ensure_race_features(season, round_num)
        rows = features_for_race(season, round_num)
        return jsonify({"season": season, "round": round_num,
                        "event": rs.event_name if rs else None,
                        "count": len(rows), "features": rows, "source": "feature_store"})
    except Exception as e:
        current_app.logger.error(f"features_race failed: {e}", exc_info=True)
        return jsonify({"error": "Failed to build race features", "message": str(e)}), 500


@api_bp.route("/features/driver", methods=["GET"])
def features_driver():
    """All ingested per-race feature rows for a driver in a season, plus season aggregates."""
    driver_code = request.args.get("driver_code")
    season = request.args.get("season", type=int)
    if not driver_code or not season:
        return jsonify({"error": "driver_code and season are required"}), 400
    try:
        return jsonify(features_for_driver(driver_code, season))
    except Exception as e:
        current_app.logger.error(f"features_driver failed: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch driver features", "message": str(e)}), 500


# ---------------------------------------------------------------- Phase 3: driver intelligence
@api_bp.route("/ai/rating", methods=["GET"])
def ai_rating():
    """Module 1: AI Driver Rating for a season, ranked, with 0-100 component scores."""
    season = request.args.get("season", type=int)
    if not season:
        return jsonify({"error": "season is required"}), 400
    try:
        return jsonify(rating_for_season(season))
    except Exception as e:
        current_app.logger.error(f"ai_rating failed: {e}", exc_info=True)
        return jsonify({"error": "Failed to compute driver rating", "message": str(e)}), 500


@api_bp.route("/ai/dna", methods=["GET"])
def ai_dna():
    """Module 2: Driver DNA vector, nearest drivers by cosine similarity, PCA coordinates."""
    season = request.args.get("season", type=int)
    driver_code = request.args.get("driver_code")
    k = request.args.get("k", default=5, type=int)
    if not season or not driver_code:
        return jsonify({"error": "season and driver_code are required"}), 400
    try:
        return jsonify(dna_for_season(season, driver_code, k))
    except ValueError as e:
        return jsonify({"error": "Driver not found in feature store", "message": str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"ai_dna failed: {e}", exc_info=True)
        return jsonify({"error": "Failed to compute driver DNA", "message": str(e)}), 500


@api_bp.route("/ai/clusters", methods=["GET"])
def ai_clusters():
    """Module 3: driving-style clusters (kmeans | dbscan | hierarchical) on a 2-D PCA map."""
    season = request.args.get("season", type=int)
    if not season:
        return jsonify({"error": "season is required"}), 400
    method = request.args.get("method", default="kmeans")
    k = request.args.get("k", default=4, type=int)
    eps = request.args.get("eps", default=1.5, type=float)
    min_samples = request.args.get("min_samples", default=2, type=int)
    try:
        return jsonify(clusters_for_season(season, method, k, eps, min_samples))
    except ValueError as e:
        return jsonify({"error": "Invalid input", "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"ai_clusters failed: {e}", exc_info=True)
        return jsonify({"error": "Failed to compute clusters", "message": str(e)}), 500


# ---------------------------------------------------------------- Phase 4: Strategy Lab
def _strategy_error(e):
    if isinstance(e, ValueError):
        return jsonify({"error": "Invalid input", "message": str(e)}), 400
    current_app.logger.error(f"strategy lab failed: {e}", exc_info=True)
    return jsonify({"error": "Strategy Lab failed", "message": str(e)}), 500


@api_bp.route("/strategy/races", methods=["GET"])
def strategy_races():
    """Rounds available in the feature store for a season."""
    season = request.args.get("season", type=int)
    if not season:
        return jsonify({"error": "season is required"}), 400
    try:
        return jsonify({"season": season, "races": strategy_lab.list_races(season)})
    except Exception as e:
        return _strategy_error(e)


@api_bp.route("/strategy/race", methods=["GET"])
def strategy_race():
    """Race context: drivers and their real strategies, compounds, pit loss, flags, pace model."""
    season = request.args.get("season", type=int)
    round_num = request.args.get("round", type=int)
    if not season or not round_num:
        return jsonify({"error": "season and round are required"}), 400
    try:
        return jsonify(strategy_lab.race_overview(strategy_lab.load_context(season, round_num)))
    except Exception as e:
        return _strategy_error(e)


@api_bp.route("/strategy/replay", methods=["GET"])
def strategy_replay():
    """Component A: race state at a lap, the team's actual decision, the AI recommendation, full timeline."""
    season = request.args.get("season", type=int)
    round_num = request.args.get("round", type=int)
    driver_code = request.args.get("driver_code")
    lap = request.args.get("lap", type=int)
    if not season or not round_num or not driver_code or not lap:
        return jsonify({"error": "season, round, driver_code and lap are required"}), 400
    try:
        ctx = strategy_lab.load_context(season, round_num)
        return jsonify(strategy_lab.replay(ctx, driver_code.upper(), lap))
    except Exception as e:
        return _strategy_error(e)


@api_bp.route("/strategy/simulate", methods=["POST"])
def strategy_simulate():
    """Component B: what-if strategy simulation.
    Body: {season, round, driver_code, pit_stops:[{lap, compound}], start_compound?, safety_car?:{lap, laps}, weather?}"""
    body = request.get_json(silent=True) or {}
    try:
        season, round_num = int(body.get("season") or 0), int(body.get("round") or 0)
        driver_code = str(body.get("driver_code") or "").upper()
        if not season or not round_num or not driver_code:
            return jsonify({"error": "season, round and driver_code are required"}), 400
        ctx = strategy_lab.load_context(season, round_num)
        return jsonify(strategy_lab.simulate(
            ctx, driver_code, body.get("pit_stops") or [],
            start_compound=body.get("start_compound"),
            safety_car=body.get("safety_car"), weather=body.get("weather")))
    except Exception as e:
        return _strategy_error(e)


# ---------------------------------------------------------------- Phase 5: AI Race Analyst
ASK_LIMIT, ASK_WINDOW = 10, 60          # questions per client IP per minute: each one spends model quota
_asks = defaultdict(deque)               # ponytail: in-memory, per-process; use flask-limiter + Redis behind several workers


def _over_ask_limit(ip: str) -> bool:
    q, now = _asks[ip], time.time()
    while q and q[0] < now - ASK_WINDOW:
        q.popleft()
    if len(q) >= ASK_LIMIT:
        return True
    q.append(now)
    return False


@api_bp.route("/analyst/status", methods=["GET"])
def analyst_status():
    """Which model backs the analyst (or offline intent mode), plus its tools."""
    return jsonify(race_analyst.status())


@api_bp.route("/analyst/ask", methods=["POST"])
def analyst_ask():
    """Body: {question, season, round?, history?:[{role, content}]} -> {answer, mode, model, tools_used, usage}"""
    if _over_ask_limit(request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()):
        return jsonify({"error": "Too many questions", "message": f"Limit is {ASK_LIMIT} per minute. Try again shortly."}), 429
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    season = body.get("season")
    if not question or not season:
        return jsonify({"error": "question and season are required"}), 400
    try:
        return jsonify(race_analyst.ask(question, int(season), body.get("round"), body.get("history")))
    except race_analyst.AnalystError as e:
        return jsonify({"error": "Analyst unavailable", "message": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": "Invalid input", "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"analyst_ask failed: {e}", exc_info=True)
        return jsonify({"error": "Analyst failed", "message": str(e)}), 500
