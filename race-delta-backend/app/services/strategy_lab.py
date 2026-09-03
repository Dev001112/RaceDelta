# app/services/strategy_lab.py
"""
Phase 4 — Strategy Lab.

Component A  Replay     reconstruct the race state for (driver, lap), show what the team did and
                        what the rule-based strategist would have done, lap by lap.
Component B  Simulator  re-run a driver's race under an alternative strategy (pit laps, compounds,
                        safety car, weather) with the per-race pace model (XGBoost when available)
                        and report finish position, race time, gain, podium probability, time saved.

The strategist is deliberately rule-based and explainable: every recommendation carries the rules
that fired with their numbers. Pace prediction is the learned part (pace_model.py).
All maths works on plain DataFrames (build_context); load_context() adds the DB read + a cache.
"""
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.services import pace_model as pm
from app.services.pace_model import PaceModel

DRY = ("SOFT", "MEDIUM", "HARD")
WETS = ("INTERMEDIATE", "WET")
DEFAULT_PIT_LOSS = 22.0
MIN_FINAL_STINT = 6
OUTCOME_HORIZON = 25
FLAG_FACTOR = {"GREEN": 1.0, "YELLOW": 1.05, "VSC": 1.25, "SC": 1.4, "RED": 1.0}
PIT_DISCOUNT = {"GREEN": 1.0, "YELLOW": 1.0, "VSC": 0.7, "SC": 0.5, "RED": 0.0}  # red flag: free tyre change
WET_PENALTY = 1.12   # ponytail: dry tyres in simulated rain; swap for wet-lap data once a wet race is modelled
DRY_ON_WETS = 1.10   # wet tyres on a dry track

LAP_COLUMNS = ["lap_number", "lap_time_s", "s1_s", "s2_s", "s3_s", "compound", "tyre_life", "stint", "position",
               "is_pit_in", "is_pit_out", "track_status", "is_accurate", "gap_ahead_s", "gap_behind_s"]
STINT_COLUMNS = ["stint_number", "compound", "lap_start", "lap_end", "laps", "avg_lap_time_s", "degradation_s_per_lap"]


def _f(v, nd=3):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if np.isfinite(x) else None


def _i(v):
    x = _f(v, 6)
    return int(x) if x is not None else None


@dataclass
class RaceContext:
    season: int
    round: int
    event: str
    total_laps: int
    rainfall: bool
    laps: pd.DataFrame
    stints: pd.DataFrame
    features: dict
    session_id: int = None
    n_laps: int = 0
    pit_loss_s: float = DEFAULT_PIT_LOSS
    lap_flags: dict = field(default_factory=dict)
    compound_stats: dict = field(default_factory=dict)
    compounds: list = field(default_factory=list)
    finish_times: dict = field(default_factory=dict)
    model: PaceModel = None

    def driver_laps(self, code: str) -> pd.DataFrame:
        return self.laps[self.laps["driver_code"] == code].sort_values("lap_number")

    def real_time(self, code: str):
        """Real race time if the driver completed every lap (lap 1 is often untimed: filled with median clean pace)."""
        g = self.driver_laps(code)
        if g.empty or int(g["lap_number"].max()) < self.total_laps:
            return None
        t = g["lap_time_s"].astype(float)
        if t.isna().sum() > 2:
            return None
        clean = pm.clean_laps(g)["lap_time_s"]
        return float(t.fillna(clean.median() if len(clean) else t.mean()).sum())


# ============================================================ race statistics
def estimate_pit_loss(laps: pd.DataFrame) -> float:
    """Median (in-lap + out-lap - 2 x clean median) over green-flag stops, clipped to a sane range."""
    losses = []
    for _, g in laps.groupby("driver_code"):
        g = g.sort_values("lap_number").reset_index(drop=True)
        clean = pm.clean_laps(g)["lap_time_s"]
        if clean.empty:
            continue
        ref = float(clean.median())
        for i in np.where(g["is_pit_in"].fillna(False).astype(bool))[0]:
            if i + 1 >= len(g):
                continue
            t_in, t_out = g.loc[i, "lap_time_s"], g.loc[i + 1, "lap_time_s"]
            if pd.isna(t_in) or pd.isna(t_out):
                continue
            if str(g.loc[i, "track_status"]) == pm.GREEN and str(g.loc[i + 1, "track_status"]) == pm.GREEN:
                losses.append(float(t_in) + float(t_out) - 2 * ref)
    if not losses:
        return DEFAULT_PIT_LOSS
    return float(np.clip(np.median(losses), 15.0, 40.0))


