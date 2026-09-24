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
   화면은 **재설계 구조**(D47, 9/20): 가동률 · Error · 추이 · TB500 · Kendall(D59) 4탭 + 장비/Error/유형·Job 팝업, 라이트 단일. 모델은 아래 '레이아웃' 의 화면 절.
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
   Scanresult 폴더 비교는 **Windows 경로 의미**(`devices.dir_key/same_dir` = ntpath normcase+normpath)로 한다 — `ScanResult`·`Scanresult`·`SCANRESULT`·끝 구분자 차이는 한 폴더이고
   `scan_dirs_of` 맨 앞은 나열된 실제 철자다. 지금 쓰는 폴더가 '백업' 으로 한 번 더 잡히면 없는 INI 마다 확인이 두 배가 된다(C05, 가드 `test_devices_csv.py`).
   4층 5대는 백업 폴더가 없다. 검증 도구는 조사 결과 읽을 수 있는 INI 가 24,050 → 53,069 개 — **실장비 재수집(`--rebuild-all`) 전후 비교는 아직 안 했다**.
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
   가드 `test_no_hardcoded_korean.py` 는 `cli.py`·`utils/config.py` 도 본다 — CLI 도움말·출력은 ko.py `CLI_*`, 설정 검사 문구는 `CFG_*`(C12·C13).
   행 데이터의 `data_issue` 자유 문장도 새 행에는 쓰지 않는다 — 코드(`issue_codes`)만 캐시에 두고 문장은 출력 때 `ko.ISSUE_TEXTS` 로 만든다(아래 행 계약).
9. **긴 작업은 UI 스레드 밖에서.** 코어 함수는 `progress(done, total, phase)` 콜백을 받고, 총량을 모르면 `total<=0`(busy) 로 보고한다.
   NAS 읽기는 **기다리는 시간이 대부분**이라(SMB 왕복 지연) 장비 나열도 Report 읽기도 **NAS 마다** `read_workers` 개씩
   동시에 한다(`collect._run(group=nas_group)`, 기본 8 · 1 이면 예전처럼 한 줄로 · 전체 `MAX_READ_THREADS` 64 상한). NAS 는 경로 글자로만 가른다 —
   UNC 는 호스트, 드라이브 문자는 연결된 UNC 의 호스트(모르면 문자) — 드라이브 X·M·V·P·Y·I 가 같은 NAS 면 OS 가 알려 준 호스트로 한 묶음이 되어 예전과 같다(서로 다른 NAS 인지는 확인 대기, `net use`) —
   장비 순서로 줄 세우면 스레드가 한 NAS 에 몰렸다(9/18 30일치 실측 읽기 79분). 풀은 하나, 한 작업이 예외면 새 작업을 꺼내지 않고 입력 순서로 가장 앞선 예외를 던진다. ★ 스레드는 **읽기만** 한다 —
   캐시·커서·오류 목록에 넣는 일은 전부 메인 스레드가 `plan` 순서대로 하므로 결과가 순서에 좌우되지 않는다.
   회귀 가드: `test_collect_incremental.py` 가 1·2·8·32개로 읽은 결과의 지문과 커서가 같은지 본다.
   장비 확인(Report/Scanresult 폴더 · 백업 나열 · 연결 확인)도 `devices._pmap` 으로 `read_workers` 개씩 동시에 하되 **범위 게이트를 지난 장비만**, 결과·로그는 입력 순서,
   취소는 새 작업 제출만 멈춘다(SMB 호출을 중간에 끊는다고 주장하지 않는다). 동시성 예산은 하나 — Report 읽기 단계 안에 풀을 겹치지 않는다(C08, 가드 `test_parallel_device_check_stays_in_scope_and_matches_serial`).
10. `requirements.txt` 변경은 업데이트가 통째로 실패할 수 있는 지점 — 작업 요약에 반드시 표시하고 `--upgrade` 는 쓰지 않는다. 테스트는 실제 pip 을 절대 실행하지 않는다.

## 레이아웃
- `main.py`(진입), `aoi_capacity/`(앱: `collect.py`, `cli.py`, `devices.py`, `scope.py`, `nas_guard.py`, `i18n/`, `utils/`, `workers/`,
  `ui/` — 수집 UI 만: `pages/collect_page.py`·`devices_page.py`·`settings_page.py`), `scripts/`(런처·빌드), `dev/`(테스트), `docs/`.
