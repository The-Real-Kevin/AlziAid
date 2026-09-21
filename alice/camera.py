"""Webcam capture, video recording and facial/iris landmark extraction.

Two background threads:
  capture thread  - reads every camera frame, timestamps it, and hands it to
                    the video writer when a section is being recorded.
  process thread  - runs MediaPipe Face Mesh (with iris refinement) on the
                    most recent frame and produces a feature vector.

If landmark processing is slower than the camera, the process thread skips
frames, but the video still contains every frame. Every processed sample
carries the index of its frame in the video file, so the two stay aligned.

A record is the tuple (t, seq, video_frame, features, openness):
  t            capture timestamp (seconds, alice.clock)
  seq          running camera frame number
  video_frame  index in the current section's video, or -1 if not recording
  features     numpy array (FEATURE_NAMES) or None if no face was found
  openness     mean eye openness (lid distance / eye width), or None
"""
import math
import queue
import sys
import threading
import time

import cv2
import numpy as np

from .clock import now

# MediaPipe Face Mesh landmark indices (refine_landmarks=True adds 468-477).
R_OUT, R_IN, R_UP, R_LO, R_IRIS = 33, 133, 159, 145, 468
L_OUT, L_IN, L_UP, L_LO, L_IRIS = 263, 362, 386, 374, 473
NOSE, CHIN, FOREHEAD, CHEEK_R, CHEEK_L = 1, 152, 10, 234, 454
PREVIEW_POINTS = [R_OUT, R_IN, L_OUT, L_IN, R_IRIS, L_IRIS]

FEATURE_NAMES = ["r_iris_x", "r_iris_y", "l_iris_x", "l_iris_y",
                 "head_yaw", "head_pitch", "head_roll",
                 "head_x", "head_y", "head_scale"]


def _eye(p, left_corner, right_corner, up, lo, iris):
    """Iris centre in the eye's own frame, in units of eye width.
    Corners are given in image left-to-right order so both eyes share one
    convention: +x = towards image right, +y = downwards."""
    o, i = p[left_corner], p[right_corner]
    c = (o + i) / 2.0
    e = i - o
    width = float(np.linalg.norm(e))
    if width < 1e-6:
        return None
    u = e / width
    v = np.array([-u[1], u[0]])
    rel = p[iris] - c
    openness = float(np.linalg.norm(p[up] - p[lo]) / width)
    return float(rel @ u / width), float(rel @ v / width), openness


def extract_features(landmarks, w, h):
    p = np.array([(lm.x * w, lm.y * h) for lm in landmarks], dtype=float)
    if len(p) < 478:
        return None, None, None
    r = _eye(p, R_OUT, R_IN, R_UP, R_LO, R_IRIS)   # subject's right eye: outer corner is image-left
    l = _eye(p, L_IN, L_OUT, L_UP, L_LO, L_IRIS)   # subject's left eye: inner corner is image-left
    if r is None or l is None:
        return None, None, None
    face_w = float(np.linalg.norm(p[CHEEK_L] - p[CHEEK_R]))
    face_h = float(np.linalg.norm(p[CHIN] - p[FOREHEAD]))
    if face_w < 1e-6 or face_h < 1e-6:
        return None, None, None
    hvec = (p[CHEEK_L] - p[CHEEK_R]) / face_w
    vvec = np.array([-hvec[1], hvec[0]])
    cheek_mid = (p[CHEEK_R] + p[CHEEK_L]) / 2.0
    eye_mid = (p[R_OUT] + p[L_OUT]) / 2.0
    yaw = float((p[NOSE] - cheek_mid) @ hvec / face_w)
    pitch = float((p[NOSE] - eye_mid) @ vvec / face_h)
    d = p[L_OUT] - p[R_OUT]
    roll = float(math.atan2(d[1], d[0]))
    feats = np.array([r[0], r[1], l[0], l[1], yaw, pitch, roll,
                      eye_mid[0] / w, eye_mid[1] / h, face_w / w])
    openness = (r[2] + l[2]) / 2.0
    pts = [(float(p[k][0]), float(p[k][1])) for k in PREVIEW_POINTS]
    return feats, openness, pts


