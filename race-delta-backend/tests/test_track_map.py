"""Geometry checks for the track map (no FastF1 download)."""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services import track_map as tm  # noqa: E402


def test_scaler_fits_the_box_keeps_aspect_and_flips_y():
    outline = np.array([[0.0, 0.0], [2000.0, 0.0], [2000.0, 500.0], [0.0, 500.0]])   # wide rectangle
    scale = tm._scaler(outline)
    out = scale(outline.copy())
    margin = 0.06 * tm.SIZE
    assert math.isclose(out[:, 0].min(), margin) and math.isclose(out[:, 0].max(), tm.SIZE - margin)
    width, height = out[:, 0].max() - out[:, 0].min(), out[:, 1].max() - out[:, 1].min()
    assert math.isclose(width / height, 4.0)                          # aspect ratio preserved
    assert out[0][1] > out[3][1]                                        # y=0 in telemetry is at the bottom in SVG
    assert math.isclose((out[:, 1].max() + out[:, 1].min()) / 2, tm.SIZE / 2)   # centred vertically


def test_rotation_is_a_pure_rotation():
    pts = np.array([[1.0, 0.0], [0.0, 1.0]])
    rot = tm._rotate(pts, math.radians(90))
    assert np.allclose(np.linalg.norm(rot, axis=1), 1.0)
    assert np.allclose(rot[0], [0.0, -1.0]) or np.allclose(rot[0], [0.0, 1.0])
