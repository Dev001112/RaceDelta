"""
Compare verdict: who is better and how, for a Compare Lab comparison.

Fixed rules score nine areas from the aggregate features (always available, fully explainable). When an
NVIDIA-hosted model is configured it rewrites those findings into prose, but it is given only these numbers.
"""
import json
import logging
import os
import re

import requests

from app.services import cache_store, compare_lab

logger = logging.getLogger(__name__)

# key, label, feature, lower_is_better, weight, scale (a gap this big is decisive), unit
AREAS = [
    ("race_pace",   "Race pace",        "avg_pace_s",                 True,  3.0, 1.0,  "s/lap"),
    ("peak_pace",   "Peak pace",        "best_lap_s",                 True,  1.0, 1.0,  "s"),
    ("qualifying",  "Qualifying",       "grid_position",              True,  1.0, 5.0,  "places"),
    ("result",      "Result",           "finish_position",            True,  2.0, 5.0,  "places"),
    ("consistency", "Consistency",      "lap_consistency_s",          True,  1.0, 0.5,  "s"),
    ("tyres",       "Tyre management",  "tyre_degradation_s_per_lap", True,  1.0, 0.05, "s/lap"),
    ("overtaking",  "Overtaking",       "overtake_count",             False, 1.0, 5.0,  "overtakes"),
    ("racecraft",   "Positions gained", "position_changes",           False, 1.0, 5.0,  "places"),
]
LEVEL = 0.05            # |r| under this counts as level
CLEAR, EDGE = 0.35, 0.12
VERDICT_TTL = 24 * 3600
NARRATIVE_TIMEOUT = int(os.getenv("VERDICT_NARRATIVE_TIMEOUT", "45"))   # background call, so a slow model is fine
NARRATIVE_ATTEMPTS = int(os.getenv("VERDICT_NARRATIVE_ATTEMPTS", "2"))
PLURAL_UNITS = {"wins", "places", "overtakes"}


def _fmt(v, d=3):
    return str(v) if isinstance(v, int) else f"{v:.{d}f}".rstrip("0").rstrip(".")


def _area(key, label, va, vb, r, weight, unit):
    leader = "A" if r > LEVEL else "B" if r < -LEVEL else None
    gap = None if va is None or vb is None else round(abs(va - vb), 3)
    return {"key": key, "label": label, "a": va, "b": vb, "leader": leader, "r": round(r, 3), "weight": weight,
            "unit": unit, "gap": gap,
            "score_a": None if va is None or vb is None else round(50 + 50 * r, 1),
            "score_b": None if va is None or vb is None else round(50 - 50 * r, 1),
            "detail": "no data" if gap is None else (f"{_fmt(gap)} {_unit(gap, unit)}" if leader else "level")}


def _unit(gap, unit):
    return unit[:-1] if unit in PLURAL_UNITS and gap == 1 else unit


def score_areas(a: dict, b: dict, wins=None, n=0) -> list:
    """Signed r per area: positive means driver A is better; |r| = 1 is a decisive gap."""
    out = []
    for key, label, feat, lower, weight, scale, unit in AREAS:
        va, vb = a.get(feat), b.get(feat)
        if va is None or vb is None:
            out.append(_area(key, label, va, vb, 0.0, weight, unit))
            continue
        diff = (vb - va) if lower else (va - vb)
        out.append(_area(key, label, va, vb, max(-1.0, min(1.0, diff / scale)), weight, unit))
    if wins and n:
        wa, wb = wins.get("a", 0), wins.get("b", 0)
        out.insert(0, _area("head_to_head", "Head-to-head", wa, wb, (wa - wb) / n, 2.0, "wins"))
    return out


def verdict(comparison: dict) -> dict:
    """Rule-based verdict from a compare_lab comparison payload."""
    codes = comparison["codes"]
    a, b = codes["a"], codes["b"]
    agg = comparison["aggregate"]
    n = agg["races_compared"]
    names = {c: (comparison.get("drivers", {}).get(c) or {}).get("name") or c for c in (a, b)}
    base = {"codes": codes, "names": names, "source": "rules", "model": None, "races_compared": n}
    if n == 0:
        return {**base, "winner": None, "confidence": 0.0, "headline": "Not enough shared races",
                "summary": f"{a} and {b} have no race in this set with telemetry for both, so there is nothing to weigh.",
                "areas": [], "caveats": []}

    wins = {"a": agg["wins"].get(a, 0), "b": agg["wins"].get(b, 0)}
    areas = score_areas(agg["a"], agg["b"], wins, n)
    scored = [x for x in areas if x["score_a"] is not None]
    total = sum(x["r"] * x["weight"] for x in scored)
    wsum = sum(x["weight"] for x in scored) or 1.0
    confidence = round(abs(total) / wsum, 3)
    winner = None if confidence < EDGE else (a if total > 0 else b)
    w_side = "A" if winner == a else "B"

    if winner is None:
        headline = "Too close to call"
    elif confidence >= CLEAR:
        headline = f"{winner} comes out clearly ahead"
    else:
        headline = f"{winner} edges it"

    def side_code(s):
        return a if s == "A" else b

    lead = sorted([x for x in scored if x["leader"] == (w_side if winner else "A")], key=lambda x: -abs(x["r"]))
    other = sorted([x for x in scored if x["leader"] and x["leader"] != (w_side if winner else "A")], key=lambda x: -abs(x["r"]))
    labels = lambda xs: ", ".join(x["label"].lower() for x in xs)  # noqa: E731

    sentences = []
    if winner:
        loser = b if winner == a else a
        if lead:
            top = lead[0]
            sentences.append(f"{winner} leads on {labels(lead[:4])}, most clearly on {top['label'].lower()} ({_fmt(top['gap'])} {top['unit']}).")
        sentences.append(f"{loser} answers on {labels(other[:3])}." if other else f"{loser} does not lead in any area.")
    else:
        if lead or other:
            sentences.append(f"{a} leads on {labels(lead[:3]) or 'nothing decisive'}; {b} leads on {labels(other[:3]) or 'nothing decisive'}.")
        else:
            sentences.append("Neither driver opens a meaningful gap in any area.")
    delta = agg.get("avg_pace_delta_s")
    pace = ("level on pace" if delta is None or abs(delta) < 0.01
            else f"{side_code('A' if delta < 0 else 'B')} faster by {_fmt(abs(delta))}s per lap on average")
    sentences.append(f"Across {n} race{'s' if n != 1 else ''}: head-to-head {wins['a']}-{wins['b']}, {pace}, "
                     f"points {_fmt(agg['a'].get('points') or 0, 0)}-{_fmt(agg['b'].get('points') or 0, 0)}.")

    caveats = []
    if n == 1:
        caveats.append("One race only: a snapshot, not a trend.")
    for side, code in (("a", a), ("b", b)):
        dnf = sum(1 for r in comparison.get("races", []) if r.get(side) and not _classified(r[side]))
        if dnf:
            caveats.append(f"{code} did not finish {dnf} of these races, which drags their result and pace averages.")

    return {**base, "winner": winner, "confidence": confidence, "headline": headline,
            "summary": " ".join(sentences), "areas": areas, "caveats": caveats}


