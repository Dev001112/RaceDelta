"""
Track map: the circuit outline of a round split into its three timing sectors, plus corner markers.

Built from FastF1 position data of the race's fastest lap, cut at that lap's official sector times, so the
segments line up with the sector averages in the feature store. Position data is a large one-off download
per session, so the map is built on the background worker and cached forever (layouts do not change).
"""
import logging
import math

import fastf1
import numpy as np
import pandas as pd

import app.fastf1_setup  # noqa: F401  (shared FastF1 cache)
from app.services import cache_store

logger = logging.getLogger(__name__)

SIZE = 1000          # coordinates are normalized into a SIZE x SIZE box, y pointing down (SVG)
STEP = 2             # keep every STEP-th position sample (~4 Hz source -> ~2 Hz, enough for a smooth outline)


FAIL_TTL = 6 * 3600  # a round whose telemetry will not parse (e.g. 2026 with this FastF1) is not retried for a while


def _key(season, round_num):
    return f"track_map:v1:{season}:{round_num}"


def _fail_key(season, round_num):
    return f"track_map_failed:v1:{season}:{round_num}"


def get(candidates: list) -> dict:
    """First candidate (season, round) with a cached map; otherwise queue the first buildable one and report pending.
    Candidates are visits of the same circuit, latest first, so a round whose telemetry cannot be parsed falls
    back to an earlier layout."""
    for season, round_num in candidates:
        cached = cache_store.get("derived", _key(season, round_num))
        if cached:
            return cached
    for season, round_num in candidates:
        if cache_store.get("derived", _fail_key(season, round_num)):
            continue
        cache_store.enqueue("derived", _key(season, round_num), cache_store.LONG_TTL, lambda s=season, r=round_num: build_safe(s, r))
        return {"season": season, "round": round_num, "pending": True}
    return {"pending": False, "unavailable": True, "reason": "No visit of this circuit has position data this FastF1 version can read."}


def build_safe(season: int, round_num: int):
    """build() for the background worker: a failure is remembered for FAIL_TTL and nothing is stored under the map key."""
    try:
        return build(season, round_num)
    except Exception as e:
        logger.warning("track map %s R%s unavailable: %s", season, round_num, e)
        cache_store.set("derived", _fail_key(season, round_num), {"error": str(e)[:200]}, FAIL_TTL)
        return None


def build(season: int, round_num: int) -> dict:
    session = fastf1.get_session(season, round_num, "R")
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    lap = _lap_with_sector_times(session)
    pos = lap.get_pos_data()
    pos = pos[pos["Status"] == "OnTrack"] if "Status" in pos else pos
    pos = pos.dropna(subset=["X", "Y", "SessionTime"])
    t1, t2 = lap["Sector1SessionTime"], lap["Sector2SessionTime"]
    parts = [pos[pos["SessionTime"] <= t1], pos[(pos["SessionTime"] > t1) & (pos["SessionTime"] <= t2)], pos[pos["SessionTime"] > t2]]

    circuit = session.get_circuit_info()
    angle = math.radians(circuit.rotation or 0)
    corners = circuit.corners[["X", "Y", "Number"]] if circuit.corners is not None else pd.DataFrame(columns=["X", "Y", "Number"])

    xy = _rotate(pos[["X", "Y"]].to_numpy(dtype=float), angle)
    cxy = _rotate(corners[["X", "Y"]].to_numpy(dtype=float), angle) if len(corners) else np.empty((0, 2))
    scale = _scaler(np.vstack([xy, cxy]) if len(cxy) else xy)

    sectors = []
    for n, part in enumerate(parts, 1):
        pts = scale(_rotate(part[["X", "Y"]].to_numpy(dtype=float), angle))[::STEP]
        sectors.append({"n": n, "points": [[int(x), int(y)] for x, y in pts]})
    # close the loop visually: sector 3 ends where sector 1 starts
    if sectors[0]["points"] and sectors[2]["points"]:
        sectors[2]["points"].append(sectors[0]["points"][0])
    for i in (0, 1):   # and each sector starts where the previous one ended
        if sectors[i]["points"] and sectors[i + 1]["points"]:
            sectors[i + 1]["points"].insert(0, sectors[i]["points"][-1])

    return {
        "season": season, "round": round_num, "event": session.event["EventName"],
        "size": SIZE, "pending": False,
        "lap": {"driver": lap["Driver"], "lap_number": int(lap["LapNumber"]), "lap_time_s": _seconds(lap["LapTime"])},
        "sectors": sectors,
        "corners": [{"n": int(num), "x": int(x), "y": int(y)} for (x, y), num in zip(scale(cxy), corners["Number"])] if len(cxy) else [],
        "start_finish": sectors[0]["points"][0] if sectors[0]["points"] else None,
    }


def _lap_with_sector_times(session):
    """Fastest lap whose sector session times are present (needed to cut the outline)."""
    laps = session.laps.pick_quicklaps() if len(session.laps) else session.laps
    laps = laps.dropna(subset=["Sector1SessionTime", "Sector2SessionTime", "LapTime"])
    if laps.empty:
        laps = session.laps.dropna(subset=["Sector1SessionTime", "Sector2SessionTime", "LapTime"])
    if laps.empty:
        raise RuntimeError(f"No lap with sector times for {session.event['EventName']} {session.event.year}")
    return laps.loc[laps["LapTime"].idxmin()]


def _rotate(xy, angle):
    if not len(xy):
        return xy
    c, s = math.cos(angle), math.sin(angle)
    return xy @ np.array([[c, s], [-s, c]])


def _scaler(xy):
    """Fit into the SIZE box with a margin, preserve aspect ratio, flip y for SVG."""
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    span = float(max(hi - lo)) or 1.0
    margin = 0.06 * SIZE
    k = (SIZE - 2 * margin) / span
    offset = (SIZE - (hi - lo) * k) / 2      # centre the shorter axis

    def scale(pts):
        if not len(pts):
            return pts
        out = (pts - lo) * k + offset
        out[:, 1] = SIZE - out[:, 1]
        return out
    return scale


def _seconds(td):
    try:
        return round(td.total_seconds(), 3)
    except Exception:
        return None
