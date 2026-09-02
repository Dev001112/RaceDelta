"""Phase-5 AI Race Analyst checks: tools on a synthetic race, offline intents, and the Claude
tool loop driven by a scripted fake client (no DB, no network, no API key)."""
import json
import os
import sys
import unittest
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services import race_analyst as ra          # noqa: E402
from app.services import race_analyst_tools as T     # noqa: E402
from app.services import strategy_lab as sl          # noqa: E402
from tests.test_strategy_lab import synthetic_race, TOTAL  # noqa: E402


def make_ctx():
    laps, stints, feats = synthetic_race()
    for col, share in (("s1_s", 0.30), ("s2_s", 0.42), ("s3_s", 0.28)):   # synthetic sector splits
        laps[col] = laps["lap_time_s"] * share
    feats["AAA"].update(name="Alpha Ace", team="Team Alpha")
    feats["BBB"].update(name="Bravo Bolt", team="Team Alpha")
    feats["CCC"].update(name="Charlie Cruz", team="Team Charlie")
    return sl.build_context(2025, 1, "Test GP", TOTAL, False, laps, stints, feats, use_xgboost=False)


class ToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = make_ctx()
        cls.provider = staticmethod(lambda s, r: cls.ctx)

    def test_name_resolution(self):
        self.assertEqual(T.resolve_driver(self.ctx, "bbb"), "BBB")
        self.assertEqual(T.resolve_driver(self.ctx, "Bolt"), "BBB")
        self.assertEqual(T.resolve_driver(self.ctx, "Charlie Cruz"), "CCC")
        self.assertIsNone(T.resolve_driver(self.ctx, "Nobody"))
        self.assertEqual(T.resolve_team(self.ctx, "team alpha"), "Team Alpha")
        self.assertIsNone(T.resolve_team(self.ctx, "Ferrari"))

    def test_race_summary(self):
        r = T.race_summary(self.ctx)
        self.assertEqual(r["data"]["classification"][0]["driver_code"], "AAA")
        self.assertEqual(r["data"]["safety_car_laps"], [10, 11, 12])
        self.assertIn("Podium: P1 AAA", r["summary"])
        self.assertIn("Safety Car on laps 10, 11, 12", r["summary"])

    def test_driver_race_and_compare(self):
        d = T.driver_race(self.ctx, "Bolt")
        self.assertEqual(d["data"]["driver_code"], "BBB")
        self.assertEqual(d["data"]["strategy"]["n_stops"], 2)
        self.assertIn("2 stop(s)", d["summary"])
        self.assertIn(f"-> P{d['data']['finish']}", d["summary"])      # finisher must not read as DNF
        c = T.compare_drivers(self.ctx, "AAA", "BBB")
        self.assertEqual(c["data"]["faster"], "AAA")           # AAA has the lower base pace
        self.assertIn("AAA was faster", c["summary"])
        c2 = T.compare_drivers(self.ctx, "AAA", "CCC", stint=2)
        self.assertEqual(c2["data"]["scope"], "stint 2")
        self.assertEqual(c2["data"]["drivers"]["AAA"]["compound"], "HARD")
        with self.assertRaises(ValueError):
            T.compare_drivers(self.ctx, "AAA", "ZZZ")

    def test_pit_stops_rank_and_flag(self):
        p = T.pit_stops(self.ctx)
        self.assertEqual(p["data"]["n_stops"], 4)
        bbb10 = next(s for s in p["data"]["stops"] if s["driver_code"] == "BBB" and s["lap"] == 10)
        self.assertEqual(bbb10["flag"], "SC")
        self.assertEqual((bbb10["from"], bbb10["to"]), ("MEDIUM", "MEDIUM"))
        self.assertIn("most decisive", p["summary"])
        only = T.pit_stops(self.ctx, "AAA")
        self.assertEqual([s["lap"] for s in only["data"]["stops"]], [12])

    def test_team_race(self):
        t = T.team_race(self.ctx, "Team Charlie")
        self.assertFalse(t["data"]["won"])
        self.assertEqual(t["data"]["winner"], "AAA")
        self.assertIn("won by AAA", t["summary"])
        self.assertTrue(any("lacked pace" in r for r in t["data"]["reasons"]))
        won = T.team_race(self.ctx, "Team Alpha")
        self.assertTrue(won["data"]["won"])

    def test_execute_tool_dispatch(self):
        out = T.execute_tool("get_strategy_replay", {"season": 2025, "round": 1, "driver": "AAA", "lap": 11}, self.provider)
        self.assertEqual(out["data"]["ai_recommendation"]["action"], "PIT")
        sim = T.execute_tool("simulate_strategy", {"season": 2025, "round": 1, "driver": "AAA",
                                                    "pit_stops": [{"lap": 12, "compound": "HARD"}], "start_compound": None,
                                                    "safety_car_lap": None, "weather": None}, self.provider)
        self.assertEqual(sim["data"]["alternative"]["predicted_finish_position"], 1)
        with self.assertRaises(ValueError):
            T.execute_tool("no_such_tool", {"season": 2025, "round": 1}, self.provider)
        names = {t["name"] for t in T.TOOLS}
        self.assertTrue(all(t.get("strict") and t["input_schema"].get("additionalProperties") is False for t in T.TOOLS))
        self.assertIn("get_pit_stops", names)


class OfflineIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = make_ctx()
        cls.provider = staticmethod(lambda s, r: cls.ctx)

    def test_intents(self):
        d = lambda q: ra.detect_intent(q, self.ctx)
        self.assertEqual(d("Which pit stop changed the race?")["intent"], "pit_stops")
        self.assertEqual(d("Why did Team Charlie lose?")["intent"], "team")
        i = d("Compare Ace and Bolt during the second stint")
        self.assertEqual((i["intent"], i["stint"], i["drivers"]), ("compare", 2, ["AAA", "BBB"]))
        i = d("Why was Cruz faster in Sector 2?")
        self.assertEqual((i["intent"], i["sector"]), ("compare_vs_winner", 2))
        self.assertEqual(d("Should Ace have pitted on lap 11?")["intent"], "strategy_at_lap")
        self.assertEqual(d("Who is the best driver this season?")["intent"], "rating")
        self.assertEqual(d("What happened in the race?")["intent"], "race_summary")

    def test_offline_answers_come_from_tools(self):
        r = ra.answer_offline("Which pit stop changed the race?", 2025, 1, self.provider)
        self.assertEqual(r["mode"], "offline")
        self.assertEqual(r["tools_used"][0]["name"], "get_pit_stops")
        self.assertIn("most decisive", r["answer"])
        r = ra.answer_offline("Why was Cruz faster in sector 2?", 2025, 1, self.provider)
        self.assertTrue(r["answer"].startswith("Sector 2:"))
        r = ra.answer_offline("Compare Ace with nobody", 2025, 1, self.provider)
        self.assertIn("Name two drivers", r["answer"])
        r = ra.answer_offline("Which pit stop changed the race?", 2025, None, self.provider)
        self.assertIn("Pick a race", r["answer"])


class FakeClient:
    """Scripted stand-in for anthropic.Anthropic(): returns canned responses in order and records requests."""
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


def tool_use_response(name, args, tid="toolu_1"):
    return NS(stop_reason="tool_use", model="claude-opus-5", usage=NS(input_tokens=100, output_tokens=20),
              content=[NS(type="text", text="Let me check."), NS(type="tool_use", id=tid, name=name, input=args)])


def final_response(text):
    return NS(stop_reason="end_turn", model="claude-opus-5", usage=NS(input_tokens=300, output_tokens=80),
              content=[NS(type="text", text=text)])


class ClaudeLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = make_ctx()
        cls.provider = staticmethod(lambda s, r: cls.ctx)

    def test_tool_loop_round_trip(self):
        client = FakeClient([tool_use_response("get_pit_stops", {"season": 2025, "round": 1, "driver": None}),
                             final_response("BBB's lap 10 stop under the Safety Car was decisive.")])
        out = ra.ask("Which pit stop changed the race?", 2025, 1, client=client, ctx_provider=self.provider)
        self.assertEqual(out["mode"], "claude")
        self.assertEqual(out["answer"], "BBB's lap 10 stop under the Safety Car was decisive.")
        self.assertEqual([t["name"] for t in out["tools_used"]], ["get_pit_stops"])
        self.assertFalse(out["tools_used"][0]["error"])
        self.assertEqual(out["usage"], {"input_tokens": 400, "output_tokens": 100})
        # second request carries assistant tool_use + our tool_result keyed by the tool_use id
        req = client.requests[1]
        self.assertEqual(req["model"], "claude-opus-5")
        self.assertEqual(req["fallbacks"], "default")
        self.assertIn("server-side-fallback-2026-07-01", req["betas"])
        self.assertEqual(req["messages"][-1]["role"], "user")
        result = req["messages"][-1]["content"][0]
        self.assertEqual((result["type"], result["tool_use_id"], result["is_error"]), ("tool_result", "toolu_1", False))
        self.assertIn("most decisive", json.loads(result["content"])["summary"])
        self.assertIn("Test GP", req["system"])

    def test_tool_error_is_returned_not_raised(self):
        client = FakeClient([tool_use_response("get_team_race", {"season": 2025, "round": 1, "team": "Ferrari"}),
                             final_response("No Ferrari data in this race.")])
        out = ra.ask("Why did Ferrari lose?", 2025, 1, client=client, ctx_provider=self.provider)
        self.assertTrue(out["tools_used"][0]["error"])
        self.assertTrue(client.requests[1]["messages"][-1]["content"][0]["is_error"])
        self.assertEqual(out["answer"], "No Ferrari data in this race.")

    def test_refusal_and_turn_cap(self):
        refusal = NS(stop_reason="refusal", model="claude-opus-5", usage=None, content=[])
        out = ra.ask("q", 2025, 1, client=FakeClient([refusal]), ctx_provider=self.provider)
        self.assertEqual(out["stop_reason"], "refusal")
        looping = [tool_use_response("get_race_summary", {"season": 2025, "round": 1}, tid=f"t{i}") for i in range(3)]
        out = ra.ask("q", 2025, 1, client=FakeClient(looping), ctx_provider=self.provider, max_turns=3)
        self.assertEqual(len(out["tools_used"]), 3)
        self.assertIn("ran out of steps", out["answer"])

    def test_history_is_cleaned_and_bounded(self):
        hist = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"},
                {"role": "system", "content": "ignored"}, {"role": "user", "content": ""}]
        client = FakeClient([final_response("ok")])
        ra.ask("next", 2025, 1, history=hist, client=client, ctx_provider=self.provider)
        roles = [m["role"] for m in client.requests[0]["messages"]]
        self.assertEqual(roles, ["user", "assistant", "user"])


if __name__ == "__main__":
    unittest.main()
