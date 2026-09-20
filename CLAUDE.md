# AOI Capacity — 작업 규칙

**새 세션은 `진행상황.md` 부터 읽는다.** 거기에 지금 상태·확정된 결정(D01~)·실물로 확인한 사실·남은 일이 있다.
이 파일에는 **규칙**만, `진행상황.md` 에는 **상태**만 적는다(서로 베끼면 따로 낡는다).

Camtek AOI 장비의 BatchReport/WaferInfo.ini 를 읽어 장비별 가동률을 내는 **PyQt6 수집 프로그램**과,
그 결과를 담아 **더블클릭으로 여는 정적 HTML 대시보드** 한 장.
배포는 exe-lite(얇은 런처 exe + python 런타임 + `app/`), 자동 업데이트는 GitHub 커밋 SHA 비교.

## 절대 규칙
1. **NAS 원본은 읽기만 한다.** NAS 경로 아래에는 어떤 파일도 만들거나 바꾸거나 지우지 않는다.
   쓰기(`open(..., "w")`, `os.replace/rename/remove/makedirs`, `shutil.*`)는 `aoi_capacity/collect.py` 의
   `_save_cache` · `write_html` · `_write_csv` 안에만 두고, 각 함수 첫 줄에서 `nas_guard.assert_local` 을 호출한다.
   회귀 가드: `dev/tests/test_nas_guard.py`(정적 AST 검사 + 동적 트립와이어).
2. **수집 허용 장비 밖은 건드리지 않는다.** 허용 목록은 `aoi_capacity/scope.py`
   (현재 30대 전부: `AOI-1`~`AOI-25` + `4F-AOI-01`~`05`. 4대 현장 테스트를 마치고 넓혔다 — 사용자 확정).
   목록에 없는 이름은 여전히 막는다(`AOI-26` 같은 오타·신규 장비). 장비를 새로 추가하려면 이 목록부터 고친다.
   목록을 바꿀 때는 `prefs.migrate` 도 함께 본다 — 이미 저장된 설정 중 **옛 기본값 그대로인 것만** 새 목록으로 옮긴다.
   범위 밖 장비에는 `scandir/stat/isdir/isfile/open` 을 한 번도 부르지 않는다 — 게이트는 "파일을 만지기 전" 단계인
   `devices.py`(`devices_from_rows` · `discover_devices` · `check_rows`)에 있고 수집 루프·CLI·백필·예약·연결 확인이 모두 같은 함수를 쓴다.
   `폴더 *`(자동 탐색)은 제한 중에 **공유를 나열하지 않고** 허용 목록의 이름만 `root/<이름>` 으로 만들어 존재만 확인한다
   (`devices._discover_under`) — 만지는 경로가 전부 허용 장비라 규칙을 지키면서도 `*` 행이 동작한다.
   (이 길이 없던 동안 실장비에서 4층 5대가 3일 내내 한 번도 수집되지 않았다.) 범위 밖 캐시는 **지우지 않고** 출력에서만 뺀다.
   회귀 가드: `dev/tests/test_scope_isolation.py`.
3. **결과 화면은 앱 안에 없다.** PyQt6 창은 **수집 전용**(수집 · 장비 목록 · 설정)이고, 화면은 수집이 만든
   `AOI_capacity.html` 한 장을 사용자가 더블클릭해 브라우저에서 본다. QtWebEngine·로컬 서버·localhost 를 쓰지 않는다.
   그 HTML 은 데이터·CSS·JS 를 모두 품고 **바깥으로 요청을 한 건도 보내지 않는다**(가드: `test_template_contract.py`).
   브라우저가 NAS 를 직접 읽는 경로도 두지 않는다 — 수집은 Python 만 한다. 자동 주기 수집은 없다(수동 실행만, D50).
   화면은 **재설계 구조**(D47, 9/20): 가동률 · Error · 추이 · 리포트 4탭 + 장비/Error/유형·Job 팝업, 라이트 단일. 모델은 아래 '레이아웃' 의 화면 절.
