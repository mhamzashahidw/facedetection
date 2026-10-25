@echo off
title UniVision Cloud Backend API (Port 8000)
cd /d "%~dp0"
echo ===================================================
echo Starting UniVision Cloud Backend Service
echo ===================================================
echo Seeding initial demo data (if fresh database)...
python backend/seed_data.py
echo Starting FastAPI Uvicorn on 127.0.0.1:8000...
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
if errorlevel 1 (
    echo.
    echo Backend encountered an error.
    pause
)
