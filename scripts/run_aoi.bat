@echo off
REM AOI Capacity - run without a console window (pythonw). Fallback when the exe is blocked.
REM Keep this file ASCII only: Korean text breaks on cp949 consoles.
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"
if not exist "%~dp0python\pythonw.exe" (
    echo [ERROR] python\pythonw.exe not found. Unzip the delivered archive again.
    pause
    exit /b 1
)
if not exist "%~dp0.deps_installed" (
    echo [INFO] First run: installing packages. This may take a few minutes...
    "%~dp0python\python.exe" "%~dp0app\main.py"
    exit /b %errorlevel%
)
start "" "%~dp0python\pythonw.exe" "%~dp0app\main.py"