4. **Scanresult 를 재귀 검색하지 않는다.** INI 경로는 `{scan}/{job}/{setup}/{lot}/{wafer}/WaferInfo.ini` 로 계산해 존재만 확인한다.
   `job`·`setup` 의 출처는 **Report 안의 `Job/Setup` 값**이다(파일명이 아니다 — 실장비 516개 중 옛 파일명 규칙에 맞는 건 6개뿐이었다).
   `Job/Setup` 이 없는 옛 형식만 파일명 규칙(`{job}_{4자리}_{lot}_…`)으로 되돌아가고, 그것도 안 맞으면
   **표의 Lot 을 파일명 뒤에서 떼어** job·setup 을 되찾는다(`_job_setup_by_table_lot`).
   실물: AOI-10 은 Setup 이 `SETUP` 이라 4자리 규칙에 걸리지 않아 job 이 비었고, INI 경로가 통째로 어긋나
   9/15 하루에만 8.8시간이 '미가동' 으로 보였다. job 이 비면 경로를 만들지 않는다(빈 칸은 사라져 남의 INI 를 가리킨다). Report·Scanresult 폴더 이름은 장비마다 달라(`Reports`)
   `devices.find_subdir` 이 후보 몇 개의 존재만 확인해 고른다.
   **Scanresult 백업 폴더도 같은 정확 경로로 확인한다**(재귀가 아니라 **루트를 늘리는 것**): 현장은 어느 날짜 기준 그 이전 Scanresult 를 통째로
   `Scanresult_Back up_260918` 같은 폴더로 옮긴다(30대 중 16대, 이름 규칙 제각각 → `Scanresult` 로 시작하는 폴더 전부, `devices.scan_dirs_of`).
   폴더 이름의 날짜가 경계(그 이전 것을 담음)라 배치 시작일로 1순위 폴더를 바로 고르고(`collect.ini_roots_for`, 확인 횟수는 예전과 같은 1번),
   거기 없을 때만 나머지를 본다. 어디에도 없는데 Wafer 폴더에 `MoveResultFlag` 만 있으면 `ini_match="MOVED_ONLY"`(이동만 되고 스캔 안 함, 누락 복구 대상).
   4층 5대는 백업 폴더가 없다. 검증 도구는 조사 결과 읽을 수 있는 INI 가 24,050 → 53,069 개 — **실장비 재수집(`--full`) 전후 비교는 아직 안 했다**.
   **4층은 Job 폴더 이름이 Report 의 Job 값과 다르다**(사용자가 NAS 에서 확인 9/20): Report `2D@RE $7781539A-WUP_0858562PD_0A` ↔ 폴더
   `2D@RE-$7781539A-WUP_0858562PD`(`2D@XX` 뒤 공백→하이픈, 끝 `_0A`/`_0B` 없음). `collect.job_folder_variants` 가 원문 · 하이픈 · 접미 뗌 · 둘 다
   네 후보를 **정확 경로로만** 차례로 본다(원문에서 찾으면 나머지는 열지 않는다). 행의 `job` 은 Report 원문 그대로, 찾은 폴더 이름은 `data_issue` 에만.
5. **시각은 근거가 있을 때만 쓴다.** `WaferInfo.ini` 는 다시 검사하면 **같은 경로에 덮어써진다**(실물 확인:
   AOI-25 9/14 `00NSP049XYG7`). 그래서 옛 Report 행에도 나중 시각이 붙는다 — INI 시각이 그 Report 의
   `Batch Start~End` 밖이면 `ini_match="STALE"` 로 두고 **시간을 쓰지 않는다**(지어내지 않는다).
   같은 INI 시각을 **여러 Report** 가 참조하면(앞 시도 Error 뒤 곧 재검사) 그 시각을 Batch 구간에 **엄격히** 담은 Report 가
   하나뿐일 때 그 Report 만 시간을 갖는다(D37, template `build` 2-pass · `time_basis` 열). 나머지 행은 '시간 미확인 · INI 덮어써짐' —
   사건(Error 건수)·원문·자재 이력은 남기고 시간은 0 기여. 하나가 아니면 소유권 보류(시간 1번, 대표 행 결정적). `BATCH_WINDOW_MARGIN_SEC`(600)은 그대로.
   **시간 미확인은 0초가 아니다** — 화면은 '—' 로 적고 Batch 전체 시간을 Error 시간으로 복사하지 않는다.
   검사된 Wafer 가 하나도 없고 정상 통과도 없는 시도는 `kind="batch"` 행 하나로 만들어 `Batch Start~End` 를
   오류 시간으로 쓰고, 그 배치의 나머지 행(LoadPort/Slot 자리표시 포함)은 `BATCH_FAILED` 로 묶어 따로 세지 않는다.
   ★ D56·D58(9/20, D54 개정): 화면 모델은 장비마다 **1분 단위 시간축에 한 번만** 배정한다 — INI 시각 구간(측정)을 먼저 놓고, Report 의 배치 시작~종료에서 남은 빈 분을
   그 Report 의 **INI 없는 Pass·Error 행들이 똑같이 나눠 갖는다**(Pass 행은 이력대로 Scan/Rescan, Error 행은 Error, Skipped·중단 행은 0). 장비-일 50% 문턱도 3분 표식도 없다.
   이것은 화면 규칙이다 — 수집기는 여전히 시각을 지어내지 않고 행의 `wafer_start_time` 은 비워 둔다. 장비 팝업이 'n장은 INI 가 없어 배치 시각으로 추정' 과 시각 확인 비율을 적는다.
