@echo off
REM AOI Capacity - collect a sample (Reports + WaferInfo.ini) for the developer.
REM Reads the NAS only. Writes a zip on your Desktop. Keep this file ASCII only (cp949 consoles).
REM Usage: double-click, or: make_sample.bat --root Y:\AOI-25 --days 2
setlocal
cd /d "%~dp0"
set "PY=%~dp0..\..\python\python.exe"
if not exist "%PY%" set "PY=%~dp0..\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0collect_sample.py" %*
echo.
pause
