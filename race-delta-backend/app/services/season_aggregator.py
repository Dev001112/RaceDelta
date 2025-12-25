# app/services/season_aggregator.py

from .points_system import points_for_position
from .openf1_service import fetch_results


def filter_driver(results, driver_code):
    return [
        r for r in results
        if r.get("driver_code") == driver_code
    ]


def aggregate_race_metrics(driver_races):
    total_points = 0
    finishes = []
    dnfs = []
    points_by_race = []

    for r in driver_races:
        classified = r.get("classified_position")

        if classified is None:
            dnfs.append(r.get("meeting_name"))
            points_by_race.append(0)
            continue

        pos = int(classified)
        finishes.append(pos)

        pts = points_for_position(pos)
        total_points += pts
        points_by_race.append(pts)

    races_started = len(driver_races)
    finishes_count = len(finishes)

    return {
        "total_points": total_points,
        "points_per_race": round(total_points / races_started, 2) if races_started else 0,
        "avg_finish": round(sum(finishes) / finishes_count, 2) if finishes_count else None,
        "wins": finishes.count(1),
        "podiums": sum(1 for f in finishes if f <= 3),
        "dnf_count": len(dnfs),
        "dnf_races": dnfs,
        "points_by_race": points_by_race
    }


def compute_q_vs_race(race_results, quali_results):
    quali_map = {}

    for q in quali_results:
        if q.get("position") is not None:
            quali_map[q.get("meeting_key")] = int(q["position"])

    deltas = []

    for r in race_results:
        meeting_key = r.get("meeting_key")
        race_pos = r.get("classified_position")

        if meeting_key not in quali_map:
            continue
        if race_pos is None:
            continue

        delta = quali_map[meeting_key] - int(race_pos)
        deltas.append(delta)

    return {
        "average_delta": round(sum(deltas) / len(deltas), 2) if deltas else 0,
        "by_race": deltas
    }


def teammate_comparison(all_race_results, driver_code):
    driver_entries = [
        r for r in all_race_results if r.get("driver_code") == driver_code
    ]

    if not driver_entries:
        return None

    team_by_meeting = {
        r["meeting_key"]: r["team_name"] for r in driver_entries
    }

    teammate_entries = [
        r for r in all_race_results
        if r.get("meeting_key") in team_by_meeting
        and r.get("team_name") == team_by_meeting[r.get("meeting_key")]
        and r.get("driver_code") != driver_code
    ]

    h2h_wins = 0
    total = 0

    for d in driver_entries:
        for t in teammate_entries:
            if d["meeting_key"] == t["meeting_key"]:
                if d.get("classified_position") and t.get("classified_position"):
                    total += 1
                    if int(d["classified_position"]) < int(t["classified_position"]):
                        h2h_wins += 1

    return {
        "teammate_name": teammate_entries[0]["full_name"] if teammate_entries else None,
        "head_to_head": f"{h2h_wins}–{total - h2h_wins}"
    }


def build_l1_season(driver_code, season):
    race_results = fetch_results(season, "Race")
    quali_results = fetch_results(season, "Qualifying")

    driver_races = filter_driver(race_results, driver_code)
    driver_quali = filter_driver(quali_results, driver_code)

    race_metrics = aggregate_race_metrics(driver_races)
    q_vs_race = compute_q_vs_race(driver_races, driver_quali)
    teammate = teammate_comparison(race_results, driver_code)

    # ----------------------------------
    # DRIVER METADATA (SAFE SOURCE)
    # ----------------------------------
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
                        f"{d.get('first_name', '')} {d.get('last_name', '')}".strip()
                    )
                    driver_meta["team"] = d.get("team_name")
                    driver_meta["image"] = d.get("headshot_url")
                    break
    except Exception:
        pass

    return {
        "driver": driver_meta,
        "season": season,
        "metrics": {
            **race_metrics,
            "q_vs_race": q_vs_race,
            "teammate": teammate
        }
    }