def lap_flags(laps: pd.DataFrame, total_laps: int) -> dict:
    """Majority track status per lap: GREEN / YELLOW / VSC / SC / RED."""
    flags = {}
    for lap, g in laps.groupby("lap_number"):
        s = g["track_status"].astype(str)
        if s.str.contains("5").mean() >= 0.5:
            f = "RED"
        elif s.str.contains("4").mean() >= 0.5:
            f = "SC"
        elif s.str.contains("6|7").mean() >= 0.5:
            f = "VSC"
        elif s.str.contains("2").mean() >= 0.5:
            f = "YELLOW"
        else:
            f = "GREEN"
        flags[int(lap)] = f
    for lap in range(1, int(total_laps) + 1):
        flags.setdefault(lap, "GREEN")
    return flags


def compound_stats(stints: pd.DataFrame) -> dict:
    out = {}
    if stints is None or stints.empty:
        return out
    for comp, g in stints.groupby("compound"):
        n = pd.to_numeric(g["laps"], errors="coerce").dropna()
        deg = pd.to_numeric(g["degradation_s_per_lap"], errors="coerce").dropna()
        avg = pd.to_numeric(g["avg_lap_time_s"], errors="coerce").dropna()
        out[str(comp)] = {
            "n_stints": int(len(g)),
            "typical_life": _f(n.median(), 1) if len(n) else None,
            "max_life": _f(n.quantile(0.9), 1) if len(n) else None,
            "avg_lap_time_s": _f(avg.median()) if len(avg) else None,
            "degradation_s_per_lap": _f(deg.median(), 4) if len(deg) else None,
        }
    return out


def build_context(season, round_num, event, total_laps, rainfall, laps, stints, features,
                  session_id=None, use_xgboost=True) -> RaceContext:
    laps = laps.sort_values(["driver_code", "lap_number"]).reset_index(drop=True)
    ctx = RaceContext(season=int(season), round=int(round_num), event=event, total_laps=int(total_laps),
                      rainfall=bool(rainfall), laps=laps, stints=stints, features=features or {},
                      session_id=session_id, n_laps=int(len(laps)))
    ctx.pit_loss_s = estimate_pit_loss(laps)
    ctx.lap_flags = lap_flags(laps, total_laps)
    ctx.compound_stats = compound_stats(stints)
    ctx.compounds = sorted(ctx.compound_stats)
    ctx.model = PaceModel(laps, use_xgboost=use_xgboost)
    ctx.finish_times = {code: t for code in laps["driver_code"].unique() if (t := ctx.real_time(code)) is not None}
    return ctx


# ============================================================ driver facts
def driver_strategy(ctx: RaceContext, code: str) -> dict:
    g = ctx.driver_laps(code)
    comps = g["compound"].dropna().astype(str)
    start = comps.iloc[0] if len(comps) else None
    stops = []
    for lap in g.loc[g["is_pit_in"].fillna(False).astype(bool), "lap_number"]:
        nxt = g[(g["lap_number"] > lap) & g["compound"].notna()]
        stops.append({"lap": int(lap), "compound": str(nxt.iloc[0]["compound"]) if not nxt.empty else start})
    return {"start_compound": start, "stops": stops, "n_stops": len(stops),
            "laps_completed": int(g["lap_number"].max()) if not g.empty else 0}


