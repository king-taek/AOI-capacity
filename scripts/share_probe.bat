@echo off
REM AOI Capacity - shared folder test for the LOT tracking page (see share_probe.py).
REM Writes only into <shared folder>\_aoi_share_probe and a local result folder. Keep this file ASCII only (cp949 consoles).
REM Usage: double-click, or: share_probe.bat --hammer 300   /   share_probe.bat --clean
setlocal
cd /d "%~dp0"
set "PY=%~dp0..\..\python\python.exe"
if not exist "%PY%" set "PY=%~dp0..\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0share_probe.py" %*
echo.
pause