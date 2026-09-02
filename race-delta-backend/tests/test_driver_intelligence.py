"""Synthetic-data checks for the Phase-3 driver intelligence maths (no DB, no network)."""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services import driver_intelligence as di  # noqa: E402


def _rows():
    """6 drivers x 3 rounds. ACE is best at everything; CLN is a near-copy of ACE; SLW is worst."""
    profiles = {          # pace_off, grid, cons, deg, overtakes, pos_change, penalties
        "ACE": (0.0, 1, 0.3, 0.02, 4, 2, 0),
        "CLN": (0.1, 2, 0.32, 0.025, 4, 2, 0),
        "MID": (0.8, 6, 0.6, 0.06, 2, 0, 0),
        "MDB": (0.9, 7, 0.65, 0.07, 1, -1, 1),
        "WET": (1.0, 9, 0.7, 0.08, 1, 0, 0),
        "SLW": (2.0, 12, 1.2, 0.15, 0, -3, 2),
    }
    rows = []
    for rnd, base in ((1, 80.0), (2, 95.0), (3, 70.0)):          # very different circuits
        rain = rnd == 2
        for code, (off, grid, cons, deg, ovt, gain, pen) in profiles.items():
            g = gain + (4 if (code == "WET" and rain) else 0)   # WET only shines in the rain
            rows.append({"driver_code": code, "round": rnd, "rainfall": rain,
                         "avg_pace_s": base + off, "grid_position": grid, "finish_position": max(1, grid - g),
                         "lap_consistency_s": cons, "tyre_degradation_s_per_lap": deg,
                         "overtake_count": ovt, "position_changes": g, "penalties": pen})
    return pd.DataFrame(rows)


class DriverIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.df = _rows()
        self.vec, self.races = di.matrix_from_frame(self.df)

    def test_matrix_is_relative_to_field_and_higher_is_better(self):
        self.assertEqual(sorted(self.vec.columns), sorted(di.ALL_DIMENSIONS))
        self.assertEqual(int(self.races["ACE"]), 3)
        self.assertGreater(self.vec.loc["ACE", "race_pace"], self.vec.loc["SLW", "race_pace"])
        self.assertGreater(self.vec.loc["ACE", "discipline"], self.vec.loc["SLW", "discipline"])
        self.assertAlmostEqual(float(self.vec["race_pace"].mean()), 0.0, places=6)   # field average = 0
        # wet dimension only comes from the rainy round: WET gained +4 there, everyone else did not
        self.assertEqual(self.vec[di.WET].idxmax(), "WET")

    def test_rating_ranks_best_first_and_is_bounded(self):
        rating = di.rating_from_matrix(self.vec, self.races)
        self.assertEqual([r["driver_code"] for r in rating][:1], ["ACE"])
        self.assertEqual(rating[-1]["driver_code"], "SLW")
        self.assertEqual([r["rank"] for r in rating], list(range(1, 7)))
        for r in rating:
            self.assertTrue(0 <= r["rating"] <= 100)
            self.assertTrue(all(0 <= v <= 100 for v in r["components"].values()))
            self.assertFalse(r["low_sample"])
        ace = rating[0]["components"]
        for dim in ("race_pace", "qualifying_pace", "consistency", "tyre_management", "discipline"):
            self.assertEqual(ace[dim], 100.0)                 # ACE tops every dimension it leads
        wet = next(r for r in rating if r["driver_code"] == "WET")["components"]
        self.assertEqual(wet["wet_performance"], 100.0)       # ...but WET owns the rain
        self.assertGreater(rating[0]["rating"], 95.0)

    def test_dna_similarity_finds_the_clone(self):
        dna = di.dna_from_matrix(self.vec, self.races, "ace", k=3)
        self.assertEqual(dna["driver_code"], "ACE")
        self.assertEqual(dna["similar"][0]["driver_code"], "CLN")
        self.assertGreater(dna["similar"][0]["cosine_similarity"], 0.95)
        self.assertLess(dna["similar"][0]["euclidean_distance"], dna["similar"][-1]["euclidean_distance"])
        self.assertEqual(len(dna["pca"]["explained_variance"]), 2)
        with self.assertRaises(ValueError):
            di.dna_from_matrix(self.vec, self.races, "NOPE")

    def test_clustering_methods(self):
        km = di.clusters_from_matrix(self.vec, self.races, "kmeans", k=3)
        self.assertEqual(km["k"], 3)
        self.assertEqual(len(km["points"]), 6)
        self.assertEqual(sum(c["size"] for c in km["clusters"]), 6)
        ace = next(p for p in km["points"] if p["driver_code"] == "ACE")
        cln = next(p for p in km["points"] if p["driver_code"] == "CLN")
        self.assertEqual(ace["cluster"], cln["cluster"])           # the clone lands with ACE
        self.assertTrue(all(c["label"] for c in km["clusters"]))
        hc = di.clusters_from_matrix(self.vec, self.races, "hierarchical", k=2)
        self.assertEqual(hc["n_clusters"], 2)
        db = di.clusters_from_matrix(self.vec, self.races, "dbscan", eps=3.0, min_samples=2)
        self.assertEqual(len(db["points"]), 6)
        with self.assertRaises(ValueError):
            di.clusters_from_matrix(self.vec, self.races, "voodoo")

    def test_empty_frame_is_safe(self):
        vec, races = di.matrix_from_frame(pd.DataFrame())
        self.assertTrue(vec.empty)
        self.assertEqual(di.rating_from_matrix(vec, races), [])
        self.assertEqual(di.clusters_from_matrix(vec, races)["points"], [])


if __name__ == "__main__":
    unittest.main()
