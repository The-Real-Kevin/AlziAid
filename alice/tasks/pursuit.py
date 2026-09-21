"""Section 1 - Smooth pursuit.

A red dot moves at constant speed in straight segments, turning to a new
random direction every 0.8-2.0 s (configurable). Each new direction is chosen
so the whole segment stays inside the safe area, so the dot never reaches the
edge of the screen.

Every screen flip is logged (time, dot position). After the section each
camera frame is matched to the dot position that was on screen at the moment
the frame was captured, and the gaze-to-target distance is computed.
"""
import math

import numpy as np
import pygame

from ..analysis import feature_columns, feature_values, hold_index
from ..clock import now
from ..config import hex_to_rgb

TAG = "01_smooth_pursuit"


def run(ctx):
    d, inp, tr, cfg, store = ctx.d, ctx.inp, ctx.tracker, ctx.cfg, ctx.store
    p = cfg["smooth_pursuit"]
    rng = ctx.rng
    colour = hex_to_rgb(p["colour"])
    radius = d.deg(p["dot_diameter_deg"]) / 2
    speed = d.deg(p["speed_deg_s"])
    mx, my = p["edge_margin_fraction"] * d.w, p["edge_margin_fraction"] * d.h
    x0, y0, x1, y1 = mx, my, d.w - mx, d.h - my
    centre = np.array(d.center, float)

    def inside(q):
        return x0 <= q[0] <= x1 and y0 <= q[1] <= y1

    def new_segment(pos):
        lo, hi = p["segment_duration_s"]
        for _ in range(200):
            ang = rng.uniform(0, 2 * math.pi)
            dur = rng.uniform(lo, hi)
            v = speed * np.array([math.cos(ang), math.sin(ang)])
            if inside(pos + v * dur):
                return v, dur
        v = centre - pos
        n = np.linalg.norm(v)
        v = speed * (v / n if n > 1e-6 else np.array([1.0, 0.0]))
        return v, min(hi, max(lo, n / speed * 0.9))

    stim = []   # (t, x, y, phase, block)
    pygame.mouse.set_visible(False)
    video_ok = tr.start_recording(store.file(f"{TAG}.mp4"))
    tr.start_log()
    t_section = now()
    try:
        for block in range(1, int(p["blocks"]) + 1):
            pos = centre.copy()
            t_end = now() + p["fixation_s"]
            while now() < t_end:
                inp.poll()
                tr.sim_hint(pos)
                d.clear()
                d.circle(colour, pos, radius)
                stim.append((d.flip(), pos[0], pos[1], "fixation", block))

            v, dur = new_segment(pos)
            t_start = t_last = now()
            seg_end = t_start + dur
            while True:
                t = now()
                if t - t_start >= p["block_duration_s"]:
                    break
                dt = t - t_last
                t_last = t
                if t >= seg_end:
                    v, dur = new_segment(pos)
                    seg_end = t + dur
                nxt = pos + v * dt
                if not inside(nxt):          # safety net; should not normally happen
                    v, dur = new_segment(pos)
                    seg_end = t + dur
                    nxt = np.clip(pos + v * dt, [x0, y0], [x1, y1])
                pos = nxt
                inp.poll()
                tr.sim_hint(pos)
                d.clear()
                d.circle(colour, pos, radius)
                stim.append((d.flip(), pos[0], pos[1], "pursuit", block))

            if block < int(p["blocks"]):
                t_end = now() + p["rest_s"]
                while now() < t_end:
                    inp.poll()
                    tr.sim_hint(centre)
                    d.clear()
                    d.text("Rest - keep your head still", (d.w / 2, d.h * 0.45), 34)
                    d.text(f"{int(math.ceil(t_end - now()))}", (d.w / 2, d.h * 0.53), 40)
                    stim.append((d.flip(), float("nan"), float("nan"), "rest", block))
    finally:
        video_times = tr.stop_recording()
        records = tr.stop_log()
        pygame.mouse.set_visible(True)

    # ---------------------------------------------------------------- merge
    frames = tr.predict_records(records)
    st = np.array([s[0] for s in stim])
    idx = hold_index(st, [f["t"] for f in frames])
    rows = []
    for f, i in zip(frames, idx):
        if i < 0:
            continue
        _, tx, ty, phase, block = stim[i]
        err_px = math.hypot(f["gaze_x"] - tx, f["gaze_y"] - ty)
        row = {"video_frame": f["video_frame"], "t_ms": (f["t"] - t_section) * 1000,
               "block": block, "phase": phase, "target_x": tx, "target_y": ty,
               "gaze_x": f["gaze_x"], "gaze_y": f["gaze_y"],
               "error_px": err_px, "error_deg": d.px_to_deg(err_px) if math.isfinite(err_px) else float("nan"),
               "face_detected": f["face"], "blink": f["blink"]}
        row.update(feature_values(f))
        rows.append(row)

    fields = ["video_frame", "t_ms", "block", "phase", "target_x", "target_y", "gaze_x", "gaze_y",
              "error_px", "error_deg", "face_detected", "blink"] + feature_columns()
    store.write_csv(f"{TAG}.csv", fields, rows)
    store.write_csv(f"{TAG}_stimulus.csv", ["t_ms", "target_x", "target_y", "phase", "block"],
                    [{"t_ms": (s[0] - t_section) * 1000, "target_x": s[1], "target_y": s[2],
                      "phase": s[3], "block": s[4]} for s in stim])
    store.write_csv(f"{TAG}_video_timestamps.csv", ["video_frame", "t_ms"],
                    [{"video_frame": k, "t_ms": (t - t_section) * 1000} for k, t in video_times])

    pur = [r for r in rows if r["phase"] == "pursuit"]
    errs = np.array([r["error_deg"] for r in pur], float)
    good = np.isfinite(errs)
    flips = np.diff([s[0] for s in stim if s[3] == "pursuit"])
    return {
        "video_saved": bool(video_ok),
        "video_frames": len(video_times),
        "gaze_frames_processed": len(frames),
        "pursuit_frames": len(pur),
        "valid_fraction": round(float(good.mean()), 3) if len(pur) else None,
        "median_error_deg": round(float(np.median(errs[good])), 3) if good.any() else None,
        "mean_error_deg": round(float(np.mean(errs[good])), 3) if good.any() else None,
        "display_frame_interval_ms": round(float(np.median(flips) * 1000), 2) if len(flips) else None,
    }
