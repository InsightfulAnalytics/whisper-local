@echo off
REM Launches Whisper Local. Prefers a local .venv if present, else system python.
REM Double-click this file, or pin its shortcut to taskbar/start menu.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" whisper-local.py
) else (
    python whisper-local.py
)