def race_state(ctx: RaceContext, code: str, lap: int) -> dict:
    g = ctx.driver_laps(code)
    if g.empty:
        raise ValueError(f"{code} has no laps in {ctx.event}")
    lap = int(lap)
    sel = g[g["lap_number"] == lap]
    if sel.empty:
        raise ValueError(f"{code} did not complete lap {lap} (completed {int(g['lap_number'].max())})")
    row = sel.iloc[0]
    age = _f(row["tyre_life"], 1)
    clean = pm.clean_laps(g)
    recent = clean[(clean["lap_number"] > lap - 6) & (clean["lap_number"] <= lap)]
    trend = None
    if len(recent) >= 3:
        trend = _f(np.polyfit(recent["lap_number"].astype(float), recent["lap_time_s"].astype(float), 1)[0], 3)
    median = _f(clean["lap_time_s"].median()) if len(clean) else None
    lap_time = _f(row["lap_time_s"])
    pos = _i(row["position"])
    flag = ctx.lap_flags.get(lap, "GREEN")
    same_lap = ctx.laps[ctx.laps["lap_number"] == lap]

    def neighbour(p):
        if p is None or p < 1:
            return None
        n = same_lap[same_lap["position"] == p]
        if n.empty:
            return None
        n = n.iloc[0]
        return {"driver_code": n["driver_code"], "compound": str(n["compound"]) if pd.notna(n["compound"]) else None,
                "tyre_life": _f(n["tyre_life"], 1)}

    return {
        "driver_code": code, "lap": lap, "total_laps": ctx.total_laps, "laps_remaining": ctx.total_laps - lap,
        "position": pos, "compound": str(row["compound"]) if pd.notna(row["compound"]) else None,
        "tyre_life": age, "stint": _i(row["stint"]), "stint_start": int(lap - (age or 1) + 1),
        "lap_time_s": lap_time, "delta_to_median_s": _f(lap_time - median) if lap_time is not None and median is not None else None,
        "recent_trend_s_per_lap": trend, "gap_ahead_s": _f(row["gap_ahead_s"], 1), "gap_behind_s": _f(row["gap_behind_s"], 1),
        "track_status": str(row["track_status"]), "flag": flag,
        "pit_loss_s": round(ctx.pit_loss_s, 1), "effective_pit_loss_s": round(ctx.pit_loss_s * PIT_DISCOUNT[flag], 1),
        "stops_so_far": int(g.loc[g["lap_number"] < lap, "is_pit_in"].fillna(False).astype(bool).sum()),
        "compounds_used": sorted(set(g.loc[g["lap_number"] <= lap, "compound"].dropna().astype(str))),
        "ahead": neighbour(pos - 1 if pos else None), "behind": neighbour(pos + 1 if pos else None),
        "rainfall": ctx.rainfall,
    }


def actual_decision(ctx: RaceContext, code: str, lap: int) -> dict:
    g = ctx.driver_laps(code)
    row = g[g["lap_number"] == lap].iloc[0]
    pitted = bool(row["is_pit_in"]) if pd.notna(row["is_pit_in"]) else False
    nxt = g[(g["lap_number"] > lap) & g["compound"].notna()]
    future = g.loc[(g["lap_number"] >= lap) & g["is_pit_in"].fillna(False).astype(bool), "lap_number"]
    return {"action": "PIT" if pitted else "STAY", "pitted_this_lap": pitted,
            "new_compound": str(nxt.iloc[0]["compound"]) if pitted and not nxt.empty else None,
            "next_pit_lap": int(future.iloc[0]) if len(future) else None}


# ============================================================ the strategist
def choose_compound(ctx: RaceContext, state: dict) -> str:
    R, lap, cur = state["laps_remaining"], state["lap"], state["compound"]
    field_ = ctx.laps.loc[ctx.laps["lap_number"] == lap, "compound"].dropna().astype(str)
    if len(field_) and float(field_.isin(WETS).mean()) >= 0.5:
        for c in WETS:
            if c in ctx.compounds:
                return c
    order = [c for c in DRY if c in ctx.compounds] or [c for c in DRY]
    need_second = cur in DRY and len(set(state["compounds_used"]) & set(DRY)) < 2 and state["stops_so_far"] == 0
    cands = [c for c in order if not (need_second and c == cur)] or order
    for c in cands:                                   # softest compound that can reach the flag
        if ((ctx.compound_stats.get(c) or {}).get("max_life") or 0) >= R:
            return c
    return cands[-1]


