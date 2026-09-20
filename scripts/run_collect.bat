@echo off
REM AOI Capacity headless collect (for Task Scheduler). Uses the same data folder as the GUI (prefs.json / devices.csv).
REM exe-lite layout: python\python.exe sits next to app\; in a dev checkout the system python is used.
REM Keep this file ASCII only: Korean text breaks on cp949 consoles.
REM
REM - PYTHONNOUSERSITE=1 so a user-site package cannot shadow the bundled runtime (same as run_aoi.bat and the launcher).
REM - The Python exit code (0 ok / 3 HTML written but CSV failed / 1 failed) is preserved as this script's ERRORLEVEL,
REM   so Task Scheduler's "last run result" tells the truth.
REM - collect.log lives in the LOCAL data folder and is rotated by size (LOG_MAX_BYTES) keeping LOG_KEEP old copies,
REM   instead of growing forever.
setlocal
cd /d "%~dp0\.."
set "PYTHONNOUSERSITE=1"
set "PY=%~dp0..\..\python\python.exe"
if not exist "%PY%" set "PY=python"

set "LOG_DIR=%LOCALAPPDATA%\AOI_Capacity"
if "%LOCALAPPDATA%"=="" set "LOG_DIR=%USERPROFILE%\.aoi_capacity"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
set "LOG=%LOG_DIR%\collect.log"
set "LOG_MAX_BYTES=5242880"
set "LOG_KEEP=4"

if exist "%LOG%" for %%F in ("%LOG%") do if %%~zF GTR %LOG_MAX_BYTES% call :rotate

"%PY%" -m aoi_capacity.cli %* >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%

:rotate
REM collect.log -> collect.log.1 -> ... -> collect.log.%LOG_KEEP% (oldest dropped). Names only, same local folder.
if exist "%LOG%.%LOG_KEEP%" del /q "%LOG%.%LOG_KEEP%" >nul 2>&1
set /a _i=%LOG_KEEP%-1
:rotate_loop
if %_i% LEQ 0 goto rotate_head
set /a _j=%_i%+1
if exist "%LOG%.%_i%" ren "%LOG%.%_i%" "collect.log.%_j%" >nul 2>&1
set /a _i=%_i%-1
goto rotate_loop
:rotate_head
ren "%LOG%" "collect.log.1" >nul 2>&1
goto :eof
