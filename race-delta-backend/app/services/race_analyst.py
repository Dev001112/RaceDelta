# app/services/race_analyst.py
"""
Phase 5 — AI Race Analyst.

    question -> Claude (claude-opus-5) -> tool calls -> RaceDelta data -> grounded answer

The model may only answer from tool results (race_analyst_tools.py); the system prompt forbids
outside knowledge. Server-side refusal fallbacks are enabled by default.

Offline mode: when no Anthropic credentials are configured, detect_intent() routes the question
to the same tools with rules and returns their plain-English summaries, so the feature works in
demos without an API key (the architecture's "Intent Detection" box, minus the LLM).
"""
import json
import logging
import os
import re

from app.services import race_analyst_tools as T
from app.services import strategy_lab as sl

try:
    import anthropic
except ImportError:  # SDK optional: offline mode still works
    anthropic = None

logger = logging.getLogger(__name__)

MODEL = os.getenv("ANALYST_MODEL", "claude-opus-5")
MAX_TURNS = 6
MAX_TOKENS = 16000
HISTORY_LIMIT = 12

SYSTEM_PROMPT = """You are RaceDelta's Race Analyst, an explainable Formula 1 analytics assistant.

Ground rules:
- Answer ONLY from the data returned by your tools. Never use outside knowledge about a race, a driver or a result, even if you think you remember it. If the tools do not contain what is needed, say exactly that.
- Call get_race_summary first when you have not yet looked at the race in this conversation, then the specific tool(s) the question needs. Prefer one or two well-chosen tool calls.
- Quote the numbers the tools give you (seconds, laps, positions) with units, and name drivers as "NAME (CODE)".
- Be concise: a one-line verdict, then 2-5 short supporting points. No preamble, no speculation beyond the data, no markdown tables.
- Compounds, pit laps and flags come from timing data; pace metrics use green-flag, non-pit laps ("clean laps").

Current context: season {season}{round_clause}. Use these unless the user names another race."""


class AnalystError(Exception):
    """User-facing failure (credentials, rate limit, upstream outage)."""


# ============================================================ credentials / client
def has_credentials() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def make_client():
    """Anthropic client from the environment, or None when no credentials are configured."""
    if anthropic is None or not has_credentials():
        return None
    return anthropic.Anthropic()


def status() -> dict:
    live = anthropic is not None and has_credentials()
    return {"mode": "claude" if live else "offline", "model": MODEL if live else None,
            "sdk_installed": anthropic is not None, "has_credentials": has_credentials(),
            "tools": [t["name"] for t in T.TOOLS],
            "suggested_questions": ["Why did Ferrari lose?", "Why was Verstappen faster in Sector 2?",
                                    "Compare Norris and Leclerc during the second stint.", "Which pit stop changed the race?",
                                    "Should Verstappen have pitted on lap 20?", "Who is the best driver this season?"]}


# ============================================================ helpers
def _system(season, round_num, ctx_provider):
    clause = ""
    if round_num:
        try:
            ctx = ctx_provider(season, round_num)
            clause = f", round {round_num} ({ctx.event}, {ctx.total_laps} laps)"
        except Exception:
            clause = f", round {round_num}"
    return SYSTEM_PROMPT.format(season=season, round_clause=clause)


def _clean_history(history):
    out = []
    for m in history or []:
        role, content = m.get("role"), m.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            out.append({"role": role, "content": content.strip()})
    return out[-HISTORY_LIMIT:]


def _run_tool(name, args, ctx_provider):
    """Execute a tool; returns (payload dict, is_error)."""
    try:
        return T.execute_tool(name, args, ctx_provider), False
    except (ValueError, KeyError) as e:
        return {"error": str(e)}, True
    except Exception as e:  # data problems must not kill the conversation
        logger.exception("tool %s failed", name)
        return {"error": f"{type(e).__name__}: {e}"}, True


