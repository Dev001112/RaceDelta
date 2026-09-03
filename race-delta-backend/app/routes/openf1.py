# app/routes/openf1.py
"""OpenF1 pass-throughs, the enriched meetings list, and per-race analytics."""
from datetime import datetime

from flask import jsonify, request, current_app

from app.routes import api_bp
from app.routes._common import cached_openf1_get
from app.services.f1_service import get_season_drivers, normalize_team


def _race_session_key(meeting_key):
    """session_key of the Grand Prix itself. OpenF1 gives the Sprint session_type "Race" too;
    only session_name tells them apart."""
    sessions = cached_openf1_get("sessions", params={"meeting_key": meeting_key}) or []
    race = next((s for s in sessions if (s.get("session_name") or "").lower() == "race"), None)
    return race.get("session_key") if race else None


def _meetings(year):
    """Grand Prix weekends of a season in calendar order, numbered as championship rounds.
    Testing and cancelled meetings are dropped *before* numbering so the round numbers line up
    with FastF1's RoundNumber, which the feature store / Strategy Lab / Analyst use."""
    params = {"year": year} if year else {}
    meetings = cached_openf1_get("meetings", params=params) or []
    meetings = [m for m in meetings
                if "test" not in m.get("meeting_name", "").lower() and not m.get("is_cancelled")]
    meetings = sorted(meetings, key=lambda x: x.get("date_start", ""))

    enriched = []
    for i, m in enumerate(meetings, 1):
        m_key = m.get("meeting_key")
        winner, race_key, is_completed = None, None, False

        date_end_str = m.get("date_end")
        if date_end_str:
            try:
                date_end = datetime.fromisoformat(date_end_str.replace("Z", "+00:00"))
                is_completed = date_end.timestamp() < datetime.now(date_end.tzinfo).timestamp()
            except ValueError as e:
                current_app.logger.warning("meeting %s has unparseable date_end %r: %s", m_key, date_end_str, e)

        if is_completed:
            race_key = _race_session_key(m_key)
            if race_key:
                results = cached_openf1_get("session_result", params={"session_key": race_key}) or []
                results = sorted(results, key=lambda x: int(x.get("position") or 999))
                if results and int(results[0].get("position") or 999) == 1:
                    winner_num = results[0].get("driver_number")
                    drivers = cached_openf1_get("drivers", params={"session_key": race_key}) or []
                    winner = next((d.get("name_acronym") for d in drivers if d.get("driver_number") == winner_num), None)

        m_copy = dict(m)
        m_copy["round"] = i
        m_copy["winner"] = winner or "-"
        m_copy["is_completed"] = is_completed
        m_copy["race_session_key"] = race_key
        m_copy["race"] = m.get("meeting_name")
        m_copy["circuit"] = m.get("circuit_short_name")
        m_copy["date"] = m.get("date_start")
        enriched.append(m_copy)
    return enriched


@api_bp.route("/meetings", methods=["GET"])
def get_meetings_route():
    return jsonify(_meetings(request.args.get("year", type=int)))


