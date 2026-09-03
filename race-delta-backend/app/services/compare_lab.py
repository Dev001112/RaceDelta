"""
Compare Lab: two drivers on any set of ingested races — one race, one track across seasons, or every
race matching a condition (wet, safety car, hot track...). Reads the feature store only; nothing is ingested here.
"""
from statistics import mean

from sqlalchemy import distinct, func, or_

from models import db, Constructor, Driver, DriverRaceFeature, Lap, Race, RaceSession
from app.services.feature_store import row_to_dict

TRACK_ALIASES = {"Monte Carlo": "Monaco"}          # venues renamed between seasons
HOT_TRACK_C = 40.0
COOL_TRACK_C = 25.0

MEAN_KEYS = ["avg_pace_s", "best_lap_s", "lap_consistency_s", "race_pace_trend_s_per_lap",
             "tyre_degradation_s_per_lap", "avg_stint_length", "pit_stop_count", "overtake_count",
             "position_changes", "penalties", "grid_position", "finish_position",
             "avg_gap_ahead_s", "avg_gap_behind_s", "s1_avg_s", "s2_avg_s", "s3_avg_s"]
SUM_KEYS = ["points", "total_laps", "clean_laps"]


def track_name(circuit, event_name):
    name = circuit or event_name or "Unknown"
    return TRACK_ALIASES.get(name, name)


def conditions(r: dict) -> dict:
    t = r.get("avg_track_temp")
    return {
        "wet": bool(r.get("rainfall")),
        "safety_car": (r.get("sc_laps") or 0) > 0,
        "virtual_safety_car": (r.get("vsc_laps") or 0) > 0,
        "hot": t is not None and t >= HOT_TRACK_C,
        "cool": t is not None and t < COOL_TRACK_C,
    }


def list_races() -> list:
    """Every ingested race with the metadata the Compare page filters on."""
    # FastF1 track status is a string of codes per lap: 4 = safety car, 6/7 = virtual safety car
    sc = (db.session.query(Lap.session_id, func.count(distinct(Lap.lap_number)).label("n"))
          .filter(Lap.track_status.like("%4%")).group_by(Lap.session_id).subquery())
    vsc = (db.session.query(Lap.session_id, func.count(distinct(Lap.lap_number)).label("n"))
           .filter(or_(Lap.track_status.like("%6%"), Lap.track_status.like("%7%")))
           .group_by(Lap.session_id).subquery())
    q = (db.session.query(RaceSession, Race.circuit, sc.c.n, vsc.c.n)
         .join(Race, Race.race_id == RaceSession.race_id)
         .outerjoin(sc, sc.c.session_id == RaceSession.session_id)
         .outerjoin(vsc, vsc.c.session_id == RaceSession.session_id)
         .filter(RaceSession.session_type == "R")
         .order_by(RaceSession.season, RaceSession.round))
    out = []
    for rs, circuit, sc_laps, vsc_laps in q.all():
        r = {
            "season": rs.season, "round": rs.round, "event": rs.event_name,
            "circuit": circuit, "track": track_name(circuit, rs.event_name),
            "total_laps": rs.total_laps, "rainfall": bool(rs.rainfall),
            "avg_air_temp": rs.avg_air_temp, "avg_track_temp": rs.avg_track_temp, "avg_humidity": rs.avg_humidity,
            "sc_laps": int(sc_laps or 0), "vsc_laps": int(vsc_laps or 0),
        }
        r.update(conditions(r))
        out.append(r)
    return out


def compare_on_races(driver1: str, driver2: str, races: list) -> dict:
    """races: [(season, round), ...]. Missing rows are reported as None, never ingested on the fly."""
    a, b = driver1.upper(), driver2.upper()
    wanted = {(int(s), int(r)) for s, r in races}
    meta = {(m["season"], m["round"]): m for m in list_races() if (m["season"], m["round"]) in wanted}
    teams = {c.constructor_id: c.name for c in Constructor.query.all()}
    rows = (DriverRaceFeature.query
            .filter(DriverRaceFeature.driver_code.in_([a, b]),
                    DriverRaceFeature.season.in_({s for s, _ in wanted}))
            .all())
    by = {a: {}, b: {}}
    for f in rows:
        if (f.season, f.round) in wanted:
            d = row_to_dict(f)
            d["team"] = teams.get(f.constructor_id)
            by[f.driver_code][(f.season, f.round)] = d
    drivers = {d.driver_code: {"code": d.driver_code, "name": d.full_name, "photo": d.photo_url}
               for d in Driver.query.filter(Driver.driver_code.in_([a, b])).all()}
    return build_comparison(a, b, by[a], by[b], [meta[k] for k in sorted(meta)], drivers)


