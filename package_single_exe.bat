@echo off
setlocal enabledelayedexpansion
title UniVision - Build Single Independent Windows Executable
cd /d "%~dp0"

echo ======================================================================
echo    UniVision Biometric Classroom Station - Single EXE Packager
echo ======================================================================
echo.

echo [Step 1/2] Building latest Flutter Windows Release binaries...
cd desktop_flutter
call flutter build windows --release
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Flutter Windows build failed!
    cd ..
    pause
    exit /b %ERRORLEVEL%
)
cd ..
echo [Step 1/2] Flutter build succeeded!
echo.

echo [Step 2/2] Packaging Flutter app + ONNX models + Python AI engine into single EXE...
cd packaging
call pyinstaller --clean --noconfirm univision_station.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller packaging failed!
    cd ..
    pause
    exit /b %ERRORLEVEL%
)
cd ..

if exist "packaging\dist\UniVision_Biometric_Station.exe" (
    if not exist "dist" mkdir dist
    copy /y "packaging\dist\UniVision_Biometric_Station.exe" "dist\UniVision_Biometric_Station.exe" >nul
    echo.
    echo ======================================================================
    echo [SUCCESS] Single Independent Executable created successfully!
    echo Binary: dist\UniVision_Biometric_Station.exe
    echo ======================================================================
    dir "dist\UniVision_Biometric_Station.exe"
) else (
    echo [ERROR] Target binary packaging\dist\UniVision_Biometric_Station.exe not found!
)

echo.
echo You can now copy dist\UniVision_Biometric_Station.exe to any Windows laptop
echo and run it directly without installing Flutter, Python, or any dependencies.
echo.
pause