- **결과 화면 재설계 프로토타입**은 `docs/design/dashboard-redesign/`(Claude Design handoff 9/19: `RULES.md`·`CHANGELOG.md`·`app/*.dc.html`·`aoi-data.json`).
  DC 런타임(`support.js`) 위에서 도는 **별도 화면**이고 제품 `template.html` 과 계산 규칙이 여러 곳에서 다르다(추정·Error 단위·재스캔 정의·Job/Lot 이름) —
  **이식은 9/20 에 끝났다**(D47~D59). 제품 규칙의 정본은 아래 모델 절이고, 원 디자인과의 차이표·살아 있는 파일 목록은 `docs/design/dashboard-redesign/STATUS.md`(S07).
  끝난 PROMPT·patch·시안은 `archive/design/` 으로 옮겼다(D62, `archive/SHA256SUMS` · 가드 `test_archive.py`). 데이터 `aoi-data.json` 은 `scripts/make_aoi_data.js`(디자인 세션 원본 그대로, Node, 표준 라이브러리 없음 — 9/20 원본 입력으로
  바이트 동일 재현 확인)가 수집 결과 HTML 의 embedded JSON 에서 만든다. 규칙의 **원본 정의는 이 JS** 다(RULES.md 와 다른 곳은 `scripts/README.md`).
  오프라인 단일 HTML 은 `python dev/tools/design_bundle.py`(표준 라이브러리, 가드 `test_design_bundle.py`)로 만들며 생성물은 커밋하지 않는다.
  업데이트 payload 는 **허용 목록**(`updater._UPDATE_TOP_ALLOW`: `main.py` · `requirements.txt` · `aoi_capacity` · `scripts`(`_UPDATE_KEEP_ONLY` 로 다시 거름) + 생성한 `VERSION`)뿐이다 — `docs/`·`dev/`·`진행상황.md` 는 들어가지 않는다(S01, 가드 `test_update_payload.py`).
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
- 행 데이터 계약(`collect.OUT_COLS`, **25열 · `ROW_SCHEMA_VERSION` 6**): `kind`("" = Wafer 한 장 · "batch" = 통째로 실패한 시도 · "slot" = 일부 성공한
  배치의 자리표시 행 Error 를 Report 당 1건으로 합성한 사건, D38), `batch_end`,
  `job`·`setup`(Report 안의 `Job/Setup`, 없으면 파일명 규칙), `report`(BatchReport 파일 이름 — 화면에서 그 파일을 다시 여는 근거),
  `cause`(원인 코드들, 규칙 순 세미콜론) · `outcome`(종료 결과) · `norm_status`(호환: 원인이 있으면 첫 원인, 없으면 결과) — **원인과 결과는 다른 축**(D43),
  `scan_type`("" · RESCAN · REWORK · TEST — 겹치면 TEST → RESCAN → REWORK 순), `ini_match`(EXACT · NOT_FOUND · MOVED_ONLY · NO_WAFER_ID · READ_ERROR · STALE · BATCH_FAILED · BATCH · BATCH_SLOT),
  `faults` · `scanned_dice` · `yield`(Report 표의 Faults · Scanned Dice · Yield **원문 그대로**, 합성 행은 빈 값 — 옛 캐시 행에는 없어 `--rebuild-all`(또는 `--refresh-window N`) 재수집으로만 채워진다),
  `time_basis`(STRICT_IN_BATCH · TOLERANCE_ONLY · OUTSIDE_BATCH · BATCH_ONLY · MISSING · INVALID · UNKNOWN_BATCH), `slots`(slot 행의 영향 Slot 수),
  `issue_codes`(C12: `CODE` 또는 `CODE=인자,인자` 를 `;` 로 이은 목록, `collect.ISSUE_CODES` 16개 — 인자 안의 `% ; = ,` 만 퍼센트 이스케이프, 경로·한글은 그대로).
  **캐시에는 코드만** 두고 사람 문장(`data_issue`)은 `collect()` 끝의 `render_issue_rows` 가 `ko.ISSUE_TEXTS` 로 채운 사본에만 있다(캐시 행 불변) — 문구를 고쳐도 재수집이 필요 없다.
  옛 캐시 행의 `data_issue` 자유 문장은 파싱하지 않고 그대로 나간다(옛·새 혼재 허용, 가드 `test_issue_codes.py`). `write_html`/`_write_csv` 를 캐시 원본 행으로 직접 부르면 문장이 비어 있다.
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
  - 화면 쪽 `S.segsOf` 는 모델의 seg 를 그대로 그리고(같은 종류 8분 이하 틈만 시각 병합, 수치 불변) 대기를 다시 계산하지 않는다. 옛 장비-일 추정(`isEst`/`estBar`)은 P4 에서 지웠다(가드 `test_removed_features_stay_removed`).
- **화면 용어·색의 단일 출처는 template 의 상수** `RUN·DUP·TEST·ERR·STOP·IDLE·FUTURE` 와 범례(D48-⑦): Scan(진한 파랑) · Rescan(연한 파랑) · Test(보라) · Error(빨강) · 에러 후 대기(연한 빨강) · 대기(회색).
  옛 용어(가동·중복스캔·재스캔·Rework·중단·미가동·정지)를 화면 JS 에 다시 쓰지 않는다(가드 `test_screen_terms…`). 원본 상태 문구·Job·Report 파일명은 바꾸지 않는다.
