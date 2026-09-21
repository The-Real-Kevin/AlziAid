"""Non-task screens: start page, participant form, instruction pages,
face positioning, dialogs, and the save screen."""
import pygame

from . import __version__
from .clock import now
from .display import Button


# =============================================================================
# Widgets
# =============================================================================
class TextField:
    def __init__(self, rect, value="", numeric=False, max_len=60):
        self.rect = pygame.Rect([int(v) for v in rect])
        self.value = str(value)
        self.numeric = numeric
        self.max_len = max_len
        self.active = False

    def draw(self, d):
        pygame.draw.rect(d.screen, (255, 255, 255), self.rect)
        pygame.draw.rect(d.screen, d.col["outline"], self.rect, 3 if self.active else 1)
        f = d.font(26)
        shown = self.value
        while shown and f.size(shown + "|")[0] > self.rect.w - 16:
            shown = shown[1:]
        cursor = "|" if self.active and int(now() * 2) % 2 == 0 else ""
        d.text(shown + cursor, (self.rect.x + 8, self.rect.centery), 26, "midleft")

    def click(self, pos):
        self.active = self.rect.collidepoint(pos)

    def key(self, e):
        if self.active and e.key == pygame.K_BACKSPACE:
            self.value = self.value[:-1]

    def textinput(self, text):
        if not self.active:
            return
        if self.numeric:
            text = "".join(c for c in text if c.isdigit())
        self.value = (self.value + text)[: self.max_len]


class Toggle:
    def __init__(self, options, x, y, bw, bh, gap=12):
        self.buttons = [Button((x + i * (bw + gap), y, bw, bh), label, key)
                        for i, (key, label) in enumerate(options)]
        self.value = None

    def draw(self, d):
        for b in self.buttons:
            b.selected = (b.key == self.value)
            d.button(b)

    def click(self, pos):
        for b in self.buttons:
            if b.hit(pos):
                self.value = b.key

    def key(self, e):
        pass

    def textinput(self, text):
        pass


# =============================================================================
# Generic loop
# =============================================================================
def wait_screen(ctx, draw, buttons, keys=None, auto=None, widgets=()):
    """Draw a static screen until a button is clicked (or a mapped key pressed).
    Returns the key of the chosen button."""
    d, inp = ctx.d, ctx.inp
    if inp.auto and auto is not None:
        b = next(x for x in buttons if x.key == auto)
        inp.auto_click(0.05, b.rect.center)
    while True:
        d.clear()
        draw()
        for w in widgets:
            w.draw(d)
        for b in buttons:
            d.button(b)
        d.flip()
        _, events = inp.poll()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for w in widgets:
                    w.click(e.pos)
                for b in buttons:
                    if b.hit(e.pos):
                        return b.key
            elif e.type == pygame.KEYDOWN:
                if keys and e.key in keys:
                    k = keys[e.key]
                    b = next((x for x in buttons if x.key == k), None)
                    if b is None or b.enabled:
                        return k
                for w in widgets:
                    w.key(e)
            elif e.type == pygame.TEXTINPUT:
                for w in widgets:
                    w.textinput(e.text)


def status_line(ctx):
    d, tr = ctx.d, ctx.tracker
    y = d.h - 28
    if tr.kind == "simulated":
        d.text("SIMULATED TRACKING - not real eye data", (28, y), 20, "bottomleft", d.col["warn"])
    elif tr.face_ok():
        d.text("Camera: face detected", (28, y), 20, "bottomleft", d.col["ok"])
    else:
        d.text("Camera: no face detected", (28, y), 20, "bottomleft", d.col["bad"])
    d.text(f"ALICE v{__version__}", (d.w - 28, y), 18, "bottomright", d.col["disabled_text"])


def _primary(d, label, key, y=0.84, enabled=True):
    bw, bh = int(d.w * 0.18), int(d.h * 0.07)
    return Button((d.w / 2 - bw / 2, d.h * y, bw, bh), label, key, enabled=enabled)


# =============================================================================
# Screens
# =============================================================================
def start_page(ctx):
    d, cfg = ctx.d, ctx.cfg
    start = _primary(d, "Start", "start", y=0.72)
    qw, qh = int(d.w * 0.09), int(d.h * 0.055)
    quit_b = Button((d.w - qw - 28, 28, qw, qh), "Quit", "quit", size=22)

    def draw():
        d.text(cfg["software"]["title"], (d.w / 2, d.h * 0.11), 56, bold=True)
        d.text(cfg["software"]["subtitle"], (d.w / 2, d.h * 0.18), 30)
        d.paragraph(cfg["instructions"]["start"], d.w * 0.22, d.h * 0.30, d.w * 0.56, 30, align="center")
        status_line(ctx)

    return wait_screen(ctx, draw, [start, quit_b], keys={pygame.K_RETURN: "start"}, auto="start")