def _create(client, **kwargs):
    if anthropic is None:
        return client.beta.messages.create(**kwargs)
    try:
        return client.beta.messages.create(**kwargs)
    except anthropic.AuthenticationError:
        raise AnalystError("The Anthropic API key was rejected. Check ANTHROPIC_API_KEY.")
    except anthropic.PermissionDeniedError:
        raise AnalystError("The Anthropic API key lacks permission for this model.")
    except anthropic.NotFoundError:
        raise AnalystError(f"Model '{kwargs.get('model')}' was not found. Check ANALYST_MODEL.")
    except anthropic.RateLimitError:
        raise AnalystError("Anthropic rate limit reached. Try again in a moment.")
    except anthropic.APIStatusError as e:
        raise AnalystError(f"Anthropic API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        raise AnalystError("Could not reach the Anthropic API. Check the network connection.")


def _text(content) -> str:
    return "".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text").strip()


# ============================================================ Claude tool loop
def ask(question: str, season: int, round_num=None, history=None, client=None, ctx_provider=None,
        max_turns: int = MAX_TURNS) -> dict:
    """Answer a race question. Uses Claude with tools when credentials exist, else offline intents."""
    ctx_provider = ctx_provider or sl.load_context
    question = (question or "").strip()
    if not question:
        raise ValueError("question is required")
    if client is None:
        client = make_client()
    if client is None:
        return answer_offline(question, season, round_num, ctx_provider)

    messages = _clean_history(history) + [{"role": "user", "content": question}]
    tools_used, usage = [], {"input_tokens": 0, "output_tokens": 0}
    response, finished = None, False
    for _ in range(max_turns):
        response = _create(
            client, model=MODEL, max_tokens=MAX_TOKENS,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=_system(season, round_num, ctx_provider), tools=T.TOOLS,
            output_config={"effort": "medium"}, messages=messages,
        )
        u = getattr(response, "usage", None)
        usage["input_tokens"] += int(getattr(u, "input_tokens", 0) or 0)
        usage["output_tokens"] += int(getattr(u, "output_tokens", 0) or 0)

        if response.stop_reason == "refusal":
            return {"answer": "I can't help with that request.", "mode": "claude", "model": getattr(response, "model", MODEL),
                    "tools_used": tools_used, "usage": usage, "stop_reason": "refusal"}
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        tool_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_blocks:
            finished = True
            break

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in tool_blocks:
            payload, is_error = _run_tool(block.name, dict(block.input or {}), ctx_provider)
            tools_used.append({"name": block.name, "input": dict(block.input or {}),
                               "summary": payload.get("error") if is_error else payload.get("summary"), "error": is_error})
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": json.dumps(payload, default=str), "is_error": is_error})
        messages.append({"role": "user", "content": results})   # all results in ONE user message

    answer = _text(response.content) if (finished and response is not None) else ""
    if not answer:
        answer = "I ran out of steps before finishing the analysis. Please narrow the question."
    return {"answer": answer, "mode": "claude", "model": getattr(response, "model", MODEL),
            "tools_used": tools_used, "usage": usage, "stop_reason": getattr(response, "stop_reason", None)}


# ============================================================ offline intent mode
_STINT_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4}


def detect_intent(question: str, ctx=None) -> dict:
    """Rule-based intent detection for offline mode. Returns {"intent", ...slots}."""
    q = question.lower()
    slots = {}
    m = re.search(r"stint\s*(\d+)|(\w+)\s+stint", q)
    if m:
        slots["stint"] = int(m.group(1)) if m.group(1) else _STINT_WORDS.get(m.group(2))
    m = re.search(r"sector\s*([123])", q)
    if m:
        slots["sector"] = int(m.group(1))
    m = re.search(r"lap\s*(\d+)", q)
    if m:
        slots["lap"] = int(m.group(1))

    drivers, team = [], None
    if ctx is not None:
        for code, f in ctx.features.items():
            name = (f.get("name") or "").lower()
            parts = [p for p in name.split() if len(p) > 2]
            if code.lower() in re.findall(r"\b[a-z]{3}\b", q) and code.lower() not in ("the", "and", "why", "was", "did", "lap", "who"):
                drivers.append(code)
            elif parts and any(re.search(rf"\b{re.escape(p)}\b", q) for p in parts):   # any name part: 'kimi' or 'antonelli' (ponytail: first names may collide with words like 'max')
                drivers.append(code)
        drivers = list(dict.fromkeys(drivers))
        for word in sorted(T.TEAM_ALIASES, key=len, reverse=True):
            if re.search(rf"\b{re.escape(word)}\b", q):
                team = T.resolve_team(ctx, word)
                if team:
                    break
        if team is None:
            for t in {f.get("team") for f in ctx.features.values() if f.get("team")}:
                if t.lower() in q:
                    team = t
                    break
    slots["drivers"], slots["team"] = drivers, team

    if re.search(r"\b(rating|ratings|rank|ranking|best driver|top driver)\b", q):
        return {"intent": "rating", **slots}
    if re.search(r"\b(dna|similar to|similar drivers|driving style)\b", q):
        return {"intent": "dna", **slots}
    if re.search(r"\bpit ?stops?\b|\bwhich stop\b|\bpitted\b", q) and "should" not in q:
        return {"intent": "pit_stops", **slots}
    if slots.get("lap") and re.search(r"\b(should|pit|stay|strategy|recommend)\b", q):
        return {"intent": "strategy_at_lap", **slots}
    if len(drivers) >= 2 or re.search(r"\b(compare|versus|vs\.?)\b", q):
        return {"intent": "compare", **slots}
    if team and re.search(r"\b(lose|lost|win|won|beat|struggle|slow|why|how)\b", q):
        return {"intent": "team", **slots}
    if len(drivers) == 1 and re.search(r"\b(faster|slower|quicker|sector|pace)\b", q):
        return {"intent": "compare_vs_winner", **slots}
    if len(drivers) == 1:
        return {"intent": "driver", **slots}
    if team:
        return {"intent": "team", **slots}
    return {"intent": "race_summary", **slots}