def _classified(row) -> bool:
    status = (row.get("status") or "").lower()
    return row.get("finish_position") is not None and (status.startswith("finished") or status.startswith("+"))


# ---------------------------------------------------------------- language model narrative (optional)
_TIDY = {0x202f: " ", 0x2009: " ", 0x00a0: " ", 0x2011: "-", 0x2013: "-", 0x2212: "-", 0x2192: "->"}

NARRATIVE_SYSTEM = (
    "You are RaceDelta's comparison analyst. You receive a JSON verdict about two Formula 1 drivers over a set of "
    "races. The JSON gives each driver's full name and three-letter code: use exactly those, as 'Full Name (CODE)' on "
    "first mention and the code afterwards. Never guess names, nationalities, teams or anything not in the JSON. "
    "Write 3 to 5 plain sentences for a fan: say who is better overall and how, naming the areas and quoting the "
    "numbers given (units included). Then state the caveat if one is given. Use ONLY the numbers in the JSON; never "
    "invent figures, races or context. No markdown, no bullet points, no headings."
)


def narrate(v: dict, context: str = "") -> dict:
    """Ask the configured NVIDIA-hosted model to write the verdict up. Returns {} when unavailable or on any failure."""
    key = os.getenv("NVIDIA_API_KEY")
    if not key or not v.get("areas"):
        return {}
    model = os.getenv("NVIDIA_MODEL", "openai/gpt-oss-120b")
    base = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    findings = {
        "context": context or None,
        "drivers": [{"code": c, "name": v.get("names", {}).get(c, c)} for c in (v["codes"]["a"], v["codes"]["b"])],
        "races_compared": v["races_compared"],
        "winner": v["winner"], "confidence": v["confidence"], "rule_summary": v["summary"], "caveats": v["caveats"],
        "areas": [{"area": x["label"], "leader": (v["codes"]["a"] if x["leader"] == "A" else v["codes"]["b"] if x["leader"] == "B" else "level"),
                   v["codes"]["a"]: x["a"], v["codes"]["b"]: x["b"], "unit": x["unit"]} for x in v["areas"] if x["gap"] is not None],
    }
    body = {"model": model, "temperature": 0.3, "max_tokens": 500,
            "reasoning_effort": os.getenv("NVIDIA_REASONING_EFFORT", "low"),
            "messages": [{"role": "system", "content": NARRATIVE_SYSTEM},
                         {"role": "user", "content": json.dumps(findings)}]}
    try:
        for attempt in range(NARRATIVE_ATTEMPTS):   # the shared endpoint occasionally strands a request
            try:
                r = requests.post(f"{base}/chat/completions", json=body, timeout=NARRATIVE_TIMEOUT,
                                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                break
            except requests.Timeout:
                if attempt == NARRATIVE_ATTEMPTS - 1:
                    raise
        r.raise_for_status()
        text = (r.json()["choices"][0]["message"].get("content") or "").strip()
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text).translate(_TIDY)
        return {"summary": text, "source": "llm:nvidia", "model": model} if text else {}
    except Exception as e:  # the rules summary stands in
        logger.warning("verdict narrative unavailable: %s", e)
        return {}


def for_races(driver1: str, driver2: str, races: list, context: str = "") -> dict:
    """Rules verdict now; model prose from cache, or queued on the background worker and flagged `pending`."""
    a, b = driver1.upper(), driver2.upper()
    spec = ",".join(f"{s}-{r}" for s, r in sorted({(int(s), int(r)) for s, r in races}))
    v = verdict(compare_lab.compare_on_races(a, b, races))
    v["context"] = context or None
    v["pending"] = False
    if not os.getenv("NVIDIA_API_KEY") or not v["areas"]:
        return v
    key = f"verdict-prose:v2:{a}:{b}:{spec}:{context}"
    prose = cache_store.get("derived", key)
    if prose:
        v["rule_summary"] = v["summary"]
        v.update(prose)
        return v
    snapshot = dict(v)
    cache_store.enqueue("derived", key, VERDICT_TTL, lambda: narrate(snapshot, context) or None)
    v["pending"] = True
    return v
