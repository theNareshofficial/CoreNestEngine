@echo off
REM CoreNestEngine Application Startup Script

echo =================================================
echo  Starting CoreNestEngine Flask Application
echo =================================================
echo.

REM --- Activate the virtual environment ---
echo Activating Python virtual environment...
call .\.venv\Scripts\activate.bat
echo.

REM --- Start the Flask App ---
echo Starting Flask server...
echo Visit http://127.0.0.1:5000 in your browser.
echo Press CTRL+C to stop the server.
echo.
python app.py

pause