6. **런처 exe 에는 앱 코드가 0줄이다.** `scripts/exe_launcher.py` 는 표준 라이브러리만 import 한다
   (PyInstaller 의 FrozenImporter 가 디스크의 새 코드를 가린다). `hiddenimports=[]`, `pathex=[]`, 앱 패키지는 `excludes`.
7. **`app.new` 는 완성·검증된 트리만.** `app.new.part` 에 만들고 검증 후 rename 한 것이 준비 신호. VERSION 은 스테이징 트리에만 쓴다.
8. **사용자 문구는 `aoi_capacity/i18n/ko.py` 에만.** 위젯·업데이터·워커에 한국어 리터럴을 두지 않는다(로그 메시지는 예외).
9. **긴 작업은 UI 스레드 밖에서.** 코어 함수는 `progress(done, total, phase)` 콜백을 받고, 총량을 모르면 `total<=0`(busy) 로 보고한다.
   NAS 읽기는 **기다리는 시간이 대부분**이라(SMB 왕복 지연) 장비 나열도 Report 읽기도 `read_workers` 개씩
   동시에 한다(`collect._run`, 기본 8 · 1 이면 예전처럼 한 줄로). ★ 스레드는 **읽기만** 한다 —
   캐시·커서·오류 목록에 넣는 일은 전부 메인 스레드가 `plan` 순서대로 하므로 결과가 순서에 좌우되지 않는다.
   회귀 가드: `test_collect_incremental.py` 가 1·2·8·32개로 읽은 결과의 지문과 커서가 같은지 본다.
10. `requirements.txt` 변경은 업데이트가 통째로 실패할 수 있는 지점 — 작업 요약에 반드시 표시하고 `--upgrade` 는 쓰지 않는다. 테스트는 실제 pip 을 절대 실행하지 않는다.

## 레이아웃
- `main.py`(진입), `aoi_capacity/`(앱: `collect.py`, `cli.py`, `devices.py`, `scope.py`, `nas_guard.py`, `i18n/`, `utils/`, `workers/`,
  `ui/` — 수집 UI 만: `pages/collect_page.py`·`devices_page.py`·`settings_page.py`), `scripts/`(런처·빌드), `dev/`(테스트), `docs/`.
- **결과 화면 재설계 프로토타입**은 `docs/design/dashboard-redesign/`(Claude Design handoff 9/19: `RULES.md`·`CHANGELOG.md`·`app/*.dc.html`·`aoi-data.json`).
  DC 런타임(`support.js`) 위에서 도는 **별도 화면**이고 제품 `template.html` 과 계산 규칙이 여러 곳에서 다르다(추정·Error 단위·재스캔 정의·Job/Lot 이름) —
  이식은 D47·D48(진행상황) 대로 진행한다. 데이터 `aoi-data.json` 은 `scripts/make_aoi_data.js`(디자인 세션 원본 그대로, Node, 표준 라이브러리 없음 — 9/20 원본 입력으로
  바이트 동일 재현 확인)가 수집 결과 HTML 의 embedded JSON 에서 만든다. 규칙의 **원본 정의는 이 JS** 다(RULES.md 와 다른 곳은 `scripts/README.md`).
  오프라인 단일 HTML 은 `python dev/tools/design_bundle.py`(표준 라이브러리, 가드 `test_design_bundle.py`)로 만들며 생성물은 커밋하지 않는다.
  `docs/` 는 업데이트 payload 에 들어가지 않는다(`_UPDATE_SKIP_TOP`).
