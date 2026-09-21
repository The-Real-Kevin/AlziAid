"""Single time source for the whole application.

Every timestamp in ALICE (screen flips, key presses, camera frames) comes from
this monotonic high-resolution clock, so all events share one timeline.
"""
import time


def now() -> float:
    """Seconds on a monotonic, high-resolution clock."""
    return time.perf_counter()