- **화면 구조**(`AOI-Dashboard.dc.html` 의 로직을 순수 JS 렌더로 — React·DC 런타임 없음, `render()` 는 HTML 문자열을 만들어 **키 있는 morph**(`morphChildren`, `data-key`)로 바뀐 노드만 손댄다 — innerHTML 통째 교체는 깜박임·스크롤 튐·포커스 상실의 근원이었다(현장 보고 9/20). `data-h` 핸들러 표는 위임 클릭):
  **전환(9/20, impeccable animate 플레이북 — 상태 150~300ms · 레이아웃/오버레이 300~500ms · `cubic-bezier(.16,1,.3,1)`, 나가는 것은 들어오는 것보다 빠르게)**: 뷰가 바뀌면 옛 `<main>` 은 제자리에서 사라지고 새 것이 올라오며 나타난다,
  `data-anim` 컨테이너의 키 있는 자식은 **GSAP Flip**(`Flip.getState` → morph → `Flip.from`, 자리 이동을 transform 으로 되감기)으로 움직이고 새 자식은 `gsap.fromTo` 로 나타나며 빠진 자식은 제자리에서 사라진 뒤 제거된다,
  팝업(`.ov`)은 **animate.css** `fadeIn`/`fadeOut` + 대화상자 GSAP 살짝 떠오름. **라이브러리는 파일 안에 인라인**(`<script id="vendor">`: GSAP 3.15 + Flip 플러그인, GreenSock 표준 무료 라이선스 · `<style>` 안 animate.css 4.1.1 일부, Hippocratic 2.1 — 머리말 원문 유지, 사용자 요청 9/20)
  — HTML 은 바깥 요청 0건이라 CDN 은 쓸 수 없고, 가드 `test_no_network_use_at_all` 은 vendor 블록·라이선스 머리말을 뺀 나머지에서 URL 을 찾고 `test_vendor_block_makes_no_requests_either` 가 vendor 안의 주소를 허용 목록(gsap.com · w3.org 네임스페이스)으로 검사한다.
  **lottie-web(lottie_light 5.13, MIT)** 도 인라인 — 자산은 손으로 쓴 JSON 둘(`LOTTIE.scan` 브랜드의 웨이퍼 스캔 표식 · `LOTTIE.check` 'Error 없음' 의 체크), `animationData` 만 넘기고 `path` 로 파일을 읽지 않는다(가드가 확인). Lottie 가 그린 SVG 는 `data-static` 컨테이너라 morph 가 자식을 건드리지 않는다.
  **3차 연출(9/20 밤)**: 카드 숫자는 값이 바뀔 때만 이전 값에서 카운트업(`cnt()` · `data-count`, GSAP), 24시간 막대는 새로 그려지거나 다른 날이 되면 왼쪽→오른쪽 sweep(`data-bar`, clip-path), 뷰가 처음 들어올 때 막대 그래프는 바닥에서 자라고 히트맵은 차례로 켜진다(`enterView`),
  날짜를 넘기면 라벨이 방향대로 미끄러진다(`slideDay`), 팝업이 열리면 무대(`.stage.behind`)는 밝기만 아주 살짝 낮아진다(움직이지 않는다 — 9/21, 물러남 scale 이 '뒷배경 재생성' 으로 보였다), 토스트·필터 칩·선택 Lot 패널은 animate.css(fadeInUp/Down).
  **4차(9/20 밤)**: 내비 표시자가 켜진 탭 아래로 움직인다(`navInd` — 9/24 부터 **물리 모델**: 질량 10개를 이웃 스프링(k 1500 · c 70)으로 이은 사슬을 **가는 방향의 앞 끝만** 스프링-감쇠(k 450 · c 20, 힘 상한 45000 px/s²)로 끌고 모든 질량에 바닥 마찰(−14·v) — 앞 끝이 먼저 가고 뒤가 딸려 와 **움직이는 동안 늘어나고(먼 탭 20~35%) 도착하며 줄어든다**(도착 뒤 폭이 느는 양 ≤ 3.5px). 휴지 길이는 앞 끝이 절반 갈 때까지 옛 폭→새 폭(늦게 바꾸면 도착해서 넓어진다 — 두 질량 모델과 이 모델 첫 시도가 그랬다, 실측). 부피 보존으로 두께 0.92~1.08, 가드 `test_tab_indicator_moves_like_a_body_dragged_by_its_front`. 박스는 `data-static` 세 조각(끝 · 가운데 scaleX · 끝, 둥근 모서리 유지)이고 궤적을 미리 계산해 **WAAPI transform(합성 스레드)** 으로 돌린다(`navGo` — 새 화면을 그리느라 메인 스레드가 막혀도 끊기지 않는다). 탭을 누르면 `navNow` 가 글자색·박스를 먼저 옮기고 새 화면은 두 프레임 뒤(브라우저 테스트는 `main[data-key="view:…"]` 를 기다린다). 연달아 누르면 표본 보간한 질량마다의 위치·속도에서 다시 계산, 창 크기 변경은 즉시 제자리), 카드는 들어올 때 차례로 떠오르고(`enterView` — 뷰·키 바뀐 차트·팝업 어디든), 홈 행의 %·Error 건수도 카운트업, 리포트 행 펼침·Job 이름 묶음은 높이 0 에서 열린다(`data-reveal`),
  장비 팝업 이름표는 다른 장비·날짜가 되면 차례로 내려오고 Error 팝업 타임라인 표식은 차례로 선다(`data-sig`), 로더는 Lottie 스캔 표식을 한 프레임 먼저 그린 뒤 다음 틱에 해석·계산한다(`loadDemo` — 브라우저 테스트는 `main[data-key^="view:"]` 를 기다린다). 하네스(Node)에는 gsap·lottie 가 없어 `canAnim()` false → morph 만 한다. `prefers-reduced-motion` 이면 이동 없이 opacity 만(Lottie 는 마지막 프레임 정지). 막대 폭·높이의 값 변화는 CSS transition(`.hbar i` · `.chart .f`). **팝업 덱**(`state.stack`, `pushTop`·`CLOSE`·`bringToFront`): 팝업 위에 팝업을 열면 아래 것은 닫히지 않고 **새 팝업의 왼쪽 뒤로** 물러난다(`behind`, 깊이 `--d` 마다 약 130px 씩 더 왼쪽 — `layoutDeck` 이 폭 차이를 보정해 `--shift` 를 준다 — rotateY·축소·어둡게).
  맨 위 팝업의 scrim 을 **뒤 카드가 보이는 자리에서 누르면 그 카드가 앞으로 온다**(`behindAt` — transform 이 반영된 rect 로 기하 판정, 호버하면 밝아지고 커서가 손가락), 빈 자리를 누르면 맨 위가 닫힌다. 왼쪽 위 **스택 바**(`stackbarHtml`)가 열린 팝업을 순서대로 칩으로 보여 주고 칩을 누르면 그 팝업이 앞으로(키보드로도). 맨 위만 살아 있고(inert) ESC 는 맨 위만 닫는다. 860px 아래에서는 옆으로 밀지 않고 위로만 살짝.
  **5차(9/20 밤, 색·손맛)**: 데이터 색은 dataviz 규칙 — 막대 색(`background-color`)은 `RUN·ERR·HEAT` 에서만 오고 CSS 가 위가 밝고 아래가 살짝 어두운 한 겹(`background-image`)만 얹는다(`.chart .f` · `.hbar i` · `.tline i` · `.gloss`, 24시간 막대는 `S.tail` 이 두 번째 gradient 층으로) — 그래서 막대 색은 inline `background:` 가 아니라 `background-color:` 로 쓴다(shorthand 는 겹을 지운다).
  히트맵 `HEAT` 는 한 색조(RUN) 6단 OKLCH 램프(밝기 단조, `dev` 스크래치 `ramp.js` 로 생성), 추이 막대는 기준 미만만 상태색(ERR) 나머지 RUN(명목 막대에 값 램프 금지), 24시간 막대의 색 구간 사이는 1px 표면 간격(0.6% 이상 구간만, 대기 제외).
  움직임: 탭 전환은 내비 순서 방향(`VIEWS`·`state.viewDir`)으로 가로 미끄러짐(`.stage{overflow-x:clip}` 이 가로 스크롤을 막는다), 히트맵은 격자 물결(`stagger.grid`), `:active` 축소 · 호버 반응 · 주의 점 맥동 3회 · 앞으로 온 팝업 `.dlg.pop`.
  ★ **틀은 그대로, 내용만 바뀐다**(사용자 요청 9/20 밤·9/21 — "버튼마다 전체 창이 재생성되는 것 같다", "탭 바 전체가 흔들린다", "팝업이 뜨면 뒷배경이 재생성되는 느낌"): 계측(`dev` 스크래치 `pw_probe*.js`·`pw_flip.js`)으로 header·main·패널·키 있는 행은 클릭마다 같은 노드였고,
  진짜 원인은 **`#app` 루트와 `.stage` 에도 Flip 이 걸려** 클릭마다 header·본문·바닥글에 1~4px 의 translate 트윈이 붙던 것(af7f35e 까지)과 화면 전체가 되감는 연출이었다.
  규칙: **Flip 은 목록 컨테이너에서, 키 순서가 바뀌었거나 행이 들고났을 때만, 실제로 3px 이상 움직인 행에만**(`flipAfter` — `before.order` 비교 · rect 비교). 루트·무대는 `data-anim="el"`(들고남만 — 팝업 fadeIn/Out · main 의 방향 등장). 행 안의 내용만 바뀐 렌더(리포트 펼침 · 값 갱신 · 팝업 안 장비 이동)에는 어떤 노드에도 transform 을 주지 않는다. `state.viewDir` 은 렌더 끝에 0 으로.
  **전수 감사(9/21, `pw_audit.js` — 클릭 42가지마다 도는 CSS transition/animation 과 GSAP 트윈을 대상별로 센다)** 로 고친 것: 내비 표시자는 자리가 바뀔 때만 트윈, 이름표(`.callout`)·히트맵 칸에는 transform transition 을 두지 않는다(GSAP 등장 뒤 `clearProps` 가 transition 을 한 번 더 일으켜 두 번 움직였다 — 히트맵 등장은 칸 330개가 아니라 **행 단위** opacity),
  대화상자 등장·퇴장은 CSS 키프레임(`.dlg.in/.out` — `.dlg` 의 덱 transform transition 과 GSAP inline transform 이 겹쳤다), 스택 바 칩 등장 없음, 주의 점 맥동 1회.
  **morph 의 형제 맞추기**: 키 없는 형제는 같은 태그를 **몇 칸 앞까지 찾아** 맞춘다 — 조건부 `<p>` 하나가 사라지면 뒤 형제 전부가 재생성되던 것이 팝업 안 이동의 번쩍임이었다. 팝업 안의 `.dlg` 와 `.stackbar` 는 `data-key`(스택 순서가 바뀔 때 stackbar 자리에 dlg 가 맞춰져 대화상자가 통째로 다시 만들어졌다). 계측: 팝업 안 장비 이동·Lot 필터에 새 노드 0.
  그래서 클릭마다 다시 도는 연출은 두지 않는다: 카운트업은 `.cards` 안에서 값이 바뀔 때만(행 숫자는 즉시, 처음 나타날 때 0 부터 세지 않음) — 예외: **Error 탭 세 목록(유형별·장비별·Job별)** 은 줄을 순위 칸(`data-key="slot:i"`, 실제 대상은 `data-row`)에 고정하고 Flip·등장·퇴장 없이 내용만 바꾼다 — 숫자(`data-txn`)는 이전 값에서 0.2초 세고 글자(`data-tx`)도 숫자처럼 왼쪽부터 한 글자씩 넘어간다(`txAnim`·`txMix`, 경계 두 칸만 같은 종류 글자로 결정적 순환 · 같은 글자는 그대로 · 흐림·번쩍임 없음), 막대 폭 0.2초(9/23 사용자 선택, 가드 `test_error_lists_keep_rows_in_place_and_only_text_changes`), 24시간 막대 sweep 은 막대가 **처음 그려질 때만**(다른 날로 바뀌면 아무 연출도 없다 — 흐림도 30개가 한꺼번에면 번쩍임이다; 같은 요소에 GSAP 트윈을 겹치면 `clearProps` 가 건너뛰어져 clip-path 가 남는다, 실측), 이름표·타임라인 표식의 순차 등장(`data-sig`)은 **처음 나타날 때 한 번**(장비·날짜·필터를 바꿔도 다시 떨어지지 않는다), 앞으로 온 팝업의 밝기 번쩍임 없음,
  차트 컨테이너 키는 고정(`chart:errors` · `chart:trend`) — 기간·지표·층·필터가 바뀌어도 같은 막대 노드의 높이·색이 CSS transition 으로 이어지고 통째로 사라졌다 다시 자라지 않는다, 자리 바뀐 행 번쩍임과 날짜 넘김의 목록 밀기는 뺐다. 등장 연출(카드 stagger · 막대 성장 · 격자 물결 · 이름표)은 **뷰나 팝업이 새로 들어올 때 한 번**뿐이다.
  ★ **9/24 — 줄은 제자리, 글자만(전 화면)**: morph 가 이미 있던 글자 노드의 값이 바뀌면 제자리에서 왼쪽부터 한 글자씩 넘긴다(`rollable`·`runRolls`, txMix 0.24s — `data-tx`/`data-txn`/`data-count` 칸과 버튼·탭·칩 이름은 제외). 이름으로 줄을 옮기던 목록(가동률 목록 · Error 팝업 유형별 · 유형/Job 팝업 장비별 · 추이 히트맵 · TB500·Kendall 표)은 전부 순위 칸(`data-key="slot:i"`, 대상은 `data-row`) — Flip·떠오름·퇴장 없음. 가동률 목록은 층·정렬·날짜가 바뀌면(`data-listsig`) 24시간 막대만 다시 그린다(`listBars`). 리포트 펼침은 새로 연 것만(`data-reveal="키"`).
  **팝업 덱 9/24**: 어두운 배경은 공유 한 장(`deckscrim`, z 49), 팝업 DOM 순서는 `POPUP_ORDER` 고정·겹침은 z-index(`topDlg`·`behindAt` 은 z 로 고른다), 스택 바는 덮개 밖 `#app` 바로 아래(`.ov` 의 perspective 가 fixed 기준 상자가 되어 스크롤에 딸려 갔다), 뒤 팝업 어둡기는 필터·흐림 대신 `.dlg::after` 덮개(뒤로 0.6s · 이동 0.55s), 앞으로 오는 팝업은 **C안** `liftFront`(그 자리에서 살짝 들리며 밝아진 뒤 0.62s 에 내려앉음 · WAAPI, 도는 동안 `.lifting` 이 CSS 전환을 끈다). **morph 는 곧 지워질 노드(새 목록에 없는 키 · 퇴장 중)를 건너뛰고 끼운다**(`skipDead`) — 살아 있는 노드를 insertBefore 로 옮기면 브라우저가 진행 중인 CSS 전환을 버린다(실측). 등장 애니메이션 클래스는 끝나면 즉시 뗀다(`onEnd`). 선택 Lot 상세 박스는 `data-key="sel"` + 첫 등장만 `fadeIn`.
  **막대 등장은 `scaleY`** 다 — `gsap.from({height:0}, clearProps:"height")` 는 inline `height:%` 까지 지워 등장 뒤 막대가 주저앉는다(5차 실측). 덱 깊이당 130px.
  Error 탭: 유형·Job 행의 깔때기 버튼(`errFType`·`errFJob`)이 그 유형/Job 만으로 카드·날짜별·유형별·장비별·Job별을 다시 집계한다(칩으로 해제, 유형/Job 팝업의 '이 유형만 통계' 도 같다) · 장비별 행은 **고른 기간 그대로** Error 상세 팝업을 연다(`errDays` — 여러 날이면 24시간 타임라인 대신 날짜별 막대 + Lot 표에 날짜 열, '하루씩 보기' 로 전환) · '전체 기간 합계로' 링크는 없다(막대를 다시 누르면 기간으로).
  TB500 · Kendall 탭: **Kendall · TB500 두 묶음**(표기명이 Kendall 로 시작하면 Kendall) 안에서 열 머리를 눌러 정렬(`rptSort`, 기본 이름 오름차순, 같은 열 다시 누르면 반대, `aria-sort`).
  **수집 창 시작일**(`D.partialDays` — `meta.retention_days` 로 계산, 보관 기간의 첫날은 수집 창이 도중에 시작해 하루 전체가 아니다): 헤더에 '부분' 표, 홈 카드 안내, 추이의 평균·주/월 묶음에서 제외(막대는 회색으로 남긴다).
  가동률(카드 3 · 층 필터 · 정렬 · 24시간 막대 목록) → **장비 팝업**(통계 6 · 막대 · Lot 이름표 지시선 · 선택 Lot 원문 · **Report 열기**) ↔ **Error 상세 팝업**(언제 났나 · 유형별 · 최근 21일 · Lot 별, 유형/Job 팝업에서 오면 필터 칩, D51) ·
  Error(기간 · 층 · 지표 → 날짜별 → 유형별·장비별·Job별 → 유형/Job 팝업) · 추이(일·주·월 + 히트맵, 전 기간 대비 없음) · **TB500 · Kendall**(D59, 옛 이름 '리포트' — 표기명 21개 Job 만 보는 탭이라 이름을 바꿨고
  '표기명 n개 Job 만(이 기간 Lot 의 p%)' 안내 한 줄을 둔다. D49: 배치시간 = Report 배치 시작~종료 회귀, 표본 5개 미만 생략, 제외 = 원인 Error 있는 Report · 5장 미만 · 배치 시각 없음. 평균 fault = `faults` 열이 있는 행의 장당 평균, `lots[13]`·`[14]`, D08).
  살펴볼 장비 = 가동률 40% 미만 또는 Error 3건 이상(`PROPS` — `meta.dashboard_settings` 의 같은 이름 숫자가 있으면 그것으로, D14). **기록 없음은 살펴볼 장비가 아니라 별도 대수**(`S.noRec`, D06·D57).
  Lot 선택 키는 `lotKey`(Job·Lot·시작·배치시작·**Report**, D16 — 같은 Lot 이 하루에 Report 두 장이면 갈린다). 팝업은 ESC 로 닫힌다(Error 팝업 → 장비 팝업 → 유형/Job 팝업 순).
  접근성(D05): `render()` 는 그리기 전 포커스(`data-fk`)·창/팝업 스크롤을 적어 두고 되돌린다, 팝업이 열리면 아래는 `inert`, Tab 은 맨 위 팝업 안에서만(`trapTab`), 열리면 제목(`aria-labelledby`)으로·닫히면 열었던 버튼으로 포커스.
  Lot 이 40개를 넘는 날은 이름표를 Error·Test·선택 Lot 만 그린다(막대 클릭 영역은 전부, D10). 화면 어디에도 열람 시계는 없다 — 수집 시각 정보가 없으면 모든 날 분모 24시간(D11).
