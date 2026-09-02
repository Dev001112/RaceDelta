# app/services/feature_engineering.py
"""
Feature Engineering Layer (Phase 2).

Pure pandas/numpy functions over FastF1 lap frames. No DB, no network, so every
function is unit-testable with a synthetic DataFrame (see tests/test_feature_engineering.py).

Vocabulary
  clean lap    accurate, green-flag (TrackStatus == '1'), not pit-in/pit-out, not deleted
  pace         mean clean lap time (s)
  consistency  population std-dev of clean lap times (s); lower = steadier
  trend        slope of clean lap time vs lap number (s/lap); positive = getting slower
  degradation  mean per-stint slope of clean lap time vs tyre life (s/lap)
"""
import re

import numpy as np
import pandas as pd

GREEN_FLAG = "1"
MIN_FIT_POINTS = 3
MIN_STINT_LAPS = 4


# ---------------------------------------------------------------- scalar helpers
def sec(value):
    """Timedelta / NaT / None / number -> float seconds or None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timedelta):
        return float(value.total_seconds())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fnum(value, ndigits=3):
    """Any number -> rounded float, or None when missing / non-finite (JSON-safe)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return round(v, ndigits) if np.isfinite(v) else None


def inum(value):
    """Any number-like -> int or None."""
    v = fnum(value, 6)
    return int(v) if v is not None else None


def td_seconds(series: pd.Series) -> pd.Series:
    """Timedelta or numeric Series -> float seconds (NaN where missing)."""
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds()
    return pd.to_numeric(series, errors="coerce")


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    return df[name] if name in df.columns else pd.Series(index=df.index, dtype="float64")


def slope(x, y):
    """Least-squares slope of y on x, or None when under-determined."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < MIN_FIT_POINTS or np.ptp(x) == 0:
        return None
    return float(np.polyfit(x, y, 1)[0])


# ---------------------------------------------------------------- lap-level
def clean_mask(laps: pd.DataFrame) -> pd.Series:
    """Boolean mask of laps that are safe to use for pace statistics."""
    m = laps["LapTime"].notna()
    if "IsAccurate" in laps:
        m &= laps["IsAccurate"].fillna(False).astype(bool)
    if "TrackStatus" in laps:
        m &= laps["TrackStatus"].astype(str) == GREEN_FLAG
    if "PitInTime" in laps:
        m &= laps["PitInTime"].isna()
    if "PitOutTime" in laps:
        m &= laps["PitOutTime"].isna()
    if "Deleted" in laps:
        m &= ~laps["Deleted"].fillna(False).astype(bool)
    return m


def compute_gaps(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Gap to the car ahead / behind on every lap, in seconds, from the session time at
    lap end ('Time') ordered by 'Position'. Returns a frame aligned to laps.index.
    """
    out = pd.DataFrame({"gap_ahead_s": np.nan, "gap_behind_s": np.nan}, index=laps.index)
    if not {"LapNumber", "Position", "Time"} <= set(laps.columns):
        return out
    df = pd.DataFrame({
        "lap": pd.to_numeric(laps["LapNumber"], errors="coerce"),
        "pos": pd.to_numeric(laps["Position"], errors="coerce"),
        "t": td_seconds(laps["Time"]),
    }, index=laps.index).dropna()
    for _, grp in df.groupby("lap"):
        g = grp.sort_values("pos")
        t = g["t"].to_numpy()
        diffs = t[1:] - t[:-1]
        out.loc[g.index, "gap_ahead_s"] = np.r_[np.nan, diffs]
        out.loc[g.index, "gap_behind_s"] = np.r_[diffs, np.nan]
    return out


def stint_features(driver_laps: pd.DataFrame) -> list:
    """One dict per tyre stint: range, compound, clean-lap pace and degradation slope."""
    rows = []
    if "Stint" not in driver_laps.columns:
        return rows
    secs = td_seconds(driver_laps["LapTime"])
    clean = clean_mask(driver_laps)
    for stint_no, g in driver_laps.groupby("Stint", sort=True):
        if pd.isna(stint_no):
            continue
        cl = clean.loc[g.index]
        s_clean = secs.loc[g.index][cl]
        life = pd.to_numeric(_col(g, "TyreLife"), errors="coerce")[cl]
        compound = _col(g, "Compound").dropna()
        rows.append({
            "stint_number": int(stint_no),
            "compound": str(compound.iloc[0]) if len(compound) else None,
            "lap_start": inum(g["LapNumber"].min()),
            "lap_end": inum(g["LapNumber"].max()),
            "laps": int(len(g)),
            "avg_lap_time_s": fnum(s_clean.mean()) if len(s_clean) else None,
            "degradation_s_per_lap": fnum(slope(life, s_clean), 4),
        })
    return rows


