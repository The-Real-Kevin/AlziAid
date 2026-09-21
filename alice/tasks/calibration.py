"""Gaze calibration, validation and drift check.

Calibration : 9 points (3x3 grid) shown one at a time in random order. The
              participant looks at each and clicks it (or the operator presses
              SPACE). Samples are taken after a short settling delay.
Validation  : 5 different points, no clicking. The fitted model predicts
              gaze at each; the angular error is the accuracy of this session.
Drift check : one centre point part-way through the session.
"""
import math
import time

import numpy as np
import pygame

from ..clock import now
from ..gaze import GazeModel

GRID = [(0, 0), (0.5, 0), (1, 0), (0, 0.5), (0.5, 0.5), (1, 0.5), (0, 1), (0.5, 1), (1, 1)]
VALIDATION = [(0.25, 0.3), (0.75, 0.3), (0.25, 0.7), (0.75, 0.7), (0.5, 0.85)]


def _to_px(d, frac, margin):
    mx, my = margin * d.w, margin * d.h
    return (mx + frac[0] * (d.w - 2 * mx), my + frac[1] * (d.h - 2 * my))


def _draw_target(d, pos, r, colour=(204, 0, 0)):
    d.circle(colour, pos, r, outline=True)
    d.circle((0, 0, 0), pos, max(2, r * 0.18))


def _present_click_point(ctx, pos):
    """Show a shrinking target until clicked/SPACE, then collect samples."""
    d, inp, tr, p = ctx.d, ctx.inp, ctx.tracker, ctx.cfg["calibration"]
    r = d.deg(p["dot_diameter_deg"]) / 2
    tr.sim_hint(pos)
    if inp.auto:
        inp.auto_click(0.5, pos)
    t0 = now()
    clicked = False     # an early click is kept and honoured once the dot has finished shrinking
    while True:
        k = min(1.0, (now() - t0) / 0.6)
        d.clear()
        _draw_target(d, pos, r * (2.5 - 1.5 * k))
        d.flip()
        _, events = inp.poll()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if math.dist(e.pos, pos) <= r * 4:
                    clicked = True
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                clicked = True
        if clicked and k >= 1.0:
            break
    t_click = now()
    logging = False
    while True:
        t = now()
        if not logging and t >= t_click + p["settle_s"]:
            tr.start_log()
            logging = True
        if t >= t_click + p["settle_s"] + p["collect_s"]:
            break
        d.clear()
        _draw_target(d, pos, r * 0.6, colour=(0, 0, 0))
        d.flip()
        inp.poll()
    return tr.stop_log()


def _present_passive_point(ctx, pos, dot_s, collect_from_s):
    d, inp, tr, p = ctx.d, ctx.inp, ctx.tracker, ctx.cfg["calibration"]
    r = d.deg(p["dot_diameter_deg"]) / 2
    tr.sim_hint(pos)
    t0 = now()
    logging = False
    while True:
        t = now()
        if not logging and t >= t0 + collect_from_s:
            tr.start_log()
            logging = True
        if t >= t0 + dot_s:
            break
        k = min(1.0, (t - t0) / 0.4)
        d.clear()
        _draw_target(d, pos, r * (2.0 - k))
        d.flip()
        inp.poll()
    return tr.stop_log()


def _brief(ctx, text, secs=1.0):
    d, inp = ctx.d, ctx.inp
    t0 = now()
    while now() - t0 < secs:
        d.clear()
        d.paragraph(text, d.w * 0.2, d.h * 0.42, d.w * 0.6, 34, align="center")
        d.flip()
        inp.poll()


