@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Build EXE - Bulk Video Watermarker

echo ============================================================
echo   BUILDING EXECUTABLE
echo ============================================================
echo.

:: --- Sanity checks -------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [X] No virtual environment found.
    echo     Run setup.bat first, then run this again.
    pause
    exit /b 1
)

if not exist "bin\ffmpeg.exe" (
    echo [X] bin\ffmpeg.exe not found.
    echo     Place ffmpeg.exe and ffprobe.exe in the bin folder first.
    pause
    exit /b 1
)

if not exist "bin\ffprobe.exe" (
    echo [X] bin\ffprobe.exe not found.
    echo     Place ffmpeg.exe and ffprobe.exe in the bin folder first.
    pause
    exit /b 1
)

:: --- Clean previous build ------------------------------------------------
echo [1/5] Cleaning old build files...
if exist "build"    rmdir /S /Q "build"
if exist "dist"     rmdir /S /Q "dist"
if exist "*.spec"   del /Q "*.spec" 2>nul
echo      done.

:: --- Install/update PyInstaller -----------------------------------------
echo [2/5] Ensuring PyInstaller is installed...
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller 1>nul
echo      done.

:: --- Icon flag (optional) -----------------------------------------------
set "ICON_FLAG="
if exist "assets\icon.ico" (
    set "ICON_FLAG=--icon assets\icon.ico"
    echo [3/5] Using custom icon: assets\icon.ico
) else (
    echo [3/5] No assets\icon.ico found - using default icon.
)

:: --- Build ---------------------------------------------------------------
echo [4/5] Building executable (this may take 1-3 minutes)...
".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name "VideoWatermarker" ^
    --add-data "bin;bin" ^
    --add-data "assets;assets" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL.Image" ^
    --hidden-import "PIL.ImageTk" ^
    --collect-all "PIL" ^
    !ICON_FLAG! ^
    main.py

if errorlevel 1 (
    echo.
    echo [X] Build failed. Read the errors above.
    pause
    exit /b 1
)

:: --- Result --------------------------------------------------------------
echo.
echo [5/5] Build complete!
echo.
echo ============================================================
echo   SUCCESS
echo ============================================================
echo.
echo   Your app is ready here:
echo.
echo     dist\VideoWatermarker\VideoWatermarker.exe
echo.
echo   To ship to a client:
echo     1. Zip the WHOLE "dist\VideoWatermarker" folder
echo     2. Send the zip
echo     3. Client extracts, then double-clicks VideoWatermarker.exe
echo.
echo ============================================================
echo.

if exist "dist\VideoWatermarker\VideoWatermarker.exe" (
    echo Opening the dist folder...
    start "" "dist\VideoWatermarker"
)

pause