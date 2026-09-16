# AOI Capacity — 작업 규칙

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
   `폴더 *`(자동 탐색)은 공유 나열 자체가 다른 장비 접근이라 제한 중에는 건너뛴다. 범위 밖 캐시는 **지우지 않고** 출력에서만 뺀다.
   회귀 가드: `dev/tests/test_scope_isolation.py`.
3. **결과 화면은 앱 안에 없다.** PyQt6 창은 **수집 전용**(수집 · 장비 목록 · 설정)이고, 화면은 수집이 만든
   `AOI_capacity.html` 한 장을 사용자가 더블클릭해 브라우저에서 본다. QtWebEngine·로컬 서버·localhost 를 쓰지 않는다.
   그 HTML 은 데이터·CSS·JS 를 모두 품고 **바깥으로 요청을 한 건도 보내지 않는다**(가드: `test_template_contract.py`).
   브라우저가 NAS 를 직접 읽는 경로도 두지 않는다 — 수집은 Python 만 한다. 자동 주기 수집은 없다(수동 실행만).
4. **Scanresult 를 재귀 검색하지 않는다.** INI 경로는 `{scan}/{job}/{setup}/{lot}/{wafer}/WaferInfo.ini` 로 계산해 존재만 확인한다.
   `job`·`setup` 의 출처는 **Report 안의 `Job/Setup` 값**이다(파일명이 아니다 — 실장비 516개 중 옛 파일명 규칙에 맞는 건 6개뿐이었다).
   `Job/Setup` 이 없는 옛 형식만 파일명 규칙으로 되돌아간다. Report·Scanresult 폴더 이름은 장비마다 달라(`Reports`)
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
  **`TEST` 만 가동률에서 뺀다**(사용자 확정, `collect.EXCLUDED_SCAN_TYPES`) — 분자·분모·오류 건수 어디에도
  넣지 않는다. 다만 화면에서 사라지지는 않는다: 타임라인에 회색 띠, 제목에 '시험 가동 n건 제외',
  Lot 목록에 '시험 · 제외' 표. 빼는 것과 없었던 것은 다르다.
- 행 데이터 계약(`collect.OUT_COLS`): `kind`("" = Wafer 한 장 · "batch" = 통째로 실패한 시도), `batch_end`,
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
테스트는 실제 pip·네트워크·서브프로세스를 절대 실행하지 않는다(`test_updater.py` 의 autouse 가드).

## 커밋
한국어로 "무엇을·왜". PR 은 요청받을 때만. 저장소 산출물에 내부 모델 식별자를 남기지 않는다.
