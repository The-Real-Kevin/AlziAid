"""Unit tests for saccade detection. Run:  python -m pytest tests   (or: python tests/test_analysis.py)"""
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from alice.analysis import detect_saccade, hold_index  # noqa: E402

P = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "config.yaml")))["saccade_detection"]
DT = 1 / 30.0


def trace(jumps, cue=1.0, dur=2.0, noise=0.0, seed=0):
    """jumps: list of (time_after_cue_s, new_position_deg)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, dur, DT) + 0.005
    x = np.zeros_like(t)
    for tj, pos in jumps:
        x[t >= cue + tj] = pos
    return t, x + rng.normal(0, noise, len(t)), cue


def test_clean_prosaccade():
    t, x, cue = trace([(0.20, 10.0)])
    s = detect_saccade(t, x, cue, P)
    assert s["quality"] == "ok" and s["direction"] == "right" and s["method"] == "velocity"
    assert 160 <= s["rt_ms"] <= 220, s["rt_ms"]     # within one frame of true 200 ms


def test_opposite_noise_spike_not_credited():
    """Regression: a +1 deg noise spike at +51 ms before a real leftward saccade
    at ~170 ms was once reported as a 68 ms onset."""
    cue = 24.056159
    rel = np.array([-249.0, -215.6, -182.2, -149.0, -115.6, -82.2, -48.9, -15.6, 17.8, 51.0, 84.4,
                    117.8, 151.1, 184.4, 217.7, 251.0, 284.4, 317.8, 351.0, 384.4, 417.7]) / 1000
    x = np.array([0.101, 0.123, -0.728, -0.309, -0.055, 0.005, 0.319, -0.304, -0.021, 1.008, -0.31,
                  0.267, -0.39, -9.499, -10.147, -10.215, -9.666, -10.236, -9.733, -9.894, -10.622])
    s = detect_saccade(cue + rel, x, cue, P)
    assert s["direction"] == "left"
    assert 150 <= s["rt_ms"] <= 190, s["rt_ms"]


def test_antisaccade_corrected_error():
    t, x, cue = trace([(0.18, 10.0), (0.45, -10.0)])
    s = detect_saccade(t, x, cue, P)
    assert s["direction"] == "right" and s["later_opposite"]


def test_no_saccade():
    t, x, cue = trace([], noise=0.3)
    assert detect_saccade(t, x, cue, P)["quality"] == "no_saccade_detected"


def test_poor_tracking():
    t, x, cue = trace([(0.2, 10.0)])
    x[(t > cue - 0.2) & (t < cue + 0.6)] = np.nan
    assert detect_saccade(t, x, cue, P)["quality"] == "poor_tracking"


def test_noisy_trials_rt_accuracy():
    errs = []
    for seed in range(200):
        true = 0.15 + (seed % 20) * 0.01
        side = 10.0 if seed % 2 else -10.0
        t, x, cue = trace([(true, side)], noise=0.5, seed=seed)
        s = detect_saccade(t, x, cue, P)
        assert s["quality"] == "ok" and s["direction"] == ("right" if side > 0 else "left")
        errs.append(s["rt_ms"] - true * 1000)
    errs = np.abs(errs)
    assert np.median(errs) <= DT * 1000, np.median(errs)   # median error within one frame


def test_hold_index():
    assert list(hold_index([1.0, 2.0, 3.0], [0.5, 1.0, 2.5, 9.0])) == [-1, 0, 1, 2]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
