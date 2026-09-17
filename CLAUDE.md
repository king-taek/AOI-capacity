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
   브라우저가 NAS 를 직접 읽는 경로도 두지 않는다 — 수집은 Python 만 한다. 자동 주기 수집은 없다(수동 실행만).
4. **Scanresult 를 재귀 검색하지 않는다.** INI 경로는 `{scan}/{job}/{setup}/{lot}/{wafer}/WaferInfo.ini` 로 계산해 존재만 확인한다.
   `job`·`setup` 의 출처는 **Report 안의 `Job/Setup` 값**이다(파일명이 아니다 — 실장비 516개 중 옛 파일명 규칙에 맞는 건 6개뿐이었다).
   `Job/Setup` 이 없는 옛 형식만 파일명 규칙(`{job}_{4자리}_{lot}_…`)으로 되돌아가고, 그것도 안 맞으면
   **표의 Lot 을 파일명 뒤에서 떼어** job·setup 을 되찾는다(`_job_setup_by_table_lot`).
   실물: AOI-10 은 Setup 이 `SETUP` 이라 4자리 규칙에 걸리지 않아 job 이 비었고, INI 경로가 통째로 어긋나
   9/15 하루에만 8.8시간이 '미가동' 으로 보였다. job 이 비면 경로를 만들지 않는다(빈 칸은 사라져 남의 INI 를 가리킨다). Report·Scanresult 폴더 이름은 장비마다 달라(`Reports`)
   `devices.find_subdir` 이 후보 몇 개의 존재만 확인해 고른다.
5. **시각은 근거가 있을 때만 쓴다.** `WaferInfo.ini` 는 다시 검사하면 **같은 경로에 덮어써진다**(실물 확인:
   AOI-25 9/14 `00NSP049XYG7`). 그래서 옛 Report 행에도 나중 시각이 붙는다 — INI 시각이 그 Report 의
   `Batch Start~End` 밖이면 `ini_match="STALE"` 로 두고 **시간을 쓰지 않는다**(지어내지 않는다).
   검사된 Wafer 가 하나도 없고 정상 통과도 없는 시도는 `kind="batch"` 행 하나로 만들어 `Batch Start~End` 를
   오류 시간으로 쓰고, 그 배치의 나머지 행(LoadPort/Slot 자리표시 포함)은 `BATCH_FAILED` 로 묶어 따로 세지 않는다.
   같은 `(Wafer, 시작, 종료)` 가 여러 번 나오면 화면에서 시간은 한 번만 세고 '다시 검사' 로 노랗게 표시한다.
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
- 행 데이터 계약(`collect.OUT_COLS`): `kind`("" = Wafer 한 장 · "batch" = 통째로 실패한 시도), `batch_end`,
  `job`·`setup`(Report 안의 `Job/Setup`, 없으면 파일명 규칙 — 나중에 쓸 일이 있어 함께 담는다),
  `report`(BatchReport 파일 이름 — 화면에서 그 파일을 다시 여는 근거),
  `scan_type`("" · RESCAN · REWORK · TEST — 겹치면 TEST → RESCAN → REWORK 순), `ini_match`(EXACT · NOT_FOUND · NO_WAFER_ID · READ_ERROR · STALE · BATCH_FAILED · BATCH).
  상태 분류는 `collect._STATUS_RULES` 와 template 의 `normStatus` 가 **같은 순서**를 쓴다(가드: `test_template_contract.py`).
  표기는 30대 전수 샘플(Report 55,717개)에서 나온 것만 넣었다 — Pass · Skipped. · Aborted. · Alignment Error. ·
  Scan 2D/3D Error. · Failed to read wafer id… · Aborted. Wafer aborted by user. · Camera Hardware Failure(HW_ERROR) ·
  FAR Model…/Illegal Lot Name./Wafer Map Import failed.(RECIPE_ERROR) · Failed to move wafer…(WAFER_LOST).
  ★ 순서가 곧 의미다: 반송 실패 문구는 `… Batch Aborted. Skipped.` 로 끝나 `skip` 규칙 **위**에 있어야 한다
  (아래에 두면 오류가 '건너뜀'(정상)으로 묻힌다).
- `LoadPort A` · `Slot n` 은 Lot·Wafer 가 아니라 자리표시다(`collect._is_placeholder`). Lot 이 비면
  `os.path.join` 에서 그 칸이 사라져 **다른 Lot 의 INI** 를 가리키므로 경로를 아예 만들지 않는다.
  배치 행의 Lot 도 자리표시를 거른 뒤 고른다 — 못 고르면 빈칸으로 두고 화면이 `(Lot 확인 불가)` 라 적는다.
- HTML 에 박는 JSON 은 `collect._embed_rows` 가 접는다 — `POOLED_COLS`(시각 두 열 빼고 전부)를 문자열 풀의
  번호로 바꾼다. 30대 × 90일이면 행이 십수만 개라 접지 않으면 HTML 이 수십 MB 가 된다. template 의 로더가 편다.
  CSV 는 사람이 읽는 파일이라 접지 않는다.
