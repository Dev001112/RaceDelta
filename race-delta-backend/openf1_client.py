# openf1_client.py
"""
OpenF1 client helpers for RaceDelta.
Provides:
 - get_meetings, get_sessions, get_drivers, get_laps, get_position
 - get_session_positions_bulk, get_session_results
 - get_latest_podium_results, get_latest_winner
 - compute_standings_from_positions
 - get_standings_from_openf1
 - try_get_openf1_driver_images, enrich_standings_with_openf1
This implementation uses OpenF1 API (configurable via OPENF1_BASE).
No DB models are required here; `db` parameters are accepted for API parity but not used.
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

OPENF1_BASE = os.getenv("OPENF1_BASE", "https://api.openf1.org/v1")
HTTP_TIMEOUT = float(os.getenv("OPENF1_TIMEOUT", "10"))
F1_POINTS_TABLE = {1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1}

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3)
session.mount("https://", adapter)
session.mount("http://", adapter)

def _get_json_from_openf1(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{OPENF1_BASE.rstrip('/')}/{path.lstrip('/')}"
    resp = session.get(url, params=params, timeout=HTTP_TIMEOUT)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return resp.text

# ---- Basic wrappers ----

def get_or_fetch(db, path: str, params: Optional[Dict[str, Any]] = None, use_cache: bool = True):
    # db param retained for compatibility; this function does not use it
    return _get_json_from_openf1(path, params=params)

def get_meetings(db, year: Optional[int] = None, use_cache: bool = True):
    params = {"year": year} if year else None
    return get_or_fetch(db, "meetings", params=params) or []

def get_sessions(db, meeting_key: Optional[str] = None, use_cache: bool = True):
    params = {"meeting_key": meeting_key} if meeting_key else None
    return get_or_fetch(db, "sessions", params=params) or []

def get_drivers(db, session_key: Optional[str] = None, use_cache: bool = True):
    params = {"session_key": session_key} if session_key else None
    return get_or_fetch(db, "drivers", params=params) or []

def get_laps(db, session_key: Optional[str] = None, driver_number: Optional[str] = None, use_cache: bool = True):
    params = {}
    if session_key:
        params["session_key"] = session_key
    if driver_number:
        params["driver_number"] = driver_number
    params = params or None
    return get_or_fetch(db, "laps", params=params)

def get_position(db, session_key: str, driver_number: Optional[str] = None, use_cache: bool = True):
    params = {}
    if session_key:
        params["session_key"] = session_key
    if driver_number:
        params["driver_number"] = driver_number
    params = params or None
    return get_or_fetch(db, "position", params=params)

def get_session_results(db, session_key: str, use_cache: bool = True):
    data = get_or_fetch(db, "session_result", params={"session_key": session_key})
    if data is None:
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("results", "data", "session_results"):
            if key in data and isinstance(data[key], list):
                return data[key]
        flattened = []
        for v in data.values():
            if isinstance(v, list):
                flattened.extend(v)
        if flattened:
            return flattened
    return None

# ---- Helpers for timestamps ----
def _parse_timestamp(sample: Dict[str, Any]) -> datetime:
    for k in ("date", "timestamp", "time", "start_time", "start"):
        v = sample.get(k)
        if not v:
            continue
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except Exception:
            continue
    return datetime(1970,1,1)

# ---- Bulk positions helper ----
def get_session_positions_bulk(db, session_key: str, use_cache: bool = True):
    data = get_or_fetch(db, "position", params={"session_key": session_key})
    if data is None:
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("samples","data","positions"):
            if k in data and isinstance(data[k], list):
                return data[k]
        flattened = []
        for v in data.values():
            if isinstance(v, list):
                flattened.extend(v)
        if flattened:
            return flattened
    return None

def _fetch_positions_for_driver(db, session_key: str, driver_number: str):
    try:
        samples = get_position(db, session_key=session_key, driver_number=driver_number)
        return driver_number, samples or []
    except Exception:
        return driver_number, []

# ---- Compute standings from positions (fallback) ----
def compute_standings_from_positions(db, year: Optional[int] = None, use_cache: bool = True) -> dict:
    meetings = get_meetings(db, year=year) or []
    drivers_points = {}
    constructors_points = {}
    for m in meetings:
        meeting_key = m.get("meeting_key") or m.get("key") or m.get("id")
        if not meeting_key:
            continue
        try:
            sessions = get_sessions(db, meeting_key=meeting_key) or []
        except Exception:
            continue
        for s in sessions:
            stype = (s.get("type") or s.get("session_type") or s.get("sessionType") or "").lower()
            if "race" not in stype:
                continue
            session_key = s.get("session_key") or s.get("key") or s.get("id")
            if not session_key:
                continue
            all_samples = get_session_positions_bulk(db, str(session_key))
            driver_samples_map = {}
            if all_samples is not None:
                for sample in all_samples:
                    dn = sample.get("driver_number") or sample.get("driverNumber") or sample.get("number")
                    if dn is None:
                        continue
                    driver_samples_map.setdefault(str(dn), []).append(sample)
            else:
                try:
                    driver_list = get_drivers(db, session_key=str(session_key)) or []
                except Exception:
                    driver_list = []
                driver_numbers = []
                if driver_list:
                    for d in driver_list:
                        dn = d.get("driver_number") or d.get("number") or d.get("driverNumber")
                        if dn is not None:
                            driver_numbers.append(str(dn))
                else:
                    entries = s.get("entries") or s.get("car_entries") or s.get("drivers") or []
                    for e in entries:
                        dn = e.get("driver_number") or e.get("number") or e.get("driverNumber")
                        if dn is not None:
                            driver_numbers.append(str(dn))
                if driver_numbers:
                    with ThreadPoolExecutor(max_workers=12) as ex:
                        futures = {ex.submit(_fetch_positions_for_driver, db, str(session_key), dn): dn for dn in driver_numbers}
                        for fut in as_completed(futures):
                            try:
                                dn, samples = fut.result()
                                if samples:
                                    driver_samples_map.setdefault(dn, []).extend(samples)
                            except Exception:
                                continue
            # compute last sample per driver (determine finishing pos)
            for dn, samples in driver_samples_map.items():
                if not samples:
                    continue
                try:
                    last = max(samples, key=lambda x: (int(x.get("lap_number") or x.get("lap") or 0), _parse_timestamp(x)))
                except Exception:
                    last = samples[-1]
                pos_val = last.get("position") or last.get("pos") or last.get("rank")
                try:
                    pos = int(pos_val)
                except Exception:
                    continue
                points = F1_POINTS_TABLE.get(pos, 0)
                # driver name resolution best-effort
                driver_name = f"Driver {dn}"
                try:
                    dlist = get_drivers(db, session_key=str(session_key)) or []
                    for dd in dlist:
                        ddn = dd.get("driver_number") or dd.get("number") or dd.get("driverNumber")
                        if ddn is not None and str(ddn) == str(dn):
                            driver_name = dd.get("driver_name") or dd.get("name") or dd.get("driver") or driver_name
                            break
                except Exception:
                    pass
                constructor = last.get("team") or last.get("constructor") or "Unknown"
                dp = drivers_points.setdefault(driver_name, {"points": 0, "wins": 0, "podiums": 0, "positions": []})
                dp["points"] += points
                dp["positions"].append(pos)
                if pos == 1:
                    dp["wins"] += 1
                if 1 <= pos <= 3:
                    dp["podiums"] += 1
                cp = constructors_points.setdefault(constructor, {"points": 0})
                cp["points"] += points

    driver_table = sorted([{"driver": k, **v} for k, v in drivers_points.items()], key=lambda x: (-x["points"], -x["wins"]))
    constructor_table = sorted([{"constructor": k, **v} for k, v in constructors_points.items()], key=lambda x: -x["points"])

    # produce stable output shape similar to what app expects
    drivers_out = []
    for pos, d in enumerate(driver_table, start=1):
        drivers_out.append({
            "driver_name": d.get("driver"),
            "driver_id": None,
            "driver_number": None,
            "points": d.get("points", 0),
            "wins": d.get("wins", 0),
            "podiums": d.get("podiums", 0),
            "position": str(pos),
            "profile_pic": None,
            "team_logo": None,
            "raw": d
        })
    constructors_out = []
    for pos, c in enumerate(constructor_table, start=1):
        constructors_out.append({
            "constructor_name": c.get("constructor"),
            "points": c.get("points", 0),
            "podiums": None,
            "position": str(pos),
            "team_logo": None,
            "raw": c
        })
    return {"drivers": drivers_out, "constructors": constructors_out}

# ---- Latest podium / winner helpers ----
def _find_latest_race_session(db, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    meetings = get_meetings(db, year=year) or []
    def meeting_date(m):
        for k in ("date", "start_date", "meeting_date", "start"):
            v = m.get(k)
            if v:
                try:
                    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                except Exception:
                    pass
        return datetime(1970,1,1)
    meetings_sorted = sorted(meetings, key=meeting_date, reverse=True)
    for m in meetings_sorted:
        meeting_key = m.get("meeting_key") or m.get("key") or m.get("id")
        if not meeting_key:
            continue
        try:
            sessions = get_sessions(db, meeting_key=meeting_key) or []
        except Exception:
            continue
        for s in sessions:
            stype = (s.get("type") or s.get("session_type") or s.get("sessionType") or "").lower()
            if "race" not in stype:
                continue
            session_key = s.get("session_key") or s.get("key") or s.get("id")
            if session_key:
                return {"meeting": m, "session": s, "session_key": session_key}
    return None

def get_latest_podium_results(db, year: Optional[int] = None, top_n: int = 3, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    cand = _find_latest_race_session(db, year=year)
    if not cand:
        return None
    session_key = cand["session_key"]
    results = get_session_results(db, str(session_key)) or []
    podium = []
    for r in results:
        try:
            pos = int(r.get("position") or r.get("pos") or 0)
        except Exception:
            pos = 0
        if 1 <= pos <= top_n:
            podium.append(r)
    podium_sorted = sorted(podium, key=lambda x: int(x.get("position") or x.get("pos") or 0))
    return {"meeting": cand["meeting"], "session": cand["session"], "podium": podium_sorted}

def get_latest_winner(db, year: Optional[int] = None, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    pod = get_latest_podium_results(db, year=year, top_n=1)
    if not pod or not pod.get("podium"):
        return None
    winner = pod["podium"][0]
    return {"meeting": pod["meeting"], "session": pod["session"], "winner": winner}

# ---- Official standings from OpenF1 (if available) ----
def get_standings_from_openf1(db, season: Optional[int] = None, use_cache: bool = True):
    params = {}
    if season:
        # some OpenF1 deployments expect 'year' or 'season'
        params["year"] = season
    data = get_or_fetch(db, "standings", params=params or None)
    return data

# ---- OpenF1 image scan & enrichment (OpenF1-only) ----
def try_get_openf1_driver_images(db, season: Optional[int] = None, max_meetings_scan: int = 8) -> Dict[str, str]:
    images: Dict[str, str] = {}
    try:
        meetings = get_meetings(db, year=season) or []
        for m in meetings[:max_meetings_scan]:
            meeting_key = m.get("meeting_key") or m.get("key") or m.get("id")
            if not meeting_key:
                continue
            sessions = get_sessions(db, meeting_key=meeting_key) or []
            for s in sessions:
                sk = s.get("session_key") or s.get("key") or s.get("id")
                if not sk:
                    continue
                try:
                    drvlist = get_drivers(db, session_key=str(sk)) or []
                except Exception:
                    drvlist = []
                for drv in drvlist:
                    if not isinstance(drv, dict):
                        continue
                    cand = None
                    # common fields that may contain image url
                    for k in ("image", "photo", "avatar", "profile_pic", "profilePic", "driver_image", "driverPhoto", "imageUrl", "img"):
                        if k in drv and drv[k]:
                            cand = drv[k]
                            break
                    if cand is None and isinstance(drv.get("Driver"), dict):
                        for k in ("image", "photo", "avatar", "url", "imageUrl"):
                            if drv["Driver"].get(k):
                                cand = drv["Driver"].get(k)
                                break
                    if not cand:
                        continue
                    url = None
                    if isinstance(cand, str) and cand.strip():
                        url = cand.strip()
                    elif isinstance(cand, dict):
                        url = cand.get("url") or cand.get("src") or cand.get("image")
                    if not url:
                        continue
                    dnum = None
                    for p in ("driver_number", "driverNumber", "number", "permanentNumber"):
                        if isinstance(drv.get(p), (str, int)):
                            dnum = str(drv.get(p))
                            break
                    if dnum:
                        images[f"num:{dnum}"] = url
                    code = drv.get("code") or (isinstance(drv.get("Driver"), dict) and drv["Driver"].get("code"))
                    if code:
                        images[f"code:{str(code).upper()}"] = url
                    did = drv.get("driverId") or (isinstance(drv.get("Driver"), dict) and drv["Driver"].get("driverId"))
                    if did:
                        images[f"id:{str(did).lower()}"] = url
                if len(images) > 200:
                    break
            if len(images) > 200:
                break
    except Exception:
        # do not raise; fail quietly
        pass
    return images

def enrich_standings_with_openf1(db, standings: dict, season: Optional[int] = None) -> dict:
    if not standings:
        return standings
    try:
        openf1_images = try_get_openf1_driver_images(db, season=season)
    except Exception:
        openf1_images = {}

    for dr in standings.get("drivers", []) or []:
        try:
            img = None
            dn = dr.get("driver_number") or dr.get("number") or (isinstance(dr.get("raw"), dict) and dr["raw"].get("driver_number"))
            if dn:
                key = f"num:{str(dn)}"
                if openf1_images.get(key):
                    img = openf1_images.get(key)
            if not img:
                code = dr.get("driver_code") or dr.get("driverId") or (isinstance(dr.get("raw"), dict) and (dr["raw"].get("driver_code") or dr["raw"].get("code") or dr["raw"].get("driverId")))
                if code:
                    ck = f"code:{str(code).upper()}"
                    if openf1_images.get(ck):
                        img = openf1_images.get(ck)
                    else:
                        ck2 = f"id:{str(code).lower()}"
                        if openf1_images.get(ck2):
                            img = openf1_images.get(ck2)
            if not img:
                raw = dr.get("raw") or {}
                if isinstance(raw, dict):
                    for k in ("image", "photo", "avatar", "profile_pic", "profilePic"):
                        if k in raw and raw[k]:
                            if isinstance(raw[k], str):
                                img = raw[k]
                                break
                            elif isinstance(raw[k], dict):
                                img = raw[k].get("url") or raw[k].get("image")
                                if img:
                                    break
            if img:
                dr["profile_pic"] = {"url": str(img)}
        except Exception:
            continue

    return standings

# Exports: names expected by app.py
__all__ = [
    "get_meetings",
    "get_sessions",
    "get_drivers",
    "get_laps",
    "get_position",
    "get_session_positions_bulk",
    "get_session_results",
    "get_latest_podium_results",
    "get_latest_winner",
    "compute_standings_from_positions",
    "get_standings_from_openf1",
    "try_get_openf1_driver_images",
    "enrich_standings_with_openf1",
]