- 코드 받기 도구는 `scripts/update_code.py`(+`update_code.bat`) — 브랜치는 파일 맨 위 `BRANCH` 상수.
  git 폴더면 fetch+ff-only(더티면 중단), zip 폴더면 바뀐 파일만 덮어쓰고 `_backup_…` 을 남긴다(가드: `test_update_code.py`).
- 현장 샘플 수집 도구는 `scripts/collect_sample.py`(+`make_sample.bat`) — 표준 라이브러리만 쓰고 NAS 는 읽기만 하며
  Lot 폴더만 정확 경로로 나열한다(가드: `test_collect_sample.py`). 배포본에도 들어간다(`_UPDATE_KEEP_ONLY`).
  `--all` 은 파일 위쪽 `DEVICE_ROOTS`(전 장비 경로, 사용자가 고치는 값)를 차례로 훑어 **zip 한 장**을 만든다.
  Lot 을 못 읽은 Report 는 **나열하지 않는다** — 그러면 Setup 폴더(= 다른 Lot 전부)를 훑게 된다(실물 AOI-18).
  한 대가 막혀도 계속하고, 맨 위 `요약.json`/`요약.txt` 에 장비별 점검 사실(폴더 이름·Job/Setup 유무·시각 표기·
  읽지 못한 시각 수·Lot 표기·INI 유무)을 남긴다. 이 도구는 사용자가 경로를 직접 지정하는 조사용이라
  `scope.py` 의 수집 범위와는 별개다 — **앱의 수집 경로는 여전히 범위 안 장비만 읽는다**.
- Lot 이름의 작업 표기는 `collect.scan_type` 이 읽는다: `RE`·`RESCAN` → RESCAN(노랑), `REWORK` → REWORK(보라).
  `TEST` → TEST(회색). 토큰이 통째로 맞을 때만 걸린다(`RETURN`·`REX`·`TESTER` 제외).
  **`SRD`·`DIA`·`3D`·`EDGE`·`BUMP`·`PIDS3/5/7/9`·`RDL2/3/4`·`TPST6`·`TPDV`·`WBG`·`STRIP`·`DUMMY`·`RW` 는
  전부 정상 검사**다(사용자 확정 — `RW` 는 확실하지 않아 정상으로 둔다). RESCAN·REWORK 도 가동률에 포함한다.
  **`TEST` 는 분모(24시간)에는 들어가되 분자(실가동)에서만 뺀다**(사용자 확정 — 양산을 위해 돈 게 아니다).
  오류 건수에도 넣지 않는다. 화면에서 사라지지는 않는다: 타임라인에 분홍 점무늬 띠, 제목에 'Test n건 제외',
  Lot 목록에 '시험 · 제외' 표. 빼는 것과 없었던 것은 다르다.
