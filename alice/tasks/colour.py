"""Section 5 - Colour discrimination (City University Test design).

A central colour patch with four candidates at 12, 3, 6 and 9 o'clock:
the correct colour (adjacent D-15 hue, closest for normal colour vision) and
three confusion colours on the protan, deutan and tritan axes. Which role sits
in which position is randomised on every plate and recorded.

All colours are hex values in config.yaml and can be tuned freely.
"""
import math

import pygame

from ..clock import now
from ..config import hex_to_rgb

TAG = "05_colour"
ROLES = ["correct", "protan", "deutan", "tritan"]
POSITIONS = ["top", "right", "bottom", "left"]
OFFSET = {"top": (0, -1), "right": (1, 0), "bottom": (0, 1), "left": (-1, 0)}


def run(ctx):
    d, inp, cfg, store, rng = ctx.d, ctx.inp, ctx.cfg, ctx.store, ctx.rng
    p = cfg["colour"]
    r = d.deg(p["patch_diameter_deg"]) / 2
    sp = d.deg(p["patch_spacing_deg"])
    cx, cy = d.center
    rows = []
    t_section = now()
    pygame.mouse.set_visible(True)

    for k, plate in enumerate(p["plates"], start=1):
        perm = list(rng.permutation(ROLES))
        layout = dict(zip(POSITIONS, perm))
        centres = {pos: (cx + OFFSET[pos][0] * sp, cy + OFFSET[pos][1] * sp) for pos in POSITIONS}

        def draw():
            d.clear()
            d.circle(hex_to_rgb(plate["centre"]), (cx, cy), r, outline=p.get("outline", True))
            for pos in POSITIONS:
                d.circle(hex_to_rgb(plate[layout[pos]]), centres[pos], r, outline=p.get("outline", True))

        draw()
        t_on = d.flip()
        if inp.auto:
            pick = "correct" if rng.random() < 0.85 else ROLES[int(rng.integers(1, 4))]
            target = next(pos for pos in POSITIONS if layout[pos] == pick)
            inp.auto_click(float(rng.uniform(0.3, 1.0)), centres[target])

        chosen = t_resp = None
        while chosen is None:
            t, ev = inp.poll()
            for e in ev:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    for pos in POSITIONS:
                        if math.dist(e.pos, centres[pos]) <= r:
                            chosen, t_resp = pos, t
            draw()
            d.flip()

        role = layout[chosen]
        rows.append({
            "plate": k, "centre_hex": plate["centre"], "correct_hex": plate["correct"],
            "protan_hex": plate["protan"], "deutan_hex": plate["deutan"], "tritan_hex": plate["tritan"],
            "layout": ";".join(f"{pos}={layout[pos]}" for pos in POSITIONS),
            "response_position": chosen, "response_role": role, "response_hex": plate[role],
            "correct": role == "correct",
            "confusion_axis_selected": "" if role == "correct" else role,
            "onset_ms": (t_on - t_section) * 1000, "response_time_ms": (t_resp - t_on) * 1000,
        })
        t_end = now() + 0.6
        while now() < t_end:
            inp.poll()
            d.clear()
            d.flip()

    fields = ["plate", "centre_hex", "correct_hex", "protan_hex", "deutan_hex", "tritan_hex", "layout",
              "response_position", "response_role", "response_hex", "correct", "confusion_axis_selected",
              "onset_ms", "response_time_ms"]
    store.write_csv(f"{TAG}.csv", fields, rows)
    return {"plates": len(rows), "correct": int(sum(r["correct"] for r in rows)),
            "confusions": {a: int(sum(r["response_role"] == a for r in rows)) for a in ROLES[1:]}}
