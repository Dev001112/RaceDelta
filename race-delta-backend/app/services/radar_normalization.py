# app/services/radar_normalization.py

def clamp(value, min_value=0, max_value=100):
    return max(min_value, min(max_value, round(value, 1)))


def normalize_radar(metrics, total_races):
    """
    Normalize L1 season metrics to 0–100 radar scores
    """

    radar = {}

    # -------------------------------
    # Points Efficiency
    # -------------------------------
    ppr = metrics.get("points_per_race", 0)
    radar["points_efficiency"] = clamp((ppr / 26) * 100)

    # -------------------------------
    # Finishing Consistency
    # -------------------------------
    avg_finish = metrics.get("avg_finish")
    if avg_finish:
        score = (1 - ((avg_finish - 1) / 19)) * 100
        radar["consistency"] = clamp(score)
    else:
        radar["consistency"] = 0

    # -------------------------------
    # Racecraft (Quali vs Race)
    # -------------------------------
    delta = metrics.get("q_vs_race", {}).get("average_delta", 0)
    radar["racecraft"] = clamp(((delta + 5) / 10) * 100)

    # -------------------------------
    # Reliability
    # -------------------------------
    dnf = metrics.get("dnf_count", 0)
    if total_races:
        radar["reliability"] = clamp((1 - (dnf / total_races)) * 100)
    else:
        radar["reliability"] = 0

    # -------------------------------
    # Winning Impact
    # -------------------------------
    wins = metrics.get("wins", 0)
    radar["winning_impact"] = clamp(min(wins / 10, 1) * 100)

    return radar