- 행 데이터 계약(`collect.OUT_COLS`, 24열 · `ROW_SCHEMA_VERSION` 5): `kind`("" = Wafer 한 장 · "batch" = 통째로 실패한 시도 · "slot" = 일부 성공한
  배치의 자리표시 행 Error 를 Report 당 1건으로 합성한 사건, D38), `batch_end`,
  `job`·`setup`(Report 안의 `Job/Setup`, 없으면 파일명 규칙), `report`(BatchReport 파일 이름 — 화면에서 그 파일을 다시 여는 근거),
  `cause`(원인 코드들, 규칙 순 세미콜론) · `outcome`(종료 결과) · `norm_status`(호환: 원인이 있으면 첫 원인, 없으면 결과) — **원인과 결과는 다른 축**(D43),
  `scan_type`("" · RESCAN · REWORK · TEST — 겹치면 TEST → RESCAN → REWORK 순), `ini_match`(EXACT · NOT_FOUND · MOVED_ONLY · NO_WAFER_ID · READ_ERROR · STALE · BATCH_FAILED · BATCH · BATCH_SLOT),
  `faults` · `scanned_dice` · `yield`(Report 표의 Faults · Scanned Dice · Yield **원문 그대로**, 합성 행은 빈 값 — 옛 캐시 행에는 없어 `--full` 재수집으로만 채워진다),
  `time_basis`(STRICT_IN_BATCH · TOLERANCE_ONLY · OUTSIDE_BATCH · BATCH_ONLY · MISSING · INVALID · UNKNOWN_BATCH), `slots`(slot 행의 영향 Slot 수).
  열은 **이름으로** 읽는다(고정 인덱스 금지) — 화면(template)은 `status` 원문에서 첫 원인(`causeOf` = 유형)만 쓰고, 합성 행(batch: 배치 시각을 Wafer 시각으로 가진 Error 1건 · slot: 시각 없는 Error)은
  다른 행과 같은 규칙으로 모델에 들어간다(디자인 데이터도 제품 HTML 에서 그대로 뽑았다). 캐시는 `PARSER_VERSION` 이 다르면 `_rederive_rows` 가 NAS 없이 재분류·재합성한다.
  옛 standalone HTML 파일 자체는 옛 JS 를 실행한다 — 최신 규칙으로 보려면 재생성(재수집 또는 `write_html`).
  분류 규칙은 `collect._CAUSE_RULES`(16개, 구체 원인 → 일반 반송 fallback) + `_OUTCOME_RULES`(PASS · USER_CANCELLED · UNKNOWN · USER_ABORT · SKIPPED · ABORTED)이고
  template 의 `CAUSE_RULES`/`OUTCOME_RULES` 와 **정규식 글자까지 같다**(가드: `test_template_contract.py`). 213문구 전수 표 `dev/samples/status_mapping_2026-09-18.tsv` 는 사람이 검토한 고정 fixture 다(`test_status_mapping.py` 가 Python·JS 를 대조).
  ★ 원인 규칙을 전부 먼저 보고 결과를 정한다 — `Failed to read wafer id … Wafer Skipped.` 는 원인 ID_READ_ERROR + 결과 SKIPPED(예전엔 건너뜀에 묻혔다, 192행).
  반송 실패 문구는 `… Batch Aborted. Skipped.` 로 끝나지만 원인 WAFER_LOST 가 먼저라 안전하다 — 회귀 테스트는 그대로 둔다.
  실패 배치의 대표 행·원인은 `_lead_error_row` 가 결정적으로 고른다(근거 행 많은 원인 → 규칙 순 → 원문 사전순, 원인은 자식 행 합집합) — 부모 `Aborted.` 가 자식 Error 를 가리지 않는다(E04).
- `LoadPort A` · `Slot n` 은 Lot·Wafer 가 아니라 자리표시다(`collect._is_placeholder`). Lot 이 비면
  `os.path.join` 에서 그 칸이 사라져 **다른 Lot 의 INI** 를 가리키므로 경로를 아예 만들지 않는다.
  배치 행의 Lot 도 자리표시를 거른 뒤 고른다 — 못 고르면 빈칸으로 두고 화면이 `(Lot 확인 불가)` 라 적는다.
- HTML 에 박는 JSON 은 `collect._embed_rows` 가 접는다 — `POOLED_COLS`(시각 두 열 빼고 전부)를 문자열 풀의
  번호로 바꾼다. 30대 × 90일이면 행이 십수만 개라 접지 않으면 HTML 이 수십 MB 가 된다. template 의 로더가 편다.
  CSV 는 사람이 읽는 파일이라 접지 않는다.
