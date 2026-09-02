"""Synthetic-race checks for the Phase-4 Strategy Lab (no DB, no network, linear pace model)."""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services import strategy_lab as sl  # noqa: E402
from app.services import pace_model as pm    # noqa: E402

TOTAL = 30
DEG = {"SOFT": 0.12, "MEDIUM": 0.08, "HARD": 0.05}
PIT_IN, PIT_OUT = 12.0, 9.0                     # -> pit loss of ~21 s
SC = (10, 12)                                   # safety car laps


def synthetic_race():
    drivers = {  # base pace, stints (start, end, compound)
        "AAA": (88.0, [(1, 12, "MEDIUM"), (13, TOTAL, "HARD")]),
        "BBB": (88.4, [(1, 10, "MEDIUM"), (11, 20, "MEDIUM"), (21, TOTAL, "HARD")]),
        "CCC": (89.0, [(1, 15, "SOFT"), (16, TOTAL, "HARD")]),
    }
    rows, stints = [], []
    for code, (base, plan) in drivers.items():
        for si, (s, e, comp) in enumerate(plan, 1):
            for L in range(s, e + 1):
                age = L - s + 1
                t = base + DEG[comp] * age + pm.FUEL_EFFECT_S_PER_LAP * L
                pit_in, pit_out = (L == e and si < len(plan)), (L == s and si > 1)
                t += PIT_IN if pit_in else 0.0
                t += PIT_OUT if pit_out else 0.0
                ts = "4" if SC[0] <= L <= SC[1] else "1"
                t = t * 1.4 if ts == "4" else t
                rows.append(dict(driver_code=code, lap_number=L, lap_time_s=t, compound=comp, tyre_life=float(age),
                                 stint=si, position=None, is_pit_in=pit_in, is_pit_out=pit_out, track_status=ts,
                                 is_accurate=not (pit_in or pit_out), gap_ahead_s=None, gap_behind_s=None))
            stints.append(dict(driver_code=code, stint_number=si, compound=comp, lap_start=s, lap_end=e,
                               laps=e - s + 1, avg_lap_time_s=None, degradation_s_per_lap=DEG[comp]))
    laps = pd.DataFrame(rows)
    laps["cum"] = laps.groupby("driver_code")["lap_time_s"].cumsum()
    laps["position"] = laps.groupby("lap_number")["cum"].rank(method="first").astype(int)
    laps = laps.sort_values(["lap_number", "position"])
    laps["gap_ahead_s"] = laps.groupby("lap_number")["cum"].diff()
    laps["gap_behind_s"] = -laps.groupby("lap_number")["cum"].diff(-1)
    final = laps[laps["lap_number"] == TOTAL].set_index("driver_code")["position"]
    features = {c: {"grid_position": i + 1, "finish_position": int(final[c]), "status": "Finished",
                    "name": f"Driver {c}", "team": "Team"} for i, c in enumerate(drivers)}
    return laps.drop(columns="cum"), pd.DataFrame(stints), features


class StrategyLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        laps, stints, feats = synthetic_race()
        cls.ctx = sl.build_context(2025, 1, "Test GP", TOTAL, False, laps, stints, feats, use_xgboost=False)

    def test_race_statistics(self):
        self.assertAlmostEqual(self.ctx.pit_loss_s, PIT_IN + PIT_OUT, delta=1.5)   # SC-lap stop (BBB) excluded
        self.assertEqual([self.ctx.lap_flags[L] for L in (9, 10, 12, 13)], ["GREEN", "SC", "SC", "GREEN"])
        self.assertEqual(self.ctx.compounds, ["HARD", "MEDIUM", "SOFT"])
        self.assertEqual(self.ctx.compound_stats["SOFT"]["typical_life"], 15.0)
        self.assertEqual(self.ctx.model.kind, "linear")
        self.assertLess(self.ctx.model.rmse, 0.05)                    # exact linear data -> near-zero error
        self.assertEqual(set(self.ctx.finish_times), {"AAA", "BBB", "CCC"})

    def test_driver_facts(self):
        s = sl.driver_strategy(self.ctx, "AAA")
        self.assertEqual((s["start_compound"], s["stops"], s["n_stops"]), ("MEDIUM", [{"lap": 12, "compound": "HARD"}], 1))
        st = sl.race_state(self.ctx, "AAA", 11)
        self.assertEqual((st["flag"], st["compound"], st["tyre_life"], st["laps_remaining"]), ("SC", "MEDIUM", 11.0, 19))
        self.assertEqual(st["effective_pit_loss_s"], round(self.ctx.pit_loss_s * 0.5, 1))
        self.assertEqual(sl.actual_decision(self.ctx, "AAA", 12)["action"], "PIT")
        self.assertEqual(sl.actual_decision(self.ctx, "AAA", 12)["new_compound"], "HARD")
        with self.assertRaises(ValueError):
            sl.race_state(self.ctx, "AAA", 99)

    def test_recommendations(self):
        under_sc = sl.recommend(self.ctx, sl.race_state(self.ctx, "AAA", 11))
        self.assertEqual((under_sc["action"], under_sc["compound"]), ("PIT", "HARD"))
        self.assertTrue(any("SC deployed" in r for r in under_sc["reasons"]))
        self.assertTrue(0.5 <= under_sc["confidence"] <= 0.95)
        self.assertIn("net_gain_s", under_sc["expected_outcome"])
        fresh = sl.recommend(self.ctx, sl.race_state(self.ctx, "AAA", 2))
        self.assertEqual(fresh["action"], "STAY")
        self.assertTrue(any("fresh" in r for r in fresh["reasons"]))
        late = sl.recommend(self.ctx, sl.race_state(self.ctx, "AAA", TOTAL - 3))
        self.assertEqual(late["action"], "STAY")
        self.assertTrue(any("cannot be recovered" in r for r in late["reasons"]))

    def test_replay(self):
        r = sl.replay(self.ctx, "AAA", 11)
        self.assertEqual(len(r["timeline"]), TOTAL)
        self.assertEqual(r["actual_pit_laps"], [12])
        self.assertTrue(r["ai_pit_laps"])
        self.assertTrue(0 <= r["agreement_pct"] <= 100)
        self.assertEqual(r["driver"]["finish_position"], 1)

    def test_simulator_same_strategy_is_neutral(self):
        res = sl.simulate(self.ctx, "AAA", [{"lap": 12, "compound": "HARD"}], start_compound="MEDIUM")
        self.assertAlmostEqual(res["alternative"]["time_saved_s"], 0.0, delta=0.05)
        self.assertEqual(res["alternative"]["predicted_finish_position"], 1)
        self.assertEqual(res["alternative"]["position_gain"], 0)
        self.assertTrue(0 <= res["alternative"]["podium_probability"] <= 1)
        self.assertAlmostEqual(res["alternative"]["estimated_race_time_s"], res["actual"]["race_time_s"], delta=0.2)

    def test_simulator_extra_stop_costs_about_one_pit_loss(self):
        res = sl.simulate(self.ctx, "AAA", [{"lap": 12, "compound": "HARD"}, {"lap": 21, "compound": "HARD"}])
        self.assertLess(res["alternative"]["time_saved_s"], -self.ctx.pit_loss_s + 6)   # fresh rubber claws ~4s back
        self.assertGreater(res["alternative"]["time_saved_s"], -self.ctx.pit_loss_s - 6)
        self.assertEqual(len(res["alternative"]["stints"]), 3)

    def test_simulator_inputs_and_warnings(self):
        for bad in ([{"lap": 0, "compound": "HARD"}], [{"lap": 15, "compound": "HARD"}, {"lap": 15, "compound": "SOFT"}],
                    [{"lap": 10, "compound": "GLUE"}]):   # (unordered stops are sorted, not rejected)
            with self.assertRaises(ValueError):
                sl.simulate(self.ctx, "AAA", bad)
        with self.assertRaises(ValueError):
            sl.simulate(self.ctx, "ZZZ", [])
        one_compound = sl.simulate(self.ctx, "AAA", [], start_compound="MEDIUM")
        self.assertTrue(any("Regulation" in w for w in one_compound["warnings"]))
        sc = sl.simulate(self.ctx, "AAA", [{"lap": 21, "compound": "HARD"}], safety_car={"lap": 20, "laps": 3})
        self.assertTrue(any("safety car" in w.lower() for w in sc["warnings"]))
        wet = sl.simulate(self.ctx, "AAA", [{"lap": 12, "compound": "HARD"}], weather="wet")
        self.assertAlmostEqual(wet["alternative"]["time_saved_s"], 0.0, delta=0.05)      # same plan, like-for-like
        self.assertGreater(wet["alternative"]["estimated_race_time_s"], wet["actual"]["race_time_s"] + 30)  # slicks in rain
        self.assertTrue(any("weather" in w.lower() for w in wet["warnings"]))


if __name__ == "__main__":
    unittest.main()
