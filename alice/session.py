"""Top-level application flow.

start page -> participant details -> face positioning -> calibration/validation
-> 1 smooth pursuit -> 2 prosaccade -> drift check -> 3 antisaccade
-> 4 RDK -> 5 colour -> save (group label) -> next participant

Esc at any time: operator chooses to abort (data so far kept, folder marked
PARTIAL) or restart the current section from scratch.
"""
import secrets
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pygame

from . import __version__, screens
from .clock import now
from .config import load_config
from .display import Display
from .inputs import AbortRequested, Input
from .storage import SessionStore, existing_subject_numbers, next_subject_number
from .tasks import calibration, colour, pursuit, rdk, saccade
from .tracking import CameraTracker, SimTracker


class SessionAborted(Exception):
    pass


@dataclass
class Ctx:
    d: Display
    inp: Input
    tracker: object
    cfg: dict
    rng: np.random.Generator = field(default_factory=np.random.default_rng)
    store: SessionStore = None
    session: dict = None


def _guard(ctx, fn, *args):
    """Run a step; on Esc ask the operator whether to abort or restart the step."""
    while True:
        try:
            return fn(*args)
        except AbortRequested:
            ctx.inp.clear_schedule()
            pygame.mouse.set_visible(True)
            if screens.confirm_abort(ctx, in_session=True) == "abort":
                raise SessionAborted()


def _save_progress(ctx):
    ctx.store.write_json("session.json", ctx.session)


# =============================================================================
# Steps
# =============================================================================
def calibration_phase(ctx, label="initial"):
    cfg, d = ctx.cfg, ctx.d
    p = cfg["calibration"]
    screens.face_position(ctx)
    screens.instruction(ctx, "Calibration", cfg["instructions"]["calibration"])
    failures = 0
    rows_all = []
    attempts = ctx.session["calibration"]["attempts"]
    while True:
        attempt = len(attempts) + 1
        summary, rows = calibration.calibrate(ctx, attempt)
        val_points = summary.pop("_val_points", [])
        summary["label"] = label
        attempts.append(summary)
        rows_all.extend(rows)
        _write_calibration_csv(ctx, rows)
        _save_progress(ctx)

        status = summary["status"]
        if status == "failed":
            failures += 1
        err = summary.get("mean_error_deg")
        col = {"pass": d.col["ok"], "warn": d.col["warn"]}.get(status, d.col["bad"])
        verdict = {"pass": "PASS", "warn": "ACCEPTABLE (will be flagged)", "failed": "FAILED"}[status]
        body = (f"Mean error: {err:.2f} deg   (pass < {p['pass_deg']}, acceptable < {p['warn_deg']})"
                if err is not None else summary.get("reason", ""))
        if status == "pass":
            options = [("continue", "Continue"), ("recal", "Recalibrate")]
        elif status == "warn":
            options = [("continue", "Continue (flagged)"), ("recal", "Recalibrate")]
        else:
            options = [("recal", "Recalibrate")]
            if failures >= p["failures_before_override"]:
                options.append(("continue", "Continue anyway (flagged)"))
        auto = "continue" if any(o[0] == "continue" for o in options) else "recal"

        def extra():
            calibration.draw_validation_map(d, val_points)
            d.text("circle = target   x = estimated gaze", (d.w / 2, d.h * 0.78), 20,
                   colour=d.col["disabled_text"])

        choice = screens.message(ctx, f"Calibration {verdict}", body, options, auto=auto, extra=extra, colour=col)
        if choice == "continue":
            summary["accepted"] = True
            summary["operator_override"] = status == "failed"
            ctx.session["calibration"]["final"] = summary
            _save_progress(ctx)
            return
        screens.face_position(ctx)


def _write_calibration_csv(ctx, rows):
    ctx.session.setdefault("_cal_rows", []).extend(rows)
    ctx.store.write_csv("calibration.csv",
                        ["attempt", "phase", "point", "target_x", "target_y", "n_samples",
                         "pred_x", "pred_y", "error_deg", "precision_rms_deg"],
                        ctx.session["_cal_rows"])


def drift_step(ctx):
    cfg = ctx.cfg
    if not cfg["calibration"]["drift_check"]["enabled"]:
        return
    screens.instruction(ctx, "Quick check", cfg["instructions"]["drift_check"])
    res = calibration.drift_check(ctx)
    res["before_section"] = 3
    ctx.session["calibration"]["drift_checks"].append(res)
    _save_progress(ctx)
    if not res["passed"]:
        err = res["error_deg"]
        body = (f"Gaze has drifted {err:.2f} deg from the centre point." if err is not None
                else "Not enough valid tracking data during the check.")
        choice = screens.message(ctx, "Drift detected", body + " Recalibration is recommended.",
                                 [("recal", "Recalibrate"), ("continue", "Continue (flagged)")],
                                 auto="continue", colour=ctx.d.col["warn"])
        if choice == "recal":
            calibration_phase(ctx, label="after_drift_check")


SECTIONS = [
    (1, "smooth_pursuit", "Part 1 of 5 - Following a dot", lambda c: pursuit.run(c)),
    (2, "prosaccade", "Part 2 of 5 - Look at the green dot", lambda c: saccade.run(c, anti=False)),
    ("drift", None, None, None),
    (3, "antisaccade", "Part 3 of 5 - Look the other way", lambda c: saccade.run(c, anti=True)),
    (4, "rdk", "Part 4 of 5 - Moving dots", lambda c: rdk.run(c)),
    (5, "colour", "Part 5 of 5 - Colours", lambda c: colour.run(c)),
]


