#!/bin/bash

# Define paths to your Python scripts
SYSLOG_SCRIPT="syslog/syslog_server.py"
API_SCRIPT="api/main.py"

# Path to your virtual environment
VENV_PATH="./venv"

# Check if virtual environment exists, if not, create it
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found. Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate the virtual environment
source "$VENV_PATH/bin/activate"

# Install dependencies from requirements.txt
if [ ! -d "$VENV_PATH" ]; then
    if [ -f "requirements.txt" ]; then
        echo "Installing dependencies from requirements.txt..."
        pip install -r requirements.txt
        
    else
        echo "requirements.txt not found. Skipping dependency installation."
    fi
fi

# Run syslog_server.py with sudo
echo "Running syslog_server.py with sudo..."
sudo python3 "$SYSLOG_SCRIPT" &

# Run main.py as a non-sudo user
echo "Running main.py as non-sudo user..."
python3 "$API_SCRIPT"

# Deactivate the virtual environment
deactivate
