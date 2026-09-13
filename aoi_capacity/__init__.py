"""AOI Capacity — Camtek AOI 장비 가동률 대시보드.

패키지 구성
- collect.py   수집 코어(표준 라이브러리만). NAS 는 읽기만 한다.
- devices.py   장비 목록 CSV 읽기/쓰기, 장비 폴더 판정.
- nas_guard.py NAS 읽기 전용 안전장치.
- cli.py       스케줄러용 헤드리스 실행.
- utils/       paths · prefs · bootstrap · updater
- workers/     Qt 백그라운드 워커
- ui/          PyQt6 화면 (테마의 단일 출처는 ui/assets/template.html 의 :root 토큰)
"""

APP_NAME = "AOI Capacity"
APP_ID = "AOI_Capacity"
