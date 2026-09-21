"""
Generate provisional colour plates for the ALICE colour discrimination section.

Design (after the City University Colour Vision Test): each plate has a central
colour and four candidates.
  - correct : a small hue step from the centre (closest for normal colour vision)
  - protan  : moved along the protan confusion line through the centre
  - deutan  : moved along the deutan confusion line through the centre
  - tritan  : moved along the tritan confusion line through the centre

Confusion colours are placed at the same luminance as the centre, on the line
joining the centre to the dichromat's copunctal point in CIE 1931 xy, far
enough away to look clearly different to a normal observer (DE_conf) but, in
theory, indistinguishable to the corresponding dichromat.

These values are a principled starting point, NOT the official CUT plate
colorimetry. They are sRGB and assume a display close to sRGB. Tune the hex
values in config.yaml as needed.

Usage:  python tools/generate_colour_plates.py
"""
import math
import numpy as np

M = np.array([[0.4124564, 0.3575761, 0.1804375],
              [0.2126729, 0.7151522, 0.0721750],
              [0.0193339, 0.1191920, 0.9503041]])
MI = np.linalg.inv(M)
WHITE = M @ np.ones(3)

COPUNCTAL = {  # CIE 1931 xy copunctal points (Smith & Pokorny)
    "protan": (0.7465, 0.2535),
    "deutan": (1.4000, -0.4000),
    "tritan": (0.1748, 0.0000),
}


def hex_to_lin(h):
    c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_hex(c):
    c = np.clip(c, 0, 1)
    s = np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)
    return "#" + "".join(f"{int(round(v * 255)):02X}" for v in s)


def in_gamut(lin, tol=1e-6):
    return bool(np.all(lin >= -tol) and np.all(lin <= 1 + tol))


def xyz_to_xyY(X):
    s = X.sum()
    return np.array([X[0] / s, X[1] / s, X[1]])


def xyY_to_xyz(v):
    x, y, Y = v
    return np.array([x * Y / y, Y, (1 - x - y) * Y / y])


def lab(X):
    def f(t):
        return np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    fx, fy, fz = f(X / WHITE)
    return np.array([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)])


def de(X1, X2):
    return float(np.linalg.norm(lab(X1) - lab(X2)))


def confusion_colour(centre_hex, axis, target_de):
    X0 = M @ hex_to_lin(centre_hex)
    x0, y0, Y0 = xyz_to_xyY(X0)
    cx, cy = COPUNCTAL[axis]
    u = np.array([x0 - cx, y0 - cy])
    u /= np.linalg.norm(u)
    best = None
    for sign in (+1, -1):
        lo, hi = 0.0, 0.3
        for _ in range(60):
            mid = (lo + hi) / 2
            xy = np.array([x0, y0]) + sign * mid * u
            X = xyY_to_xyz((xy[0], xy[1], Y0))
            if de(X0, X) < target_de:
                lo = mid
            else:
                hi = mid
        xy = np.array([x0, y0]) + sign * hi * u
        X = xyY_to_xyz((xy[0], xy[1], Y0))
        lin = MI @ X
        if in_gamut(lin):
            cand = (abs(de(X0, X) - target_de), lin_to_hex(lin))
            if best is None or cand[0] < best[0]:
                best = cand
    return best[1] if best else None


def hue_step(centre_hex, target_de, avoid_dirs):
    """Small step in xy (same luminance) in the direction furthest from all confusion lines."""
    X0 = M @ hex_to_lin(centre_hex)
    x0, y0, Y0 = xyz_to_xyY(X0)
    best = None
    for ang in np.linspace(0, 2 * math.pi, 360, endpoint=False):
        d = np.array([math.cos(ang), math.sin(ang)])
        sep = min(abs(math.acos(min(1.0, abs(float(d @ a))))) for a in avoid_dirs)
        lo, hi = 0.0, 0.1
        for _ in range(50):
            mid = (lo + hi) / 2
            X = xyY_to_xyz((x0 + mid * d[0], y0 + mid * d[1], Y0))
            if de(X0, X) < target_de:
                lo = mid
            else:
                hi = mid
        X = xyY_to_xyz((x0 + hi * d[0], y0 + hi * d[1], Y0))
        lin = MI @ X
        if in_gamut(lin) and (best is None or sep > best[0]):
            best = (sep, lin_to_hex(lin))
    return best[1]


def make_plate(centre_hex, de_conf=22.0, de_correct=8.0):
    X0 = M @ hex_to_lin(centre_hex)
    x0, y0, _ = xyz_to_xyY(X0)
    dirs = []
    for c in COPUNCTAL.values():
        v = np.array([x0 - c[0], y0 - c[1]])
        dirs.append(v / np.linalg.norm(v))
    plate = {"centre": centre_hex, "correct": hue_step(centre_hex, de_correct, dirs)}
    for axis in ("protan", "deutan", "tritan"):
        plate[axis] = confusion_colour(centre_hex, axis, de_conf)
    return plate


CENTRES = ["#6F8F9C", "#8F7F9F", "#9A8F66", "#9E7F86", "#7A9A82"]

if __name__ == "__main__":
    print("  plates:")
    for c in CENTRES:
        p = make_plate(c)
        print(f'    - {{centre: "{p["centre"]}", correct: "{p["correct"]}", '
              f'protan: "{p["protan"]}", deutan: "{p["deutan"]}", tritan: "{p["tritan"]}"}}')
