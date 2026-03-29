#!/usr/bin/env bash
set -e

echo "=============================================="
echo "  Couple's Money Planner - Streamlit Launch"
echo "=============================================="
echo

cd "$(dirname "$0")"

if [ ! -f backend/venv/bin/python ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv backend/venv
fi

echo "Installing Streamlit dependencies..."
./backend/venv/bin/python -m pip install -r requirements.txt

echo
echo "Starting Streamlit app on http://localhost:8501"
echo "Press Ctrl+C to stop."
echo
./backend/venv/bin/python -m streamlit run main.py --server.port 8501