- **Report 열기**는 장비 팝업의 선택 Lot 에서만(`reportUrl` · `openReport`). 경로는 `meta.devices[].note` + `report_dir` + `report` 로만 만들고 드라이브 문자와 UNC(`\\10.x`) 를 모두 다룬다.
  여는 주체는 사람이 연 그 탭이지 이 화면이 아니다 — 화면은 여전히 바깥으로 요청을 한 건도 보내지 않는다. 수집 상태 칩(`collectChip`: 수집 실패 · 일부 누락)과 '수집 범위 / 수집 안 함' 은 `meta` 에서 그린다. **사본 저장**(`saveHtml`)은 수집기가 준 열·풀 구조 그대로 다시 접는다.
- 추이 화면에 **전 기간 대비(전주·전월·전일)는 두지 않는다**(사용자 확정, 가드: `test_no_period_over_period_comparison_anywhere`). 선택한 기간의 값만 보여 준다.
- 결과 HTML 의 위치·생성은 `utils/results.py` 한 곳에서만 묻는다(`html_path` · `ensure_html` · `last_collect_time`).
- **결과 HTML 분할(9/23, 사용자 요청)**: `write_html` 은 파일이 `split_mb`(기본 30, 0 = 안 나눔 — cfg · prefs · 설정 페이지)를 넘으면 `split_rows_by_day` 로 **날짜 구간별 자립형 HTML 여러 장**을 쓴다.
  가장 최근 구간이 원래 이름(`AOI_capacity.html`), 옛 구간은 `paths.part_name` = `AOI_capacity_<첫날>~<끝날>.html`. 날짜 = 행의 배치 시작일(한 Report 는 한 파일).
  각 파일에는 구간 앞뒤 하루치 행 · 같은 (장비, Report 이름) 행 · 구간 안 Wafer ID 의 **앞선 시도 전부**(Rescan = 앞선 시도 PASS, D63 — 기간 제한 없음)를 **맥락**으로 더 넣고,
  화면(`buildModelV3`)은 `meta.part.from~to` 밖 날을 그리지 않는다 → **각 날의 장비-일 값이 나누지 않은 파일과 같다**(원래 행 순서 유지 — 모델의 동점 처리가 입력 순서를 따른다, 실측).
  헤더에 `분할 n/m · 기간` 칩(`partChip`, 다른 파일 이름은 링크가 아니라 글자). 필요 없어진 옛 구간 파일은 `part_re` 모양 이름만 지운다(가드 `test_html_split.py`).
