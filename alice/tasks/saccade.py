"""Sections 2 and 3 - Prosaccade and antisaccade.

Layout: red fixation dot at centre, dark blue dots left and right. After a
random fixation period one blue dot turns green for 1 s.

  Prosaccade  : look AT the green dot;   F = left, J = right.
  Antisaccade : look AWAY from it;        F = look left, J = look right.

In both tasks the key names the direction the participant should LOOK.

Timing: the screen is static except at cue onset/offset, so instead of
redrawing every frame the loop only flips when the stimulus changes and
otherwise polls the keyboard about every millisecond. Cue onset time is the
flip timestamp; key time is the poll timestamp at which the press was seen.

Two independent reaction-time channels are saved per trial:
  rt_key_ms   manual response (keyboard)
  rt_gaze_ms  saccade onset detected in the webcam gaze trace
They measure different things and should be analysed separately.
"""
import time

import numpy as np
import pygame

from ..analysis import detect_saccade, feature_columns, feature_values, hold_index
from ..clock import now
from ..config import hex_to_rgb

KEYS = {pygame.K_f: "F", pygame.K_j: "J"}
LOOK_TO_KEY = {"left": "F", "right": "J"}


def run(ctx, anti=False):
    d, inp, tr, cfg, store, rng = ctx.d, ctx.inp, ctx.tracker, ctx.cfg, ctx.store, ctx.rng
    name = "antisaccade" if anti else "prosaccade"
    tag = f"03_{name}" if anti else f"02_{name}"
    p = cfg[name]
    sd = cfg["saccade_detection"]

    ecc = d.deg(p["eccentricity_deg"])
    cx, cy = d.center
    pos = {"centre": (cx, cy), "left": (cx - ecc, cy), "right": (cx + ecc, cy)}
    r_fix = d.deg(p["fixation_diameter_deg"]) / 2
    r_tgt = d.deg(p["target_diameter_deg"]) / 2
    c_fix, c_tgt, c_cue = (hex_to_rgb(p[k]) for k in ("fixation_colour", "target_colour", "cue_colour"))

    def draw(cue=None):
        d.clear()
        d.circle(c_fix, pos["centre"], r_fix)
        for side in ("left", "right"):
            d.circle(c_cue if cue == side else c_tgt, pos[side], r_tgt)

    def balanced(n):
        sides = ["left", "right"] * (n // 2) + (["left"] if n % 2 else [])
        rng.shuffle(sides)
        return sides

    trials = [(True, s) for s in balanced(int(p["practice_trials"]))] + \
             [(False, s) for s in balanced(int(p["trials"]))]

    stim = []           # (t, state, trial)
    rows = []
    pygame.mouse.set_visible(False)
    video_ok = tr.start_recording(store.file(f"{tag}.mp4"))
    tr.start_log()
    t_section = now()
    practice_announced = False
    try:
        n_main = 0
        for k, (practice, cue_side) in enumerate(trials, start=1):
            if not practice and not practice_announced and p["practice_trials"] > 0:
                practice_announced = True
                _hold_message(ctx, cfg["instructions"].get(f"{name}_practice_done", "The test starts now."), 4.0)
            if not practice:
                n_main += 1
            look = cue_side if not anti else ("left" if cue_side == "right" else "right")
            want = LOOK_TO_KEY[look]
            iti = float(rng.uniform(*p["iti_s"]))

            draw()
            tr.sim_hint(pos["centre"])
            t_fix = d.flip(tick=False)
            stim.append((t_fix, "fixation", k))
            early = 0
            while now() < t_fix + iti:
                _, ev = inp.poll()
                early += sum(1 for e in ev if e.type == pygame.KEYDOWN and e.key in KEYS)
                time.sleep(0.0005)

            draw(cue=cue_side)
            t_cue = d.flip(tick=False)
            stim.append((t_cue, f"cue_{cue_side}", k))
            if inp.auto:
                _autopilot(ctx, anti, cue_side, look, pos)

            key = key_t = None
            t_off = None
            while now() < t_cue + p["response_window_s"]:
                if t_off is None and now() >= t_cue + p["cue_duration_s"]:
                    draw()
                    t_off = d.flip(tick=False)
                    stim.append((t_off, "fixation", k))
                t, ev = inp.poll()
                for e in ev:
                    if e.type == pygame.KEYDOWN and e.key in KEYS and key is None:
                        key, key_t = KEYS[e.key], t
                time.sleep(0.0005)
            if t_off is None:
                draw()
                t_off = d.flip(tick=False)
                stim.append((t_off, "fixation", k))

            rt_key = (key_t - t_cue) * 1000 if key_t is not None else float("nan")
            rows.append({
                "trial": k, "practice": practice, "main_trial": n_main if not practice else "",
                "cue_side": cue_side, "correct_look": look, "correct_key": want,
                "iti_ms": iti * 1000,
                "cue_onset_ms": (t_cue - t_section) * 1000, "cue_offset_ms": (t_off - t_section) * 1000,
                "key": key or "", "key_time_ms": (key_t - t_section) * 1000 if key_t else float("nan"),
                "rt_key_ms": rt_key, "key_correct": (key == want) if key else False,
                "key_missing": key is None,
                "key_anticipatory": bool(key_t is not None and rt_key < p["anticipatory_ms"]),
                "early_keypresses": early, "_t_cue": t_cue,
            })

            if practice:
                ok = key == want
                txt = "Correct" if ok else (
                    f"Remember: look to the {'OPPOSITE side' if anti else 'green dot'} and press {want}"
                    if key else f"Too slow - press {want} for this one")
                _hold_message(ctx, txt, 1.5, colour=d.col["ok"] if ok else d.col["bad"])
    finally:
        video_times = tr.stop_recording()
        records = tr.stop_log()
        inp.clear_schedule()
        pygame.mouse.set_visible(True)

    # ------------------------------------------------------------- analysis
    frames = tr.predict_records(records)
    ft = np.array([f["t"] for f in frames])
    fx = np.array([d.px_to_deg(f["gaze_x"] - cx) if np.isfinite(f["gaze_x"]) else np.nan for f in frames])
    for row in rows:
        s = detect_saccade(ft, fx, row["_t_cue"], sd)
        sacc_ok = s["quality"] == "ok"
        correct = sacc_ok and s["direction"] == row["correct_look"]
        row.update({
            "saccade_onset_ms": (s["onset_t"] - t_section) * 1000 if sacc_ok else float("nan"),
            "rt_gaze_ms": s["rt_ms"], "saccade_direction": s["direction"],
            "saccade_correct": correct if sacc_ok else "",
            "saccade_amplitude_deg": s["amplitude_deg"],
            "peak_velocity_deg_s": s["peak_velocity_deg_s"],
            "gaze_anticipatory": bool(sacc_ok and s["rt_ms"] < p["anticipatory_ms"]),
            "detection_method": s["method"], "gaze_quality": s["quality"],
            "gaze_valid_fraction": s["valid_fraction"],
        })
        if anti:
            err = sacc_ok and s["direction"] == row["cue_side"]
            row["direction_error"] = err if sacc_ok else ""
            row["corrected_error"] = (err and s["later_opposite"]) if sacc_ok else ""

    st = np.array([s[0] for s in stim])
    idx = hold_index(st, ft)
    frame_rows = []
    for f, i, xd in zip(frames, idx, fx):
        if i < 0:
            continue
        r = {"video_frame": f["video_frame"], "t_ms": (f["t"] - t_section) * 1000,
             "trial": stim[i][2], "stimulus": stim[i][1],
             "gaze_x": f["gaze_x"], "gaze_y": f["gaze_y"], "gaze_x_deg": xd,
             "face_detected": f["face"], "blink": f["blink"]}
        r.update(feature_values(f))
        frame_rows.append(r)

    trial_fields = ["trial", "practice", "main_trial", "cue_side", "correct_look", "correct_key", "iti_ms",
                    "cue_onset_ms", "cue_offset_ms", "key", "key_time_ms", "rt_key_ms", "key_correct",
                    "key_missing", "key_anticipatory", "early_keypresses",
                    "saccade_onset_ms", "rt_gaze_ms", "saccade_direction", "saccade_correct"]
    if anti:
        trial_fields += ["direction_error", "corrected_error"]
    trial_fields += ["saccade_amplitude_deg", "peak_velocity_deg_s", "gaze_anticipatory",
                     "detection_method", "gaze_quality", "gaze_valid_fraction"]
    store.write_csv(f"{tag}_trials.csv", trial_fields, rows)
    store.write_csv(f"{tag}_frames.csv",
                    ["video_frame", "t_ms", "trial", "stimulus", "gaze_x", "gaze_y", "gaze_x_deg",
                     "face_detected", "blink"] + feature_columns(), frame_rows)
    store.write_csv(f"{tag}_video_timestamps.csv", ["video_frame", "t_ms"],
                    [{"video_frame": k, "t_ms": (t - t_section) * 1000} for k, t in video_times])

    main = [r for r in rows if not r["practice"]]
    rt_k = [r["rt_key_ms"] for r in main if r["key_correct"] and not r["key_anticipatory"]]
    rt_g = [r["rt_gaze_ms"] for r in main if r["gaze_quality"] == "ok" and r["saccade_correct"]
            and not r["gaze_anticipatory"]]
    summary = {
        "video_saved": bool(video_ok), "video_frames": len(video_times),
        "trials": len(main), "practice_trials": len(rows) - len(main),
        "key_accuracy": round(np.mean([r["key_correct"] for r in main]), 3) if main else None,
        "key_missing": int(sum(r["key_missing"] for r in main)),
        "median_rt_key_ms": round(float(np.median(rt_k)), 1) if rt_k else None,
        "saccades_detected": int(sum(r["gaze_quality"] == "ok" for r in main)),
        "median_rt_gaze_ms": round(float(np.median(rt_g)), 1) if rt_g else None,
    }
    if anti:
        det = [r for r in main if r["gaze_quality"] == "ok"]
        summary["gaze_direction_error_rate"] = round(np.mean([r["direction_error"] for r in det]), 3) if det else None
    return summary


def _hold_message(ctx, text, secs, colour=None):
    d, inp = ctx.d, ctx.inp
    t0 = now()
    while now() - t0 < secs:
        d.clear()
        d.paragraph(text, d.w * 0.2, d.h * 0.42, d.w * 0.6, 34, colour=colour, align="center")
        d.flip()
        inp.poll()


def _autopilot(ctx, anti, cue_side, look, pos):
    """Simulated participant for automated tests: occasional errors, plausible latencies."""
    inp, tr, rng = ctx.inp, ctx.tracker, ctx.rng
    lat = float(rng.uniform(0.18, 0.32 if not anti else 0.40))
    if anti and rng.random() < 0.25:                         # reflexive error, then correct
        inp.schedule(lat, lambda: tr.sim_hint(pos[cue_side]))
        inp.schedule(lat + 0.25, lambda: tr.sim_hint(pos[look]))
    else:
        inp.schedule(lat, lambda: tr.sim_hint(pos[look]))
    inp.schedule(1.2, lambda: tr.sim_hint(pos["centre"]))
    key = pygame.K_f if look == "left" else pygame.K_j
    if rng.random() < 0.1:
        key = pygame.K_j if key == pygame.K_f else pygame.K_f
    inp.auto_key(lat + float(rng.uniform(0.12, 0.3)), key)