@api_bp.route("/race/<int:season>/<int:round_num>", methods=["GET"])
def race_page(season, round_num):
    """Everything the race page needs in one round trip: the meeting, its race session and the analytics."""
    meeting = next((m for m in _meetings(season) if m["round"] == round_num), None)
    if not meeting:
        return jsonify({"error": "Round not found", "message": f"No round {round_num} in {season}."}), 404
    session_key = meeting.get("race_session_key") or _race_session_key(meeting.get("meeting_key"))
    if not session_key:
        return jsonify({"error": "No race session", "message": f"{meeting['meeting_name']} has no completed race session yet."}), 404
    try:
        analytics = _race_analytics(session_key)
    except Exception as e:
        current_app.logger.error(f"Race analytics failed: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500
    return jsonify({"meeting": meeting, "session_key": session_key, "analytics": analytics})


@api_bp.route("/sessions", methods=["GET"])
def get_sessions_route():
    meeting_key = request.args.get("meeting_key")
    params = {"meeting_key": meeting_key} if meeting_key else {}
    data = cached_openf1_get("sessions", params=params)
    return jsonify(data or [])


@api_bp.route("/laps", methods=["GET"])
def get_laps_route():
    session_key = request.args.get("session_key")
    driver_number = request.args.get("driver_number")
    params = {}
    if session_key:
        params["session_key"] = session_key
    if driver_number:
        params["driver_number"] = driver_number
    data = cached_openf1_get("laps", params=params)
    return jsonify(data or [])


@api_bp.route("/position", methods=["GET"])
def get_position_route():
    session_key = request.args.get("session_key")
    driver_number = request.args.get("driver_number")
    params = {}
    if session_key:
        params["session_key"] = session_key
    if driver_number:
        params["driver_number"] = driver_number
    data = cached_openf1_get("position", params=params)
    return jsonify(data or [])


@api_bp.route("/weather", methods=["GET"])
def get_weather_route():
    session_key = request.args.get("session_key")
    if not session_key:
        return jsonify({"error": "session_key is required"}), 400
    data = cached_openf1_get("weather", params={"session_key": session_key})
    return jsonify(data or [])


@api_bp.route("/stints", methods=["GET"])
def get_stints_route():
    session_key = request.args.get("session_key")
    if not session_key:
        return jsonify({"error": "session_key is required"}), 400
    data = cached_openf1_get("stints", params={"session_key": session_key})
    return jsonify(data or [])


@api_bp.route("/session_results", methods=["GET"])
def get_session_results_route():
    session_key = request.args.get("session_key")
    if not session_key:
        return jsonify({"error": "session_key is required"}), 400
    data = cached_openf1_get("session_result", params={"session_key": session_key})
    return jsonify(data or [])


@api_bp.route("/race_analytics/<int:session_key>", methods=["GET"])
def get_race_analytics(session_key):
    try:
        return jsonify(_race_analytics(session_key))
    except Exception as e:
        current_app.logger.error(f"Race analytics failed: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


def _race_analytics(session_key):
    # 1. Fetch weather
    weather_data = cached_openf1_get("weather", params={"session_key": session_key}) or []
    avg_air_temp = 0.0
    avg_track_temp = 0.0
    avg_humidity = 0.0
    rainfall_detected = False

    if weather_data:
        air_temps = [w["air_temperature"] for w in weather_data if w.get("air_temperature") is not None]
        track_temps = [w["track_temperature"] for w in weather_data if w.get("track_temperature") is not None]
        humidities = [w["humidity"] for w in weather_data if w.get("humidity") is not None]
        rains = [w["rainfall"] for w in weather_data if w.get("rainfall") is not None]

        avg_air_temp = round(sum(air_temps) / len(air_temps), 1) if air_temps else 0.0
        avg_track_temp = round(sum(track_temps) / len(track_temps), 1) if track_temps else 0.0
        avg_humidity = round(sum(humidities) / len(humidities), 1) if humidities else 0.0
        rainfall_detected = any(r > 0 for r in rains) if rains else False

    # 2. Fetch tyre stints
    stints_data = cached_openf1_get("stints", params={"session_key": session_key}) or []
    stints_by_driver = {}
    for s in stints_data:
        dn = str(s["driver_number"])
        stints_by_driver.setdefault(dn, []).append({
            "stint_number": s.get("stint_number"),
            "compound": s.get("compound"),
            "lap_start": s.get("lap_start"),
            "lap_end": s.get("lap_end"),
            "tyre_age_at_start": s.get("tyre_age_at_start")
        })

    # 3. Fetch session results
    results_data = cached_openf1_get("session_result", params={"session_key": session_key}) or []
    results_data = sorted(results_data, key=lambda x: int(x.get("position") or 999))

    # 4. Fetch position data to determine grid_positions & sampled charts
    positions = cached_openf1_get("position", params={"session_key": session_key}) or []
    position_chart = {}
    grid_positions = {}

    if positions:
        # Group by driver to find chronological records
        driver_positions = {}
        for p in positions:
            dn = str(p['driver_number'])
            driver_positions.setdefault(dn, []).append(p)

        for dn in driver_positions:
            driver_positions[dn].sort(key=lambda x: x['date'])
            if driver_positions[dn]:
                # The first recorded position represents their starting grid position
                grid_positions[dn] = driver_positions[dn][0].get("position")

        # Sampling timestamps for line chart
        dates = sorted(list(set(p['date'] for p in positions)))
        if dates:
            num_samples = min(15, len(dates))
            indices = [int(i * (len(dates) - 1) / (num_samples - 1)) for i in range(num_samples)]
            sampled_dates = [dates[i] for i in indices]
            timestamps = [d.split('T')[1][:5] for d in sampled_dates] # HH:MM

            drivers_chart = {}
            for dn, records in driver_positions.items():
                positions_at_timestamps = []
                for target_date in sampled_dates:
                    pos = None
                    for r in records:
                        if r['date'] <= target_date:
                            pos = r['position']
                        else:
                            break
                    positions_at_timestamps.append(pos)
                drivers_chart[dn] = positions_at_timestamps

            position_chart = {
                "timestamps": timestamps,
                "drivers": drivers_chart
            }

    # 5. Fetch laps to resolve the fastest lap of the race
    laps_data = cached_openf1_get("laps", params={"session_key": session_key}) or []
    fastest_lap_driver = None
    fastest_lap_time = None

    valid_laps = [l for l in laps_data if l.get("lap_duration") is not None and l.get("lap_duration") > 50.0]
    if valid_laps:
        fastest_lap = min(valid_laps, key=lambda x: x["lap_duration"])
        fastest_lap_driver = str(fastest_lap.get("driver_number"))
        fastest_lap_time = fastest_lap.get("lap_duration")

    # 6. Fetch season drivers list to map high-quality photos
    headshot_map = {}
    try:
        meeting_year = 2024
        meeting_key = weather_data[0].get("meeting_key") if weather_data else None
        if not meeting_key and results_data:
            meeting_key = results_data[0].get("meeting_key")

        if meeting_key:
            meeting_info = cached_openf1_get("meetings", params={"meeting_key": meeting_key})
            if meeting_info and isinstance(meeting_info, list) and meeting_info[0].get("year"):
                meeting_year = meeting_info[0]["year"]
            elif meeting_info and isinstance(meeting_info, dict) and meeting_info.get("year"):
                meeting_year = meeting_info["year"]

        season_drivers = get_season_drivers(year=meeting_year)
        if "drivers" in season_drivers:
            for d in season_drivers["drivers"]:
                code = d.get("code") or d.get("driver_code")
                if code and d.get("headshot_url"):
                    headshot_map[code.upper()] = d["headshot_url"]
    except Exception as e:
        current_app.logger.warning("headshot lookup failed for session %s: %s", session_key, e)

    # 7. Fetch basic openf1 drivers metadata
    drivers_info = {}
    try:
        openf1_drivers = cached_openf1_get("drivers", params={"session_key": session_key}) or []
        for d in openf1_drivers:
            dn = str(d.get("driver_number"))
            first_name = d.get("first_name") or ""
            last_name = d.get("last_name") or ""
            drivers_info[dn] = {
                "code": d.get("name_acronym"),
                "name": f"{first_name} {last_name}".strip(),
                "team": normalize_team(d.get("team_name") or ""),
                "photo": d.get("headshot_url")
            }
    except Exception as e:
        current_app.logger.warning("driver metadata lookup failed for session %s: %s", session_key, e)

    # 8. Enrich results
    enriched_results = []
    for r in results_data:
        dn = str(r["driver_number"])
        meta = drivers_info.get(dn, {
            "code": f"D{dn}",
            "name": f"Driver {dn}",
            "team": "Unknown",
            "photo": None
        })

        # Resolve image (season official headshot prioritized, fallback to OpenF1)
        code_upper = meta["code"].upper() if meta.get("code") else ""
        resolved_photo = headshot_map.get(code_upper) or meta.get("photo")

        # Check if this driver held the fastest lap
        is_fastest = (fastest_lap_driver is not None and str(fastest_lap_driver) == dn)

        enriched_results.append({
            "position": r.get("position"),
            "driver_number": r.get("driver_number"),
            "number_of_laps": r.get("number_of_laps"),
            "points": r.get("points"),
            "gap_to_leader": r.get("gap_to_leader"),
            "duration": r.get("duration"),
            "dnf": r.get("dnf") or (r.get("status") and "finished" not in str(r.get("status")).lower() and "+" not in str(r.get("status"))),
            "dns": r.get("dns"),
            "dsq": r.get("dsq"),
            "driver_name": meta["name"],
            "driver_code": meta["code"],
            "team": meta["team"],
            "headshot_url": resolved_photo,
            "grid_position": grid_positions.get(dn),
            "is_fastest_lap": is_fastest
        })

    # 9. Compute Winner Cards
    winner_card = None
    if enriched_results:
        p1 = enriched_results[0]
        winner_card = {
            "driver_code": p1["driver_code"],
            "driver_name": p1["driver_name"],
            "team": p1["team"],
            "headshot_url": p1["headshot_url"],
            "duration": p1["duration"]
        }

    # 10. Compute Climber / Best Driver Card
    best_driver_card = None
    max_gain = -999
    best_climber = None
    for r in enriched_results:
        if r.get("grid_position") and r.get("position") and not r.get("dnf"):
            gain = int(r["grid_position"]) - int(r["position"])
            if gain > max_gain:
                max_gain = gain
                best_climber = r

    if best_climber and max_gain > 0:
        best_driver_card = {
            "driver_code": best_climber["driver_code"],
            "driver_name": best_climber["driver_name"],
            "team": best_climber["team"],
            "headshot_url": best_climber["headshot_url"],
            "positions_gained": max_gain
        }

    return {
        "session_key": session_key,
        "weather": {
            "avg_air_temp": avg_air_temp,
            "avg_track_temp": avg_track_temp,
            "avg_humidity": avg_humidity,
            "rainfall": rainfall_detected
        },
        "results": enriched_results,
        "stints": stints_by_driver,
        "position_chart": position_chart,
        "winner": winner_card,
        "best_driver": best_driver_card,
        "fastest_lap": {
            "driver_number": fastest_lap_driver,
            "lap_duration": fastest_lap_time
        }
    }
