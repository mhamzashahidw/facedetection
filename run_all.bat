@echo off
title UniVision Enterprise Suite Launcher
cd /d "%~dp0"
echo ===============================================================
echo       UniVision Edge-Biometric Attendance System
echo ===============================================================
echo.
echo [1/3] Launching Cloud Backend API on port 8000...
start "UniVision Cloud Backend (8000)" cmd /k "call run_backend.bat"

echo [2/3] Launching Desktop AI & Local Storage Bridge on port 8001...
start "UniVision AI Bridge (8001)" /min python -m uvicorn desktop.app.bridge_service:app --host 127.0.0.1 --port 8001

timeout /t 2 /nobreak > nul

echo [3/3] Launching Flutter Desktop Workstation GUI...
call run_desktop_flutter.bat %1

echo System launched successfully.
