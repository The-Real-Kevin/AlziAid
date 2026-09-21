# ALICE — Data Collection Software for AlziAid

ALICE administers a fixed battery of eye-movement and visual-function tasks using an
ordinary webcam and saves the raw data for the AlziAid study (AI-assisted diagnosis of
Alzheimer's disease from iris and pupil movement). **It collects data only — it does not
score or diagnose.**

📺 **Demo video:** _[YouTube link — to be added]_
🏥 **Hospital staff:** follow **`setup.txt`** — it covers installation and running a session step by step.

---

## Quick start

| | Windows | Mac |
|---|---|---|
| Install (once) | `install_windows.bat` | `install_mac.command` |
| Check camera | `camera_test_windows.bat` | `camera_test_mac.command` |
| Run ALICE | `start_alice.bat` | `start_alice.command` |

Requires Python 3.11 (or 3.12), a webcam, and a keyboard with F and J keys.

From a terminal (inside the activated `.venv`):

```
python run_alice.py                 # normal use: webcam, fullscreen
python run_alice.py --camera-test   # camera preview + face detection only
python run_alice.py --simulate      # no camera; gaze follows the mouse (to try the software)
python run_alice.py --windowed      # run in a window (development)
python run_alice.py --autotest      # automated end-to-end run with a simulated participant
python -m pytest tests              # unit tests for the saccade detector
```

**Keys:** `Esc` stop (restart section / abort session) · `Space` confirm a calibration dot
(operator alternative to clicking) · `F` / `J` responses in parts 2–3 · `Enter` continue on
instruction screens.

---

## Session flow

```
Start → Participant details → Face positioning → Calibration (9 pts) + Validation (5 pts)
 → 1 Smooth pursuit        (video)
 → 2 Prosaccade            (video)
 → Drift check
 → 3 Antisaccade           (video, 3 practice trials first)
 → 4 Random dot kinematogram
 → 5 Colour discrimination
 → Save (group A / M / H, notes) → next participant
```

| Part | Task | Default parameters |
|---|---|---|
| Calibration | Look at and click 9 dots (random order); then passively view 5 validation dots | pass < 1.5°, acceptable < 2.5° mean error |
| 1 Smooth pursuit | Follow a red dot moving in random straight segments; never reaches edges | 8 °/s, turns every 0.8–2.0 s, 2 × 30 s |
| 2 Prosaccade | Look at the side dot that turns green; press F (left) / J (right) | ±10°, cue 1 s, random 1.5–3.5 s fixation, 10 trials |
| 3 Antisaccade | Look to the *opposite* side; press F when looking left / J when looking right | as above, + 3 practice trials with feedback |
| 4 RDK | Choose direction of coherent motion (3 directions + "I don't know") | 10° aperture, 6 °/s, static noise dots, coherence 80/60/40/25/15 % (+1 practice at 100 %) |
| 5 Colour | Click the outer patch most similar to the centre | 5 plates; correct + protan/deutan/tritan confusion colours; positions randomised |

All parameters are in **`config.yaml`**; sizes are in degrees of visual angle, converted
using the screen size and viewing distance set there. A copy of the config is saved
into every session folder.

---

## Output

One folder per session in `results/`:

```
S012_H_20261003_1430/                 S<subject>_<group>_<date>_<time>
  session.json                        metadata, calibration quality, section summaries
  config_used.yaml                    exact parameters used for this session
  calibration.csv
  01_smooth_pursuit.mp4               webcam video
  01_smooth_pursuit.csv               per camera frame: target vs gaze
  01_smooth_pursuit_stimulus.csv      per screen refresh: dot position
  01_smooth_pursuit_video_timestamps.csv
  02_prosaccade.mp4
  02_prosaccade_trials.csv            one row per trial
  02_prosaccade_frames.csv            per camera frame gaze trace
  02_prosaccade_video_timestamps.csv
  03_antisaccade.mp4 / _trials.csv / _frames.csv / _video_timestamps.csv
  04_rdk.csv
  05_colour.csv
```

The folder is created as `…_PENDING_…` when the session starts and each part is written as
soon as it finishes. On save it is renamed with the group label; on abort it becomes
`…_PARTIAL_…`. A leftover `PENDING` folder means the program was closed or crashed.

**Conventions:** all times in milliseconds from the start of that section, from one
monotonic clock shared by screen, keyboard and camera. Gaze and target positions in
screen pixels (origin top-left); `*_deg` columns in degrees of visual angle. Booleans are
`1`/`0`; missing values are empty cells. `video_frame` is the frame index in that
section's `.mp4` (−1 if not recorded).

### Data dictionary

**Frame files** (`01_smooth_pursuit.csv`, `02/03_*_frames.csv`) — one row per processed camera frame

| Column | Meaning |
|---|---|
| `target_x/y` | dot position on screen at the moment the frame was captured (part 1) |
| `gaze_x/y` | estimated gaze position; empty during blinks or when no face is found |
| `error_px`, `error_deg` | gaze-to-target distance (part 1) |
| `phase` / `stimulus` | `fixation`, `pursuit`, `rest` / `fixation`, `cue_left`, `cue_right` |
| `face_detected`, `blink` | tracking status for that frame |
| `f_*`, `eye_openness` | raw landmark features (iris position within each eye, head pose) — allows the gaze model to be refitted offline |

**Saccade trials** (`02/03_*_trials.csv`)

| Column | Meaning |
|---|---|
| `cue_side`, `correct_look`, `correct_key` | where the green cue appeared; where the participant should look; which key they should press |
| `rt_key_ms`, `key`, `key_correct` | manual reaction time and response |
| `key_anticipatory` | response < 100 ms after cue (exclude from RT analysis) |
| `early_keypresses` | presses during the fixation period before the cue |
| `rt_gaze_ms`, `saccade_direction`, `saccade_correct` | saccade latency and direction from the webcam trace |
| `direction_error`, `corrected_error` | antisaccade: first saccade toward the cue; later corrected to the right side |
| `saccade_amplitude_deg`, `peak_velocity_deg_s` | see limitations — velocity is heavily underestimated at 30 fps |
| `detection_method` | `velocity` (normal) or `position` (slow crossing — review) |
| `gaze_quality` | `ok`, `poor_tracking`, `no_saccade_detected`, `no_data` |
| `practice` | 1 for antisaccade practice trials — exclude from analysis |

`rt_key_ms` and `rt_gaze_ms` measure different things (manual response vs eye movement) and
should be analysed separately.

**`04_rdk.csv`** — `coherence`, `true_direction`, `options` (as shown), `response`
(`up`/`right`/`down`/`left`/`dont_know`), `correct`, `response_time_ms` (from stimulus offset),
`stimulus_frames`, `practice`.

**`05_colour.csv`** — all five plate hex values, `layout` (which role was at which
position), `response_role` (`correct`/`protan`/`deutan`/`tritan`), `confusion_axis_selected`,
`response_time_ms`.

**`calibration.csv`** — every calibration and validation point for every attempt, with sample
counts and, for validation points, predicted position, accuracy (`error_deg`) and precision
(`precision_rms_deg`).

**`session.json`** — participant details (age, sex, glasses, contacts, eye conditions — no
names), operator initials, random seed, hardware (screen size, px/deg, vsync status,
measured refresh rate, camera resolution and measured fps), all calibration attempts with
the accepted one under `calibration.final`, drift check result, per-section summaries,
group label, notes, status (`complete` / `aborted` / `crashed`).

---

## How gaze estimation works

MediaPipe Face Mesh (with iris refinement) locates 478 facial landmarks per frame. From
these ALICE computes the iris centre's position within each eye (normalised by eye width)
plus head yaw and pitch. During calibration a ridge-regression model maps these features to
screen coordinates; polynomial degree (1 or 2) and regularisation strength are chosen by
leave-one-point-out cross-validation. Validation on 5 separate points gives the accuracy
figure recorded for the session. Blinks are detected from eye openness relative to the
participant's own calibration baseline, and those frames have no gaze estimate.

The camera is read on a background thread that timestamps and records every frame; a
second thread runs landmark detection. Every gaze sample is tagged with its frame index in
the video, so the video can be re-processed later with a better method and re-aligned
exactly.

---

## Known limitations

- **Webcam accuracy.** Expect roughly 1–3° gaze error. Saccade *direction* and *latency*
  are robust; absolute pursuit error in degrees is noisy. Use `calibration.final.mean_error_deg`
  to weight or exclude sessions.
- **Temporal resolution.** At 30 fps the camera samples every 33 ms; gaze reaction times are
  quantised to about ±17 ms and peak velocity is strongly underestimated. A 60 fps camera
  halves this (set `camera: fps: 60`).
- **Camera latency.** Frame timestamps are taken when the frame arrives, which includes the
  camera's internal delay (typically 30–80 ms). This adds a roughly constant offset to
  `rt_gaze_ms`. It is the same for every participant on the same hardware, so group
  comparisons are valid, but absolute values should not be compared with published
  eye-tracker latencies.
- **Pupil size is not measured.** MediaPipe tracks the iris, not the pupil, and webcam
  resolution at 60 cm is insufficient for pupil diameter. Raw video is kept for any future
  offline analysis.
- **Display timing.** Stimulus onsets are exact to the screen refresh when vsync is active
  (`hardware.vsync_active` in `session.json`). If it is off, onsets may lag by up to one frame.
- **Colour plates** are provisional values generated by `tools/generate_colour_plates.py`
  (confusion colours on protan/deutan/tritan lines through each centre colour), not the
  official City University Test colorimetry. Edit freely in `config.yaml`.
- **Simulated runs** (`--simulate`, `--autotest`) are labelled
  `SIMULATED … not real eye data` in `session.json` → `hardware.tracking_mode`.
  Delete them before any analysis.

---

## Project structure

```
run_alice.py              entry point
config.yaml               all parameters and instruction texts
alice/
  session.py              application flow, abort/restart, saving
  screens.py              start page, forms, instructions, dialogs, save screen
  display.py              fullscreen window, vsync check, degrees <-> pixels, drawing
  inputs.py               keyboard/mouse polling, Esc handling, test autopilot
  camera.py               capture + video recording threads, landmark features
  tracking.py             camera tracker and simulated tracker
  gaze.py                 calibration regression model
  analysis.py             saccade detection, stimulus/frame alignment
  storage.py              session folders, CSV/JSON output
  tasks/                  calibration, pursuit, saccade, rdk, colour
tests/test_analysis.py    saccade detector tests
tools/generate_colour_plates.py
```

**Never commit participant data.** `results/` is excluded in `.gitignore`.
