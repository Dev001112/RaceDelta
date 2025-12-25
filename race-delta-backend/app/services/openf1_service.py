# app/services/openf1_service.py

import requests

OPENF1_BASE = "https://api.openf1.org/v1"


def fetch_results(season, session_type):
    """
    session_type: 'Race' or 'Qualifying'
    """
    url = f"{OPENF1_BASE}/results"
    params = {
        "year": season,
        "session_type": session_type
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()
