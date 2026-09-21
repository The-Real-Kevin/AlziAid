"""
Generate colour-discrimination plates following the City University Test design.

Each plate has a central colour and four options:
  correct  - a small hue step from the centre (closest for normal colour vision)
  protan / deutan / tritan - colours on the dichromatic confusion line through
             the centre, at equal luminance. For a dichromat of that type the
             confusion colour is (theoretically) indistinguishable from the centre,
             while for normal vision it is clearly further away than 'correct'.

Confusion lines use the standard copunctal points in CIE 1931 xy.
All output is sRGB hex, printed as YAML ready to paste into config.yaml.

NOTE: this is a colorimetric approximation of the CUT design, assuming an sRGB
display. If official CUT plate values are available, use those instead.

Usage:  python tools/generate_color_plates.py
"""
import numpy as np

COPUNCTAL = {"protan": (0.747, 0.253), "deutan": (1.40, -0.40), "tritan": (0.171, 0.0)}

M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
MI = np.linalg.inv(M)
WHITE = M @ np.ones(3)


def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - 0.055)


def xyY_to_rgb(x, y, Y):
    X, Z = x * Y / y, (1 - x - y) * Y / y
    return lin_to_srgb(MI @ np.array([X, Y, Z]))


def rgb_to_xyY(rgb):
    X, Y, Z = M @ srgb_to_lin(rgb)
    s = X + Y + Z
    return X / s, Y / s, Y


def lab(rgb):
    xyz = (M @ srgb_to_lin(rgb)) / WHITE
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def lch_to_rgb(L, C, h):
    a, b = C * np.cos(np.radians(h)), C * np.sin(np.radians(h))
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    inv = lambda f: f ** 3 if f ** 3 > 216 / 24389 else (116 * f - 16) / (24389 / 27)
    xyz = np.array([inv(fx), inv(fy), inv(fz)]) * WHITE
    return lin_to_srgb(MI @ xyz)


def in_gamut(rgb):
    return bool(np.all(rgb >= 0) and np.all(rgb <= 1))


def dE(a, b):
    return float(np.linalg.norm(lab(a) - lab(b)))


def to_hex(rgb):
    return "#" + "".join(f"{int(round(v * 255)):02X}" for v in np.clip(rgb, 0, 1))


def confusion_colour(centre, kind, target_de):
    x, y, Y = rgb_to_xyY(centre)
    cx, cy = COPUNCTAL[kind]
    d = np.array([x - cx, y - cy]); d /= np.linalg.norm(d)
    best = None
    for sign in (1, -1):
        for t in np.linspace(0.001, 0.25, 500):
            rgb = xyY_to_rgb(x + sign * t * d[0], y + sign * t * d[1], Y)
            if not in_gamut(rgb):
                break
            if dE(centre, rgb) >= target_de:
                if best is None or abs(dE(centre, rgb) - target_de) < abs(dE(centre, best) - target_de):
                    best = rgb
                break
    return best


def correct_colour(L, C, h, target_de):
    for step in np.linspace(0.5, 60, 400):
        for sign in (1, -1):
            rgb = lch_to_rgb(L, C, h + sign * step)
            if in_gamut(rgb) and dE(lch_to_rgb(L, C, h), rgb) >= target_de:
                return rgb
    return None


def main(correct_de=7.0, confusion_de=16.0):
    plates, L, C = [], 62, 30
    for h in [20, 95, 160, 220, 290, 60, 130, 190, 250, 330]:
        centre = lch_to_rgb(L, C, h)
        if not in_gamut(centre):
            continue
        opts = {"correct": correct_colour(L, C, h, correct_de)}
        for k in COPUNCTAL:
            opts[k] = confusion_colour(centre, k, confusion_de)
        if any(v is None for v in opts.values()):
            continue
        plates.append((h, centre, opts))
        if len(plates) == 5:
            break
    print("  plates:")
    for h, c, o in plates:
        print(f"    - {{centre: \"{to_hex(c)}\", correct: \"{to_hex(o['correct'])}\", "
              f"protan: \"{to_hex(o['protan'])}\", deutan: \"{to_hex(o['deutan'])}\", "
              f"tritan: \"{to_hex(o['tritan'])}\"}}   # hue {h}, dE correct="
              f"{dE(c, o['correct']):.1f}, confusion={dE(c, o['tritan']):.1f}")


if __name__ == "__main__":
    main()
