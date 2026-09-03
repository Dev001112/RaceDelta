# app/services/race_analyst_tools.py
"""
Tools for the AI Race Analyst (Phase 5).

Every tool answers ONLY from RaceDelta's own data (feature store, laps/stints, Strategy Lab,
driver intelligence) and returns   {"data": <compact JSON>, "summary": <plain-English answer>}.
The summary is what the model reads first and doubles as the answer in offline (no-key) mode.

Analysis functions take a RaceContext so they are unit-testable on a synthetic race;
execute_tool() resolves the context from the DB via `ctx_provider`.
"""
import re

import numpy as np
import pandas as pd

from app.services import pace_model as pm
from app.services import strategy_lab as sl

TEAM_ALIASES = {
    "red bull": "Red Bull Racing", "redbull": "Red Bull Racing", "rbr": "Red Bull Racing",
    "racing bulls": "Racing Bulls", "vcarb": "Racing Bulls", "rb": "Racing Bulls",
    "sauber": "Kick Sauber", "kick sauber": "Kick Sauber", "haas": "Haas F1 Team",
    "ferrari": "Ferrari", "mclaren": "McLaren", "mercedes": "Mercedes", "merc": "Mercedes",
    "aston martin": "Aston Martin", "aston": "Aston Martin", "alpine": "Alpine", "williams": "Williams",
}
SECTORS = ("s1_s", "s2_s", "s3_s")


def _f(v, nd=3):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if np.isfinite(x) else None


def _fmt(v, nd=3, unit="s"):
    return "n/a" if v is None else f"{v:.{nd}f}{unit}"


def _pos(p):
    return f"P{p}" if p else "DNF"


# ============================================================ name resolution
def resolve_driver(ctx: sl.RaceContext, text):
    """'VER', 'Verstappen', 'Max Verstappen' -> 'VER' (None when nobody matches)."""
    if not text:
        return None
    t = str(text).strip()
    codes = set(ctx.laps["driver_code"].unique())
    if t.upper() in codes:
        return t.upper()
    tl = t.lower()
    for code, f in ctx.features.items():
        name = (f.get("name") or "").lower()
        if name and (tl == name or tl in name.split() or tl in name):
            return code
    return None


def resolve_team(ctx: sl.RaceContext, text):
    if not text:
        return None
    tl = str(text).strip().lower()
    teams = {f.get("team") for f in ctx.features.values() if f.get("team")}
    for team in teams:
        if tl == team.lower() or tl in team.lower():
            return team
    alias = TEAM_ALIASES.get(tl)
    if alias:
        for team in teams:
            if alias.lower() in team.lower() or team.lower() in alias.lower():
                return team
    return None


def _drivers_of_team(ctx, team):
    return [c for c, f in ctx.features.items() if (f.get("team") or "").lower() == team.lower()]


# ============================================================ pace helpers
def _pace_block(g: pd.DataFrame) -> dict:
    clean = pm.clean_laps(g)
    secs = clean["lap_time_s"].astype(float)
    out = {"laps": int(len(g)), "clean_laps": int(len(clean)),
           "avg_pace_s": _f(secs.mean()) if len(secs) else None,
           "best_lap_s": _f(g["lap_time_s"].min()) if g["lap_time_s"].notna().any() else None,
           "consistency_s": _f(secs.std(ddof=0)) if len(secs) > 1 else None}
    for col in SECTORS:
        out[col.replace("_s", "_avg_s")] = _f(pd.to_numeric(clean[col], errors="coerce").mean()) if col in clean and len(clean) else None
    return out


def _winner(ctx):
    rows = [(f.get("finish_position"), c) for c, f in ctx.features.items() if f.get("finish_position")]
    return min(rows)[1] if rows else None


