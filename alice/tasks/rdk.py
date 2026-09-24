"""Section 4 - Random dot kinematogram (RDK).

A circular aperture of white dots on a dark field. A proportion of the dots
(the coherence) move together in one direction at a fixed speed; the others
are either static (noise_mode "static", as specified) or move in random
directions (noise_mode "random"). Each dot is re-placed at a random location
after its lifetime expires so that no single dot can be tracked. Signal dots
that leave the aperture re-enter from the opposite side.

The dots are shown for a fixed duration, then disappear and the response
buttons become active: the correct direction, (direction_options - 1) other
directions, and "I don't know". Buttons are always listed in the same
clockwise order (up, right, down, left) so position gives no cue.
"""
import math

import numpy as np
import pygame

from ..clock import now
from ..config import hex_to_rgb
from ..display import Button

TAG = "04_rdk"
VEC = {"up": (0.0, -1.0), "right": (1.0, 0.0), "down": (0.0, 1.0), "left": (-1.0, 0.0)}
CANON = ["up", "right", "down", "left"]
LABEL = {"up": "Up", "right": "Right", "down": "Down", "left": "Left", "dont_know": "I don't know"}


def _arrow(d, rect, direction, colour):
    cx, cy = rect.centerx, rect.y + rect.h * 0.34
    s = rect.h * 0.18
    pts = {"up": [(0, -1), (-0.8, 0.6), (0.8, 0.6)], "down": [(0, 1), (-0.8, -0.6), (0.8, -0.6)],
           "left": [(-1, 0), (0.6, -0.8), (0.6, 0.8)], "right": [(1, 0), (-0.6, -0.8), (-0.6, 0.8)]}[direction]
    pygame.draw.polygon(d.screen, colour, [(cx + x * s, cy + y * s) for x, y in pts])


