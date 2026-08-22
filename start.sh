#!/usr/bin/env bash
set -e

echo "========================================================="
echo "   🚀 Launching TraceForge 83 Authenticity Engine"
echo "========================================================="

# Check Python environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtualenv and installing requirements..."
source venv/bin/activate
pip install -r backend/requirements.txt

echo "Running automated verification tests..."
PYTHONPATH=backend pytest backend/tests/

echo "Starting TraceForge 83 server on http://localhost:8000 ..."
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