# ============================================================ analyses
def race_summary(ctx: sl.RaceContext) -> dict:
    order = sorted(ctx.features.items(), key=lambda kv: (kv[1].get("finish_position") is None, kv[1].get("finish_position") or 99))
    classification = []
    for code, f in order:
        strat = sl.driver_strategy(ctx, code)
        classification.append({"position": f.get("finish_position"), "driver_code": code, "name": f.get("name"), "team": f.get("team"),
                               "grid": f.get("grid_position"), "points": f.get("points"), "status": f.get("status"),
                               "stops": strat["n_stops"], "strategy": strat["start_compound"] and
                               " -> ".join([strat["start_compound"]] + [s["compound"] for s in strat["stops"]])})
    best = None
    for code in ctx.laps["driver_code"].unique():
        g = ctx.driver_laps(code)
        bl = _f(g["lap_time_s"].min())
        if bl is not None and (best is None or bl < best[1]):
            best = (code, bl)
    data = {"season": ctx.season, "round": ctx.round, "event": ctx.event, "total_laps": ctx.total_laps,
            "rainfall": ctx.rainfall, "pit_loss_s": round(ctx.pit_loss_s, 1),
            "safety_car_laps": [l for l, f in ctx.lap_flags.items() if f == "SC"],
            "vsc_laps": [l for l, f in ctx.lap_flags.items() if f == "VSC"],
            "compounds": ctx.compounds, "fastest_lap": {"driver_code": best[0], "lap_time_s": best[1]} if best else None,
            "classification": classification}
    top = classification[:3]
    podium = ", ".join(f"{_pos(r['position'])} {r['driver_code']} ({r['team']}, {r['strategy'] or '?'})" for r in top)
    sc = data["safety_car_laps"]
    summary = (f"{ctx.event} ({ctx.season} R{ctx.round}), {ctx.total_laps} laps, {'wet' if ctx.rainfall else 'dry'}. "
               f"Podium: {podium}. Pit loss about {ctx.pit_loss_s:.0f}s; "
               f"{'Safety Car on laps ' + ', '.join(map(str, sc)) if sc else 'no Safety Car'}. "
               + (f"Fastest lap {best[0]} {best[1]:.3f}s." if best else ""))
    return {"data": data, "summary": summary}


def driver_race(ctx: sl.RaceContext, code: str) -> dict:
    code = resolve_driver(ctx, code) or code
    if code not in set(ctx.laps["driver_code"]):
        raise ValueError(f"No data for driver '{code}' in {ctx.event}")
    f = ctx.features.get(code, {})
    g = ctx.driver_laps(code)
    pace = _pace_block(g)
    strat = sl.driver_strategy(ctx, code)
    stints = []
    if ctx.stints is not None and not ctx.stints.empty:
        for _, s in ctx.stints[ctx.stints["driver_code"] == code].sort_values("stint_number").iterrows():
            stints.append({"stint": int(s["stint_number"]), "compound": s["compound"], "laps": f"{int(s['lap_start'])}-{int(s['lap_end'])}",
                           "avg_lap_time_s": _f(s["avg_lap_time_s"]), "degradation_s_per_lap": _f(s["degradation_s_per_lap"], 4)})
    # pace rank within the field
    field = sorted(((_pace_block(ctx.driver_laps(c))["avg_pace_s"] or 999, c) for c in ctx.laps["driver_code"].unique()))
    rank = next((i for i, (_, c) in enumerate(field, 1) if c == code), None)
    winner = _winner(ctx)
    wpace = _pace_block(ctx.driver_laps(winner))["avg_pace_s"] if winner else None
    delta_w = _f(pace["avg_pace_s"] - wpace) if pace["avg_pace_s"] is not None and wpace is not None else None
    data = {"driver_code": code, "name": f.get("name"), "team": f.get("team"), "grid": f.get("grid_position"),
            "finish": f.get("finish_position"), "status": f.get("status"), "points": f.get("points"),
            "penalties": f.get("penalties"), "pace": pace, "pace_rank_in_field": rank, "delta_to_winner_pace_s": delta_w,
            "strategy": strat, "stints": stints}
    summary = (f"{f.get('name') or code} ({code}, {f.get('team')}): grid {_pos(data['grid'])} -> {_pos(data['finish'])}"
               f"{' (' + str(f.get('status')) + ')' if f.get('status') and f.get('status') != 'Finished' else ''}. "
               f"Average clean pace {_fmt(pace['avg_pace_s'])} (rank {rank} of {len(field)} in the field"
               + (f", {delta_w:+.3f}s/lap vs winner {winner}" if delta_w is not None else "") + f"), best lap {_fmt(pace['best_lap_s'])}, "
               f"consistency sigma {_fmt(pace['consistency_s'])}. Strategy: {strat['start_compound']} start, {strat['n_stops']} stop(s)"
               + (": " + ", ".join(f"lap {s['lap']} -> {s['compound']}" for s in strat["stops"]) if strat["stops"] else "") + ".")
    return {"data": data, "summary": summary}


