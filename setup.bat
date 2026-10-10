@echo off
REM CoreNestEngine Application Startup Script
REM ===================================================
REM  CoreNestEngine Windows Startup & Setup Script
REM ===================================================

echo =================================================
echo  Starting CoreNestEngine Flask Application
echo =================================================
echo ===================================================
echo   CoreNestEngine - Stock & Billing Engine
echo ===================================================
echo.

REM --- Activate the virtual environment ---
echo Activating Python virtual environment...
call .\.venv\Scripts\activate.bat
REM --- Check for Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

REM --- Setup Virtual Environment if not exists ---
if not exist ".venv" (
    echo [INFO] Creating Python virtual environment in .venv...
    python -m venv .venv
    echo [INFO] Installing dependencies...
    call .venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

REM --- Create .env from template if missing ---
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [INFO] Created .env configuration file.
    )
)

echo.

REM --- Start the Flask App ---
echo Starting Flask server...
echo [INFO] Starting CoreNestEngine Flask server...
echo [INFO] Built-in SQLite database will be initialized automatically.
echo [INFO] Default credentials: admin / admin123
echo.
echo Visit http://127.0.0.1:5000 in your browser.
echo Press CTRL+C to stop the server.
echo ===================================================
echo.

python app.py

pause