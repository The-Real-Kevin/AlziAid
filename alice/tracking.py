"""Gaze tracker front-ends used by the tasks.

CameraTracker - real webcam + MediaPipe (used at the hospital).
SimTracker    - no camera. Gaze follows the mouse ("mouse" mode, for
                developers to try the software) or a position the task
                supplies ("auto" mode, for automated end-to-end tests).
                Simulated sessions are labelled as such in session.json.

Both expose the same interface, so tasks never need to know which is active.
"""
import threading
import time

import numpy as np

from .camera import FEATURE_NAMES, Camera
from .clock import now


class BaseTracker:
    kind = "base"

    def __init__(self, cfg):
        self.cfg = cfg
        self.feature_idx = [FEATURE_NAMES.index(n) for n in cfg["tracking"]["features"]]
        self.model = None
        self.openness_ref = None

    def is_blink(self, openness):
        if openness is None:
            return True
        t = self.cfg["tracking"]
        if self.openness_ref:
            return openness < t["blink_relative_threshold"] * self.openness_ref
        return openness < t["blink_absolute_threshold"]

    def valid(self, rec):
        return rec[3] is not None and not self.is_blink(rec[4])

    def predict_records(self, records):
        """Convert raw records into per-frame dicts with predicted gaze (NaN if unavailable)."""
        n = len(records)
        gaze = np.full((n, 2), np.nan)
        ok = [i for i, r in enumerate(records) if self.valid(r)]
        if self.model is not None and ok:
            X = np.array([records[i][3][self.feature_idx] for i in ok])
            gaze[ok] = self.model.predict(X)
        out = []
        for i, r in enumerate(records):
            face = r[3] is not None
            out.append({
                "t": r[0], "video_frame": r[2], "face": face,
                "blink": face and self.is_blink(r[4]),
                "gaze_x": gaze[i, 0], "gaze_y": gaze[i, 1],
                "features": r[3], "openness": r[4],
            })
        return out

    def latest_gaze(self):
        rec = self.latest_record()
        if rec is None or self.model is None or not self.valid(rec):
            return None
        return self.model.predict(rec[3][self.feature_idx])[0]

    def face_ok(self):
        rec = self.latest_record()
        return (rec is not None and rec[3] is not None
                and now() - rec[0] < self.cfg["tracking"]["face_timeout_s"])

    def sim_hint(self, pos):
        """Tasks call this with the position a simulated participant should look at."""


class CameraTracker(BaseTracker):
    kind = "camera"

    def __init__(self, cfg):
        super().__init__(cfg)
        self.cam = Camera(cfg)

    @property
    def error(self):
        return self.cam.error

    def start(self):
        self.cam.start()

    def stop(self):
        self.cam.stop()

    def has_frames(self):
        return self.cam.actual_size is not None

    def latest_record(self):
        with self.cam.lock:
            return self.cam.latest

    def start_log(self):
        self.cam.start_log()

    def stop_log(self):
        return self.cam.stop_log()

    def start_recording(self, path):
        return self.cam.start_recording(path)

    def stop_recording(self):
        return self.cam.stop_recording()

    def preview(self):
        return self.cam.preview()

    def fps(self):
        return self.cam.fps_measured

    def info(self):
        d = {"tracking_mode": "camera"}
        d.update(self.cam.info())
        return d


class SimTracker(BaseTracker):
    kind = "simulated"

    def __init__(self, cfg, display, mode="mouse", hz=30.0, noise_deg=0.4, seed=None):
        super().__init__(cfg)
        self.d = display
        self.mode = mode
        self.hz = hz
        self.noise_px = noise_deg * display.px_per_deg
        self.rng = np.random.default_rng(seed)
        self.lock = threading.Lock()
        self.point = np.array(display.center, float)
        self.running = False
        self.error = None
        self.latest = None
        self._log = None
        self._rec = False
        self._rec_idx = 0
        self._rec_times = []

    def set_point(self, p):
        with self.lock:
            self.point = np.array(p, float)

    def sim_hint(self, pos):
        if self.mode == "auto":
            self.set_point(pos)

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True, name="sim-tracker").start()

    def stop(self):
        self.running = False

    def has_frames(self):
        return True

    def _loop(self):
        period = 1.0 / self.hz
        next_t = now()
        seq = 0
        while self.running:
            next_t += period
            delay = next_t - now()
            if delay > 0:
                time.sleep(delay)
            t = now()
            with self.lock:
                p = self.point.copy()
            g = p + self.rng.normal(0, self.noise_px, 2)
            feats = np.zeros(len(FEATURE_NAMES))
            feats[0] = feats[2] = g[0] / self.d.w
            feats[1] = feats[3] = g[1] / self.d.h
            feats[7] = feats[8] = 0.5
            feats[9] = 0.2
            openness = 0.05 if self.rng.random() < 0.01 else 0.3   # occasional blink
            seq += 1
            with self.lock:
                vidx = -1
                if self._rec:
                    vidx = self._rec_idx
                    self._rec_times.append((vidx, t))
                    self._rec_idx += 1
                rec = (t, seq, vidx, feats, openness)
                self.latest = rec
                if self._log is not None:
                    self._log.append(rec)

    def latest_record(self):
        with self.lock:
            return self.latest

    def start_log(self):
        with self.lock:
            self._log = []

    def stop_log(self):
        with self.lock:
            log, self._log = self._log or [], None
        return log

    def start_recording(self, path):
        with self.lock:
            self._rec, self._rec_idx, self._rec_times = True, 0, []
        return False   # no video file in simulation

    def stop_recording(self):
        with self.lock:
            self._rec = False
            times, self._rec_times = self._rec_times, []
        return times

    def preview(self):
        return None, []

    def fps(self):
        return self.hz

    def info(self):
        return {"tracking_mode": f"SIMULATED ({self.mode}) - not real eye data"}
