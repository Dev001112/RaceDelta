"""Rule-based verdict checks (no DB, no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.compare_verdict import verdict  # noqa: E402


def _comparison(a_feats, b_feats, wins, n=3, delta=None):
    return {"codes": {"a": "AAA", "b": "BBB"}, "drivers": {},
            "races": [{"season": 2026, "round": 1, "a": {"status": "Finished", "finish_position": 2},
                       "b": {"status": "Retired", "finish_position": None}}],
            "aggregate": {"races_compared": n, "wins": {"AAA": wins[0], "BBB": wins[1], "tie": 0},
                          "avg_pace_delta_s": delta, "a": a_feats, "b": b_feats}}


FAST = {"avg_pace_s": 90.0, "best_lap_s": 88.0, "grid_position": 2, "finish_position": 2, "lap_consistency_s": 0.4,
        "tyre_degradation_s_per_lap": 0.02, "overtake_count": 4, "position_changes": 1, "points": 50}
SLOW = {"avg_pace_s": 90.5, "best_lap_s": 88.6, "grid_position": 5, "finish_position": 5, "lap_consistency_s": 0.7,
        "tyre_degradation_s_per_lap": 0.05, "overtake_count": 3, "position_changes": 0, "points": 20}


def test_faster_more_successful_driver_wins_with_areas_explained():
    v = verdict(_comparison(FAST, SLOW, wins=(3, 0), delta=-0.5))
    assert v["winner"] == "AAA" and v["confidence"] > 0.12
    pace = next(x for x in v["areas"] if x["key"] == "race_pace")
    assert pace["leader"] == "A" and pace["detail"] == "0.5 s/lap"
    assert next(x for x in v["areas"] if x["key"] == "head_to_head")["leader"] == "A"
    assert "AAA leads on" in v["summary"] and "head-to-head 3-0" in v["summary"]
    assert any("BBB did not finish" in c for c in v["caveats"])


def test_identical_drivers_are_too_close_to_call():
    v = verdict(_comparison(dict(FAST), dict(FAST), wins=(1, 1), n=2, delta=0.0))
    assert v["winner"] is None and v["headline"] == "Too close to call"
    assert all(x["leader"] is None for x in v["areas"])


def test_no_shared_races_gives_an_honest_answer():
    v = verdict(_comparison({}, {}, wins=(0, 0), n=0))
    assert v["winner"] is None and v["areas"] == [] and "no race" in v["summary"]