def expected_net_gain(ctx: RaceContext, state: dict, new_comp: str):
    """Seconds gained by pitting now vs staying out, over the next OUTCOME_HORIZON laps (+ = pit is better)."""
    H = min(state["laps_remaining"], OUTCOME_HORIZON)
    if H <= 0 or not new_comp or not state["compound"] or ctx.model is None:
        return None
    code, age, lap = state["driver_code"], state["tyre_life"] or 0.0, state["lap"]
    laps = np.arange(lap + 1, lap + H + 1, dtype=float)
    stay = ctx.model.predict([code] * H, [state["compound"]] * H, age + np.arange(1, H + 1), laps)
    pit = ctx.model.predict([code] * H, [new_comp] * H, np.arange(1, H + 1, dtype=float), laps)
    fac = np.array([FLAG_FACTOR[ctx.lap_flags.get(int(L), "GREEN")] for L in laps])
    eff_loss = ctx.pit_loss_s * PIT_DISCOUNT[state["flag"]]
    return {"horizon_laps": int(H), "net_gain_s": round(float(((stay - pit) * fac).sum() - eff_loss), 1),
            "pit_loss_applied_s": round(eff_loss, 1),
            "stay_out_avg_lap_s": _f(stay.mean()), "fresh_tyre_avg_lap_s": _f(pit.mean())}


def recommend(ctx: RaceContext, state: dict, with_outcome: bool = True) -> dict:
    score, reasons = 0.0, []
    R, age, comp, flag = state["laps_remaining"], state["tyre_life"] or 0.0, state["compound"], state["flag"]
    cs = ctx.compound_stats.get(comp) or {}
    typical = cs.get("typical_life") or 20.0
    max_life = cs.get("max_life") or typical * 1.3
    pit_loss, eff_loss = ctx.pit_loss_s, state["effective_pit_loss_s"]

    if R <= MIN_FINAL_STINT:
        score -= 3
        reasons.append(f"Only {R} laps left: a {eff_loss:.0f}s stop cannot be recovered.")
    else:
        if flag in ("SC", "VSC", "RED") and age >= 0.4 * typical:
            score += 2.5 if flag != "VSC" else 1.5
            reasons.append(f"{flag} deployed: pit loss drops to ~{eff_loss:.0f}s from ~{pit_loss:.0f}s, a cheap stop.")
        if age >= max_life:
            score += 2
            reasons.append(f"{comp} tyres at {age:.0f} laps, beyond this race's typical maximum of ~{max_life:.0f}.")
        elif age >= typical:
            score += 1.2
            reasons.append(f"{comp} tyres at {age:.0f} laps, past the typical {comp} stint of ~{typical:.0f}.")
        elif age < 0.5 * typical:
            score -= 1.5
            reasons.append(f"{comp} tyres are fresh ({age:.0f} of ~{typical:.0f} typical laps).")
        tr = state["recent_trend_s_per_lap"]
        if tr is not None:
            if tr >= 0.3:
                score += 1.5
                reasons.append(f"Lap times rising {tr:+.2f}s/lap over the last clean laps: heavy degradation.")
            elif tr >= 0.12:
                score += 0.8
                reasons.append(f"Lap times drifting {tr:+.2f}s/lap: degradation setting in.")
            elif tr <= -0.1:
                score -= 0.5
                reasons.append(f"Pace still improving ({tr:+.2f}s/lap): no urgency.")
        ah, ga = state["ahead"], state["gap_ahead_s"]
        if ah and ga is not None and 0 < ga < pit_loss and (ah.get("tyre_life") or 0) >= age and R > 0.5 * typical:
            score += 0.8
            reasons.append(f"Undercut window on {ah['driver_code']}: {ga:.1f}s ahead (< {pit_loss:.0f}s pit loss) on older tyres.")
        if comp in DRY and len(set(state["compounds_used"]) & set(DRY)) < 2 and state["stops_so_far"] == 0:
            if R <= max(typical, 12):
                score += 2.5
                reasons.append("A second dry compound is still mandatory and the window to take it is closing.")
            else:
                reasons.append("Second dry compound still to be taken (mandatory).")

    action = "PIT" if score >= 1.5 else "STAY"
    new_comp = choose_compound(ctx, state) if action == "PIT" else None
    if action == "PIT":
        headline = f"Pit this lap, switch to {new_comp}"
    elif score > 0:
        headline = "Stay out, pit window is opening"
    else:
        headline = "Stay out"
    win_from = int(round(state["stint_start"] + typical - 2))
    win_to = int(round(state["stint_start"] + max_life))
    win_to = min(win_to, ctx.total_laps - MIN_FINAL_STINT)
    win_from = max(min(win_from, win_to), state["stint_start"] + 3)
    rec = {"action": action, "headline": headline, "compound": new_comp,
           "confidence": round(min(0.95, 0.5 + 0.12 * abs(score)), 2), "score": round(score, 2),
           "reasons": reasons, "pit_window": {"from": win_from, "to": win_to}}
    if with_outcome:
        rec["expected_outcome"] = expected_net_gain(ctx, state, new_comp or choose_compound(ctx, state))
    return rec


