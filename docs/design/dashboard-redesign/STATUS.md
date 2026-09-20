# 이 폴더의 지금 상태 (2026-09-20)

**이식은 끝났다.** 이 폴더의 프로토타입은 제품 `aoi_capacity/ui/assets/template.html` 로 옮겨졌고(D47·D48, 9/20),
지금은 **참고 자료와 동일성 근거**로만 남아 있다. 여기 문서의 규칙을 그대로 제품에 되살리지 않는다 —
**제품의 현재 규칙은 `CLAUDE.md` 의 '레이아웃' 절**(결과 화면 모델 · product 알고리즘 D56)이고, 확정 결정 번호는 `진행상황.md` 에 있다.

## 아직 살아 있는 것 (코드·테스트가 읽는다)

| 파일 | 누가 쓰나 | 역할 |
|---|---|---|
| `scripts/make_aoi_data.js` | `dev/tests/test_dashboard_js.py`(legacy 프로필 동일성, slow) · `test_design_extract.py` · `test_template_contract.py`(`CR` 정규식 = `collect._CAUSE_RULES`) | **legacy 프로필의 oracle**. `[원본]` 블록은 디자인 세션이 실제로 돌린 코드 그대로 — 고치지 않는다(고치면 동일성 근거가 사라진다) |
| `scripts/job_alias.js` | 표기명 21개의 원본 표(제품 `JOB_ALIAS` 와 같은 21개) | 고치지 않는다 |
| `scripts/build_offline.js` · `scripts/README.md` | 디자인 세션이 준 설명(원문). 바이트 수 2,246,732 는 그 세션의 보고값이고 저장소의 `app/aoi-data.json` 은 2,246,736 bytes 다(`test_design_extract.py` docstring) | 기록 |
| `app/AOI-Dashboard.dc.html` · `app/support.js` · `app/aoi-data.json` · `offline_shell.html` · `offline_shell.json` | `dev/tools/design_bundle.py`(오프라인 단일 HTML 생성, 생성물은 커밋하지 않음) · `test_design_bundle.py` | 프로토타입 본체와 DC 런타임. 제품 화면이 아니다 |
| `app/AOI-Dashboard-offline.dc.html` | `design_bundle.py` 의 출력이자 추적 파일(`test_design_bundle.py` 가 지문으로 지킨다) | 생성물 |
| `data/*.txt` | `진행상황.md` '실물로 확인한 사실'(백업 폴더 조사 4건) | 조사 기록 — 스크립트는 파일로 남은 적이 없다(`scripts/README.md`) |
| `RULES.md` · `CHANGELOG.md` · `HANDOFF.md` · `github.md` | 사람 | **역사 문서**. 9/19 디자인 세션 시점의 규칙·경위. 제품과 다른 곳은 아래 표 |

## 보관으로 옮긴 것 (`archive/design/`, D62)

`PROMPT.md`(할 일 4가지 — 전부 반영) · `PROMPT_extract-script.md`(답을 받은 요청문) · `patch/collector-backup-lookup.md`(커밋 `6b4a114` 로 적용) ·
`app/Err-Popup-A.dc.html`(반영된 시안) · `app/AOI-4 해결 제안.dc.html` + `app/aoi-recovery.json`(적용된 제안서와 검증 결과). 원본 지문은 `archive/SHA256SUMS`.

## 디자인 규칙과 제품 규칙이 다른 곳

디자인 문서(`RULES.md` · `github.md` · `make_aoi_data.js`)를 읽을 때 헷갈리는 곳만 적는다. **오른쪽이 제품이고, 근거는 `CLAUDE.md` 와 결정 번호**다.

| 항목 | 디자인(9/19, `make_aoi_data.js` · `RULES.md`) | 제품(`template.html` product 프로필, MODEL_VERSION 3) | 결정 |
|---|---|---|---|
| INI 없는 행의 시간 | 장비-일의 시각 확인 비율이 50% 미만이면 그 날 전체를 Report 배치 시각으로 **추정**(`isEst`, 화면이 판정) | 장비-일 판정 없음. 장비마다 1분 축에 INI 구간을 먼저 놓고, 각 Report 배치 창의 **빈 분을 INI 없는 Pass·Error 행이 똑같이 나눠 가진다**(팝업에 'n장은 배치 시각으로 추정') | D54 → D56·D58 |
| Error 후 대기 | Error 구간 + 다음 Wafer 까지의 공백, **최대 240분** | **Error 를 담은 Report 가 끝난 뒤** 다음 활동 · 관측 종료 · 그날 자정 중 이른 것까지, 상한 없음 | D44 · D56③ |
| 하루 분모 | 00:00~24:00 고정(`Math.min(1440, …)`) | 지난 날 1440분, **수집한 날은 모든 장비의 마지막 기록까지**(장비마다 다르지 않음). '오늘' 은 수집 시각의 날짜 | D57 · D40 |
| Test Lot | 행 단위(`/TEST/i.test(lot)`) | Lot 원문에 `TEST` 가 있으면 **그 Report 의 행 전부 Test**, 그 안의 원인 Error 도 Error 로 세지 않음 | D64 |
| Rescan | 앞선 시도가 Pass → Rescan, Error → 정상 Scan | 같다 — **앞선 시도의 결과가 PASS 였을 때만** Rescan(Skipped·중단 뒤는 Scan), 장비 무관 | D63 |
| PASS 없이 중단만 남은 Report | 시간 0 | **ABORTED Error** 로 세고 그 뒤를 대기로 | D52 |
| 날짜 파싱 | JS `Date` 자동 보정(2월 30일 → 3월 2일) | 숫자 범위 + 역변환 검사, 틀리면 그 행은 `badRows` 로 세고 버림 | D09 |
| 자정을 넘는 구간 | — | 날짜 경계로 잘라 시간은 두 날에, Error 건수·Wafer 수는 시작일에 한 번 | D04 |
| 리포트 탭 | 이름 '리포트'. 표본 제외 = Error · 중단 · 5장 미만(Test 포함) | 이름 **'TB500 · Kendall'**. 배치시간 = Report 배치 시작~종료 회귀, 표본 5개 미만 생략, 제외 = 원인 Error 있는 Report · 5장 미만 · 배치 시각 없음. 평균 fault 는 `faults` 열이 있는 행의 장당 평균 | D49 · D59 · D08 |
| `faults` · `scanned_dice` · `yield` | 입력에 없음(RULES '데이터 출처') | 수집기가 24열에 담는다(`ROW_SCHEMA_VERSION` 5) — 옛 캐시 행은 `--rebuild-all` 로 다시 읽어야 채워진다 | — |
| 가동률 40% · Error 3건 문턱 | Tweaks 로 조절 | `PROPS` 기본값, `meta.dashboard_settings` 의 같은 이름 숫자가 있으면 그것으로 | D14 |

같은 것: 라이트 단일 테마 · 용어(Scan · Rescan · Test · Error · 에러 후 대기 · 대기) · Error 건수는 Lot 단위 · Job 병합(`jobKey`) · Lot 이름(`lotName`) · 표기명 21개 · 유형 = `CAUSE_RULES` 첫 원인.
legacy 프로필(`buildModelLegacy`, `RULES.profile==="legacy"` + 네 스위치 끔)은 위 스크립트와 장비-일 전부 같아야 한다 — 이식이 규칙을 새지 않았다는 근거일 뿐 제품 정답이 아니다.
