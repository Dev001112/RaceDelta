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


def get_current_f1_teams():
    """
    Returns official FIA F1 constructor standings
    for the CURRENT season.

    Schema detected:
    [
      'position', 'positionText', 'points', 'wins',
      'constructorId', 'constructorUrl',
      'constructorName', 'constructorNationality'
    ]
    """

    try:
        response = ergast.get_constructor_standings(
            season="current",
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
