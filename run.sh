#!/usr/bin/env bash
# ===================================================
#  CoreNestEngine Linux/macOS Startup Script
# ===================================================

set -e

echo "==================================================="
echo "  CoreNestEngine - Stock & Billing Engine"
echo "==================================================="
echo ""

# Find Python binary
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python 3 is not installed or not in PATH."
    exit 1
fi

# Create virtual environment if missing
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment in .venv..."
    $PYTHON_CMD -m venv .venv
    echo "[INFO] Installing dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Copy .env from template if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "[INFO] Created .env configuration from .env.example"
fi

echo ""
echo "[INFO] Starting CoreNestEngine Flask server..."
echo "[INFO] Built-in SQLite database will be initialized automatically."
echo "[INFO] Default credentials: admin / admin123"
echo ""
echo "Open http://127.0.0.1:5000 in your browser."
echo "Press CTRL+C to stop the server."
echo "==================================================="
echo ""

python app.py