def compare_drivers(ctx: sl.RaceContext, a: str, b: str, stint=None) -> dict:
    ca, cb = resolve_driver(ctx, a), resolve_driver(ctx, b)
    if not ca or not cb:
        raise ValueError(f"Could not resolve drivers '{a}' / '{b}' in {ctx.event}")
    blocks, meta = {}, {}
    for code in (ca, cb):
        g = ctx.driver_laps(code)
        if stint is not None:
            g = g[pd.to_numeric(g["stint"], errors="coerce") == int(stint)]
            if g.empty:
                raise ValueError(f"{code} has no laps in stint {stint}")
        blocks[code] = _pace_block(g)
        comp = g["compound"].dropna().astype(str)
        meta[code] = {"compound": comp.iloc[0] if len(comp) else None, "laps": f"{int(g['lap_number'].min())}-{int(g['lap_number'].max())}",
                      "finish": ctx.features.get(code, {}).get("finish_position"), "strategy": sl.driver_strategy(ctx, code)}
    A, B = blocks[ca], blocks[cb]

    def d(k):
        return _f(A[k] - B[k]) if A.get(k) is not None and B.get(k) is not None else None

    deltas = {"avg_pace_s": d("avg_pace_s"), "best_lap_s": d("best_lap_s"), "consistency_s": d("consistency_s"),
              "s1_avg_s": d("s1_avg_s"), "s2_avg_s": d("s2_avg_s"), "s3_avg_s": d("s3_avg_s")}
    sec = {k: v for k, v in deltas.items() if k.startswith("s") and k != "s" and v is not None and k[1].isdigit()}
    scope = f"stint {stint}" if stint is not None else "the race"
    faster = ca if (deltas["avg_pace_s"] or 0) < 0 else cb
    slower = cb if faster == ca else ca
    lines = [f"Over {scope}, {faster} was faster on average by {abs(deltas['avg_pace_s'] or 0):.3f}s/lap "
             f"({ca} {_fmt(A['avg_pace_s'])} vs {cb} {_fmt(B['avg_pace_s'])}, clean laps {A['clean_laps']}/{B['clean_laps']})."]
    if sec:
        parts = []
        for k in ("s1_avg_s", "s2_avg_s", "s3_avg_s"):
            if k in sec:
                who = ca if sec[k] < 0 else cb
                parts.append(f"S{k[1]}: {who} by {abs(sec[k]):.3f}s")
        biggest = min(sec, key=lambda k: -abs(sec[k]))
        lines.append("Sector deltas: " + "; ".join(parts) + f". The largest gap is in Sector {biggest[1]}.")
    lines.append(f"Best laps {ca} {_fmt(A['best_lap_s'])} vs {cb} {_fmt(B['best_lap_s'])}; "
                 f"consistency sigma {ca} {_fmt(A['consistency_s'])} vs {cb} {_fmt(B['consistency_s'])}.")
    if stint is not None:
        lines.append(f"Compounds in stint {stint}: {ca} {meta[ca]['compound']} (laps {meta[ca]['laps']}), {cb} {meta[cb]['compound']} (laps {meta[cb]['laps']}).")
    else:
        lines.append(f"Finish: {ca} {_pos(meta[ca]['finish'])} ({meta[ca]['strategy']['n_stops']} stop), {cb} {_pos(meta[cb]['finish'])} ({meta[cb]['strategy']['n_stops']} stop).")
    data = {"season": ctx.season, "round": ctx.round, "event": ctx.event, "scope": scope, "stint": stint,
            "drivers": {ca: {**A, **meta[ca]}, cb: {**B, **meta[cb]}}, "deltas_a_minus_b": deltas, "faster": faster, "slower": slower}
    return {"data": data, "summary": " ".join(lines)}