- **결과 화면 모델은 template 의 `buildModel(rows, meta, rules)`** — 프로필이 둘이다(`RULES.profile`). **product(기본, `buildModelV3`, MODEL_VERSION 3)** 가 제품 규칙이고,
  **legacy(`buildModelLegacy`)** 는 `docs/design/dashboard-redesign/scripts/make_aoi_data.js` [원본] 이식으로 네 스위치를 끄면 스크립트와 같은 출력(가드 `test_legacy_profile_equals_the_design_script…`) — 디자인 동일성 근거일 뿐 제품 정답이 아니다.
  공통 도우미(`P`·`lotName`·`jobKey`·`matKey`)는 두 프로필이 같이 쓴다. 규칙을 바꾸면 `MODEL_VERSION` 을 올린다. 열 때마다 원천 행에서 다시 계산한다(저장하지 않는다).
  - **product 알고리즘(D56 · 9/20)**: 장비마다 로드 첫날 00:00 기준 1분 축(`kind` Int8Array)에 ① INI 시각 구간을 Error > Scan > Rescan > Test 순으로 배타 배정(같은 Report 같은 종류의 3분 이하 틈은 이어 칠함)
    ② 각 Report 의 배치 창에서 아직 빈 분을 그 Report 의 INI 없는 Pass·Error 행들이 **똑같이 나눠 가짐**(Pass → 이력대로 Scan/Rescan, Error → Error — D58 '시각 없는 Error = 배치 창의 빈 시간', Skipped·중단은 0, PASS·원인 없는 Report 는 D52 로 ABORTED)
    ③ **Error 를 담은 Report 가 끝난 뒤** 다음 활동까지(관측 종료·그날 자정 중 이른 것까지, D44)를 '에러 후 대기'(Report 안에서 Error 뒤 스캔이 이어지면 그 사이는 스캔)
    ④ 날짜 경계로 잘라(D04) 장비-일 값을 만든다 — 시간은 걸치는 날마다, Error 건수(Lot 단위)·Wafer 수는 시작일에 한 번. **불변식**: 장비-일마다 r+d+t+x+s ≤ den, seg 는 서로 겹치지 않음(30일치 slow 가드).
  - 장비-일 값 `t`: `r` Scan · `d` Rescan · `t` Test · `x` Error 구간 · `s` 에러 후 대기 (전부 분) · `e` Error 건수(Lot 단위) · `w` 이 날 시작한 행 수 · `seg` [시작,끝,종류] (0 Scan · 1 Error · 2 Test · **3 대기** · 4 Rescan, 배타) ·
    `ct` {유형:[건수,Error+대기 분]} · `lots` [job,lot,a,b,w,e,dup,test,rep,causes,st,ba,bb] · `cv` 시각 확인 %(이 날 행 기준) · `bseg`/`be` 배치 구간·점유 · `we` 이 날 마지막 대기의 끝 · `ne` 배치 시각을 받은 Pass 행 수 · `den` 분모(분).
  - 종류: 원인 코드(`CAUSE_RULES` 첫 매치)가 있으면 Error, **Lot 원문에 `TEST` 가 있으면 그 Report 의 행은 전부 Test(D64 — 원인 Error 도 Error 로 세지 않음)**,
    같은 자재의 **앞선 시도의 결과가 PASS 였을 때만** Rescan(D63, 장비 무관), 아니면 Scan. 자재 키 = `jobKey(Job)|Lot 토큰(RE·RESCAN·REWORK·SRD·R 제외)|Wafer ID(영숫자)`.
    **Job 병합(`jobKey`)** 은 구분자·공백·대소문자 · `_Copy` · `LIVE` · 장비별 복사본 · `Test_` 접두 · 끝 4자리 날짜 · `AO`→`A0` 를 묶고 R접두어(RE·R2·R3…)와 단계 번호(PI2/PI3, RDL1~4)는 나눈다(D48-④). 통계에서만 묶고 **표기는 원문**, 표기명 21개는 `JOB_ALIAS`.
  - **Lot 이름은 Report 파일명에서**(`lotName`, D48-⑤): 4자리 설비번호 다음 칸(없으면 날짜 앞 칸), `Setup1_`·`6324_` 접두 제거, 3글자 코드 뒤 꼬리표는 `KEEP`(DIA·2D·3D·EDGE·CENTER·RE·SRD·RESCAN·PCM·DUMMY·SPT)만 남김, 모르는 낱말이 섞이면 원문 그대로.
    product 는 Setup 이 4자리가 아닌 옛 파일명(R2)에서 표의 Lot 이 파일명 줄기의 끝과 같으면 표의 Lot 을 그대로 쓴다(D12, AOI-10 `SETUP_AMD Venice_U-Pad Dummy`).
  - **분모(D57 · D17 개정)**: 지난 날 1440분. **수집한 날(`today` = `meta.generated_iso` 날짜)은 모든 장비의 마지막 기록(관측 종료)** 까지 — 장비마다 다르지 않다. 기록이 없는 장비는 그날 항목이 없어 평균에서 빠진다(0% 로 채우지 않음).
    **가동률 = (r + d) ÷ den**. 평균은 값이 있는 장비만(`S.fleetUtil`). 화면의 '오늘' 은 열람 시계가 아니라 수집 시각이다(D40) — 집계 경로에 `Date.now()`/`new Date()` 가 없다(가드).
  - **D09 로더**: 날짜는 숫자 범위 + 역변환 검사(2월 30일·25시·월 약어 오타 → null, 그 행은 `badRows` 로 세고 버림), `unfold` 는 cols 중복·행 길이·풀 번호 범위를 검사해 예외를 던지고 `loadDemo` 가 오류 패널로 보여 준다(무한 '불러오는 중…' 없음).
  - 화면 쪽 `S.segsOf` 는 모델의 seg 를 그대로 그리고(같은 종류 8분 이하 틈만 시각 병합, 수치 불변) 대기를 다시 계산하지 않는다. 옛 장비-일 추정(`isEst`/`estBar`)은 product 에서 도달 불가(legacy 잔재, P5 에서 정리).