def run_section(ctx, num, key, title, fn):
    screens.instruction(ctx, title, ctx.cfg["instructions"][key])
    t0 = datetime.now().isoformat(timespec="seconds")
    summary = fn(ctx)
    summary.update({"started": t0, "finished": datetime.now().isoformat(timespec="seconds")})
    ctx.session["sections"][f"{num}_{key}"] = summary
    ctx.session["sections_completed"].append(num)
    _save_progress(ctx)


# =============================================================================
# Session
# =============================================================================
def one_session(ctx):
    """Returns True to run another session, False to quit."""
    cfg = ctx.cfg
    try:
        if screens.start_page(ctx) == "quit":
            return False
        meta = screens.participant_form(ctx, next_subject_number(cfg), existing_subject_numbers(cfg))
    except AbortRequested:
        return screens.confirm_abort(ctx, in_session=False) != "quit"

    seed = cfg["software"].get("random_seed")
    seed = int(seed) if seed is not None else secrets.randbits(32)
    ctx.rng = np.random.default_rng(seed)
    ctx.store = SessionStore(cfg, meta["subject_number"])
    hw = ctx.d.info()
    hw.update(ctx.tracker.info())
    ctx.session = {
        "subject_id": ctx.store.subject_id,
        "group_label": None,
        "status": "in_progress",
        "session_datetime": datetime.now().isoformat(timespec="seconds"),
        "software_version": __version__,
        "operator_initials": meta.pop("operator_initials"),
        "participant": {k: v for k, v in meta.items() if k != "subject_number"},
        "random_seed": seed,
        "hardware": hw,
        "calibration": {"attempts": [], "final": None, "drift_checks": []},
        "sections": {},
        "sections_completed": [],
        "notes": "",
    }
    _save_progress(ctx)

    try:
        _guard(ctx, calibration_phase, ctx)
        for num, key, title, fn in SECTIONS:
            if num == "drift":
                _guard(ctx, drift_step, ctx)
            else:
                _guard(ctx, run_section, ctx, num, key, title, fn)
        ctx.session["hardware"].update(ctx.tracker.info())   # final measured fps
        group, notes = _guard(ctx, screens.save_screen, ctx)
        ctx.session.update({"group_label": group, "notes": notes, "status": "complete",
                            "session_end": datetime.now().isoformat(timespec="seconds")})
        ctx.session.pop("_cal_rows", None)
        _save_progress(ctx)
        path = ctx.store.finalize(group)
        partial = False
    except SessionAborted:
        ctx.session.pop("_cal_rows", None)
        ctx.session.update({"status": "aborted",
                            "session_end": datetime.now().isoformat(timespec="seconds")})
        _save_progress(ctx)
        path = ctx.store.mark_partial()
        partial = True
    except Exception:
        ctx.session.pop("_cal_rows", None)
        ctx.session.update({"status": "crashed", "error": traceback.format_exc()})
        try:
            _save_progress(ctx)
            ctx.store.mark_partial()
        except Exception:
            pass
        raise

    print(f"[ALICE] Saved: {path}")
    ctx.session = None
    try:
        return screens.done_screen(ctx, path, partial=partial) == "new"
    except AbortRequested:
        return False


def _wait_for_camera(ctx):
    cfg, d, tr = ctx.cfg, ctx.d, ctx.tracker
    t0 = now()
    while now() - t0 < cfg["camera"]["startup_timeout_s"]:
        if tr.error:
            break
        if tr.has_frames():
            return True
        d.clear()
        d.text("Starting camera...", d.center, 34)
        d.flip()
        pygame.event.pump()
    screens.error_screen(ctx, "Camera problem",
                         (tr.error or "The camera did not start in time.") +
                         "\n\nClose any other program using the camera (Zoom, Teams, browser), check "
                         "camera permissions in system settings, then restart ALICE. To use a different "
                         "camera, change camera: index in config.yaml.")
    return False


def autotest_overrides(cfg):
    """Shorter timings for the automated self-test only."""
    cfg["smooth_pursuit"].update({"block_duration_s": 3, "rest_s": 1, "fixation_s": 0.4})
    for k in ("prosaccade", "antisaccade"):
        cfg[k].update({"iti_s": [0.3, 0.6], "cue_duration_s": 0.6, "response_window_s": 1.4})
    cfg["rdk"].update({"stimulus_duration_s": 0.6, "inter_trial_s": 0.2})
    cfg["calibration"].update({"validation_dot_s": 1.0, "validation_collect_from_s": 0.3})
    cfg["calibration"]["drift_check"].update({"dot_s": 1.0, "collect_from_s": 0.3})


def run_app(args):
    cfg = load_config(args.config)
    if args.autotest:
        autotest_overrides(cfg)
    d = Display(cfg, windowed=args.windowed)
    inp = Input(auto=args.autotest)
    if args.simulate or args.autotest:
        tracker = SimTracker(cfg, d, mode="auto" if args.autotest else "mouse")
        if not args.autotest:
            inp.mouse_sim = tracker
    else:
        tracker = CameraTracker(cfg)
    tracker.start()
    ctx = Ctx(d=d, inp=inp, tracker=tracker, cfg=cfg)
    print(f"[ALICE] v{__version__} | {d.w}x{d.h} | {d.px_per_deg:.1f} px/deg | "
          f"vsync={'on' if d.vsync_active else 'OFF'} | tracker={tracker.kind}")
    try:
        if not _wait_for_camera(ctx):
            return 1
        if args.camera_test:
            try:
                screens.face_position(ctx, camera_test=True)
            except AbortRequested:
                pass
            return 0
        while one_session(ctx):
            if args.autotest:
                break
        return 0
    finally:
        tracker.stop()
        time.sleep(0.2)
        pygame.quit()
