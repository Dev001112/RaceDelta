
from scripts.ergast_teams import get_f1_teams
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

try:
    print("Fetching 2025 teams...")
    teams = get_f1_teams(season=2025)
    print("IDs found:")
    for t in teams:
        print(f" - {t['constructor_id']} ({t['team']})")
        
except Exception as e:
    print(e)