def answer_offline(question: str, season: int, round_num=None, ctx_provider=None) -> dict:
    ctx_provider = ctx_provider or sl.load_context
    tools_used = []

    def use(name, args):
        payload, err = _run_tool(name, args, ctx_provider)
        tools_used.append({"name": name, "input": args, "summary": payload.get("error") if err else payload.get("summary"), "error": err})
        return payload, err

    base = {"mode": "offline", "model": None, "usage": None, "stop_reason": "end_turn"}
    if not round_num:
        intent = detect_intent(question)
        if intent["intent"] in ("rating", "dna"):
            name = "get_driver_rating" if intent["intent"] == "rating" else "get_driver_dna"
            args = {"season": season, "top": 10} if name == "get_driver_rating" else {"season": season, "driver": (intent["drivers"] or [""])[0]}
            payload, err = use(name, args)
            return {**base, "answer": payload.get("error") or payload["summary"], "tools_used": tools_used}
        return {**base, "answer": "Pick a race first (season and round), then ask about it.", "tools_used": tools_used}

    ctx = ctx_provider(season, round_num)
    intent = detect_intent(question, ctx)
    kind, d, team = intent["intent"], intent["drivers"], intent["team"]
    race = {"season": season, "round": round_num}

    if kind == "rating":
        payload, err = use("get_driver_rating", {"season": season, "top": 10})
    elif kind == "dna":
        payload, err = use("get_driver_dna", {"season": season, "driver": (d or [""])[0]})
    elif kind == "pit_stops":
        payload, err = use("get_pit_stops", {**race, "driver": d[0] if d else None})
    elif kind == "strategy_at_lap":
        payload, err = use("get_strategy_replay", {**race, "driver": d[0] if d else T._winner(ctx), "lap": intent["lap"]})
    elif kind == "compare":
        if len(d) < 2:
            payload, err = {"error": "Name two drivers to compare (e.g. 'Compare Norris and Leclerc')."}, True
        else:
            payload, err = use("compare_drivers", {**race, "driver_a": d[0], "driver_b": d[1], "stint": intent.get("stint")})
    elif kind == "compare_vs_winner":
        winner = T._winner(ctx)
        other = winner if winner != d[0] else (ctx.features and next((c for c in ctx.features if c != d[0]), None))
        payload, err = use("compare_drivers", {**race, "driver_a": d[0], "driver_b": other, "stint": intent.get("stint")})
    elif kind == "team":
        payload, err = use("get_team_race", {**race, "team": team})
    elif kind == "driver":
        payload, err = use("get_driver_race", {**race, "driver": d[0]})
    else:
        payload, err = use("get_race_summary", race)

    answer = payload.get("error") if err else payload["summary"]
    if not err and intent.get("sector") and kind in ("compare", "compare_vs_winner"):
        sec = intent["sector"]
        delta = payload["data"]["deltas_a_minus_b"].get(f"s{sec}_avg_s")
        a, b = list(payload["data"]["drivers"])
        if delta is not None:
            answer = f"Sector {sec}: {a if delta < 0 else b} was faster by {abs(delta):.3f}s per lap on average. " + answer
        else:
            answer = f"Sector {sec}: no sector timing is stored for this race, so here is the overall comparison. " + answer
    return {**base, "answer": answer, "tools_used": tools_used, "intent": intent["intent"]}