def count_penalties(rcm: pd.DataFrame, abbreviation: str, driver_number) -> int:
    """
    Stewards' penalty messages addressed to this car, from race-control messages.
    ponytail: text heuristic ('PENALTY' minus 'PENALTY SERVED' follow-ups); upgrade to a
    structured penalty source if one appears.
    """
    if rcm is None or getattr(rcm, "empty", True) or "Message" not in rcm.columns:
        return 0
    msgs = rcm["Message"].astype(str)
    is_penalty = (msgs.str.contains("PENALTY", case=False, na=False)
                  & ~msgs.str.contains("SERVED", case=False, na=False))
    mine = msgs.str.upper().str.contains(re.escape(f"({str(abbreviation).upper()})"), regex=True, na=False)
    num = inum(driver_number)
    if num is not None:
        mine |= msgs.str.contains(rf"\bCAR\s+{num}\b", case=False, regex=True, na=False)
    return int((is_penalty & mine).sum())


def weather_summary(weather: pd.DataFrame) -> dict:
    empty = {"avg_air_temp": None, "avg_track_temp": None, "avg_humidity": None, "rainfall": False}
    if weather is None or getattr(weather, "empty", True):
        return empty
    return {
        "avg_air_temp": fnum(pd.to_numeric(_col(weather, "AirTemp"), errors="coerce").mean(), 1),
        "avg_track_temp": fnum(pd.to_numeric(_col(weather, "TrackTemp"), errors="coerce").mean(), 1),
        "avg_humidity": fnum(pd.to_numeric(_col(weather, "Humidity"), errors="coerce").mean(), 1),
        "rainfall": bool(_col(weather, "Rainfall").fillna(False).astype(bool).any()),
    }


# ---------------------------------------------------------------- driver x race
def driver_race_features(driver_laps: pd.DataFrame, gaps: pd.DataFrame = None,
                         result=None, weather: dict = None, penalties: int = 0) -> dict:
    """
    The standardized feature vector for one driver in one race. Keys match the
    DriverRaceFeature columns exactly so the dict can be written straight to the store.
    `result` is a FastF1 results row (Series) or a plain dict; `weather` from weather_summary().
    """
    dl = driver_laps.sort_values("LapNumber")
    lapno = pd.to_numeric(dl["LapNumber"], errors="coerce")
    secs = td_seconds(dl["LapTime"])
    cl = clean_mask(dl)
    clean_secs = secs[cl]

    stints = stint_features(dl)
    degs = [s["degradation_s_per_lap"] for s in stints
            if s["degradation_s_per_lap"] is not None and s["laps"] >= MIN_STINT_LAPS]

    pit_in = _col(dl, "PitInTime").notna()
    pit_laps = [int(x) for x in lapno[pit_in].dropna().tolist()]

    # ponytail: naive lap-over-lap position gains; pit-cycle noise is not filtered out.
    pos = pd.to_numeric(_col(dl, "Position"), errors="coerce").ffill()
    overtakes = int((pos.diff() < 0).sum()) if pos.notna().any() else 0

    grid = finish = status = points = None
    if result is not None:
        grid = inum(result.get("GridPosition"))
        grid = grid if grid and grid > 0 else None          # 0 = pit-lane start
        finish = inum(result.get("ClassifiedPosition"))     # non-numeric (R, D, W) = not classified
        status = result.get("Status")
        status = None if status is None or (isinstance(status, float) and np.isnan(status)) else str(status)
        points = fnum(result.get("Points"), 1)
    position_changes = (grid - finish) if (grid is not None and finish is not None) else None

    gap_ahead = gap_behind = None
    if gaps is not None and len(gaps):
        g = gaps.reindex(dl.index)
        gap_ahead = fnum(g["gap_ahead_s"].mean())
        gap_behind = fnum(g["gap_behind_s"].mean())

    def sector(col):
        return fnum(td_seconds(_col(dl, col))[cl].mean()) if cl.any() else None

    w = weather or {}
    return {
        "total_laps": int(lapno.notna().sum()),
        "clean_laps": int(cl.sum()),
        "avg_pace_s": fnum(clean_secs.mean()) if len(clean_secs) else None,
        "best_lap_s": fnum(secs.min()) if secs.notna().any() else None,
        "s1_avg_s": sector("Sector1Time"),
        "s2_avg_s": sector("Sector2Time"),
        "s3_avg_s": sector("Sector3Time"),
        "lap_consistency_s": fnum(clean_secs.std(ddof=0)) if len(clean_secs) > 1 else None,
        "race_pace_trend_s_per_lap": fnum(slope(lapno[cl], clean_secs), 4),
        "tyre_degradation_s_per_lap": fnum(float(np.mean(degs)), 4) if degs else None,
        "avg_stint_length": fnum(float(np.mean([s["laps"] for s in stints])), 2) if stints else None,
        "pit_stop_count": int(pit_in.sum()),
        "pit_laps": pit_laps,
        "grid_position": grid,
        "finish_position": finish,
        "status": status,
        "points": points,
        "position_changes": position_changes,
        "overtake_count": overtakes,
        "avg_gap_ahead_s": gap_ahead,
        "avg_gap_behind_s": gap_behind,
        "penalties": int(penalties or 0),
        "avg_air_temp": w.get("avg_air_temp"),
        "avg_track_temp": w.get("avg_track_temp"),
        "rainfall": bool(w.get("rainfall", False)),
    }