- 결과 화면에서 **막대·오류 표·Lot 표를 더블클릭하면 그 BatchReport 가 새 탭으로 열린다**
  (`reportUrl`·`openReport`). 경로는 `meta.devices[].note` + `report_dir` + `report` 로만 만들고
  드라이브 문자와 UNC(`\\10.x`) 를 모두 다룬다. 여는 주체는 사람이 연 그 탭이지 이 화면이 아니다 —
  화면은 여전히 바깥으로 요청을 한 건도 보내지 않는다.
- **가동률 = 가동시간 ÷ 하루 24시간**(사용자 확정, 분모 고정). 단 **오늘만** 아직 오지 않은 시간을
  미가동으로 셀 수 없으므로 `00:00 ~ 그날 마지막 스캔`(`dayLastScan`)까지로 끊는다.
- 타임라인에서 **오류 구간과 그 뒤 '정지(추정)' 는 막대 하나로 이어 그린다**(사용자 확정).
  숫자(`m.err`·`m.stop`)는 그대로 따로 세고, 툴팁이 **오류 발생 시각 · 오류 종류 · 오류 구간 · 그 뒤 정지**를
  나눠 적는다. 어제 난 오류가 오늘까지 이어진 경우엔 오늘 화면에 오류 구간이 없으므로 정지만 흐리게 따로 그린다.
- **Lot 막대는 하나로 두되 안을 조각별 색으로 칠한다**(사용자 확정). 통째로 파랗게 칠하면 섞여 있는 오류가
  묻힌다(실물: 9/15 AOI-8 NTM — 배치가 통째로 중단된 시도가 파란 막대 안에 숨어 있었다).
  툴팁(`lotTip`)이 Wafer 몇 장 중 정상·중복스캔·재스캔·Rework·Error·Test 가 각각 몇인지 종합해 준다.
  막대를 묶는 기준은 `lotKey` — **Lot 이름을 있는 그대로** 쓴다(사용자 확정). `TTP DIA`·`TTP-DIA`,
  `GUX-PIDS3`·`GUX-PIDS3 RE`, `DYD-FS`·`DYD-FS REWORK` 는 전부 따로다. 따로 돌린 것이면 따로 보여야
  실가동률을 깎은 원인(재스캔·재작업)이 화면에 남는다. 시험 가동만 이름 앞에 표를 붙여 섞이지 않게 한다.
  같은 Lot 이어도 **중간에 `LOT_GAP_SEC`(60초)보다 길게 비면 막대를 나눈다**(사용자 확정) — 빈 시간이
  파랗게 칠해지면 안 된다. 근거: 실장비 3일치에서 같은 Lot 안 연속 Wafer 사이 11,529건 중 95%가 52초,
  99%가 1,068초 — 60초면 Wafer 교체(20~30초)는 붙이고 실제 멈춤은 가른다(9/15 기준 막대 358→477개).
- **화면 용어·색·패턴의 단일 출처는 template 의 `DISPLAY_META`** 다(사용자 확정 D30): 가동 · 중복스캔(청록 사선) · 재스캔(노랑) ·
  Rework(보라) · Error(빨강) · Test(분홍 점무늬) · 미가동. 범례·툴팁·막대·표·상세가 전부 여기서 읽는다. 옛말(검사·재검사·재작업·오류·시험)을
  화면 JS 에 다시 쓰지 않는다(가드: `test_rescan_and_rework_are_shown_apart`). 원본 상태 문구·Lot 이름·Report 파일명은 바꾸지 않는다.
- **데이터 중복과 실제 반복은 다르다**(사용자 확정 D31·D32, template `build`·`materialIndex`):
  ① 같은 원본 행이 두 번(`rawDups`) → 한 번, ② 서로 다른 Report 가 같은 INI 시각을 참조(`refs`) → 시간 한 번·이력 보존·**재스캔으로 단정하지 않음**,
  ③ 시각이 다른 실제 시도 → 시간을 모두 세고 관계를 붙인다. 관계는 조회 날짜·장비 필터와 무관하게 **로드한 전체 행**에서 한 번 계산한다.
  자재 키 = Lot 원문에서 RE·RESCAN·REWORK·TEST 토큰만 뗀 것 + Wafer ID(장비명 없음, 대소문자·구분자 그대로). 같은 장비·앞선 시도 정상 → 중복스캔,
  같은 장비 Error 뒤 복구·RE 표기·**다른 장비에서 먼저 스캔/Error** → 재스캔. Recipe 까지 같으면 확정, 자재만 같으면 추정(실물 `BS`/`BS_1`).
  시각이 겹치거나 같은 시작이면 **보류**(임의 순서로 정하지 않는다). 첫 시도는 '확인된 첫 기록' 이고 소급해서 바꾸지 않는다.
  LoadPort/Slot·실패 배치 행은 후보가 아니다. 시각 없는(STALE) 앞선 시도는 Batch 구간으로 선후만 보고 시간은 지어내지 않는다.
  분류 규칙이 바뀌면 `CLASS_VERSION` 을 올린다 — 저장하지 않고 열 때마다 원천 행에서 다시 계산한다(저장 열 계약은 그대로 17열).