def run(ctx):
    d, inp, tr, cfg, store, rng = ctx.d, ctx.inp, ctx.tracker, ctx.cfg, ctx.store, ctx.rng
    p = cfg["rdk"]
    R = d.deg(p["aperture_diameter_deg"]) / 2
    ac = (d.w / 2, d.h * 0.40)
    n = max(10, int(round(p["dot_density_per_deg2"] * math.pi * (p["aperture_diameter_deg"] / 2) ** 2)))
    dot_r = max(1, int(round(d.deg(p["dot_diameter_deg"]) / 2)))
    speed = d.deg(p["speed_deg_s"])
    life = p.get("dot_lifetime_s")
    ap_col, dot_col = hex_to_rgb(p["aperture_colour"]), hex_to_rgb(p["dot_colour"])
    dirs = [x for x in p["directions"] if x in VEC]
    n_opt = max(2, min(int(p["direction_options"]), len(dirs)))

    trials = [(True, float(p["practice_coherence"]))] * int(p["practice_trials"]) + \
             [(False, float(c)) for c in p["trials_coherence"]]

    def rand_pos(k):
        r = R * np.sqrt(rng.random(k))
        a = rng.uniform(0, 2 * np.pi, k)
        return np.stack([r * np.cos(a), r * np.sin(a)], axis=1)

    rows = []
    t_section = now()
    pygame.mouse.set_visible(True)
    for k, (practice, coh) in enumerate(trials, start=1):
        true_dir = dirs[int(rng.integers(len(dirs)))]
        others = [x for x in dirs if x != true_dir]
        chosen = [true_dir] + list(rng.choice(others, n_opt - 1, replace=False))
        options = [x for x in CANON if x in chosen] + ["dont_know"]

        bw, bh, gap = int(d.w * 0.12), int(d.h * 0.11), int(d.w * 0.015)
        total = len(options) * bw + (len(options) - 1) * gap
        buttons = [Button((d.w / 2 - total / 2 + i * (bw + gap), d.h * 0.78, bw, bh),
                          LABEL[o], o, enabled=False, size=24) for i, o in enumerate(options)]

        n_sig = int(round(coh * n))
        pos = rand_pos(n)
        signal = np.zeros(n, bool)
        signal[rng.permutation(n)[:n_sig]] = True
        noise_dir = rng.uniform(0, 2 * np.pi, n)
        noise_vec = np.stack([np.cos(noise_dir), np.sin(noise_dir)], axis=1)
        age = rng.uniform(0, life, n) if life else np.zeros(n)
        u = np.array(VEC[true_dir])

        def draw_frame(show_dots):
            d.clear()
            pygame.draw.circle(d.screen, ap_col, (int(ac[0]), int(ac[1])), int(R))
            pygame.draw.circle(d.screen, d.col["outline"], (int(ac[0]), int(ac[1])), int(R), 1)
            if show_dots:
                for x, y in pos:
                    pygame.draw.circle(d.screen, dot_col, (int(ac[0] + x), int(ac[1] + y)), dot_r)
            for b in buttons:
                pygame.draw.rect(d.screen, d.col["button_fill"], b.rect)
                pygame.draw.rect(d.screen, d.col["outline"], b.rect, 2 if b.enabled else 1)
                c = d.col["text"] if b.enabled else d.col["disabled_text"]
                if b.key in VEC:
                    _arrow(d, b.rect, b.key, c)
                    d.text(b.label, (b.rect.centerx, b.rect.y + b.rect.h * 0.75), 24, colour=c)
                else:
                    d.text(b.label, b.rect.center, 22, colour=c)

        # blank aperture briefly before onset
        t_end = now() + 0.5
        while now() < t_end:
            inp.poll()
            draw_frame(False)
            d.flip()

        t_on = None
        t_last = now()
        n_frames = 0
        while True:
            t = now()
            if t_on is not None and t - t_on >= p["stimulus_duration_s"]:
                break
            dt = t - t_last
            t_last = t
            if t_on is not None:
                move = np.zeros_like(pos)
                move[signal] = u * speed * dt
                if p["noise_mode"] == "random":
                    move[~signal] = noise_vec[~signal] * speed * dt
                pos += move
                out = np.hypot(pos[:, 0], pos[:, 1]) > R
                if out.any():   # re-enter from the opposite side along the motion axis
                    q = pos[out]
                    mv = np.where(signal[out, None], u, noise_vec[out])
                    q = q - 2 * (q * mv).sum(1, keepdims=True) * mv
                    rr = np.hypot(q[:, 0], q[:, 1])
                    q *= np.minimum(1.0, (R * 0.999) / np.maximum(rr, 1e-9))[:, None]
                    pos[out] = q
                if life:
                    age += dt
                    dead = age >= life
                    if dead.any():
                        n_dead = int(dead.sum())
                        pos[dead] = rand_pos(n_dead)
                        age[dead] = 0.0
                        a = rng.uniform(0, 2 * np.pi, n_dead)
                        noise_vec[dead] = np.stack([np.cos(a), np.sin(a)], axis=1)
            inp.poll()
            draw_frame(True)
            ft = d.flip()
            n_frames += 1
            if t_on is None:
                t_on = ft
                t_last = now()
        draw_frame(False)
        t_off = d.flip()

        for b in buttons:
            b.enabled = True
        if inp.auto:
            p_correct = 0.4 + 0.6 * coh
            pick = true_dir if rng.random() < p_correct else ("dont_know" if rng.random() < 0.5 else options[0])
            b = next(x for x in buttons if x.key == pick)
            inp.auto_click(float(rng.uniform(0.3, 0.8)), b.rect.center)
        response = t_resp = None
        while response is None:
            t, ev = inp.poll()
            for e in ev:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    for b in buttons:
                        if b.hit(e.pos):
                            response, t_resp = b.key, t
            draw_frame(False)
            d.flip()

        rows.append({
            "trial": k, "practice": practice, "coherence": coh, "n_dots": n, "n_signal": n_sig,
            "noise_mode": p["noise_mode"], "speed_deg_s": p["speed_deg_s"],
            "true_direction": true_dir, "options": "|".join(options), "response": response,
            "correct": response == true_dir, "dont_know": response == "dont_know",
            "stimulus_onset_ms": (t_on - t_section) * 1000, "stimulus_offset_ms": (t_off - t_section) * 1000,
            "stimulus_frames": n_frames, "response_time_ms": (t_resp - t_off) * 1000,
        })

        t_end = now() + p["inter_trial_s"]
        while now() < t_end:
            inp.poll()
            d.clear()
            d.flip()

    fields = ["trial", "practice", "coherence", "n_dots", "n_signal", "noise_mode", "speed_deg_s",
              "true_direction", "options", "response", "correct", "dont_know",
              "stimulus_onset_ms", "stimulus_offset_ms", "stimulus_frames", "response_time_ms"]
    store.write_csv(f"{TAG}.csv", fields, rows)
    main = [r for r in rows if not r["practice"]]
    return {"trials": len(main),
            "correct": int(sum(r["correct"] for r in main)),
            "dont_know": int(sum(r["dont_know"] for r in main)),
            "dots_per_trial": n}