- 장비는 `key`(**영속 안정 키** `dev:AOI-25`, C03) · `id`(정규화 경로 — **연결용**, 안정 키를 찾는 열쇠) · `path` · `name`(표시명 `AOI-25` · `4F-AOI-01`) · `aliases`(옛 표시명) · `path_aliases` 로 나눠 다룬다.
  안정 키는 처음 볼 때 표시명에서 한 번 만들어 캐시의 `devices` 대응표(`{key: {name, ids, aliases}}`)에 영속한다 — 표시명·드라이브 문자를 바꿔도 이력이 갈라지지 않는다.
  **Report 캐시 키 = `dev:<장비>|<Report 폴더 아래 상대 경로>`**(절대 경로가 아니다). 같은 장비로 잇는 다른 경로 표기는 **검증·승인된 것만** — OS 가 알려 준 드라이브의 UNC 동치(`devices.UNC_RESOLVER`)와 cfg `device_path_aliases`;
  폴더 이름·표시명이 같다는 이유로는 절대 합치지 않는다(이름 충돌은 새 키 + `identity.conflicts` 기록). Report 를 읽을 때 SHA256 을 함께 두어 같은 키의 내용 변화는 `revision`, 다른 폴더의 같은 파일명은 다른 키다.
  옛 절대 경로 캐시는 `_migrate_identity` 가 한 번 옮긴다(멱등 · 행 삭제 0 · 중복은 `superseded_by` 로 출력에서만 제외, `cache_format` 2, 가드 `test_cache_identity.py`). 홈 정렬은 `devices.sort_key`(= template 의 `cmpDev`) — AOI-1…AOI-25 뒤에 4F-AOI-01….
