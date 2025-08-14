#!/bin/bash

# install_alziaid.sh
set -e

echo "Starting AlziAid Eye Tracking Test Setup..."
echo "This script installs required software."
echo "If errors occur, please contact yuqisun@umich.edu or call +852 59816970 on whatsapp."

# Check internet
if ! ping -c 1 google.com >/dev/null 2>&1; then
    echo "Error: Internet connection required."
    echo "Contact IT support or request a USB version."
    exit 1
fi

# Install Homebrew
if ! command -v brew >/dev/null 2>&1; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
        echo "Error: Failed to install Homebrew."
        exit 1
    }
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "Homebrew already installed."
fi

# Install Tcl/Tk 9.0.2
echo "Installing Tcl/Tk 9.0.2..."
brew install tcl-tk || true
export LDFLAGS="-L/opt/homebrew/Cellar/tcl-tk/9.0.2/lib"
export CPPFLAGS="-I/opt/homebrew/Cellar/tcl-tk/9.0.2/include"
export TK_LIBRARY="/opt/homebrew/Cellar/tcl-tk/9.0.2/lib/tk9.0"
export TCL_LIBRARY="/opt/homebrew/Cellar/tcl-tk/9.0.2/lib/tcl9.0"


# Verify Tkinter
echo "Verifying Tkinter..."
/opt/homebrew/opt/python@3.13/bin/python3 -c "import tkinter; print('Tkinter OK:', tkinter.Tcl().eval('info library'))" || {
    echo "Error: Tkinter failed. Reinstalling Python..."
    brew reinstall python@3.13 || {
        echo "Error: Tkinter still failed."
        exit 1
    }
}

# Install CMake for dlib
echo "Installing CMake..."
brew install cmake || true

# Install FFmpeg
echo "Installing FFmpeg..."
brew install ffmpeg || true

# Set up virtual environment
echo "Setting up virtual environment..."
/opt/homebrew/opt/python@3.13/bin/python3 -m venv ~/AlziAid/alziaid_venv || {
    echo "Error: Failed to create virtual environment."
    exit 1
}
source ~/AlziAid/alziaid_venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install opencv-python==4.12.0.88 numpy==2.2.6 dlib==20.0.0 || {
    echo "Error: Failed to install dependencies."
    exit 1
}

# Copy project files
echo "Setting up project files..."
mkdir -p ~/AlziAid
cp main.py ~/AlziAid/ || {
    echo "Error: Failed to copy main.py."
    exit 1
}
cp -r gaze_tracking ~/AlziAid/ || {
    echo "Error: Failed to copy gaze_tracking."
    exit 1
}

echo "Setup complete. Run ./run_alziaid.sh to start the test."
