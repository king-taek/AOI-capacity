@echo off
REM AOI Capacity - run with a console so errors are visible.
REM Use this if the app does not start or the window closes instantly.
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"
set "AOI_DEBUG=1"
if not exist "%~dp0python\python.exe" (
    echo [ERROR] python\python.exe not found. Unzip the delivered archive again.
    pause
    exit /b 1
)
"%~dp0python\python.exe" "%~dp0app\main.py"
echo.
echo [EXITED] If there is an error (traceback) above, please report it.
pause