- **수집 창 UI(9/23 개편, 사용자 요청 — "HTML 테마에 맞게", "어떤 상황에 어떤 옵션을 눌러야 하는지 직관적으로")**: 결과 HTML 과 같은 틀 — 상단 바(`widgets/nav_bar.NavBar`: 브랜드 · 내비 탭 · 마지막 수집, 옛 왼쪽 사이드바 대체)와
  가운데 정렬 페이지, 라이트가 기본(prefs v4 가 옛 기본값 "dark" 만 옮긴다 · 어두운 화면은 설정), 글꼴은 HTML 의 `--sans`/`--mono`. 수집 페이지는 체크박스 대신 **상황 카드**(`collect_page.ModeCard`):
  평소 수집(캐시가 없으면 '처음 수집' — 이때 나머지 카드는 잠김) + '결과가 이상하거나 비어 있을 때만' 네 장(빠진 날 채우기 = backfill · 최근 며칠 다시 읽기 = refresh(카드 안 일수, prefs `refresh_pick_days`) ·
  시간 미확인 복구 = recover(캐시로 센 대상 수 표시) · 전체 다시 만들기 = rebuild). 카드마다 '이럴 때' · '무엇을 하나' · 걸리는 시간 배지, 실행 버튼 이름이 고른 카드를 따르고, 수집이 끝나면 평소 수집으로 돌아간다.
- 시각 테마의 단일 출처는 `aoi_capacity/ui/assets/template.html` 의 `:root` 토큰 두 블록(dark · light). `ui/theme.py` 는 그 값을 그대로 쓴다(가드: `test_theme.py`).
  결과 화면은 라이트 단일(D48-⑥, `<html data-theme="light">`)이고 dark 블록은 수집 창의 다크 모드 값이다. CSS 주석에 `:root{` 를 적지 않는다(파서가 첫 블록으로 오인한다 — 실측).
- 사용자 데이터는 `%LOCALAPPDATA%\AOI_Capacity`(`utils/paths.data_root()`), 절대 `app/` 안이 아니다(업데이트가 `app/` 를 통째로 교체).

