# app/services/l1_season_fastf1.py

import fastf1
import numpy as np
import os

# --------------------------------------------------
# FastF1 cache (SAFE INIT)
# --------------------------------------------------
CACHE_DIR = "fastf1_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def safe_number(val, default=0):
    """
    Ensures JSON-safe numeric output.
    Converts NaN / None / invalid -> default
    """
    try:
        if val is None:
            return default
        if isinstance(val, float) and val != val:  # NaN
            return default
        return val
    except Exception:
        return default


# --------------------------------------------------
# L1 — DRIVER SEASON METRICS
# --------------------------------------------------
def get_driver_season_metrics(season: int, driver_code: str):
    """
    L1 – Season-level analytics using FastF1
    JSON-safe, driver-agnostic
    """

    schedule = fastf1.get_event_schedule(season)

    # Exclude testing
    races = schedule[schedule["EventFormat"] != "testing"]

    metrics = {
        "avg_finish": None,
        "dnf_count": 0,
        "dnf_races": [],
        "wins": 0,
        "podiums": 0,
        "total_points": 0,
        "points_by_race": [],
        "points_per_race": 0,
        "q_vs_race": {
            "average_delta": 0,
            "by_race": []
        }
    }

    finish_positions = []
    q_deltas = []
    points_accumulator = []

    for _, event in races.iterrows():
        round_no = int(event["RoundNumber"])
        race_name = event["EventName"]

        try:
            # -------------------------------
            # RACE
            # -------------------------------
            race = fastf1.get_session(season, round_no, "R")
            race.load(laps=False, telemetry=False, weather=False)
            results = race.results

            if driver_code not in results["Abbreviation"].values:
                continue

            row = results[results["Abbreviation"] == driver_code].iloc[0]

            status = str(row["Status"])
            pos = (
                int(row["ClassifiedPosition"])
                if str(row["ClassifiedPosition"]).isdigit()
                else None
            )
            points = safe_number(float(row["Points"]), 0)

            metrics["points_by_race"].append({
                "round": round_no,
                "race": race_name,
                "points": points
            })
            points_accumulator.append(points)

            # Finish stats
            if pos:
                finish_positions.append(pos)
                if pos == 1:
                    metrics["wins"] += 1
                if pos <= 3:
                    metrics["podiums"] += 1

            # DNF
            if not status.startswith("Finished") and not status.startswith("+"):
                metrics["dnf_count"] += 1
                metrics["dnf_races"].append(race_name)

            # -------------------------------
            # QUALI vs RACE
            # -------------------------------
            try:
                quali = fastf1.get_session(season, round_no, "Q")
                quali.load(laps=False, telemetry=False)
                q_results = quali.results

                if driver_code in q_results["Abbreviation"].values and pos:
                    q_pos = int(
                        q_results[q_results["Abbreviation"] == driver_code]
                        .iloc[0]["Position"]
                    )
                    delta = safe_number(q_pos - pos, 0)

                    metrics["q_vs_race"]["by_race"].append({
                        "round": round_no,
                        "race": race_name,
                        "delta": delta
                    })
                    q_deltas.append(delta)

            except Exception:
                pass

        except Exception as e:
            print(f"[L1] Error processing round {round_no}: {e}")

    # --------------------------------------------------
    # FINAL AGGREGATES (ABSOLUTELY JSON SAFE)
    # --------------------------------------------------
    metrics["total_points"] = safe_number(sum(points_accumulator), 0)

    metrics["avg_finish"] = (
        safe_number(round(float(np.mean(finish_positions)), 2))
        if finish_positions else None
    )

    metrics["points_per_race"] = (
        safe_number(round(metrics["total_points"] / len(points_accumulator), 2))
        if points_accumulator else 0
    )

    metrics["q_vs_race"]["average_delta"] = (
        safe_number(round(float(np.mean(q_deltas)), 2))
        if q_deltas else 0
    )

    return metrics


# --------------------------------------------------
# OPTIONAL — TEAMMATE DETECTION (SAFE)
# --------------------------------------------------
def get_teammate_code(season: int, driver_code: str):
    """
    Detect teammate based on first race where driver appears.
    Returns None safely if not found.
    """

    schedule = fastf1.get_event_schedule(season)
    races = schedule[schedule["EventFormat"] != "testing"]

    for _, event in races.iterrows():
        try:
            race = fastf1.get_session(season, int(event["RoundNumber"]), "R")
            race.load(laps=False, telemetry=False, weather=False)
            results = race.results

            if driver_code not in results["Abbreviation"].values:
                continue

            driver_row = results[results["Abbreviation"] == driver_code].iloc[0]
            team = driver_row["TeamName"]

            teammate_rows = results[
                (results["TeamName"] == team) &
                (results["Abbreviation"] != driver_code)
            ]

            if not teammate_rows.empty:
                return teammate_rows.iloc[0]["Abbreviation"]

        except Exception:
            continue

    return None