def participant_form(ctx, default_subject, existing):
    d = ctx.d
    lx, fx = d.w * 0.22, d.w * 0.48
    fw, fh = d.w * 0.30, d.h * 0.055
    row = lambda i: d.h * 0.18 + i * d.h * 0.085
    tw = d.w * 0.09

    subject = TextField((fx, row(0), fw * 0.4, fh), str(default_subject), numeric=True, max_len=3)
    operator = TextField((fx, row(1), fw * 0.4, fh), "", max_len=6)
    age = TextField((fx, row(2), fw * 0.4, fh), "", numeric=True, max_len=3)
    sex = Toggle([("F", "Female"), ("M", "Male")], fx, row(3), tw, fh)
    glasses = Toggle([("yes", "Yes"), ("no", "No")], fx, row(4), tw, fh)
    contacts = Toggle([("yes", "Yes"), ("no", "No")], fx, row(5), tw, fh)
    eye = TextField((fx, row(6), fw, fh), "", max_len=150)
    widgets = [subject, operator, age, sex, glasses, contacts, eye]
    labels = ["Subject number", "Operator initials", "Age (years)", "Sex",
              "Wearing glasses now", "Wearing contact lenses", "Known eye conditions (blank if none)"]
    cont = _primary(d, "Continue", "continue", y=0.86)

    if ctx.inp.auto:
        operator.value, age.value = "AT", "70"
        sex.value, glasses.value, contacts.value = "F", "no", "no"

    def problem():
        if not subject.value or not (1 <= int(subject.value) <= 999):
            return "Subject number must be 1-999."
        if int(subject.value) in existing:
            return f"Subject number {int(subject.value)} already exists in the results folder."
        if not operator.value.strip():
            return "Enter operator initials."
        if not age.value or not (18 <= int(age.value) <= 120):
            return "Enter a valid age."
        if sex.value is None or glasses.value is None or contacts.value is None:
            return "Complete all selections."
        return None

    def draw():
        d.text("Participant details", (d.w / 2, d.h * 0.08), 40, bold=True)
        for i, lab in enumerate(labels):
            d.text(lab, (lx, row(i) + fh / 2), 26, "midleft")
        msg = problem()
        cont.enabled = msg is None
        if msg:
            d.text(msg, (d.w / 2, d.h * 0.81), 22, colour=d.col["bad"])
        d.text("Do not enter names or other identifying details.", (d.w / 2, d.h * 0.95), 20,
               colour=d.col["disabled_text"])

    wait_screen(ctx, draw, [cont], auto="continue", widgets=widgets)
    return {
        "subject_number": int(subject.value),
        "operator_initials": operator.value.strip().upper(),
        "age": int(age.value),
        "sex": sex.value,
        "wears_glasses": glasses.value == "yes",
        "wears_contacts": contacts.value == "yes",
        "known_eye_conditions": eye.value.strip(),
    }


def instruction(ctx, title, text, button="Begin"):
    d = ctx.d
    b = _primary(d, button, "go")

    def draw():
        d.text(title, (d.w / 2, d.h * 0.12), 44, bold=True)
        d.paragraph(text, d.w * 0.18, d.h * 0.24, d.w * 0.64, 32, spacing=1.45)
        status_line(ctx)

    wait_screen(ctx, draw, [b], keys={pygame.K_RETURN: "go"}, auto="go")


def message(ctx, title, body, options, auto=None, extra=None, colour=None):
    """options: list of (key, label). Returns the chosen key."""
    d = ctx.d
    bw, bh, gap = int(d.w * 0.26), int(d.h * 0.07), int(d.w * 0.02)
    total = len(options) * bw + (len(options) - 1) * gap
    x0 = d.w / 2 - total / 2
    buttons = [Button((x0 + i * (bw + gap), d.h * 0.84, bw, bh), lab, key, size=24)
               for i, (key, lab) in enumerate(options)]

    def draw():
        d.text(title, (d.w / 2, d.h * 0.12), 42, bold=True, colour=colour)
        if body:
            d.paragraph(body, d.w * 0.2, d.h * 0.22, d.w * 0.6, 30, align="center")
        if extra:
            extra()

    return wait_screen(ctx, draw, buttons, auto=auto)


def confirm_abort(ctx, in_session=True):
    ctx.inp.allow_abort = False
    try:
        if in_session:
            return message(ctx, "Stop the session?",
                           "Choose whether to abort the whole session (data collected so far is kept "
                           "and the folder is marked PARTIAL) or to restart the current section from "
                           "the beginning.",
                           [("abort", "Abort session"), ("restart", "Restart this section")],
                           auto="restart")
        return message(ctx, "Quit ALICE?", "", [("quit", "Quit"), ("cancel", "Cancel")], auto="quit")
    finally:
        ctx.inp.allow_abort = True