def calibrate(ctx, attempt):
    """Run one calibration + validation attempt. Returns (summary, csv_rows)."""
    d, tr, cfg = ctx.d, ctx.tracker, ctx.cfg
    p = cfg["calibration"]
    pygame.mouse.set_visible(True)
    order = list(range(len(GRID)))
    ctx.rng.shuffle(order)

    X, Y, G, openness, rows = [], [], [], [], []
    for gi in order:
        pos = _to_px(d, GRID[gi], p["margin_fraction"])
        valid = []
        for tries in range(p["max_point_retries"] + 1):
            recs = _present_click_point(ctx, pos)
            valid = [r for r in recs if tr.valid(r)]
            if len(valid) >= p["min_samples_per_point"]:
                break
            if tries < p["max_point_retries"]:
                _brief(ctx, "Let's try that dot again.")
        for r in valid:
            X.append(r[3][tr.feature_idx])
            Y.append(pos)
            G.append(gi)
            openness.append(r[4])
        rows.append({"attempt": attempt, "phase": "calibration", "point": gi,
                     "target_x": pos[0], "target_y": pos[1], "n_samples": len(valid)})

    used_points = len(set(G))
    if used_points < 6:
        return ({"attempt": attempt, "status": "failed", "reason": f"only {used_points} usable points",
                 "mean_error_deg": None}, rows)

    model = GazeModel(p["model_degrees"], p["ridge_alphas"]).fit(np.array(X), np.array(Y), np.array(G))
    tr.model = model
    tr.openness_ref = float(np.median(openness))

    # ---- validation
    if not ctx.inp.auto:
        _brief(ctx, ctx.cfg["instructions"]["validation"], 2.5)
    errs, precs, val_points = [], [], []
    for vi, frac in enumerate(VALIDATION):
        pos = _to_px(d, frac, p["margin_fraction"])
        recs = _present_passive_point(ctx, pos, p["validation_dot_s"], p["validation_collect_from_s"])
        frames = tr.predict_records(recs)
        g = np.array([[f["gaze_x"], f["gaze_y"]] for f in frames if np.isfinite(f["gaze_x"])])
        row = {"attempt": attempt, "phase": "validation", "point": vi,
               "target_x": pos[0], "target_y": pos[1], "n_samples": len(g)}
        if len(g) >= 3:
            med = np.median(g, axis=0)
            err = d.px_to_deg(float(np.linalg.norm(med - np.array(pos))))
            prec = d.px_to_deg(float(np.sqrt(np.mean(np.sum((g - med) ** 2, axis=1)))))
            errs.append(err)
            precs.append(prec)
            row.update({"pred_x": med[0], "pred_y": med[1], "error_deg": err, "precision_rms_deg": prec})
            val_points.append((pos, tuple(med)))
        else:
            val_points.append((pos, None))
        rows.append(row)

    if len(errs) < 3:
        summary = {"attempt": attempt, "status": "failed", "reason": "too few valid validation samples",
                   "mean_error_deg": None}
    else:
        mean_err = float(np.mean(errs))
        status = "pass" if mean_err < p["pass_deg"] else ("warn" if mean_err < p["warn_deg"] else "failed")
        summary = {"attempt": attempt, "status": status,
                   "mean_error_deg": round(mean_err, 3), "max_error_deg": round(float(np.max(errs)), 3),
                   "precision_rms_deg": round(float(np.mean(precs)), 3),
                   "n_calibration_points": used_points, "n_calibration_samples": len(X),
                   "model": model.describe(),
                   "cv_error_deg": round(d.px_to_deg(model.cv_error_px), 3),
                   "openness_reference": round(tr.openness_ref, 4)}
    summary["_val_points"] = val_points
    return summary, rows


def draw_validation_map(d, val_points):
    """Targets (circles) and predicted gaze (crosses) for the operator."""
    for pos, pred in val_points:
        pygame.draw.circle(d.screen, (0, 0, 0), (int(pos[0]), int(pos[1])), 10, 2)
        if pred is not None:
            x, y = int(pred[0]), int(pred[1])
            pygame.draw.line(d.screen, (150, 150, 150), (int(pos[0]), int(pos[1])), (x, y), 1)
            pygame.draw.line(d.screen, (204, 0, 0), (x - 8, y - 8), (x + 8, y + 8), 3)
            pygame.draw.line(d.screen, (204, 0, 0), (x - 8, y + 8), (x + 8, y - 8), 3)


def drift_check(ctx):
    d, tr, p = ctx.d, ctx.tracker, ctx.cfg["calibration"]["drift_check"]
    pygame.mouse.set_visible(False)
    recs = _present_passive_point(ctx, d.center, p["dot_s"], p["collect_from_s"])
    frames = tr.predict_records(recs)
    g = np.array([[f["gaze_x"], f["gaze_y"]] for f in frames if np.isfinite(f["gaze_x"])])
    if len(g) < 3:
        return {"error_deg": None, "passed": False, "n_samples": len(g)}
    med = np.median(g, axis=0)
    err = d.px_to_deg(float(np.linalg.norm(med - np.array(d.center))))
    return {"error_deg": round(err, 3), "passed": err <= p["fail_deg"], "n_samples": len(g),
            "offset_x_deg": round(d.px_to_deg(med[0] - d.center[0]), 3),
            "offset_y_deg": round(d.px_to_deg(med[1] - d.center[1]), 3)}
