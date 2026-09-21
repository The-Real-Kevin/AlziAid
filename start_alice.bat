@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo ALICE is not installed yet. Double-click install_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe run_alice.py %*
if errorlevel 1 pause