- **화면 용어·색의 단일 출처는 template 의 상수** `RUN·DUP·TEST·ERR·STOP·IDLE·FUTURE` 와 범례(D48-⑦): Scan(진한 파랑) · Rescan(연한 파랑) · Test(보라) · Error(빨강) · 에러 후 대기(연한 빨강) · 대기(회색).
  옛 용어(가동·중복스캔·재스캔·Rework·중단·미가동·정지)를 화면 JS 에 다시 쓰지 않는다(가드 `test_screen_terms…`). 원본 상태 문구·Job·Report 파일명은 바꾸지 않는다.
- **화면 구조**(`AOI-Dashboard.dc.html` 의 로직을 순수 JS 렌더로 — React·DC 런타임 없음, `render()` 가 `#app` 을 통째로 다시 그리고 `data-h` 핸들러 표를 위임 클릭으로 받는다):
  가동률(카드 3 · 층 필터 · 정렬 · 24시간 막대 목록) → **장비 팝업**(통계 6 · 막대 · Lot 이름표 지시선 · 선택 Lot 원문 · **Report 열기**) ↔ **Error 상세 팝업**(언제 났나 · 유형별 · 최근 21일 · Lot 별, 유형/Job 팝업에서 오면 필터 칩, D51) ·
  Error(기간 · 층 · 지표 → 날짜별 → 유형별·장비별·Job별 → 유형/Job 팝업) · 추이(일·주·월 + 히트맵, 전 기간 대비 없음) · 리포트(D49: 표기명 21개, 배치시간 = Report 배치 시작~종료 회귀, 표본 5개 미만 생략).
  살펴볼 장비 = 가동률 40% 미만 또는 Error 3건 이상(`PROPS`). 팝업은 ESC 로 닫힌다(Error 팝업 → 장비 팝업 → 유형/Job 팝업 순).
- **Report 열기**는 장비 팝업의 선택 Lot 에서만(`reportUrl` · `openReport`). 경로는 `meta.devices[].note` + `report_dir` + `report` 로만 만들고 드라이브 문자와 UNC(`\\10.x`) 를 모두 다룬다.
  여는 주체는 사람이 연 그 탭이지 이 화면이 아니다 — 화면은 여전히 바깥으로 요청을 한 건도 보내지 않는다. 수집 상태 칩(`collectChip`: 수집 실패 · 일부 누락)과 '수집 범위 / 수집 안 함' 은 `meta` 에서 그린다. **사본 저장**(`saveHtml`)은 수집기가 준 열·풀 구조 그대로 다시 접는다.
- 추이 화면에 **전 기간 대비(전주·전월·전일)는 두지 않는다**(사용자 확정, 가드: `test_no_period_over_period_comparison_anywhere`). 선택한 기간의 값만 보여 준다.
- 결과 HTML 의 위치·생성은 `utils/results.py` 한 곳에서만 묻는다(`html_path` · `ensure_html` · `last_collect_time`).
- 장비는 `id`(정규화 경로, 캐시 커서·집계 키) · `path` · `name`(표시명 `AOI-25` · `4F-AOI-01`) · `aliases`(옛 표시명) 로 나눠 다룬다.
  표시명을 바꿔도 이력이 갈라지지 않는다. 홈 정렬은 `devices.sort_key`(= template 의 `cmpDev`) — AOI-1…AOI-25 뒤에 4F-AOI-01….
- 시각 테마의 단일 출처는 `aoi_capacity/ui/assets/template.html` 의 `:root` 토큰 두 블록(dark · light). `ui/theme.py` 는 그 값을 그대로 쓴다(가드: `test_theme.py`).
  결과 화면은 라이트 단일(D48-⑥, `<html data-theme="light">`)이고 dark 블록은 수집 창의 다크 모드 값이다. CSS 주석에 `:root{` 를 적지 않는다(파서가 첫 블록으로 오인한다 — 실측).
