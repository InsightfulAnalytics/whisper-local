@echo off
REM Launches Whisper Local FROM SOURCE. Prefers a local .venv if present, else system python.
REM Double-click this file, or pin its shortcut to taskbar/start menu.
REM
REM NOTE: this is the developer launcher and needs Python 3.11+ installed.
REM Just want the app? Download the standalone exe instead (no Python needed):
REM   https://github.com/InsightfulAnalytics/whisper-local/releases/latest/download/whisper-local.exe
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" whisper-local.py
    goto :done
)
REM "where python" fails both when Python is missing AND when only the
REM Microsoft Store alias stub is on PATH refusing real work — catch it here
REM with a readable message instead of a window that flashes and vanishes.
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo   Python 3.11+ is required to run Whisper Local from source, but no
    echo   'python' command was found on this PC.
    echo.
    echo   EITHER install Python from https://www.python.org/downloads/
    echo   ^(tick "Add python.exe to PATH" in the installer^), then run:
    echo       pip install https://github.com/InsightfulAnalytics/whisper-local/archive/refs/heads/main.zip
    echo.
    echo   OR skip Python entirely - download the standalone app:
    echo       https://github.com/InsightfulAnalytics/whisper-local/releases/latest/download/whisper-local.exe
    echo.
    pause
    exit /b 1
)
python whisper-local.py
:done
if errorlevel 1 pause