# ============================================================ component A: replay
def replay(ctx: RaceContext, code: str, lap: int) -> dict:
    state = race_state(ctx, code, lap)
    rec = recommend(ctx, state, with_outcome=True)
    actual = actual_decision(ctx, code, lap)
    timeline, ai_pit_laps, agree, prev = [], [], 0, "STAY"
    g = ctx.driver_laps(code)
    for L in g["lap_number"].astype(int):
        st = race_state(ctx, code, L)
        r = recommend(ctx, st, with_outcome=False)
        pitted = bool(g.loc[g["lap_number"] == L, "is_pit_in"].fillna(False).iloc[0])
        if r["action"] == "PIT" and prev != "PIT":
            ai_pit_laps.append(int(L))
        prev = r["action"]
        agree += int((r["action"] == "PIT") == pitted)
        timeline.append({"lap": int(L), "position": st["position"], "compound": st["compound"],
                         "tyre_life": st["tyre_life"], "lap_time_s": st["lap_time_s"], "gap_ahead_s": st["gap_ahead_s"],
                         "flag": st["flag"], "pitted": pitted, "ai_action": r["action"], "ai_score": r["score"],
                         "ai_confidence": r["confidence"]})
    strat = driver_strategy(ctx, code)
    feat = ctx.features.get(code, {})
    return {
        "season": ctx.season, "round": ctx.round, "event": ctx.event, "total_laps": ctx.total_laps,
        "driver": {"driver_code": code, "name": feat.get("name"), "team": feat.get("team"),
                   "grid_position": feat.get("grid_position"), "finish_position": feat.get("finish_position"),
                   "status": feat.get("status")},
        "state": state, "actual_decision": actual, "recommendation": rec,
        "actual_strategy": strat, "actual_pit_laps": [s["lap"] for s in strat["stops"]], "ai_pit_laps": ai_pit_laps,
        "agreement_pct": round(100.0 * agree / max(1, len(timeline)), 1),
        "timeline": timeline, "pit_loss_s": round(ctx.pit_loss_s, 1), "compound_stats": ctx.compound_stats,
        "model": ctx.model.describe(), "source": "strategy_lab",
    }


# ============================================================ component B: simulator
def _stint_plan(start_compound: str, pit_stops, total_laps: int) -> list:
    stops = sorted(({"lap": int(s["lap"]), "compound": str(s["compound"]).upper()} for s in pit_stops), key=lambda s: s["lap"])
    last = 0
    for s in stops:
        if not 1 <= s["lap"] < total_laps:
            raise ValueError(f"pit lap {s['lap']} must be between 1 and {total_laps - 1}")
        if s["lap"] <= last:
            raise ValueError("pit laps must be strictly increasing")
        last = s["lap"]
    plan, start, comp = [], 1, str(start_compound).upper()
    for s in stops:
        plan.append({"compound": comp, "start": start, "end": s["lap"], "pit_at_end": True})
        start, comp = s["lap"] + 1, s["compound"]
    plan.append({"compound": comp, "start": start, "end": int(total_laps), "pit_at_end": False})
    return plan


def _describe_plan(plan) -> str:
    return " -> ".join(f"{st['compound']} {st['start']}-{st['end']}" for st in plan)


