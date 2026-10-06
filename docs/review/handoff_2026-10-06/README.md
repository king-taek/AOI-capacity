# AOI 화면 개선 — Claude Code 전달 패키지

## 먼저 읽기

1. 루트의 `AOI_screen_improvement_handoff_2026-10-06.md`를 읽는다. 최종 확정된 8개 안의 문구·동작·함수·선택자·가드·받아들임 기준이 정본이다.
2. `final_choices.json`으로 선택을 빠르게 확인한다. **C8은 재검토 A로 확정**됐다.
3. `examples/AOI_screen_review_ABC_2026-10-06.html`을 브라우저에서 열어 선택안의 화면을 참고한다. C1 B, C2 B, C3 C(같은 높이 숫자), C4 A, C5 C, C6 A, C7 C, C8 재검토 A.
4. 원래 화면과 실데이터는 `samples/AOI_capacity_2026-09-21.html`; 해당 생성 기록은 `samples/app.log`.
5. 구현 전 `instructions/` 지침과 저장소의 `CLAUDE.md`, `진행상황.md`를 읽는다. 호출·가드 확인은 `reference/` 사본을 보조로 사용한다.

## 바로 입력할 요청

> 이 ZIP의 README와 최종 handoff를 읽고, king-taek/AOI-capacity의 결과 HTML 화면에 확정된 C1~C8만 구현하세요. 실제 화면 원본은 aoi_capacity/ui/assets/template.html입니다. 계산·수집기·업데이터는 변경하지 말고 기존 결정·테마·애니메이션·morph·팝업 접근성 계약을 유지하세요. 함수·선택자·기존/신규 가드와 받아들임 기준은 handoff를 따르세요. 코드 수정 뒤 기존 가드와 새 브라우저 검증을 실행하고 실데이터·Windows Chrome/Edge에서 남은 확인 항목을 보고하세요. 최신 저장소가 기준 SHA와 다르면 관련 소스와 결정 변경을 먼저 대조하세요. 이 패키지 전달을 배포나 main 머지 승인으로 간주하지 마세요.

## 기준과 파일의 역할

- 저장소: https://github.com/king-taek/AOI-capacity
- handoff 작성 시 확인한 main: `01d26c73c612b28c45933517852754df20010ff6`.
- graphify Built from commit: `01d26c73`; graph.json의 전체 SHA도 위와 동일.
- 원본 샘플: v4a6f0bc, 2026-09-21~2026-10-05, 157,299행.
- `reference/main/`은 **검토 기준 커밋의 일부 파일 사본**이다. 전체 저장소나 실행 가능한 프로젝트가 아니므로 작업 저장소 위에 덮어쓰지 않는다. 실제 저장소 소스가 구현 대상이다.
- `reference/graphify-out/`은 읽기용 코드 지도. main에 넣거나 updater 대상 파일로 추가하지 않는다.
- 선택 HTML의 저장된 선택 UI에는 C8이 미선택으로 남아 있을 수 있다. 최종 확정은 이 패키지의 handoff와 final_choices.json이 우선한다. 기존 브라우저 localStorage도 최종 결정을 바꾸지 않는다.
- 예시의 날짜·데이터·innerHTML 재생성은 시연용이다. 제품에 고정값이나 재생성 엔진을 복사하지 않는다.
- `validation/`은 선택 예시와 문서 대조 결과다. **제품 구현 후 테스트 통과 결과가 아니다**.
- 실데이터/로그 원문은 그대로 보관했다. NAS Report 연결의 실제 내용 확인은 현장 환경이 필요하다.
- Codex는 저장소를 수정하거나 커밋·푸시·PR·이슈·코멘트를 하지 않았다.

## 포함 파일

- `AOI_screen_improvement_handoff_2026-10-06.md`
- `examples/AOI_screen_review_ABC_2026-10-06.html`
- `final_choices.json`
- `instructions/CODEX_저장소_참고_지침.md`
- `instructions/CODEX_화면검토_지침.md`
- `reference/graphify-out/GRAPH_REPORT.md`
- `reference/graphify-out/graph.json`
- `reference/main/CLAUDE.md`
- `reference/main/aoi_capacity/ui/assets/template.html`
- `reference/main/dev/tests/test_dashboard_browser.py`
- `reference/main/dev/tests/test_dashboard_js.py`
- `reference/main/dev/tests/test_template_contract.py`
- `reference/main/docs/design/dashboard-redesign/STATUS.md`
- `reference/main/진행상황.md`
- `samples/AOI_capacity_2026-09-21.html`
- `samples/app.log`
- `validation/example-checks.json`
- `validation/handoff-validation.json`
- `validation/revision-checks.json`
- `SHA256SUMS.txt`: 각 파일의 무결성 확인용 해시