- 사용자 데이터는 `%LOCALAPPDATA%\AOI_Capacity`(`utils/paths.data_root()`), 절대 `app/` 안이 아니다(업데이트가 `app/` 를 통째로 교체).

## 빌드·업데이트
- `python scripts\build.py exe-lite` → `dist/AOI_Capacity_Lite/` (런처 exe + `python/` + `app/`, `.deps_installed` **없음**), `make_release_zip.py --lite` 가 검증 통과 시에만 zip 을 만든다.
- `requirements.txt` 는 PyQt6 와 truststore 뿐이다(QtWebEngine 제거 — 결과 화면이 브라우저로 옮겨갔다).
- `utils/updater.py`: 기본 브랜치 SHA 비교 → 브랜치 zip → `app.new.part` 스테이징 → `_verify_staged`(필수 파일, template `__DATA__`, style.qss 렌더) → `app.new` rename. `_UPDATE_KEEP_ONLY` 의 이름은 실재해야 한다(`test_update_payload.py`).
- `updater.DEFAULT_BRANCH` 는 오프라인 폴백 — GitHub 기본 브랜치가 바뀌면 함께 갱신한다.

## 테스트
`QT_QPA_PLATFORM=offscreen python -m pytest -q` (빠른 확인: `-m "not ui and not slow"`, `slow` = 30일치 샘플 전수). PyQt6 가 없는 환경에서는 ui 테스트가 skip 된다.
보관 샘플에서 행을 꺼낼 때는 `dev/tests/sample_rows.py`(이름 기반 열 복원·풀 검증), 집계 수치를 잴 때는 `python dev/tools/measure.py <샘플> [--design-rules]`(새 모델의 장비-일 합과 일별 평균 가동률),
단계별 전후는 `dev/samples/ledger_2026-09-18.md` 에 적는다 — 예상치에 맞추어 규칙·테스트를 고치지 않는다.
테스트는 실제 pip·네트워크를 절대 실행하지 않는다(`test_updater.py` 의 autouse 가드). 유일한 예외는 `test_dashboard_js.py` —
`dev/tests/js_harness.js` 가 template 의 스크립트를 **로컬 Node(vm, DOM 대역)** 에서 실행해 `buildModel` 을 검사한다(네트워크·파일 쓰기 없음, Node 가 없으면 skip):
slow 한 개가 30일치로 디자인 스크립트와의 동일성을, 나머지가 D48 규칙을 작은 fixture 로 본다. `test_status_mapping.py` 는 하네스의 classify 모드로 Python·JS 분류를 대조한다.
문자열 검사(`test_template_contract.py`)만으로 화면 로직을 '완료' 라고 하지 않는다. 화면은 Chromium(Playwright, `/opt/pw-browsers`)으로 클릭 경로를 실측한다.

## 커밋
한국어로 "무엇을·왜". PR 은 요청받을 때만. 저장소 산출물에 내부 모델 식별자를 남기지 않는다.

**코드를 고치는 커밋에는 `진행상황.md` 를 반드시 함께 넣는다**(세션이 바뀌어도 이어서 일할 수 있게).
커밋 직전에 그 파일에서 고칠 것:
1. `## 작업 기록` **맨 위**에 한 줄 — `- <날짜> <커밋> — 무엇을·왜`. 지금 만드는 커밋의 해시는 아직
   없으니 `(작업 중)` 으로 적고, **다음 커밋 때 그 자리를 채우면서** 자기 항목을 새로 올린다
   (`--amend` 로 채우면 해시가 또 바뀌어 헛돈다).
2. 달라진 것만 골라: `## 지금 상태` 표 · `## 확정된 결정`(사용자가 새로 정해 준 것) ·
   `## 실물로 확인한 사실`(근거가 생긴 것) · `## 다음 할 일` · `## 확인 대기`.
3. 맨 위 `마지막 갱신` 날짜.

가드: `dev/tests/test_progress_doc.py` 가 형식과 **코드와의 어긋남**(수집 범위 대수·결정 번호 연속성 등)을 본다.
`git config core.hooksPath dev/hooks` 를 한 번 해 두면 `진행상황.md` 없이 코드를 커밋할 때 커밋이 멈춘다
(정말 필요하면 `git commit --no-verify`).
