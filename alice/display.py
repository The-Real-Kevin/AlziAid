"""Screen management: fullscreen window, refresh/vsync detection,
degree <-> pixel conversion, and drawing helpers shared by every screen."""
import math
import platform
import statistics

import pygame
from pygame import gfxdraw

from .clock import now
from .config import hex_to_rgb


class Button:
    def __init__(self, rect, label, key=None, enabled=True, selected=False, size=26):
        self.rect = pygame.Rect([int(v) for v in rect])
        self.label = label
        self.key = key if key is not None else label
        self.enabled = enabled
        self.selected = selected
        self.size = size

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


class Display:
    def __init__(self, cfg, windowed=False):
        self.cfg = cfg
        dcfg = cfg["display"]
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption(f'{cfg["software"]["title"]} - {cfg["software"]["subtitle"]}')

        self.vsync_requested = False
        if windowed:
            self.screen = pygame.display.set_mode((1280, 800))
        else:
            try:
                size = pygame.display.get_desktop_sizes()[0]
            except Exception:
                size = (1920, 1080)
            try:
                self.screen = pygame.display.set_mode(
                    size, pygame.FULLSCREEN | pygame.SCALED, vsync=1)
                self.vsync_requested = True
            except pygame.error:
                self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)

        self.w, self.h = self.screen.get_size()
        self.center = (self.w / 2.0, self.h / 2.0)
        self.col = {k: hex_to_rgb(v) for k, v in dcfg["colours"].items()}

        # Physical geometry -> pixels per degree of visual angle.
        width_cm = dcfg.get("width_cm")
        if not width_cm:
            diag_cm = float(dcfg["diagonal_inches"]) * 2.54
            aspect = self.w / self.h
            width_cm = diag_cm * aspect / math.sqrt(1 + aspect ** 2)
        self.width_cm = float(width_cm)
        self.px_per_cm = self.w / self.width_cm
        self.viewing_distance_cm = float(dcfg["viewing_distance_cm"])
        self.px_per_deg = self.viewing_distance_cm * math.tan(math.radians(1.0)) * self.px_per_cm

        self.clock = pygame.time.Clock()
        self._fonts = {}
        self.vsync_active = False
        self.refresh_hz = None
        self._measure_refresh()

    # ------------------------------------------------------------------ timing
    def _measure_refresh(self, n=40):
        """If flip() blocks for roughly one refresh period, vsync is active and
        flip timestamps correspond to real screen updates."""
        stamps = []
        for _ in range(n):
            self.screen.fill(self.col["background"])
            pygame.display.flip()
            pygame.event.pump()
            stamps.append(now())
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        med = statistics.median(gaps) if gaps else 0.0
        if med > 0.004:
            self.vsync_active = True
            self.refresh_hz = 1.0 / med
        else:
            self.vsync_active = False
            self.refresh_hz = None

    def flip(self, tick=True):
        """Show the frame and return its timestamp. With vsync this is the
        moment the frame reached the screen buffer at a refresh boundary."""
        pygame.display.flip()
        t = now()
        if tick and not self.vsync_active:
            self.clock.tick(self.cfg["display"]["fallback_fps"])
        return t

    def info(self):
        return {
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "pygame": pygame.version.ver,
            "screen_resolution": f"{self.w}x{self.h}",
            "screen_width_cm": round(self.width_cm, 2),
            "screen_diagonal_inches": self.cfg["display"]["diagonal_inches"],
            "viewing_distance_cm": self.viewing_distance_cm,
            "px_per_deg": round(self.px_per_deg, 3),
            "vsync_requested": self.vsync_requested,
            "vsync_active": self.vsync_active,
            "refresh_hz_measured": round(self.refresh_hz, 2) if self.refresh_hz else None,
        }

    # ------------------------------------------------------------- geometry
    def deg(self, d):
        return float(d) * self.px_per_deg

    def px_to_deg(self, px):
        return float(px) / self.px_per_deg

    # -------------------------------------------------------------- drawing
    def clear(self, colour=None):
        self.screen.fill(colour or self.col["background"])

    def font(self, size):
        px = max(10, int(round(size * self.h / 1080.0 * self.cfg["display"].get("font_scale", 1.0))))
        f = self._fonts.get(px)
        if f is None:
            f = pygame.font.SysFont("arial,helvetica,liberationsans,dejavusans", px)
            self._fonts[px] = f
        return f

    def text(self, s, pos, size=28, anchor="center", colour=None, bold=False):
        f = self.font(size)
        f.set_bold(bold)
        surf = f.render(str(s), True, colour or self.col["text"])
        f.set_bold(False)
        rect = surf.get_rect()
        setattr(rect, anchor, (int(pos[0]), int(pos[1])))
        self.screen.blit(surf, rect)
        return rect

    def wrap(self, s, width, size):
        f = self.font(size)
        lines = []
        for para in str(s).split("\n"):
            if not para.strip():
                lines.append("")
                continue
            cur = ""
            for word in para.split(" "):
                trial = (cur + " " + word).strip()
                if f.size(trial)[0] <= width or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = word
            lines.append(cur)
        return lines

    def paragraph(self, s, left, top, width, size=28, colour=None, spacing=1.35, align="left"):
        f = self.font(size)
        lh = int(f.get_linesize() * spacing)
        y = top
        for line in self.wrap(s, width, size):
            if line:
                if align == "center":
                    self.text(line, (left + width / 2, y), size, "midtop", colour)
                else:
                    self.text(line, (left, y), size, "topleft", colour)
            y += lh
        return y

    def button(self, b):
        fill = self.col["button_selected"] if b.selected else self.col["button_fill"]
        pygame.draw.rect(self.screen, fill, b.rect)
        pygame.draw.rect(self.screen, self.col["outline"], b.rect, 2 if b.enabled else 1)
        self.text(b.label, b.rect.center, b.size, "center",
                  self.col["text"] if b.enabled else self.col["disabled_text"])

    def circle(self, colour, pos, radius, outline=False):
        x, y, r = int(round(pos[0])), int(round(pos[1])), max(1, int(round(radius)))
        gfxdraw.filled_circle(self.screen, x, y, r, colour)
        gfxdraw.aacircle(self.screen, x, y, r, colour)
        if outline:
            gfxdraw.aacircle(self.screen, x, y, r, self.col["outline"])
