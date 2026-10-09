@echo off
REM AOI Capacity - collect wafer-folder logs (INI/txt/json, no .dat, no images) for the developer.
REM Reads the NAS only. Writes zips (25-29.9MB each) to OUT_DIR at the top of collect_wafer_logs.py.
REM Keep this file ASCII only (cp949 consoles).
REM Usage: double-click, or: make_wafer_logs.bat --plan     (show the Lots it would pick, read nothing else)
setlocal
cd /d "%~dp0"
set "PY=%~dp0..\..\python\python.exe"
if not exist "%PY%" set "PY=%~dp0..\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0collect_wafer_logs.py" %*
echo.
pause
