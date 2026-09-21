"""Post-section computations run before files are written.

These are first-pass measures intended to make the data immediately usable.
The raw per-frame data is always saved as well, so every measure here can be
recomputed offline with different methods or parameters.
"""
import math

import numpy as np

from .camera import FEATURE_NAMES

NAN = float("nan")


def hold_index(stim_t, t):
    """For each time in t, the index of the stimulus frame on screen at that
    moment (the last flip at or before t), or -1 if before the first flip."""
    return np.searchsorted(np.asarray(stim_t, float), np.asarray(t, float), side="right") - 1


def feature_columns():
    return [f"f_{n}" for n in FEATURE_NAMES] + ["eye_openness"]


def feature_values(frame):
    out = {}
    f = frame["features"]
    for i, n in enumerate(FEATURE_NAMES):
        out[f"f_{n}"] = NAN if f is None else float(f[i])
    out["eye_openness"] = NAN if frame["openness"] is None else float(frame["openness"])
    return out


def detect_saccade(t, x, cue_t, p):
    """Detect the first horizontal saccade after a cue in a webcam gaze trace.

    t      sample timestamps (s)
    x      horizontal gaze relative to screen centre in degrees (+ = right), NaN if invalid
    cue_t  cue onset time (s)
    p      config['saccade_detection']

    Method: find the first sample after the cue displaced from baseline by at
    least min_amplitude_deg; this fixes the saccade's direction. Then walk
    backwards through the contiguous run of samples whose velocity in that same
    direction exceeds velocity_threshold_deg_s - the jump that carried the eye
    there. Onset is the midpoint of the first sample pair in that run, so
    resolution is limited by the camera frame interval. Noise spikes in the
    opposite direction, or before a slow-velocity gap, cannot be credited as
    the onset. If the crossing itself was slow (below threshold), the trial is
    labelled method="position" for review.
    """
    res = {"onset_t": NAN, "rt_ms": NAN, "direction": "", "amplitude_deg": NAN,
           "peak_velocity_deg_s": NAN, "method": "", "valid_fraction": NAN,
           "quality": "", "later_opposite": False}
    t = np.asarray(t, float)
    x = np.asarray(x, float)
    b0, b1 = p["baseline_window_s"]
    s0, s1 = p["search_window_s"]

    win = (t >= cue_t + b0) & (t <= cue_t + s1)
    if not win.any():
        res["quality"] = "no_data"
        return res
    vf = float(np.isfinite(x[win]).mean())
    res["valid_fraction"] = vf
    if vf < p["min_valid_fraction"]:
        res["quality"] = "poor_tracking"
        return res

    base = (t >= cue_t + b0) & (t < cue_t + b1) & np.isfinite(x)
    baseline = float(np.median(x[base])) if base.any() else 0.0

    # include the last valid sample before the search window as a starting point
    sm = (t >= cue_t + s0) & (t <= cue_t + s1) & np.isfinite(x)
    pre = np.where((t < cue_t + s0) & np.isfinite(x))[0]
    idx = np.where(sm)[0]
    if len(pre):
        idx = np.concatenate([[pre[-1]], idx])
    ts, xs = t[idx], x[idx] - baseline
    if len(ts) < 3:
        res["quality"] = "poor_tracking"
        return res

    dt = np.diff(ts)
    dt[dt <= 0] = 1e-6
    vel = np.diff(xs) / dt          # vel[k] = velocity between samples k and k+1
    thr, amp, conf = p["velocity_threshold_deg_s"], p["min_amplitude_deg"], p["confirm_window_s"]

    # 1) anchor on the first sample displaced by >= min amplitude after the cue
    beyond = np.where((np.abs(xs) >= amp) & (ts >= cue_t + s0))[0]
    beyond = beyond[beyond > 0]
    if not len(beyond):
        res["quality"] = "no_saccade_detected"
        return res
    j = int(beyond[0])
    sgn = 1.0 if xs[j] > 0 else -1.0
    # 2) walk backwards through the contiguous run of same-direction,
    #    above-threshold velocity that carried the eye there
    onset_i = j - 1
    if sgn * vel[onset_i] >= thr:
        while onset_i - 1 >= 0 and sgn * vel[onset_i - 1] >= thr:
            onset_i -= 1
        method = "velocity"
    else:
        method = "position"       # slow drift across the amplitude threshold; treat with caution
    onset = (ts[onset_i] + ts[onset_i + 1]) / 2.0
    after = (ts >= ts[onset_i]) & (ts <= onset + 0.25)
    vmask = (ts[:-1] >= ts[onset_i]) & (ts[:-1] <= onset + conf)
    res.update({
        "onset_t": onset,
        "rt_ms": (onset - cue_t) * 1000.0,
        "direction": "right" if sgn > 0 else "left",
        "amplitude_deg": float(np.max(sgn * xs[after])),
        "peak_velocity_deg_s": float(np.max(np.abs(vel[vmask]))) if vmask.any() else NAN,
        "method": method,
        "quality": "ok",
        "later_opposite": bool(np.any(-sgn * xs[ts > onset + 0.05] >= amp)),
    })
    return res
