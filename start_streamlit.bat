@echo off
setlocal

echo ==============================================
echo   Couple's Money Planner - Streamlit Launch
echo ==============================================
echo.

cd /d %~dp0

if not exist backend\venv\Scripts\python.exe (
  echo Creating Python virtual environment...
  python -m venv backend\venv
)

echo Installing Streamlit dependencies...
backend\venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo Starting Streamlit app on http://localhost:8501
echo Press Ctrl+C to stop.
echo.
backend\venv\Scripts\python.exe -m streamlit run main.py --server.port 8501
