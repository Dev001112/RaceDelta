import fastf1
from fastf1.ergast import Ergast
import os

# --------------------------------------------------
# Setup
# --------------------------------------------------
CACHE_DIR = os.path.join(os.path.expanduser("~"), "fastf1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

ergast = Ergast()


def get_f1_teams(season="current"):
    """
    Returns official FIA F1 constructor standings
    for the specified season (default: current).

    Schema detected:
    [
      'position', 'positionText', 'points', 'wins',
      'constructorId', 'constructorUrl',
      'constructorName', 'constructorNationality'
    ]
    """

    try:
        season_val = int(season) if str(season).isdigit() else season
        response = ergast.get_constructor_standings(
            season=season_val,
            round="last"
        )

        if (not response or not response.content or response.content[0].empty) and isinstance(season_val, int):
            from app.utils.season_resolver import resolve_seasons
            from app.services.f1_service import get_season_drivers, get_constructor_standings
            
            # See if we have anything for this season from OpenF1 (roster exist?)
            drivers_data = get_season_drivers(year=season_val)
            
            if drivers_data and drivers_data.get("drivers"):
                # Season has active drivers/races! Compute using OpenF1
                openf1_data = get_constructor_standings(season=str(season_val))
                team_list = openf1_data.get("standings", [])
                
                teams = []
                # If openf1 points fetched fallback data (i.e. empty), build zero-point teams from drivers
                if "fallback" in str(openf1_data.get("source", "")):
                    unique_teams = list(set([d.get("team") for d in drivers_data["drivers"] if d.get("team")]))
                    team_list = [{"team": t, "position": i+1, "points": 0, "wins": 0} for i, t in enumerate(sorted(unique_teams))]
                elif not team_list:
                    unique_teams = list(set([d.get("team") for d in drivers_data["drivers"] if d.get("team")]))
                    team_list = [{"team": t, "position": i+1, "points": 0, "wins": 0} for i, t in enumerate(sorted(unique_teams))]

                # Ergast compatibility mapping
                ergast_map = {
                    "red bull racing": "red_bull",
                    "aston martin": "aston_martin",
                    "mercedes": "mercedes",
                    "ferrari": "ferrari",
                    "mclaren": "mclaren",
                    "alpine": "alpine",
                    "rbr": "red_bull",
                    "williams": "williams",
                    "haas": "haas",
                    "sauber": "sauber",
                    "rb": "rb"
                }

                for row in team_list:
                    t_name = row.get("team", "Unknown")
                    slug = ergast_map.get(t_name.lower(), t_name.lower().replace(" ", "_").replace(".", ""))
                    teams.append({
                        "team_name": t_name,
                        "constructor_id": slug,
                        "nationality": "International",
                        "position": int(row.get("position", 0)),
                        "points": float(row.get("points", 0)),
                        "wins": int(row.get("wins", 0))
                    })
                
                # Sort and return OpenF1 computed standings
                teams.sort(key=lambda x: (-x["points"], x["team_name"]))
                for i, t in enumerate(teams):
                    t["position"] = i + 1
                    
                return teams
                
            # If no openF1 data exist, only then fallback to previous season
            if season_val >= resolve_seasons()["calendar_season"]:
                response = ergast.get_constructor_standings(
                    season=season_val - 1,
                    round="last"
                )

        if not response or not response.content or response.content[0].empty:
            print("Constructor standings empty")
            return []

        df = response.content[0]

        teams = []
        for _, row in df.iterrows():
            teams.append({
                "team_name": row["constructorName"],
                "constructor_id": row["constructorId"],
                "nationality": row["constructorNationality"],
                "position": int(row["position"]),
                "points": float(row["points"]),
                "wins": int(row["wins"])
            })

        return teams

    except Exception as e:
        print("Teams API error:", e)
        return []
