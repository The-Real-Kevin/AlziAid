@echo off
cd /d "%~dp0"
echo Installing ALICE... this takes a few minutes and needs an internet connection.
py -3.11 -m venv .venv 2>nul || py -3.12 -m venv .venv 2>nul || python -m venv .venv
if errorlevel 1 (
  echo.
  echo Could not create the Python environment. Is Python 3.11 installed? See setup.txt step 1.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installation FAILED. Please send a photo of this window to the research team.
  pause
  exit /b 1
)
echo.
echo Installation complete. Double-click start_alice.bat to run ALICE.
pause