def _run_plan(ctx: RaceContext, code: str, plan: list, pace_flags: dict, pit_flags: dict, weather):
    """pace_flags: real flags (their slow laps are in everyone's real times); pit_flags: real + simulated
    neutralisations, which only make a stop cheaper (a simulated SC slows the whole field equally)."""
    total, detail = 0.0, []
    for st in plan:
        n = st["end"] - st["start"] + 1
        if n <= 0:
            continue
        laps = np.arange(st["start"], st["end"] + 1, dtype=float)
        t = ctx.model.predict([code] * n, [st["compound"]] * n, np.arange(1, n + 1, dtype=float), laps)
        t = t * np.array([FLAG_FACTOR[pace_flags.get(int(L), "GREEN")] for L in laps])
        if weather == "wet" and st["compound"] in DRY:
            t = t * WET_PENALTY
        elif weather == "dry" and st["compound"] in WETS:
            t = t * DRY_ON_WETS
        stint_time = float(t.sum())
        pit = ctx.pit_loss_s * PIT_DISCOUNT[pit_flags.get(st["end"], "GREEN")] if st["pit_at_end"] else 0.0
        total += stint_time + pit
        detail.append({"compound": st["compound"], "laps": f"{st['start']}-{st['end']}", "n_laps": int(n),
                       "stint_time_s": round(stint_time, 1), "avg_lap_s": round(stint_time / n, 3),
                       "pit_loss_s": round(pit, 1)})
    return total, detail


