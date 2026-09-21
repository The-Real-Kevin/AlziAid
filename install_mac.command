#!/bin/bash
cd "$(dirname "$0")"
echo "Installing ALICE... this takes a few minutes and needs an internet connection."
PY=""
for c in python3.11 python3.12 python3; do
  if command -v $c >/dev/null 2>&1; then PY=$c; break; fi
done
if [ -z "$PY" ]; then echo "Python 3.11 not found. See setup.txt step 1."; read -p "Press Enter to close"; exit 1; fi
$PY -m venv .venv || { echo "Could not create the Python environment."; read -p "Press Enter to close"; exit 1; }
source .venv/bin/activate
python -m pip install --upgrade pip
if python -m pip install -r requirements.txt; then
  echo; echo "Installation complete. Double-click start_alice.command to run ALICE."
else
  echo; echo "Installation FAILED. Please send a screenshot of this window to the research team."
fi
read -p "Press Enter to close"
