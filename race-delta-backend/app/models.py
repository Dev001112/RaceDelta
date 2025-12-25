# D:\RaceDelta\race-delta-backend\app\models.py
# Compatibility shim so code importing `app.models` works.
from models import db, Driver, Constructor, Race, RaceResult, StandingsCache

# Backwards-compatible aliases expected by older modules:
Team = Constructor      # some modules expect "Team"
Lap = RaceResult       # some modules expect "Lap"