## 빌드·업데이트
- `python scripts\build.py exe-lite` → `dist/AOI_Capacity_Lite/` (런처 exe + `python/` + `app/`, `.deps_installed` **없음**), `make_release_zip.py --lite` 가 검증 통과 시에만 zip 을 만든다.
- `requirements.txt` 는 PyQt6 와 truststore 뿐이다(QtWebEngine 제거 — 결과 화면이 브라우저로 옮겨갔다).
- `utils/updater.py`(D61, P1 9/20): 기본 브랜치 SHA 비교 → **CI 게이트** `_ci_gate`(그 SHA 에 워크플로 파일 `tests.yml`·이름 `tests` 가 `completed/success` 인 run 이 있어야 함 — 없음·진행 중·실패·조회 불가는 전부 **보류(`held`)** 로 이유를 말하고 현재 버전 유지) →
  `archive/<40자 SHA>.zip`(브랜치 HEAD zip 이 아니다) → `_check_zip_entries`·`_safe_extract`(루트 폴더 하나 · 절대/`..`/드라이브/심링크/대소문자 충돌 거부 · 파일 수·용량 상한, 쓰기 전에 검사) →
  `app.new.part` 스테이징(허용 목록만) → `_verify_staged`(필수 파일, template `__DATA__`, style.qss 렌더, 예상 밖 최상위 항목 거부) → `app.new` rename. `_UPDATE_KEEP_ONLY` 의 이름은 실재해야 한다(`test_update_payload.py`).
  **TLS 는 검증만 한다** — 인증서 검증 실패는 확인·적용 모두 `TlsVerifyError` 로 중단(무검증 재시도 없음, C01). 런처의 교체(`_promote_in_place`)는 파일마다 저널(prepared → old_moved → new_moved)을 남기고
  어느 단계에서 실패하든 그 항목과 앞 항목을 되돌린다(N02, 되돌리기까지 실패하면 `RollbackError` 가 파일 이름과 백업 이름을 적는다). pip 은 `PIP_TIMEOUT_SEC`(600) 상한·취소 콜백(C10).
  워크플로 이름이 바뀌면 `REQUIRED_WORKFLOW_FILE`/`REQUIRED_WORKFLOW_NAME` 도 같이 바꾼다.
- `updater.DEFAULT_BRANCH` 는 오프라인 폴백 — GitHub 기본 브랜치가 바뀌면 함께 갱신한다.

## 수집 모드(D60, P1 9/20)
`collect.collect(cfg, full, backfill, *, recover, refresh_window_days, rebuild_all)` 하나를 GUI·CLI·예약이 같이 쓴다.
증분(기본) · `--backfill`(검색 창만 `backfill_days` 로 넓힘, **캐시된 파일은 건너뜀**) · `--refresh-window N`(최근 N일은 캐시에 있어도 다시 읽음, 창 밖 이력 보존, 실패한 파일은 이전 행 유지 + 다음 수집에서 재시도) ·
`--rebuild-all`(보관 기간 전부를 **후보 캐시**로 새로 읽고 검증 뒤 교체 — 실패하면 기존 캐시 그대로, `RebuildRejected`) · `--full` 은 `--rebuild-all` 의 별칭(**이력 삭제 없음**) · `--recover`(시간 미확인 Report 다시 읽기).
**Report 목록(9/23)**: 커서가 있는 장비의 증분 수집은 폴더 전체 대신 Report 이름의 날짜(`…_26-Sep-16_(12.38.36)_BatchReport.htm`, 배치 종료일 = 파일이 생긴 날)로
`*_YY-Mon-DD_(*` 패턴을 커서 전날~내일만큼 만들어 **NAS 가 거르게** 한다(`report_name_patterns` · `PATTERN_LISTER` = `nas_guard.find_pattern`, Windows `FindFirstFileExW` · 다른 OS 는 None).
고르는 규칙은 전체 나열과 같다(부분집합만 받는다). 처음 보는 장비 · backfill · refresh · recover · rebuild · 패턴 14일 초과 · 패턴 실패 · 마지막 전체 나열(캐시 `full_listed`)이 20시간(`FULL_LIST_EVERY_SEC`) 넘음이면 **전체 나열** —
이름 규칙 밖 파일(`EXPORT.htm`)·나중에 다시 쓰인 옛 Report 는 그때 잡힌다(가드 `test_collect_listing.py`, 목록 단계 9/18 실측 5.5분).
GUI 체크 '최근 N일 다시 읽기(이력 보존)' 은 `refresh_window_days`(N 은 '처음 수집 기간' 스핀 값). 캐시 저장은 고유 tmp → fsync → strict 재읽기 검증 → `os.replace`, 손상 캐시는 덮어쓰지 않고 `aoi_cache.json.bad-<시각>` 으로 보존(C15).
CSV 를 못 쓰는 OS 오류(Excel 잠금)는 실패가 아니라 **부분 성공**(`warnings`, CLI exit 3, 워커 `completed_with_warnings`) — HTML 이 주 산출물이다(C06). 회귀 가드: `test_collect_incremental.py` · `test_collector_worker.py`.
캐시는 **바뀐 이유(`_Dirty`: created · corrupt · format · parser · cursor · identity · device_mapping · reports · reports_updated · failed · retention · rebuild · listing)가 있을 때만 저장**한다 — 아무것도 안 바뀐 실행은 파일을 건드리지 않는다(mtime·바이트 동일), rows 0 이어도 커서·재시도·보관 정리는 저장(C04, `stats["cache_dirty"]`·`cache_saved`).
`write_html` 은 `__DATA__` 가 정확히 하나임을 확인하고 앞부분·데이터·뒷부분을 같은 임시 파일에 차례로 쓴다(C07, 30일치 최고점 181 → 107MB). 크기·메모리 측정은 `python dev/tools/measure_cache.py <샘플> --out <임시>`.
`python -m aoi_capacity.cli --update` 는 갱신되면 같은 인자(`--update` 제외)로 **자식 프로세스**를 띄워 기다리고 그 종료 코드를 돌려준다(exec 아님 — 스케줄러가 '완료' 를 잘못 보지 않게, C14).
`scripts/run_collect.bat` 은 `PYTHONNOUSERSITE=1`, ERRORLEVEL 보존, `collect.log` 5MB 초과 시 `.1~.4` 회전. 의존성 설치 실패 안내는 `main._pause_or_notify` — stdin 없음/EOF/RuntimeError(pythonw)면 MessageBoxW(ctypes) 또는 print, PyQt6 재import 없음(C16).