def build_comparison(a, b, rows_a, rows_b, races_meta, drivers=None) -> dict:
    """Pure: per-race lines plus aggregates over the races where both drivers have data."""
    per_race, both = [], []
    for m in races_meta:
        k = (m["season"], m["round"])
        ra, rb = rows_a.get(k), rows_b.get(k)
        line = dict(m)
        line.update({"a": ra, "b": rb, "winner": _winner(ra, rb), "pace_delta_s": _delta(ra, rb, "avg_pace_s")})
        per_race.append(line)
        if ra and rb:
            both.append((ra, rb))

    wins = {a: 0, b: 0, "tie": 0}
    for ra, rb in both:
        w = _winner(ra, rb)
        wins[a if w == "A" else b if w == "B" else "tie"] += 1
    deltas = [d for d in (_delta(x, y, "avg_pace_s") for x, y in both) if d is not None]
    aggregate = {
        "races_compared": len(both),
        "wins": wins,
        "a": _means([x for x, _ in both]),
        "b": _means([y for _, y in both]),
        "avg_pace_delta_s": round(mean(deltas), 3) if deltas else None,
    }
    drivers = drivers or {}
    return {"codes": {"a": a, "b": b},
            "drivers": {a: drivers.get(a, {"code": a}), b: drivers.get(b, {"code": b})},
            "races": per_race, "aggregate": aggregate}


def _finish_rank(r):
    """Classified finishers by position, then non-finishers by laps completed."""
    if not r:
        return (2, 0)
    status = (r.get("status") or "").lower()
    classified = r.get("finish_position") is not None and (status.startswith("finished") or status.startswith("+"))
    return (0, r["finish_position"]) if classified else (1, -(r.get("total_laps") or 0))


def _winner(ra, rb):
    if not ra or not rb:
        return None
    ka, kb = _finish_rank(ra), _finish_rank(rb)
    return "A" if ka < kb else "B" if kb < ka else None


def _delta(ra, rb, key):
    if not ra or not rb or ra.get(key) is None or rb.get(key) is None:
        return None
    return round(ra[key] - rb[key], 3)


def _means(rows):
    out = {}
    for k in MEAN_KEYS:
        vals = [r[k] for r in rows if r.get(k) is not None]
        out[k] = round(mean(vals), 3) if vals else None
    for k in SUM_KEYS:
        vals = [r[k] for r in rows if r.get(k) is not None]
        out[k] = round(sum(vals), 1) if vals else None
    return out


def laps_for_race(driver1: str, driver2: str, season: int, round_num: int) -> dict:
    """Both drivers' lap rows for one race, for the lap-by-lap chart."""
    codes = [driver1.upper(), driver2.upper()]
    rs = RaceSession.query.filter_by(season=season, round=round_num, session_type="R").first()
    if not rs:
        return {"season": season, "round": round_num, "laps": {c: [] for c in codes}}
    ids = {d.driver_id: d.driver_code for d in Driver.query.filter(Driver.driver_code.in_(codes)).all()}
    laps = (Lap.query.filter(Lap.session_id == rs.session_id, Lap.driver_id.in_(list(ids)))
            .order_by(Lap.lap_number).all())
    out = {c: [] for c in codes}
    for lap in laps:
        status = lap.track_status or ""
        out[ids[lap.driver_id]].append({
            "lap": lap.lap_number, "lap_time_s": lap.lap_time_s, "position": lap.position,
            "compound": lap.compound, "pit": bool(lap.is_pit_in or lap.is_pit_out),
            "sc": "4" in status, "vsc": ("6" in status) or ("7" in status),
        })
    return {"season": season, "round": round_num, "event": rs.event_name, "total_laps": rs.total_laps, "laps": out}
