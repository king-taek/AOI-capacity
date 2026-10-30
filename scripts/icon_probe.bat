@echo off
REM AOI Capacity - shortcut icon test (see icon_probe.py). Writes only into a Desktop test folder and <shared folder>\_aoi_icon_test.
REM Usage: double-click, or: icon_probe.bat --clean   Keep this file ASCII only (cp949 consoles).
setlocal
cd /d "%~dp0"
set "PY=%~dp0..\..\python\python.exe"
if not exist "%PY%" set "PY=%~dp0..\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0icon_probe.py" %*
echo.
pause