## 설정 검사(C13 · D14, P3 9/20)
`utils/config.normalize_config` 하나를 prefs(GUI)·cli(config.json)가 같이 쓴다. 성능·기간 값(`read_workers` 1~32 · `backfill_days`/`retention_days` 1~3650 · `refresh_window_days` 0~3650 · `attention_util` 0~100 · `attention_err` 0~999,
bool 은 문자열을 엄격 판정 — `bool("false")` 없음)은 **경고 + 기본값/클램프**, `scope_devices`·경로·폴더 이름(구분자·`..`·NUL)은 `ConfigError` 로 **실행 차단** — `collect.collect` 첫머리와 장비 게이트 4곳이 파일 접근 전에 부른다(fail closed).
`retention_days` 가 `backfill_days` 보다 짧으면 backfill 값으로 늘린다. `prefs_version` 이 잘못돼도 장비 목록을 기본 30대로 되돌리지 않는다. 문구는 ko.py `CFG_*`. 가드 `test_config_normalize.py` · `test_config_example.py`(예시 공개 키 = `DEFAULT_CONFIG`).
`meta.dashboard_settings = {attentionUtil, attentionErr}` 는 cfg `attention_util/attention_err`(prefs 필드명은 `threshold_util/threshold_err` 그대로, 설정 페이지 '주의 장비 기준' 스핀)에서 `write_html` 이 넣고 화면 `PROPS` 가 읽는다(D14).

## 테스트
`QT_QPA_PLATFORM=offscreen python -m pytest -q` (빠른 확인: `-m "not ui and not slow"`, `slow` = 30일치 샘플 전수). PyQt6 가 없는 환경에서는 ui 테스트가 skip 된다.
CI 는 `.github/workflows/tests.yml`(이름 `tests`, main 푸시·PR) — `core` 잡이 전체 스위트(Linux · Qt offscreen · Node 22), `browser` 잡이 `-m browser`(Playwright Chromium), `progress-doc` 잡(PR 만)이 merge-base→HEAD 에 코드 변경이 있으면 `진행상황.md` 동반을 요구한다(`dev/tools/progress_doc_check.py`, S14).
이 워크플로의 성공이 업데이터의 배포 조건(D61)이므로 이름·파일명을 바꾸면 `updater.py` 도 같이 바꾼다. `test_progress_doc.py` 는 CLAUDE.md 의 숫자(수집 범위 대수 · OUT_COLS 열 수 · ROW_SCHEMA_VERSION · MODEL_VERSION · 원인 규칙 수 · 표기명 수)를 코드와 대조한다(S18) — 숫자를 바꾸면 이 파일도.
보관물은 `archive/`(D62: `git mv` + 큰 것은 gzip + `archive/SHA256SUMS`, 가드 `test_archive.py`) — 지우지 않고 옮긴다. 옛 샘플 두 장은 `dev/samples/` 에서 gzip(원본 sha 는 `test_sample_rows.py` 가 확인).
dev 의존성은 `dev/requirements-dev.txt`(pyyaml · playwright — 런타임 `requirements.txt` 에는 넣지 않는다). 테스트는 저장소 안 파일을 다시 쓰지 않는다(S04 — `design_bundle.py`·`graphify_build.py` 는 출력 경로를 인자로 받고, 가드가 전후 지문을 비교한다).
보관 샘플에서 행을 꺼낼 때는 `dev/tests/sample_rows.py`(이름 기반 열 복원·풀 검증), 집계 수치를 잴 때는 `python dev/tools/measure.py <샘플> [--design-rules]`(새 모델의 장비-일 합과 일별 평균 가동률),
단계별 전후는 `dev/samples/ledger_2026-09-18.md` 에 적는다 — 예상치에 맞추어 규칙·테스트를 고치지 않는다.
테스트는 실제 pip·네트워크를 절대 실행하지 않는다(`test_updater.py` 의 autouse 가드). 유일한 예외는 `test_dashboard_js.py` —
`dev/tests/js_harness.js` 가 template 의 스크립트를 **로컬 Node(vm, DOM 대역)** 에서 실행해 `buildModel` 을 검사한다(네트워크·파일 쓰기 없음, Node 가 없으면 skip):
slow 두 개가 30일치로 디자인 스크립트와의 동일성(legacy 프로필)과 product 불변식을, 나머지가 D48~D64 규칙을 작은 fixture 로 본다(하네스 모드: classify · rows+meta+rules · embedded · globals · screen). `test_status_mapping.py` 는 하네스의 classify 모드로 Python·JS 분류를 대조한다.
문자열 검사(`test_template_contract.py`)만으로 화면 로직을 '완료' 라고 하지 않는다. 화면은 Chromium(Playwright)으로 클릭 경로를 실측한다 — `dev/tests/test_dashboard_browser.py`(마커 `browser`, S06: 작은 fixture 를 template 에 박아 file:// 로 열고
가동률 → 장비 팝업(포커스·inert·Tab·ESC) → Error·유형 팝업 → 추이 → TB500 · Kendall 을 누른다, 바깥 요청 0건·콘솔 오류 0 확인; Playwright 나 Chromium 이 없으면 skip, `/opt/pw-browsers` 도 찾는다). 30일치 전수는 스크래치 스크립트로 따로 본다.

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