def pit_stops(ctx: sl.RaceContext, code=None) -> dict:
    stops = []
    codes = [resolve_driver(ctx, code) or code] if code else list(ctx.laps["driver_code"].unique())
    last_lap = int(ctx.laps["lap_number"].max())
    for c in codes:
        g = ctx.driver_laps(c).set_index("lap_number")
        for lap in g.index[g["is_pit_in"].fillna(False).astype(bool)]:
            lap = int(lap)
            before = g["position"].get(lap - 1, g["position"].get(lap))
            after_lap = min(lap + 5, last_lap)   # let the field's own stops settle before judging the swing
            after = g["position"].get(after_lap)
            comp_from = g["compound"].get(lap)
            nxt = g.loc[g.index > lap, "compound"].dropna()
            comp_to = nxt.iloc[0] if len(nxt) else None
            flag = ctx.lap_flags.get(lap, "GREEN")
            places = (int(before) - int(after)) if pd.notna(before) and pd.notna(after) else None
            stops.append({"driver_code": c, "lap": lap, "from": comp_from, "to": comp_to, "flag": flag,
                          "position_before": int(before) if pd.notna(before) else None,
                          "position_after": int(after) if pd.notna(after) else None, "places_gained": places})
    stops.sort(key=lambda s: (-(s["places_gained"] or -99), s["lap"]))
    data = {"season": ctx.season, "round": ctx.round, "event": ctx.event, "pit_loss_s": round(ctx.pit_loss_s, 1),
            "n_stops": len(stops), "stops": stops}
    if not stops:
        return {"data": data, "summary": f"No pit stops recorded for {code or 'any driver'} in {ctx.event}."}
    top = stops[0]
    under = f" under the {top['flag']}" if top["flag"] != "GREEN" else ""
    if (top["places_gained"] or 0) > 0:
        summary = (f"{len(stops)} stops in {ctx.event} (pit loss about {ctx.pit_loss_s:.0f}s). The most decisive was "
                   f"{top['driver_code']}'s lap {top['lap']} stop ({top['from']} -> {top['to']}{under}): "
                   f"{_pos(top['position_before'])} -> {_pos(top['position_after'])} five laps later ({top['places_gained']:+d} places). ")
    else:
        summary = (f"{len(stops)} stops in {ctx.event} (pit loss about {ctx.pit_loss_s:.0f}s). No stop changed the running order: "
                   f"the field pitted in the same window and positions were held through the cycle, so the most decisive factor was track position, not a stop. ")
    sc_stops = [s for s in stops if s["flag"] in ("SC", "VSC")]
    if sc_stops:
        summary += f"{len(sc_stops)} stop(s) were taken under a neutralisation (cheap stops): " + \
                   ", ".join(f"{s['driver_code']} lap {s['lap']}" for s in sc_stops[:6]) + ". "
    worst = stops[-1]
    if worst is not top and worst["places_gained"] is not None:
        summary += f"The costliest was {worst['driver_code']}'s lap {worst['lap']} stop ({worst['places_gained']:+d} places)."
    return {"data": data, "summary": summary}


