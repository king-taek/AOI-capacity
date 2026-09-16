# AOI Capacity — 작업 규칙

Camtek AOI 장비의 BatchReport/WaferInfo.ini 를 읽어 장비별 가동률을 내는 **PyQt6 수집 프로그램**과,
그 결과를 담아 **더블클릭으로 여는 정적 HTML 대시보드** 한 장.
배포는 exe-lite(얇은 런처 exe + python 런타임 + `app/`), 자동 업데이트는 GitHub 커밋 SHA 비교.

## 절대 규칙
1. **NAS 원본은 읽기만 한다.** NAS 경로 아래에는 어떤 파일도 만들거나 바꾸거나 지우지 않는다.
   쓰기(`open(..., "w")`, `os.replace/rename/remove/makedirs`, `shutil.*`)는 `aoi_capacity/collect.py` 의
   `_save_cache` · `write_html` · `_write_csv` 안에만 두고, 각 함수 첫 줄에서 `nas_guard.assert_local` 을 호출한다.
   회귀 가드: `dev/tests/test_nas_guard.py`(정적 AST 검사 + 동적 트립와이어).
2. **수집 허용 장비 밖은 건드리지 않는다.** 허용 목록은 `aoi_capacity/scope.py`(현재 `AOI-25` 한 대).
   범위 밖 장비에는 `scandir/stat/isdir/isfile/open` 을 한 번도 부르지 않는다 — 게이트는 "파일을 만지기 전" 단계인
   `devices.py`(`devices_from_rows` · `discover_devices` · `check_rows`)에 있고 수집 루프·CLI·백필·예약·연결 확인이 모두 같은 함수를 쓴다.
   `폴더 *`(자동 탐색)은 공유 나열 자체가 다른 장비 접근이라 제한 중에는 건너뛴다. 범위 밖 캐시는 **지우지 않고** 출력에서만 뺀다.
   회귀 가드: `dev/tests/test_scope_isolation.py`.
3. **결과 화면은 앱 안에 없다.** PyQt6 창은 **수집 전용**(수집 · 장비 목록 · 설정)이고, 화면은 수집이 만든
   `AOI_capacity.html` 한 장을 사용자가 더블클릭해 브라우저에서 본다. QtWebEngine·로컬 서버·localhost 를 쓰지 않는다.
   그 HTML 은 데이터·CSS·JS 를 모두 품고 **바깥으로 요청을 한 건도 보내지 않는다**(가드: `test_template_contract.py`).
   브라우저가 NAS 를 직접 읽는 경로도 두지 않는다 — 수집은 Python 만 한다. 자동 주기 수집은 없다(수동 실행만).
4. **Scanresult 를 재귀 검색하지 않는다.** INI 경로는 `{scan}/{equipment}/{process}/{lot}/{wafer}/WaferInfo.ini` 로 계산해 존재만 확인한다.
5. **런처 exe 에는 앱 코드가 0줄이다.** `scripts/exe_launcher.py` 는 표준 라이브러리만 import 한다
   (PyInstaller 의 FrozenImporter 가 디스크의 새 코드를 가린다). `hiddenimports=[]`, `pathex=[]`, 앱 패키지는 `excludes`.
6. **`app.new` 는 완성·검증된 트리만.** `app.new.part` 에 만들고 검증 후 rename 한 것이 준비 신호. VERSION 은 스테이징 트리에만 쓴다.
7. **사용자 문구는 `aoi_capacity/i18n/ko.py` 에만.** 위젯·업데이터·워커에 한국어 리터럴을 두지 않는다(로그 메시지는 예외).
8. **긴 작업은 UI 스레드 밖에서.** 코어 함수는 `progress(done, total, phase)` 콜백을 받고, 총량을 모르면 `total<=0`(busy) 로 보고한다.
9. `requirements.txt` 변경은 업데이트가 통째로 실패할 수 있는 지점 — 작업 요약에 반드시 표시하고 `--upgrade` 는 쓰지 않는다. 테스트는 실제 pip 을 절대 실행하지 않는다.

## 레이아웃
- `main.py`(진입), `aoi_capacity/`(앱: `collect.py`, `cli.py`, `devices.py`, `scope.py`, `nas_guard.py`, `i18n/`, `utils/`, `workers/`,
  `ui/` — 수집 UI 만: `pages/collect_page.py`·`devices_page.py`·`settings_page.py`), `scripts/`(런처·빌드), `dev/`(테스트), `docs/`.
- 현장 샘플 수집 도구는 `scripts/collect_sample.py`(+`make_sample.bat`) — 표준 라이브러리만 쓰고 NAS 는 읽기만 하며
  Lot 폴더만 정확 경로로 나열한다(가드: `test_collect_sample.py`). 배포본에도 들어간다(`_UPDATE_KEEP_ONLY`).
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
