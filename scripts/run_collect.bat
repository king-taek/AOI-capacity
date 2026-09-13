@echo off
rem AOI Capacity 헤드리스 수집(작업 스케줄러용). GUI 와 같은 데이터 폴더(prefs.json / devices.csv)를 쓴다.
rem exe 배포본이면 python\python.exe 가 옆에 있고, 개발 폴더면 시스템 python 을 쓴다.
cd /d "%~dp0\.."
set "PY=%~dp0..\..\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m aoi_capacity.cli %* >> "%LOCALAPPDATA%\AOI_Capacity\collect.log" 2>&1
