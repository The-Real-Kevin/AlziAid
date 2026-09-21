"""Event polling, the abort key, and an autopilot used for automated testing."""
import pygame

from .clock import now


class AbortRequested(Exception):
    """Raised when the operator presses Esc (or closes the window)."""


class Input:
    def __init__(self, auto=False):
        self.auto = auto              # autopilot: synthesises responses (testing only)
        self.allow_abort = True
        self.mouse_sim = None         # SimTracker in mouse mode, fed with the cursor position
        self._scheduled = []

    # ---------------------------------------------------------------- polling
    def poll(self):
        """Return (timestamp, events). Timestamp is taken immediately after the
        event queue is read, so key times are accurate to the polling interval."""
        if self._scheduled:
            t = now()
            due = [s for s in self._scheduled if s[0] <= t]
            if due:
                self._scheduled = [s for s in self._scheduled if s[0] > t]
                for _, fn in sorted(due, key=lambda s: s[0]):
                    fn()
        events = pygame.event.get()
        t = now()
        if self.mouse_sim is not None:
            self.mouse_sim.set_point(pygame.mouse.get_pos())
        for e in events:
            if e.type == pygame.QUIT:
                raise AbortRequested()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and self.allow_abort:
                raise AbortRequested()
        return t, events

    # -------------------------------------------------------------- autopilot
    def schedule(self, delay_s, fn):
        if self.auto:
            self._scheduled.append((now() + delay_s, fn))

    def clear_schedule(self):
        self._scheduled.clear()

    def auto_click(self, delay_s, pos):
        p = (int(pos[0]), int(pos[1]))
        self.schedule(delay_s, lambda: pygame.event.post(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": p, "button": 1})))

    def auto_key(self, delay_s, key):
        self.schedule(delay_s, lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0, "unicode": "", "scancode": 0})))
