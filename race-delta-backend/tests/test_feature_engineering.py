"""Synthetic-data checks for the Phase-2 feature engineering layer (no DB, no network)."""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services import feature_engineering as fe  # noqa: E402


def _driver_frame(abbr, number, base, per_lap, positions, pit_lap=6, n=12):
    """A driver whose lap time is exactly linear in lap number, with one pit stop."""
    laps = np.arange(1, n + 1)
    times = base + per_lap * laps
    stint = np.where(laps <= pit_lap, 1, 2)
    tyre_life = np.where(laps <= pit_lap, laps, laps - pit_lap)
    df = pd.DataFrame({
        "Driver": abbr, "DriverNumber": str(number), "Team": "Test Team",
        "LapNumber": laps.astype(float),
        "LapTime": pd.to_timedelta(times, unit="s"),
        "Sector1Time": pd.to_timedelta(times * 0.3, unit="s"),
        "Sector2Time": pd.to_timedelta(times * 0.4, unit="s"),
        "Sector3Time": pd.to_timedelta(times * 0.3, unit="s"),
        "Time": pd.to_timedelta(np.cumsum(times), unit="s"),
        "Stint": stint.astype(float),
        "TyreLife": tyre_life.astype(float),
        "Compound": np.where(stint == 1, "MEDIUM", "HARD"),
        "Position": np.array(positions, dtype=float),
        "TrackStatus": "1", "IsAccurate": True, "Deleted": False,
        "PitInTime": pd.to_timedelta([np.nan] * n, unit="s"),
        "PitOutTime": pd.to_timedelta([np.nan] * n, unit="s"),
    })
    df.loc[df["LapNumber"] == pit_lap, "PitInTime"] = pd.Timedelta(seconds=1)
    df.loc[df["LapNumber"] == pit_lap + 1, "PitOutTime"] = pd.Timedelta(seconds=1)
    return df


class FeatureEngineeringTests(unittest.TestCase):
    def setUp(self):
        # AAA starts P2 and passes BBB on lap 4; BBB is quicker per lap early on.
        self.aaa = _driver_frame("AAA", 7, 90.0, 0.10, [2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.bbb = _driver_frame("BBB", 8, 90.0, 0.05, [1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2])
        self.laps = pd.concat([self.aaa, self.bbb], ignore_index=True)
        self.gaps = fe.compute_gaps(self.laps)
        self.rcm = pd.DataFrame({"Message": [
            "FIA STEWARDS: 5 SECOND TIME PENALTY FOR CAR 7 (AAA) - UNSAFE RELEASE",
            "FIA STEWARDS: PENALTY SERVED - 5 SECOND TIME PENALTY FOR CAR 7 (AAA)",
            "GREEN LIGHT - PIT EXIT OPEN",
        ]})

    def test_clean_mask_excludes_pit_laps(self):
        self.assertEqual(int(fe.clean_mask(self.aaa).sum()), 10)  # 12 laps minus pit-in + pit-out

    def test_pace_trend_and_degradation_recover_known_slopes(self):
        f = fe.driver_race_features(self.aaa, self.gaps,
                                    {"GridPosition": 2, "ClassifiedPosition": "1", "Status": "Finished", "Points": 25})
        self.assertAlmostEqual(f["race_pace_trend_s_per_lap"], 0.10, places=3)
        self.assertAlmostEqual(f["tyre_degradation_s_per_lap"], 0.10, places=3)
        self.assertGreater(f["lap_consistency_s"], 0)
        self.assertEqual(f["clean_laps"], 10)
        self.assertEqual(f["pit_stop_count"], 1)
        self.assertEqual(f["pit_laps"], [6])
        self.assertEqual(f["avg_stint_length"], 6.0)
        self.assertEqual(f["overtake_count"], 1)
        self.assertEqual(f["position_changes"], 1)  # grid 2 -> finish 1
        self.assertEqual(f["finish_position"], 1)
        self.assertEqual(f["points"], 25.0)

    def test_dnf_has_no_finish_or_position_change(self):
        f = fe.driver_race_features(self.bbb, self.gaps,
                                    {"GridPosition": 1, "ClassifiedPosition": "R", "Status": "Retired", "Points": 0})
        self.assertIsNone(f["finish_position"])
        self.assertIsNone(f["position_changes"])
        self.assertEqual(f["overtake_count"], 0)

    def test_gaps_follow_running_order(self):
        lap1 = self.laps[self.laps["LapNumber"] == 1]
        a = self.gaps.loc[lap1[lap1["Driver"] == "AAA"].index[0]]
        b = self.gaps.loc[lap1[lap1["Driver"] == "BBB"].index[0]]
        self.assertTrue(np.isnan(b["gap_ahead_s"]))                # leader has nobody ahead
        self.assertAlmostEqual(a["gap_ahead_s"], 0.05, places=6)   # AAA 90.10 vs BBB 90.05
        self.assertAlmostEqual(b["gap_behind_s"], 0.05, places=6)

    def test_penalties_count_only_awards_for_this_car(self):
        self.assertEqual(fe.count_penalties(self.rcm, "AAA", "7"), 1)  # 'SERVED' not double counted
        self.assertEqual(fe.count_penalties(self.rcm, "BBB", "8"), 0)
        self.assertEqual(fe.count_penalties(None, "AAA", "7"), 0)

    def test_stint_features(self):
        stints = fe.stint_features(self.aaa)
        self.assertEqual([s["stint_number"] for s in stints], [1, 2])
        self.assertEqual([s["compound"] for s in stints], ["MEDIUM", "HARD"])
        self.assertEqual((stints[0]["lap_start"], stints[0]["lap_end"], stints[0]["laps"]), (1, 6, 6))
        self.assertAlmostEqual(stints[1]["degradation_s_per_lap"], 0.10, places=3)

    def test_weather_summary(self):
        w = fe.weather_summary(pd.DataFrame({"AirTemp": [20, 22], "TrackTemp": [30, 34],
                                             "Humidity": [50, 60], "Rainfall": [False, True]}))
        self.assertEqual(w, {"avg_air_temp": 21.0, "avg_track_temp": 32.0, "avg_humidity": 55.0, "rainfall": True})


if __name__ == "__main__":
    unittest.main()
