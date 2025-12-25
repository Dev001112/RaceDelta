# scripts/ergast_client.py

from fastf1.ergast import Ergast

# Single shared Ergast instance
# No timeout parameter — FastF1 does not support it here
ergast = Ergast()
