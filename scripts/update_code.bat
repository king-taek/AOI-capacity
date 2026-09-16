@echo off
REM AOI Capacity - pull the latest code into this folder (git or GitHub zip).
REM Keep this file ASCII only (cp949 consoles). Branch is set at the top of update_code.py.
setlocal
cd /d "%~dp0"
set "PY=%~dp0..\..\python\python.exe"
if not exist "%PY%" set "PY=%~dp0..\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0update_code.py" %*
echo.
pause
