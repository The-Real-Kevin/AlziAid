#!/bin/bash
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then echo "ALICE is not installed yet. Double-click install_mac.command first."; read -p "Press Enter to close"; exit 1; fi
.venv/bin/python run_alice.py "$@" || read -p "ALICE closed with an error. Press Enter to close"