def team_race(ctx: sl.RaceContext, team: str) -> dict:
    tname = resolve_team(ctx, team)
    if not tname:
        raise ValueError(f"Team '{team}' not found in {ctx.event}")
    codes = _drivers_of_team(ctx, tname)
    winner = _winner(ctx)
    wpace = _pace_block(ctx.driver_laps(winner))["avg_pace_s"] if winner else None
    drivers = []
    for c in codes:
        f = ctx.features.get(c, {})
        p = _pace_block(ctx.driver_laps(c))
        strat = sl.driver_strategy(ctx, c)
        drivers.append({"driver_code": c, "name": f.get("name"), "grid": f.get("grid_position"), "finish": f.get("finish_position"),
                        "status": f.get("status"), "points": f.get("points"), "penalties": f.get("penalties"),
                        "avg_pace_s": p["avg_pace_s"], "delta_to_winner_pace_s": _f(p["avg_pace_s"] - wpace) if p["avg_pace_s"] and wpace else None,
                        "consistency_s": p["consistency_s"], "stops": strat["n_stops"],
                        "strategy": strat["start_compound"] and " -> ".join([strat["start_compound"]] + [s["compound"] for s in strat["stops"]]),
                        "pit_laps": [s["lap"] for s in strat["stops"]]})
    drivers.sort(key=lambda d: (d["finish"] is None, d["finish"] or 99))
    best = drivers[0] if drivers else None
    wname = ctx.features.get(winner, {}).get("team") if winner else None
    reasons = []
    for d in drivers:
        if d["delta_to_winner_pace_s"] is not None and d["delta_to_winner_pace_s"] > 0.15:
            reasons.append(f"{d['driver_code']} lacked pace: {d['delta_to_winner_pace_s']:+.3f}s/lap vs the winner")
        if d["status"] and d["status"] != "Finished":
            reasons.append(f"{d['driver_code']} did not finish ({d['status']})")
        if (d["penalties"] or 0) > 0:
            reasons.append(f"{d['driver_code']} took {d['penalties']} penalty/penalties")
        if d["grid"] and d["finish"] and d["finish"] > d["grid"]:
            reasons.append(f"{d['driver_code']} lost {d['finish'] - d['grid']} places from {_pos(d['grid'])} on the grid")
    won = winner in codes
    summary = (f"{tname} in {ctx.event}: " + "; ".join(f"{d['driver_code']} {_pos(d['grid'])} -> {_pos(d['finish'])} ({d['strategy'] or '?'}, {d['stops']} stop)" for d in drivers) + ". ")
    if won:
        summary += f"{tname} won with {winner}."
    else:
        summary += f"The race was won by {winner} ({wname}). " + ("Why they lost: " + "; ".join(reasons) + "." if reasons else
                                                                    f"Pace was close to the winner ({best['delta_to_winner_pace_s']:+.3f}s/lap for {best['driver_code']}); the result came down to track position and strategy timing.")
    data = {"season": ctx.season, "round": ctx.round, "event": ctx.event, "team": tname, "won": won, "winner": winner,
            "winner_team": wname, "drivers": drivers, "reasons": reasons}
    return {"data": data, "summary": summary}


def strategy_replay(ctx: sl.RaceContext, code: str, lap: int) -> dict:
    c = resolve_driver(ctx, code) or code
    r = sl.replay(ctx, c, int(lap))
    rec, act, st = r["recommendation"], r["actual_decision"], r["state"]
    data = {"driver_code": c, "lap": int(lap), "state": st, "team_decision": act, "ai_recommendation": rec,
            "actual_pit_laps": r["actual_pit_laps"], "ai_pit_laps": r["ai_pit_laps"], "agreement_pct": r["agreement_pct"]}
    summary = (f"Lap {lap}, {c} {_pos(st['position'])} on {st['compound']} ({st['tyre_life']} laps old), {st['flag']} flag, "
               f"{st['laps_remaining']} laps left, gap ahead {st['gap_ahead_s']}s. Team: {act['action']}"
               + (f" (next real stop lap {act['next_pit_lap']})" if act.get("next_pit_lap") and act["action"] == "STAY" else "") +
               f". RaceDelta AI: {rec['headline']} (confidence {int(rec['confidence'] * 100)}%). Reasons: " + " ".join(rec["reasons"]) +
               f" Over the race the AI agreed with the team on {r['agreement_pct']}% of laps; AI pit laps {r['ai_pit_laps']} vs actual {r['actual_pit_laps']}.")
    return {"data": data, "summary": summary}


