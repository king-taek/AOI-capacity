@echo off
rem AOI Capacity 수집기 실행. 작업 스케줄러에 이 파일을 등록하세요 (예: 10분마다).
cd /d "%~dp0"
python aoi_collect.py >> collect.log 2>&1
