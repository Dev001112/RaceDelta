# app/services/standings_service.py
"""
Service layer for fetching standings via FastF1 Ergast (Jolpica) API.
Keeps FastF1 calls isolated so routes.py stays clean and testable.
"""
from datetime import datetime, timedelta
import threading
import pandas as pd
from fastf1.ergast import Ergast

# Single Ergast instance used by service
ergast = Ergast()

# small thread-safe in-memory TTL cache for dev
_cache = {}
_cache_lock = threading.Lock()

def _set_cache(key, value, ttl_seconds=60):
    with _cache_lock:
        _cache[key] = {'value': value, 'expires_at': datetime.utcnow() + timedelta(seconds=ttl_seconds)}

def _get_cache(key):
    with _cache_lock:
        item = _cache.get(key)
        if not item:
            return None
        if item['expires_at'] < datetime.utcnow():
            del _cache[key]
            return None
        return item['value']

def _choose_latest_from_resp(resp):
    """
    ErgastMultiResponse -> resp.content is list of DataFrames (ascending seasons)
    Return (df, season_info)
    """
    if hasattr(resp, 'content') and isinstance(resp.content, list) and resp.content:
        df = resp.content[-1]
        season_info = {}
        if hasattr(resp, 'description') and not resp.description.empty:
            desc = resp.description.iloc[-1].to_dict()
            season_info = {
                'season': int(desc.get('season')) if desc.get('season') is not None else None,
                'round': int(desc.get('round')) if desc.get('round') is not None else None
            }
        return df, season_info

    # If resp is a DataFrame directly
    if isinstance(resp, pd.DataFrame):
        return resp, {}

    # ErgastSimpleResponse might hold data/frame attributes
    df = getattr(resp, 'data', None) or getattr(resp, 'frame', None) or None
    return df, {}

def _df_to_normalized_records(df: pd.DataFrame):
    """
    Map Ergast DataFrame rows into a stable normalized dict the frontend expects.
    """
    if df is None:
        return []
    df = df.where(pd.notnull(df), None)  # convert NaN -> None
    records = df.to_dict(orient='records')
    out = []
    for r in records:
        out.append({
            'position': str(r.get('position') or r.get('positionText') or ''),
            'points': r.get('points') or r.get('pointsText') or 0,
            'wins': r.get('wins') or 0,
            'driver_id': r.get('driverId') or r.get('Driver') or r.get('driver') or None,
            'driver_name': ( (r.get('givenName') and r.get('familyName') and f"{r.get('givenName')} {r.get('familyName')}")
                             or r.get('Driver') or r.get('driverName') or None ),
            'constructor_name': r.get('constructorName') or r.get('Constructor') or r.get('constructor') or None,
            'constructor_id': r.get('constructorId') or None,
            'raw': r,  # pass raw row for any unanticipated fields
        })
    return out

def get_driver_standings(season: int = None, cache_ttl: int = 60):
    """
    Returns dict: {'season_info': {...}, 'drivers': [...]}
    season: int or None -> if None, service will request multi-season and pick latest
    """
    key = f"drivers:{season or 'latest'}"
    cached = _get_cache(key)
    if cached:
        return cached

    if season:
        resp = ergast.get_driver_standings(season=int(season), result_type='pandas')
    else:
        resp = ergast.get_driver_standings(result_type='pandas')

    df, season_info = _choose_latest_from_resp(resp)
    drivers = _df_to_normalized_records(df)
    payload = {'season_info': season_info, 'drivers': drivers}
    _set_cache(key, payload, ttl_seconds=cache_ttl)
    return payload

def get_constructor_standings(season: int = None, cache_ttl: int = 60):
    """
    Returns dict: {'season_info': {...}, 'constructors': [...]}
    """
    key = f"constructors:{season or 'latest'}"
    cached = _get_cache(key)
    if cached:
        return cached

    if season:
        resp = ergast.get_constructor_standings(season=int(season), result_type='pandas')
    else:
        resp = ergast.get_constructor_standings(result_type='pandas')

    df, season_info = _choose_latest_from_resp(resp)
    constructors = _df_to_normalized_records(df)
    payload = {'season_info': season_info, 'constructors': constructors}
    _set_cache(key, payload, ttl_seconds=cache_ttl)
    return payload
