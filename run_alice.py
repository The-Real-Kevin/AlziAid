"""ALICE - data collection software for the AlziAid study.

    python run_alice.py                 normal use (webcam, fullscreen)
    python run_alice.py --camera-test   check the camera and face detection only
    python run_alice.py --simulate      no camera; gaze follows the mouse (for trying the software)
    python run_alice.py --windowed      run in a window instead of fullscreen (development)
    python run_alice.py --autotest      automated end-to-end self-test with a simulated participant

Press Esc at any time to abort or restart the current section.
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser(description="ALICE data collection software")
    ap.add_argument("--config", default=None, help="path to config.yaml (default: the one next to this file)")
    ap.add_argument("--windowed", action="store_true", help="run in a window (development only)")
    ap.add_argument("--simulate", action="store_true", help="no camera; gaze follows the mouse")
    ap.add_argument("--camera-test", action="store_true", help="show camera preview and face detection only")
    ap.add_argument("--autotest", action="store_true", help="automated end-to-end self-test")
    ap.add_argument("--headless", action="store_true", help="no visible window (with --autotest)")
    args = ap.parse_args()

    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    os.environ.setdefault("GLOG_minloglevel", "2")       # quieter MediaPipe logging
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from alice.session import run_app
    sys.exit(run_app(args))


if __name__ == "__main__":
    main()
