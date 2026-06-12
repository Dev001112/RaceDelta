# app/services/openf1_service.py

import requests
from app.services import cache_store

OPENF1_BASE = "https://api.openf1.org/v1"
OPENF1_CACHE_TTL = 60 * 60 * 6


def fetch_results(season, session_type):
    """
    session_type: 'Race' or 'Qualifying'
    """
    url = f"{OPENF1_BASE}/results"
    params = {
        "year": season,
        "session_type": session_type
    }

    cache_key = f"{url}:{dict(sorted(params.items()))}"
    cached = cache_store.get("openf1", cache_key)
    if cached is not None:
        return cached

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    cache_store.set("openf1", cache_key, data, OPENF1_CACHE_TTL)
    return data
