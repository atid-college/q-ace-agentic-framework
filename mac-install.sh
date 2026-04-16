#!/bin/bash

# Stop on error
set -e

echo "Starting Q-ACE Framework Setup..."

# --- 1. Main Application Environment (venv) ---
if [ ! -d "venv" ]; then
    echo "Creating main virtual environment (venv)..."
    python3 -m venv venv
fi

echo "Activating main environment..."
source venv/bin/activate

echo "Installing main dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Initializing Authentication Database..."
python3 init_auth_db.py
deactivate

# --- 2. Browser Agent Environment (.venv) ---
echo "Checking for 'uv' (required for Browser Agent)..."
if ! command -v uv &> /dev/null; then
    echo "uv not found. Installing uv..."
    pip install uv
fi

if [ ! -d ".venv" ]; then
    echo "Creating specialized Browser Agent environment (.venv)..."
    uv venv
fi

echo "Installing Browser Agent dependencies into .venv..."
source .venv/bin/activate
uv pip install browser-use
uvx browser-use install
deactivate

# --- 3. Launch Server ---
echo "Re-activating main environment for server launch..."
source venv/bin/activate

echo ""
echo "###########################################################"
echo "#                                                         #"
echo "#           SUCCESS: Q-ACE Setup Completed!               #"
echo "#                                                         #"
echo "###########################################################"
echo ""
echo " The application is now UP AND RUNNING."
echo ""
echo " 1. Open your browser at: http://localhost:8090"
echo " 2. Login with the default credentials:"
echo ""
echo "    Username: admin"
echo "    Password: admin123"
echo ""
echo "###########################################################"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8090 --reload