class Camera:
    def __init__(self, cfg):
        self.cfg = cfg["camera"]
        self.lock = threading.Lock()
        self.running = False
        self.error = None
        self.fps_measured = None
        self.actual_size = None
        self.backend = None

        self._frame = None
        self._frame_t = None
        self._seq = 0
        self._rec_q = None
        self._rec_thread = None
        self._rec_idx = 0
        self._rec_seq_to_idx = {}
        self._rec_times = []
        self._log = None
        self.latest = None
        self._preview_pts = []

    # --------------------------------------------------------------- control
    def start(self):
        self.running = True
        threading.Thread(target=self._capture_loop, daemon=True, name="capture").start()
        threading.Thread(target=self._process_loop, daemon=True, name="landmarks").start()

    def stop(self):
        self.stop_recording()
        self.running = False

    def _open(self):
        idx = int(self.cfg["index"])
        if sys.platform == "darwin":
            cap, self.backend = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION), "AVFoundation"
        elif sys.platform.startswith("win"):
            cap, self.backend = cv2.VideoCapture(idx, cv2.CAP_DSHOW), "DirectShow"
        else:
            cap, self.backend = cv2.VideoCapture(idx), "default"
        if not cap.isOpened():
            cap, self.backend = cv2.VideoCapture(idx), "default"
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.cfg["width"]))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.cfg["height"]))
        cap.set(cv2.CAP_PROP_FPS, int(self.cfg["fps"]))
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        return cap

    # --------------------------------------------------------------- threads
    def _capture_loop(self):
        try:
            cap = self._open()
            if not cap.isOpened():
                raise RuntimeError(
                    f"Camera {self.cfg['index']} could not be opened. Check that it is connected, "
                    "not in use by another program, and that camera permission is granted.")
            stamps = []
            fails = 0
            while self.running:
                ok, frame = cap.read()
                t = now()
                if not ok or frame is None:
                    fails += 1
                    if fails > 200:
                        raise RuntimeError("Camera stopped delivering frames.")
                    time.sleep(0.005)
                    continue
                fails = 0
                with self.lock:
                    self._seq += 1
                    self._frame, self._frame_t = frame, t
                    if self._rec_q is not None:
                        self._rec_seq_to_idx[self._seq] = self._rec_idx
                        self._rec_times.append((self._rec_idx, t))
                        self._rec_idx += 1
                        # Queued inside the lock so no frame can land after the stop marker.
                        # Blocks only if the writer falls behind; indices stay consistent.
                        self._rec_q.put(frame)
                if self.actual_size is None:
                    self.actual_size = (frame.shape[1], frame.shape[0])
                stamps.append(t)
                if len(stamps) > 90:
                    stamps.pop(0)
                if len(stamps) > 10:
                    self.fps_measured = (len(stamps) - 1) / (stamps[-1] - stamps[0])
            cap.release()
        except Exception as e:  # surfaced to the operator by the session
            self.error = str(e)
            self.running = False

    def _process_loop(self):
        try:
            import mediapipe as mp
            mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1, refine_landmarks=True,
                min_detection_confidence=0.5, min_tracking_confidence=0.5)
        except Exception as e:
            self.error = f"MediaPipe could not be started: {e}"
            self.running = False
            return
        last_seq = 0
        while self.running:
            with self.lock:
                frame, t, seq = self._frame, self._frame_t, self._seq
                vidx = self._rec_seq_to_idx.get(seq, -1)
            if frame is None or seq == last_seq:
                time.sleep(0.002)
                continue
            last_seq = seq
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            res = mesh.process(rgb)
            feats = openness = None
            pts = []
            if res.multi_face_landmarks:
                feats, openness, pts = extract_features(
                    res.multi_face_landmarks[0].landmark, frame.shape[1], frame.shape[0])
            rec = (t, seq, vidx, feats, openness)
            with self.lock:
                self.latest = rec
                self._preview_pts = pts or []
                if self._log is not None:
                    self._log.append(rec)
        mesh.close()

    # ------------------------------------------------------------ recording
    def start_log(self):
        with self.lock:
            self._log = []

    def stop_log(self):
        with self.lock:
            log, self._log = self._log or [], None
        return log

    def start_recording(self, path):
        """Start writing every camera frame to `path`. Returns True on success."""
        w, h = self.actual_size or (int(self.cfg["width"]), int(self.cfg["height"]))
        fourcc = cv2.VideoWriter_fourcc(*self.cfg.get("video_codec", "mp4v"))
        writer = cv2.VideoWriter(str(path), fourcc, float(self.cfg["fps"]), (w, h))
        if not writer.isOpened():
            return False
        q = queue.Queue(maxsize=60)

        def run():
            while True:
                f = q.get()
                if f is None:
                    break
                writer.write(f)
            writer.release()

        th = threading.Thread(target=run, daemon=True, name="video-writer")
        th.start()
        with self.lock:
            self._rec_idx = 0
            self._rec_seq_to_idx = {}
            self._rec_times = []
            self._rec_q, self._rec_thread = q, th
        return True

    def stop_recording(self):
        """Stop recording; returns [(video_frame_index, timestamp), ...]."""
        with self.lock:
            q, th = self._rec_q, self._rec_thread
            self._rec_q = self._rec_thread = None
            times, self._rec_times = self._rec_times, []
            self._rec_seq_to_idx = {}
        if q is not None:
            q.put(None)
            th.join(timeout=60)
        return times

    # -------------------------------------------------------------- preview
    def preview(self):
        with self.lock:
            frame = None if self._frame is None else self._frame.copy()
            pts = list(self._preview_pts)
        return frame, pts

    def info(self):
        return {
            "camera_index": self.cfg["index"],
            "camera_backend": self.backend,
            "capture_resolution": f"{self.actual_size[0]}x{self.actual_size[1]}" if self.actual_size else None,
            "capture_fps_requested": self.cfg["fps"],
            "capture_fps_measured": round(self.fps_measured, 2) if self.fps_measured else None,
            "video_codec": self.cfg.get("video_codec", "mp4v"),
        }
