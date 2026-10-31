# boot_bench — 시작 화면(랜딩 애니메이션) 렉 계측 · 개선안 변형 (2026-10-31)

수동 도구다(테스트 아님, CI 에서 돌지 않음). 결과 보고서는 `docs/proposals/boot_lag_2026-10-31/report.html`.

- `variants/*.js` — `<script id="boot">` 교체본. `_shell.js`(덮개 · 단계 글자 · AOI_BOOT API · 4초 최소) + `_layout.js`(고정 장면) + 엔진(`_engine.js` 입자 Worker · `_css.js` CSS 스켈레톤 · `_text.js` 글자) 위에 변형 하나씩.
  `*.patch.json` 은 현재 template 의 boot 스크립트에 치환만 적용하는 변형(cheap · noblur).
- `build.py <변형> <보관 샘플> <출력.html> [--lot]` — template + `dev/samples` 의 embedded JSON 으로 시험용 HTML.
- `measure.js <html> [--cpu N] [--dpr D] [--w W] [--h H] [--out x.json]` — Playwright Chromium: Worker rAF 간격 · 콜백 시간, 메인 LoAF · rAF, 걷힘 구간, CDP 트레이스 드롭 프레임.
- `run_set.sh <변형>`(세 조건) · `run_all.sh` · `run_text.sh` · `run_more.sh` — 보고서에 쓴 실행 묶음. 결과는 `out/*.json`(커밋됨).
- `shot.js <html> <접두> [ms…]` — 장면 스크린샷(`shots/`, 커밋 안 함 — 다시 만들면 된다).
- `demo.py <폴더>` — 변형마다 더블클릭용 데모 HTML(가짜 로딩 `?load=ms` · `?busy=1` 메인 스레드 막힘 · `?lot=1`).
- `report.py <폴더>` — `out/*.json` + `shots/` → `report.html` + `demos/`(바깥 요청 0, 이미지 인라인).

재현: `python3 build.py baseline AOI_capacity_2026-09-18_30일치.html.gz html/baseline.html` → `./run_set.sh baseline` → … → `python3 report.py <폴더>`.
