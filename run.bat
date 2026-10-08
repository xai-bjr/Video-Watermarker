@echo off
setlocal
cd /d "%~dp0"
title Bulk Video Watermarker

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    echo [!] Virtual environment not found. Run setup.bat first.
    pause
)