def simulate_strategy(ctx: sl.RaceContext, code: str, pit_stops_, start_compound=None, safety_car=None, weather=None) -> dict:
    c = resolve_driver(ctx, code) or code
    r = sl.simulate(ctx, c, pit_stops_ or [], start_compound=start_compound, safety_car=safety_car, weather=weather)
    a = r["alternative"]
    data = {"driver_code": c, "inputs": r["inputs"], "actual": {k: v for k, v in r["actual"].items() if k != "strategy"},
            "alternative": {k: v for k, v in a.items() if k != "stints"}, "stints": a["stints"], "warnings": r["warnings"]}
    summary = (f"Simulated {c} with {sl._describe_plan(sl._stint_plan(r['inputs']['start_compound'], r['inputs']['pit_stops'], ctx.total_laps))}: "
               f"predicted {_pos(a['predicted_finish_position'])} (actual {_pos(r['actual']['finish_position'])}), "
               f"{a['time_saved_s']:+.1f}s vs the real strategy, podium probability {int(a['podium_probability'] * 100)}%. "
               + " ".join(r["explanation"][2:4]) + (" " + " ".join(r["warnings"]) if r["warnings"] else ""))
    return {"data": data, "summary": summary}


# ============================================================ tool registry (Claude tool definitions)
def _race_props(extra=None):
    props = {"season": {"type": "integer", "description": "Season year, e.g. 2025"},
             "round": {"type": "integer", "description": "Round number within the season"}}
    props.update(extra or {})
    return props


TOOLS = [
    {"name": "get_race_summary", "description": "Classification, podium, strategies, weather, Safety Car laps, pit loss and fastest lap for one race. Call this first when the race is not yet known.",
     "input_schema": {"type": "object", "properties": _race_props(), "required": ["season", "round"], "additionalProperties": False}},
    {"name": "get_driver_race", "description": "One driver's race: result, clean-lap pace and rank in the field, sectors, consistency, strategy and per-stint pace/degradation. Driver may be a code (VER) or a name (Verstappen).",
     "input_schema": {"type": "object", "properties": _race_props({"driver": {"type": "string"}}), "required": ["season", "round", "driver"], "additionalProperties": False}},
    {"name": "compare_drivers", "description": "Head-to-head pace, sector-by-sector deltas, best lap and consistency for two drivers over the race or over one stint number.",
     "input_schema": {"type": "object", "properties": _race_props({"driver_a": {"type": "string"}, "driver_b": {"type": "string"},
                                                                  "stint": {"type": ["integer", "null"], "description": "Restrict to this stint number (1 = first stint); null for the whole race"}}),
                      "required": ["season", "round", "driver_a", "driver_b", "stint"], "additionalProperties": False}},
    {"name": "get_pit_stops", "description": "Every pit stop with compound change, flag (SC/VSC) and positions before/after, ranked by places gained; identifies the most decisive stop. Optional driver filter.",
     "input_schema": {"type": "object", "properties": _race_props({"driver": {"type": ["string", "null"]}}), "required": ["season", "round", "driver"], "additionalProperties": False}},
    {"name": "get_team_race", "description": "Both drivers of a constructor: results, pace vs the winner, strategies, penalties, and the data-backed reasons the team won or lost.",
     "input_schema": {"type": "object", "properties": _race_props({"team": {"type": "string", "description": "e.g. Ferrari, McLaren, Red Bull"}}), "required": ["season", "round", "team"], "additionalProperties": False}},
    {"name": "get_strategy_replay", "description": "Race state at a given lap for a driver, the team's actual pit decision and RaceDelta's explainable AI recommendation with reasons.",
     "input_schema": {"type": "object", "properties": _race_props({"driver": {"type": "string"}, "lap": {"type": "integer"}}), "required": ["season", "round", "driver", "lap"], "additionalProperties": False}},
    {"name": "simulate_strategy", "description": "What-if simulation with the per-race pace model: alternative pit laps/compounds, optional safety car and weather. Returns predicted finish, time saved and podium probability.",
     "input_schema": {"type": "object", "properties": _race_props({
         "driver": {"type": "string"},
         "pit_stops": {"type": "array", "items": {"type": "object", "properties": {"lap": {"type": "integer"}, "compound": {"type": "string", "enum": ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]}}, "required": ["lap", "compound"], "additionalProperties": False}},
         "start_compound": {"type": ["string", "null"], "enum": ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET", None]},
         "safety_car_lap": {"type": ["integer", "null"]}, "weather": {"type": ["string", "null"], "enum": ["dry", "wet", None]}}),
                      "required": ["season", "round", "driver", "pit_stops", "start_compound", "safety_car_lap", "weather"], "additionalProperties": False}},
    {"name": "get_driver_rating", "description": "Season-long AI Driver Rating (0-100) with component scores, ranked. Use for 'who is the best driver' style questions.",
     "input_schema": {"type": "object", "properties": {"season": {"type": "integer"}, "top": {"type": "integer", "description": "How many drivers to return"}}, "required": ["season", "top"], "additionalProperties": False}},
    {"name": "get_driver_dna", "description": "A driver's season DNA vector (relative strengths) and the most similar drivers.",
     "input_schema": {"type": "object", "properties": {"season": {"type": "integer"}, "driver": {"type": "string"}}, "required": ["season", "driver"], "additionalProperties": False}},
]
for _t in TOOLS:
    _t["strict"] = True