def face_position(ctx, camera_test=False):
    d, cfg, tr = ctx.d, ctx.cfg, ctx.tracker
    cont = _primary(d, "Close" if camera_test else "Continue", "continue", y=0.86, enabled=False)
    ok_since = [None]
    area = pygame.Rect(int(d.w * 0.27), int(d.h * 0.24), int(d.w * 0.46), int(d.h * 0.52))
    mirror = cfg["camera"].get("mirror_preview", True)

    def draw():
        d.text("Camera check" if camera_test else "Position the participant", (d.w / 2, d.h * 0.07), 40, bold=True)
        d.paragraph(cfg["instructions"]["face_position"], d.w * 0.18, d.h * 0.12, d.w * 0.64, 22, align="center")
        frame, pts = tr.preview()
        pygame.draw.rect(d.screen, (225, 225, 225), area)
        if frame is not None:
            import cv2
            fh, fw = frame.shape[:2]
            img = cv2.flip(frame, 1) if mirror else frame
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            surf = pygame.image.frombuffer(img.tobytes(), (fw, fh), "RGB")
            s = min(area.w / fw, area.h / fh)
            sw, sh = int(fw * s), int(fh * s)
            surf = pygame.transform.smoothscale(surf, (sw, sh))
            ox, oy = area.centerx - sw // 2, area.centery - sh // 2
            d.screen.blit(surf, (ox, oy))
            for (px, py) in pts:
                px = fw - px if mirror else px
                pygame.draw.circle(d.screen, (0, 220, 0), (int(ox + px * s), int(oy + py * s)), 3)
            guide = pygame.Rect(0, 0, int(sw * 0.30), int(sh * 0.62))
            guide.center = (area.centerx, area.centery)
            pygame.draw.ellipse(d.screen, (255, 255, 255), guide, 2)
        else:
            msg = "Simulated tracking - no camera preview" if tr.kind == "simulated" else "Waiting for camera..."
            d.text(msg, area.center, 26)
        pygame.draw.rect(d.screen, d.col["outline"], area, 1)

        face = tr.face_ok()
        if face:
            ok_since[0] = ok_since[0] or now()
        else:
            ok_since[0] = None
        steady = ok_since[0] is not None and now() - ok_since[0] >= 1.0
        cont.enabled = camera_test or steady or ctx.inp.auto
        col = d.col["ok"] if face else d.col["bad"]
        d.text("Face detected" if face else "No face detected", (d.w / 2, area.bottom + 24), 26, colour=col)
        fps = tr.fps()
        if fps:
            d.text(f"Camera {fps:.1f} fps", (area.right, area.bottom + 24), 20, "midright", d.col["disabled_text"])

    wait_screen(ctx, draw, [cont], keys={pygame.K_RETURN: "continue"}, auto="continue")


def save_screen(ctx):
    d = ctx.d
    bw, bh = int(d.w * 0.30), int(d.h * 0.075)
    x = d.w / 2 - bw / 2
    groups = Toggle([("A", "A - Alzheimer's disease")], x, d.h * 0.30, bw, bh)
    groups.buttons += [Button((x, d.h * 0.30 + (bh + 14), bw, bh), "M - Mild cognitive impairment", "M"),
                       Button((x, d.h * 0.30 + 2 * (bh + 14), bw, bh), "H - Healthy control", "H")]
    notes = TextField((d.w * 0.2, d.h * 0.66, d.w * 0.6, d.h * 0.055), "", max_len=500)
    save = _primary(d, "Save", "save", y=0.84, enabled=False)
    if ctx.inp.auto:
        groups.value = "H"

    def draw():
        d.text("Test complete - save data", (d.w / 2, d.h * 0.08), 42, bold=True)
        d.paragraph(ctx.cfg["instructions"]["save"], d.w * 0.2, d.h * 0.15, d.w * 0.6, 24, align="center")
        d.text("Operator notes (optional)", (d.w * 0.2, d.h * 0.66 - 8), 24, "bottomleft")
        save.enabled = groups.value is not None

    wait_screen(ctx, draw, [save], auto="save", widgets=[groups, notes])
    return groups.value, notes.value.strip()


def done_screen(ctx, path, partial=False):
    title = "Partial data saved" if partial else "Data saved"
    body = f"Folder:\n{path.name}\n\nLocation:\n{path.parent}"
    return message(ctx, title, body, [("new", "New session"), ("quit", "Quit")], auto="quit")


def error_screen(ctx, title, body):
    ctx.inp.allow_abort = False
    try:
        message(ctx, title, body, [("quit", "Quit")], auto="quit", colour=ctx.d.col["bad"])
    finally:
        ctx.inp.allow_abort = True
