import os
import shutil
import requests
import fastf1
from functools import lru_cache
from fastf1.ergast import Ergast

# --------------------------------------------------
# FASTF1 CACHE SETUP
# --------------------------------------------------
CACHE_DIR = os.path.join(os.path.expanduser("~"), "fastf1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

try:
    fastf1.Cache.enable_cache(CACHE_DIR)
except Exception:
    shutil.rmtree(CACHE_DIR, ignore_errors=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)

# --------------------------------------------------
# CLIENTS
# --------------------------------------------------
ergast = Ergast()
OPENF1_BASE = "https://api.openf1.org/v1"

# --------------------------------------------------
# CANONICAL TEAM NORMALIZATION
# --------------------------------------------------
TEAM_NAME_MAP = {
    # Red Bull family
    "Red Bull": "Red Bull Racing",
    "Red Bull Racing": "Red Bull Racing",

    # RB / AlphaTauri lineage
    "RB": "RB",
    "Racing Bulls": "RB",
    "Scuderia AlphaTauri": "RB",

    # Sauber lineage
    "Kick Sauber": "Kick Sauber",
    "Sauber": "Kick Sauber",
    "Alfa Romeo": "Kick Sauber",

    # Direct mappings
    "Ferrari": "Ferrari",
    "Mercedes": "Mercedes",
    "McLaren": "McLaren",
    "Williams": "Williams",
    "Aston Martin": "Aston Martin",
    "Alpine": "Alpine",
    "Haas F1 Team": "Haas F1 Team",
}

def normalize_team_name(name: str | None) -> str:
    if not name:
        return "Unknown"
    return TEAM_NAME_MAP.get(name, name)

# --------------------------------------------------
# OPENF1 DRIVER METADATA (SINGLE SOURCE OF TRUTH)
# --------------------------------------------------
@lru_cache(maxsize=1)
def get_openf1_driver_index():
    """
    Returns:
    {
        "VER": {
            "driver_number": 1,
            "team": "Red Bull Racing",
            "country_code": "NED",
            "headshot_url": "...",
            "team_colour": "#3671C6"
        },
        ...
    }
    """
    try:
        resp = requests.get(
            f"{OPENF1_BASE}/drivers?session_key=latest",
            timeout=10
        )
        resp.raise_for_status()

        driver_map = {}

        for d in resp.json():
            code = d.get("name_acronym")
            if not code:
                continue

            raw_team = d.get("team_name")

            driver_map[code] = {
                "driver_number": d.get("driver_number"),
                "team": normalize_team_name(raw_team),
                "country_code": d.get("country_code"),
                "headshot_url": d.get("headshot_url"),
                "team_colour": (
                    f"#{d['team_colour']}"
                    if d.get("team_colour") else "#FFFFFF"
                ),
            }

        return driver_map

    except Exception as e:
        print("OpenF1 driver index error:", e)
        return {}

# --------------------------------------------------
# DRIVER STANDINGS (ERGAST + OPENF1)
# --------------------------------------------------
def get_current_driver_standings():
    response = ergast.get_driver_standings(
        season="current",
        round="last"
    )

    if not response or not response.content:
        return {"season": "current", "standings": []}

    df = response.content[0]
    openf1_drivers = get_openf1_driver_index()

    standings = []

    for _, row in df.iterrows():
        code = row.get("driverCode")
        openf1 = openf1_drivers.get(code, {})

        raw_team = (
            openf1.get("team")
            or row.get("constructorName")
        )

        standings.append({
            "position": int(row["position"]),
            "driver_code": code,
            "driver_name": f"{row.get('givenName')} {row.get('familyName')}",
            "driver_number": openf1.get("driver_number"),
            "team": normalize_team_name(raw_team),
            "country_code": openf1.get("country_code"),
            "headshot_url": openf1.get("headshot_url"),
            "team_colour": openf1.get("team_colour", "#FFFFFF"),
            "points": float(row["points"]),
            "wins": int(row["wins"]),
        })

    return {
        "season": "current",
        "standings": standings
    }

# --------------------------------------------------
# CONSTRUCTOR STANDINGS (ERGAST + OPENF1 COLOURS)
# --------------------------------------------------
def get_current_constructor_standings():
    response = ergast.get_constructor_standings(
        season="current",
        round="last"
    )

    if not response or not response.content:
        return {"season": "current", "standings": []}

    df = response.content[0]
    openf1_drivers = get_openf1_driver_index()

    # Build canonical team → colour map
    team_colour_map = {}
    for d in openf1_drivers.values():
        team = d.get("team")
        colour = d.get("team_colour")
        if team and team not in team_colour_map:
            team_colour_map[team] = colour

    standings = []

    for _, row in df.iterrows():
        raw_team = (
            row.get("constructorName")
            or row.get("name")
        )

        team = normalize_team_name(raw_team)

        standings.append({
            "position": int(row["position"]),
            "team": team,
            "team_colour": team_colour_map.get(team, "#FFFFFF"),
            "points": float(row["points"]),
            "wins": int(row["wins"]),
        })

    return {
        "season": "current",
        "standings": standings
    }