def execute_tool(name: str, args: dict, ctx_provider) -> dict:
    """Run one tool. Raises ValueError for user-fixable problems (unknown driver/team/lap)."""
    # models fill optional slots with the string "None"/"null" instead of JSON null, which would
    # otherwise be looked up as a driver name and answer "no pit stops recorded for None"
    args = {k: (None if isinstance(v, str) and v.strip().lower() in ("", "none", "null", "n/a") else v)
            for k, v in (args or {}).items()}
    if name in ("get_driver_rating", "get_driver_dna"):
        from app.services import driver_intelligence as di
        if name == "get_driver_rating":
            r = di.rating_for_season(int(args["season"]))
            top = r["drivers"][: int(args.get("top") or 10)]
            data = [{k: d[k] for k in ("rank", "driver_code", "name", "team", "rating", "races", "strongest")} for d in top]
            summary = f"AI Driver Rating {args['season']} (top {len(top)}): " + "; ".join(
                f"#{d['rank']} {d['driver_code']} {d['rating']} (strongest: {d['strongest'].replace('_', ' ')})" for d in top) + "."
            return {"data": data, "summary": summary}
        r = di.dna_for_season(int(args["season"]), str(args["driver"]))
        vec = sorted(r["vector"].items(), key=lambda kv: -kv[1])
        summary = (f"{r['driver_code']} DNA {args['season']}: strongest {', '.join(f'{k.replace('_', ' ')} ({v:+.2f})' for k, v in vec[:3])}; "
                   f"weakest {', '.join(f'{k.replace('_', ' ')} ({v:+.2f})' for k, v in vec[-2:])}. Most similar: "
                   + ", ".join(f"{s['driver_code']} ({int(s['cosine_similarity'] * 100)}%)" for s in r["similar"][:3]) + ".")
        return {"data": {"driver_code": r["driver_code"], "vector": r["vector"], "similar": r["similar"][:5]}, "summary": summary}

    ctx = ctx_provider(int(args["season"]), int(args["round"]))
    if name == "get_race_summary":
        return race_summary(ctx)
    if name == "get_driver_race":
        return driver_race(ctx, args["driver"])
    if name == "compare_drivers":
        return compare_drivers(ctx, args["driver_a"], args["driver_b"], args.get("stint"))
    if name == "get_pit_stops":
        return pit_stops(ctx, args.get("driver"))
    if name == "get_team_race":
        return team_race(ctx, args["team"])
    if name == "get_strategy_replay":
        return strategy_replay(ctx, args["driver"], int(args["lap"]))
    if name == "simulate_strategy":
        sc = {"lap": int(args["safety_car_lap"]), "laps": 3} if args.get("safety_car_lap") else None
        return simulate_strategy(ctx, args["driver"], args.get("pit_stops") or [], args.get("start_compound"), sc, args.get("weather"))
    raise ValueError(f"Unknown tool '{name}'")