- **시간 분할 U+T+E+S+R = D** 는 같은 장비·같은 날 안에서 우선순위(Error > 가동 > Test > 정지)로 **한 번만** 배정하고 겹친 초를 `overlap` 에 적는다
  (`max(0,…)` 로 숨기지 않는다). 건수는 **시작한 날에 한 번**(자정을 넘는 구간은 시간만 나눈다). 복구 기록 없는 마지막 Error 의 정지(추정)는
  **관측 종료(로드한 데이터의 마지막 시각)까지만** — 다음 날로 늘리지 않고, 정지 확정으로 표현하지 않는다.
- 홈의 **가동률 저하 사유** 차트(`renderLoss`)는 같은 `dayMetrics` 를 Error 구간·Error 후 정지(추정)·Test·미가동(사유 미확인)으로 나눈다.
  %p 기여 = 100/N × Σ(L/D) 라 합이 100 − 평균 가동률이다(가드 `test_t24…`). 중복스캔·재스캔·Rework 는 가동시간의 부분집합이라 저하 사유에 넣지 않는다
  (별도 '반복 가동' 카드). 사유는 관측 분류이지 물리적 원인이 아니다 — 인력·자재·보전 같은 원인을 지어내지 않는다.
- **장비 상세 패널은 하나뿐이고 클릭한 장비 버튼 바로 아래에 붙는다**(사용자 확정 D34): 렌더 전 `#detPark` 로 빼 두었다가 선택한 장비의
  `.dmount` 로 옮긴다. 카드는 `.ditem.open` 이 한 줄 전체로 넓어지고, 표는 바로 다음 `tr.detrow`. 안 보이는 보기는 비운다(같은 id 가 남으면 상세가 숨은 쪽에 붙는다).
- 추이·장비 비교 화면에 **전 기간 대비(전주·전월·전일)는 두지 않는다**(사용자 확정, 가드:
  `test_no_period_over_period_comparison_anywhere`). 선택한 기간의 값만 보여 준다.
- 결과 HTML 의 위치·생성은 `utils/results.py` 한 곳에서만 묻는다(`html_path` · `ensure_html` · `last_collect_time`).
- 장비는 `id`(정규화 경로, 캐시 커서·집계 키) · `path` · `name`(표시명 `AOI-25` · `4F-AOI-01`) · `aliases`(옛 표시명) 로 나눠 다룬다.
  표시명을 바꿔도 이력이 갈라지지 않는다. 홈 정렬은 `devices.sort_key`(= template 의 `cmpDev`) — AOI-1…AOI-25 뒤에 4F-AOI-01….
- 시각 테마의 단일 출처는 `aoi_capacity/ui/assets/template.html` 의 `:root` 토큰. `ui/theme.py` 는 그 값을 그대로 쓴다(가드: `test_theme.py`).
- 사용자 데이터는 `%LOCALAPPDATA%\AOI_Capacity`(`utils/paths.data_root()`), 절대 `app/` 안이 아니다(업데이트가 `app/` 를 통째로 교체).

## 빌드·업데이트
- `python scripts\build.py exe-lite` → `dist/AOI_Capacity_Lite/` (런처 exe + `python/` + `app/`, `.deps_installed` **없음**), `make_release_zip.py --lite` 가 검증 통과 시에만 zip 을 만든다.
- `requirements.txt` 는 PyQt6 와 truststore 뿐이다(QtWebEngine 제거 — 결과 화면이 브라우저로 옮겨갔다).
- `utils/updater.py`: 기본 브랜치 SHA 비교 → 브랜치 zip → `app.new.part` 스테이징 → `_verify_staged`(필수 파일, template `__DATA__`, style.qss 렌더) → `app.new` rename. `_UPDATE_KEEP_ONLY` 의 이름은 실재해야 한다(`test_update_payload.py`).
- `updater.DEFAULT_BRANCH` 는 오프라인 폴백 — GitHub 기본 브랜치가 바뀌면 함께 갱신한다.

## 테스트
`QT_QPA_PLATFORM=offscreen python -m pytest -q` (빠른 확인: `-m "not ui"`). PyQt6 가 없는 환경에서는 ui 테스트가 skip 된다.
테스트는 실제 pip·네트워크를 절대 실행하지 않는다(`test_updater.py` 의 autouse 가드). 유일한 예외는 `test_dashboard_js.py` —
`dev/tests/js_harness.js` 가 template 의 스크립트를 **로컬 Node(vm, DOM 대역)** 에서 실행해 분류·시간 모델을 검사한다(네트워크·파일 쓰기 없음,
Node 가 없으면 skip). 문자열 검사(`test_template_contract.py`)만으로 화면 로직을 '완료' 라고 하지 않는다.

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