def simulate(ctx: RaceContext, code: str, pit_stops, start_compound=None, safety_car=None, weather=None) -> dict:
    if code not in set(ctx.laps["driver_code"]):
        raise ValueError(f"{code} has no laps in {ctx.event}")
    weather = (weather or "").lower() or None
    if weather not in (None, "dry", "wet"):
        raise ValueError("weather must be 'dry' or 'wet'")
    actual = driver_strategy(ctx, code)
    start = str(start_compound or actual["start_compound"] or "MEDIUM").upper()
    known = set(ctx.compounds) | set(DRY) | set(WETS)
    for s in pit_stops or []:
        if str(s.get("compound", "")).upper() not in known:
            raise ValueError(f"unknown compound '{s.get('compound')}'")
    if start not in known:
        raise ValueError(f"unknown start compound '{start}'")

    plan = _stint_plan(start, pit_stops or [], ctx.total_laps)
    actual_plan = _stint_plan(actual["start_compound"], actual["stops"], ctx.total_laps) if actual["start_compound"] else plan
    pit_flags = dict(ctx.lap_flags)
    if safety_car and safety_car.get("lap"):
        L0, dur = int(safety_car["lap"]), int(safety_car.get("laps", 3))
        for L in range(L0, min(L0 + dur, ctx.total_laps) + 1):
            pit_flags[L] = "SC"

    real_flags = ctx.lap_flags
    sim_actual, _ = _run_plan(ctx, code, actual_plan, real_flags, real_flags, None)        # as raced
    sim_actual_cond, _ = _run_plan(ctx, code, actual_plan, real_flags, pit_flags, weather)  # actual plan, what-if conditions
    sim_alt, detail = _run_plan(ctx, code, plan, real_flags, pit_flags, weather)
    real = ctx.real_time(code)
    bias = (real - sim_actual) if real is not None else 0.0
    alt_time = sim_alt + bias
    time_saved = sim_actual_cond - sim_alt          # like-for-like under the same what-if conditions
    # a weather change slows the whole field: scale rivals' real times by what it does to this driver's real plan
    field_scale = (sim_actual_cond / sim_actual) if (weather and sim_actual > 0) else 1.0

    others = {c: t * field_scale for c, t in ctx.finish_times.items() if c != code}
    pred_pos = 1 + sum(1 for t in others.values() if t < alt_time)
    feat = ctx.features.get(code, {})
    actual_finish = feat.get("finish_position")
    sigma = max(float(ctx.model.rmse or 0.5), 0.25) * math.sqrt(ctx.total_laps)
    srt = sorted(others.values())
    t3 = srt[2] if len(srt) >= 3 else None
    podium = 1.0 if t3 is None else 0.5 * (1 + math.erf((t3 - alt_time) / (sigma * math.sqrt(2))))

    warnings = []
    if weather != "wet" and not ctx.rainfall and len({st["compound"] for st in plan if st["compound"] in DRY}) < 2:
        warnings.append("Regulation: a dry race requires at least two different dry compounds.")
    if safety_car:
        warnings.append("A simulated Safety Car is modelled as a cheap-stop opportunity (its slow laps hit every car equally, "
                        "so they are not added to the race time); rivals' strategies are not re-optimised.")
    if weather:
        warnings.append("Weather what-if: rivals' real times are scaled by the same field-wide effect; their tyre choices are not re-simulated.")
    if real is None:
        warnings.append(f"{code} did not complete every lap in the real race, so no calibration offset was applied.")

    explanation = [
        f"Pace model: {ctx.model.kind} trained on {ctx.model.n_train} clean laps of this race (RMSE {ctx.model.rmse:.2f}s per lap).",
        f"Pit loss in this race is about {ctx.pit_loss_s:.1f}s (50% under a Safety Car, 70% under a VSC).",
        f"Actual strategy ({actual['n_stops']}-stop): {_describe_plan(actual_plan)} simulated at {sim_actual:.1f}s"
        + (f" vs {real:.1f}s real (offset {bias:+.1f}s applied)." if real is not None else "."),
        f"Alternative ({len(plan) - 1}-stop): {_describe_plan(plan)} simulated at {sim_alt:.1f}s, {time_saved:+.1f}s vs the actual strategy"
        + (" under the same what-if conditions." if (safety_car or weather) else "."),
        f"Projected {alt_time:.1f}s ranks P{pred_pos} against the other lead-lap finishers' real times.",
    ]
    return {
        "season": ctx.season, "round": ctx.round, "event": ctx.event, "driver_code": code,
        "inputs": {"start_compound": start, "pit_stops": [{"lap": s["lap"], "compound": s["compound"]} for s in
                   sorted(({"lap": int(s["lap"]), "compound": str(s["compound"]).upper()} for s in pit_stops or []), key=lambda s: s["lap"])],
                   "safety_car": safety_car, "weather": weather},
        "actual": {"finish_position": actual_finish, "race_time_s": _f(real, 1), "strategy": actual,
                   "simulated_time_s": round(sim_actual, 1)},
        "alternative": {"predicted_finish_position": int(pred_pos), "estimated_race_time_s": round(alt_time, 1),
                        "position_gain": (int(actual_finish) - int(pred_pos)) if actual_finish else None,
                        "podium_probability": round(float(podium), 3), "time_saved_s": round(time_saved, 1),
                        "simulated_time_s": round(sim_alt, 1), "stints": detail},
        "model": ctx.model.describe(), "sigma_s": round(sigma, 1),
        "explanation": explanation, "warnings": warnings, "source": "strategy_lab",
    }


# ============================================================ DB layer
_CTX = {}


