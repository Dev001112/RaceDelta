"""Pure checks for the Compare Lab aggregation (no DB)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.compare_lab import build_comparison, conditions, track_name  # noqa: E402


def test_build_comparison_aggregates_only_races_both_drivers_ran():
    meta = [{"season": 2026, "round": r, "event": f"GP {r}"} for r in (1, 2, 3)]
    rows_a = {
        (2026, 1): {"avg_pace_s": 90.0, "finish_position": 1, "status": "Finished", "points": 25, "total_laps": 50},
        (2026, 2): {"avg_pace_s": 91.0, "finish_position": None, "status": "Retired", "points": 0, "total_laps": 10},
        (2026, 3): {"avg_pace_s": 88.0, "finish_position": 1, "status": "Finished", "points": 25, "total_laps": 60},
    }
    rows_b = {
        (2026, 1): {"avg_pace_s": 90.5, "finish_position": 2, "status": "Finished", "points": 18, "total_laps": 50},
        (2026, 2): {"avg_pace_s": 91.2, "finish_position": 5, "status": "+1 Lap", "points": 10, "total_laps": 49},
    }
    out = build_comparison("AAA", "BBB", rows_a, rows_b, meta)
    agg = out["aggregate"]
    assert agg["races_compared"] == 2                                   # round 3 has no BBB row
    assert agg["wins"] == {"AAA": 1, "BBB": 1, "tie": 0}                # AAA retired in round 2
    assert agg["avg_pace_delta_s"] == round(((90.0 - 90.5) + (91.0 - 91.2)) / 2, 3)
    assert agg["a"]["points"] == 25 and agg["b"]["points"] == 28
    assert out["races"][2]["b"] is None and out["races"][2]["winner"] is None
    assert out["races"][0]["pace_delta_s"] == -0.5


def test_condition_flags_and_track_aliases():
    r = {"rainfall": True, "sc_laps": 3, "vsc_laps": 0, "avg_track_temp": 45}
    assert conditions(r) == {"wet": True, "safety_car": True, "virtual_safety_car": False, "hot": True, "cool": False}
    assert conditions({"avg_track_temp": 20})["cool"] is True
    assert track_name("Monte Carlo", None) == "Monaco"
    assert track_name(None, "Dutch Grand Prix") == "Dutch Grand Prix"
