@echo off
setlocal
cd /d "%~dp0"
title Setup - Bulk Video Watermarker

echo ============================================================
echo   Bulk Video Watermarker ^& Short-Form Formatter - SETUP
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python was not found on PATH. Install it from python.org
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment .venv ...
if not exist ".venv" (
    python -m venv .venv
) else (
    echo        already exists - skipping
)

echo [2/4] Upgrading pip ...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [3/4] Installing requirements ...
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo [4/4] Checking for ffmpeg in .\bin ...
if exist "bin\ffmpeg.exe" (
    echo        ffmpeg.exe found - good.
) else (
    echo.
    echo  [!] ffmpeg.exe not found in .\bin
    echo      Download a build from https://www.gyan.dev/ffmpeg/builds/
    echo      and place ffmpeg.exe and ffprobe.exe in the bin\ folder.
)

echo.
echo  Setup finished.  Run "run.bat" to launch the app.
pause