def load_context(season: int, round_num: int, use_xgboost: bool = True) -> RaceContext:
    """RaceContext for a round (ingesting from FastF1 on first request), cached per process."""
    from models import db, Lap, Stint, Driver, Constructor, DriverRaceFeature
    from app.services.feature_store import ensure_race_features

    rs = ensure_race_features(season, round_num)
    if not rs:
        raise ValueError(f"No race data for {season} round {round_num}")
    n = Lap.query.filter_by(session_id=rs.session_id).count()
    key = (int(season), int(round_num))
    ctx = _CTX.get(key)
    if ctx is not None and ctx.n_laps == n and ctx.session_id == rs.session_id:
        return ctx

    lap_rows = (db.session.query(Lap, Driver.driver_code).join(Driver, Lap.driver_id == Driver.driver_id)
                .filter(Lap.session_id == rs.session_id).all())
    laps = pd.DataFrame([{**{c: getattr(l, c) for c in LAP_COLUMNS}, "driver_code": code} for l, code in lap_rows])
    stint_rows = (db.session.query(Stint, Driver.driver_code).join(Driver, Stint.driver_id == Driver.driver_id)
                  .filter(Stint.session_id == rs.session_id).all())
    stints = pd.DataFrame([{**{c: getattr(s, c) for c in STINT_COLUMNS}, "driver_code": code} for s, code in stint_rows])
    teams = {c.constructor_id: c.name for c in Constructor.query.all()}
    feats = DriverRaceFeature.query.filter_by(session_id=rs.session_id).all()
    drivers = {d.driver_id: d for d in Driver.query.filter(Driver.driver_id.in_({f.driver_id for f in feats})).all()}
    features = {}
    for f in feats:
        d = drivers.get(f.driver_id)
        features[f.driver_code] = {"grid_position": f.grid_position, "finish_position": f.finish_position,
                                   "status": f.status, "points": f.points, "pit_laps": f.pit_laps,
                                   "name": d.full_name if d else f.driver_code, "team": teams.get(f.constructor_id)}
    ctx = build_context(season, round_num, rs.event_name, rs.total_laps, rs.rainfall, laps, stints, features,
                        session_id=rs.session_id, use_xgboost=use_xgboost)
    if len(_CTX) >= 12:
        _CTX.pop(next(iter(_CTX)))
    _CTX[key] = ctx
    return ctx


def list_races(season: int) -> list:
    """Every completed round of the season. `ingested` False = not in the feature store yet
    (it is ingested from FastF1 the first time it is opened, which can take up to a minute)."""
    from sqlalchemy import func
    from models import db, RaceSession, DriverRaceFeature
    ingested = {rs.round: rs for rs in RaceSession.query.filter_by(season=season, session_type="R").all()}
    driver_counts = dict(db.session.query(DriverRaceFeature.session_id, func.count())
                         .filter(DriverRaceFeature.session_id.in_([rs.session_id for rs in ingested.values()]))
                         .group_by(DriverRaceFeature.session_id).all()) if ingested else {}
    rounds = {}
    try:
        import fastf1
        import app.fastf1_setup  # noqa: F401
        from datetime import datetime
        sched = fastf1.get_event_schedule(season)
        sched = sched[sched["RoundNumber"] > 0]
        if "EventFormat" in sched.columns:
            sched = sched[sched["EventFormat"] != "testing"]
        dates = sched["EventDate"]
        if dates.dt.tz is not None:
            dates = dates.dt.tz_convert(None)
        for _, ev in sched[dates < datetime.utcnow()].iterrows():
            rounds[int(ev["RoundNumber"])] = str(ev["EventName"])
    except Exception:  # schedule unavailable: fall back to what is already in the store
        pass
    for r, rs in ingested.items():
        rounds.setdefault(r, rs.event_name)
    out = []
    for r in sorted(rounds):
        rs = ingested.get(r)
        out.append({"round": r, "event": rs.event_name if rs else rounds[r], "ingested": rs is not None,
                    "total_laps": rs.total_laps if rs else None, "rainfall": rs.rainfall if rs else None,
                    "drivers": driver_counts.get(rs.session_id, 0) if rs else 0})
    return out


def race_overview(ctx: RaceContext) -> dict:
    drivers = []
    for code in sorted(ctx.laps["driver_code"].unique()):
        f = ctx.features.get(code, {})
        drivers.append({"driver_code": code, "name": f.get("name", code), "team": f.get("team"),
                        "grid_position": f.get("grid_position"), "finish_position": f.get("finish_position"),
                        "status": f.get("status"), **driver_strategy(ctx, code)})
    drivers.sort(key=lambda d: (d["finish_position"] is None, d["finish_position"] or 99, d["driver_code"]))
    return {
        "season": ctx.season, "round": ctx.round, "event": ctx.event, "total_laps": ctx.total_laps,
        "rainfall": ctx.rainfall, "pit_loss_s": round(ctx.pit_loss_s, 1), "compounds": ctx.compounds,
        "compound_stats": ctx.compound_stats,
        "sc_laps": [l for l, f in ctx.lap_flags.items() if f == "SC"],
        "vsc_laps": [l for l, f in ctx.lap_flags.items() if f == "VSC"],
        "model": ctx.model.describe(), "drivers": drivers, "source": "strategy_lab",
    }
