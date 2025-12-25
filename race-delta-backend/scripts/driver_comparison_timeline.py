"""
Driver comparison timeline
- Points over season
- Head-to-head wins
- Per-round results

Optimized with:
✔ diskcache (persistent)
✔ threading (parallel fetch)
✔ graceful Ergast failure handling
✔ current season support
"""

from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor
import requests
from diskcache import Cache

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

ERGAST_BASES = [
    "https://ergast.com/api/f1",
    "https://api.jolpi.ca/ergast/f1"  # mirror (more reliable)
]

CACHE_DIR = "./.cache"
MAX_WORKERS = 5
CACHE_TTL = 60 * 60 * 6  # 6 hours

cache = Cache(CACHE_DIR)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def normalize_season(season):
    if season == "current":
        return datetime.utcnow().year
    return int(season)


def fetch_json(url: str):
    """
    Fetch JSON with:
    - disk cache
    - retries
    - graceful failure (never throws)
    """
    if url in cache:
        return cache[url]

    for base in ERGAST_BASES:
        full_url = url.replace("https://ergast.com/api/f1", base)

        for attempt in range(3):
            try:
                r = requests.get(full_url, timeout=15)
                r.raise_for_status()
                data = r.json()
                cache.set(url, data, expire=CACHE_TTL)
                return data
            except Exception as e:
                if attempt == 2:
                    print("ERGAST FAILED:", full_url, e)

    return None  # graceful failure


# --------------------------------------------------
# ERGAST QUERIES
# --------------------------------------------------

def get_race_schedule(season: int):
    """
    Returns:
    [{round, race, date}]
    """
    url = f"https://ergast.com/api/f1/{season}.json"
    data = fetch_json(url)

    if not data:
        return []

    races = data["MRData"]["RaceTable"].get("Races", [])
    schedule = []

    for r in races:
        try:
            schedule.append({
                "round": int(r["round"]),
                "race": r["raceName"],
                "date": date.fromisoformat(r["date"])
            })
        except Exception:
            continue

    return schedule


def get_race_results(season: int, round_no: int):
    """
    Returns:
    {driverCode: points}
    """
    url = f"https://ergast.com/api/f1/{season}/{round_no}/results.json"
    data = fetch_json(url)

    if not data:
        return None

    races = data["MRData"]["RaceTable"].get("Races", [])
    if not races:
        return None

    results = {}
    for r in races[0]["Results"]:
        results[r["Driver"]["code"]] = int(float(r["points"]))

    return results


# --------------------------------------------------
# MAIN BUILDER
# --------------------------------------------------

def build_driver_comparison_timeline(driver1, driver2, season):
    """
    Returns:
    {
      season,
      rounds: [
        {round, race, points, cumulative, winner}
      ],
      head_to_head: {driver1, driver2}
    }
    """

    season = normalize_season(season)
    cache_key = f"timeline:{season}:{driver1}:{driver2}"

    if cache_key in cache:
        return cache[cache_key]

    print(f"BUILD TIMELINE: {driver1} vs {driver2} ({season})")

    schedule = get_race_schedule(season)
    today = date.today()

    if not schedule:
        output = {
            "season": season,
            "rounds": [],
            "head_to_head": {driver1: 0, driver2: 0}
        }
        cache.set(cache_key, output, expire=CACHE_TTL)
        return output

    # only completed races
    completed = [r for r in schedule if r["date"] <= today]

    # ----------------------------------------------
    # PARALLEL FETCH (SAFE)
    # ----------------------------------------------

    def fetch_round(r):
        results = get_race_results(season, r["round"])
        if not results:
            return None
        if driver1 not in results or driver2 not in results:
            return None

        return {
            "round": r["round"],
            "race": r["race"],
            "p1": results[driver1],
            "p2": results[driver2]
        }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        raw = list(pool.map(fetch_round, completed))

    # ----------------------------------------------
    # BUILD TIMELINE (SEQUENTIAL)
    # ----------------------------------------------

    cumulative = {driver1: 0, driver2: 0}
    head_to_head = {driver1: 0, driver2: 0}
    timeline = []

    for r in sorted(filter(None, raw), key=lambda x: x["round"]):
        cumulative[driver1] += r["p1"]
        cumulative[driver2] += r["p2"]

        winner = driver1 if r["p1"] > r["p2"] else driver2
        head_to_head[winner] += 1

        timeline.append({
            "round": r["round"],
            "race": r["race"],
            "points": {
                driver1: r["p1"],
                driver2: r["p2"]
            },
            "cumulative": {
                driver1: cumulative[driver1],
                driver2: cumulative[driver2]
            },
            "winner": winner
        })

    output = {
        "season": season,
        "rounds": timeline,
        "head_to_head": head_to_head
    }

    cache.set(cache_key, output, expire=CACHE_TTL)
    return output
