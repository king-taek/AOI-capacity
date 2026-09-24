# Graph Report - AOI-capacity  (2026-09-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2360 nodes · 5486 edges · 104 communities (89 shown, 15 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 214 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f4569a3c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103

## God Nodes (most connected - your core abstractions)
1. `collect()` - 86 edges
2. `make_cfg()` - 78 edges
3. `MainWindow` - 44 edges
4. `rows_for_report()` - 40 edges
5. `write_html()` - 39 edges
6. `h()` - 38 edges
7. `download_and_apply()` - 37 edges
8. `r()` - 36 edges
9. `parse_report()` - 35 edges
10. `render()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `window()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `test_zero_new_rows_but_state_change_still_saves()` --indirect_call--> `collect()`  [INFERRED]
  dev/tests/test_cache_identity.py → aoi_capacity/collect.py
- `test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent()` --indirect_call--> `collect()`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → aoi_capacity/collect.py
- `test_cli_flags_and_exit_codes()` --indirect_call--> `collect()`  [INFERRED]
  dev/tests/test_collect_incremental.py → aoi_capacity/collect.py
- `test_device_whose_reports_all_fail_is_partial_not_done()` --indirect_call--> `collect()`  [INFERRED]
  dev/tests/test_collect_incremental.py → aoi_capacity/collect.py

## Import Cycles
- None detected.

## Communities (104 total, 15 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (63): B(), CAUSE_CODES, CAUSE_RULES, CLOSE, devStatus, di(), DROPW, embCols (+55 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (70): _a(), Ae(), Ao(), Ba(), be(), cb(), ce(), $d() (+62 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (55): _FakeBuild, _out(), _polluted(), Path, make_release_zip — 검증 실패면 zip 없음, 통과면 최상위 폴더 하나 + 설치방법.txt(BOM, CRLF), 찌꺼기 제외., 빌드 PC 잔재: 낱개 pyc · pytest 캐시 · 로그 · 백업 · 옛 폴더 · 제자리 스테이징 — 그리고 지켜야 할 런타임 파일., test_no_zip_when_verification_fails(), test_polluted_dist_ships_no_cache_log_or_backup_but_keeps_runtime() (+47 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (56): _IniMemo, issue_text(), parse_report(), 코드 목록 → 사람이 읽는 문장(ko.py). 아는 코드만 문장으로, 모르는 코드는 원문 항목 그대로., Report 한 장을 (job, setup, lot, wafer 행, 요약)으로 푼다. ★ Scanresult 경로의 출처는 **Report…, `TB500_RDL2 - Multi/Setup1` → (`TB500_RDL2 - Multi`, `Setup1`). 마지막 `/` 로만 가른다., 수집 한 번 안에서 같은 WaferInfo.ini 를 **한 번만** 연다. 같은 Wafer 가 여러 Report 에 나오면(재검사) INI…, → ("ok", 필드 dict) · ("missing", None) · ("error", 예외) (+48 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (59): test_ini_memo_lets_concurrent_readers_share_one_open(), slow(), at(), busy(), _clean_batches(), globals_(), _hhmm(), meta() (+51 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (54): prefs_file(), load(), migrate(), patch(), Prefs, Any, 수집 코어가 받는 cfg. 경로는 전부 이 PC 의 데이터 폴더(또는 사용자가 고른 로컬 폴더)., 모르는 키는 버리고, 아는 키는 **형을 검사해** 받는다(C13) — 잘못된 값 하나 때문에 파일 전체를 기본값으로 되돌리지 않는다.… (+46 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (49): _check_zip_entries(), _ci_gate(), _default_branch(), deps_changed(), _describe_err(), _gate_info(), _http_get(), _identity() (+41 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (18): _card(), CollectPage, _label(), ModeCard, _PlanWorker, QThread, QWidget, [(글자, 종류)] — 종류: rec(추천 · 초록) · warn(주의 · 노랑) · slow(회색) · "" (파랑). (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (48): _batch_from_rows(), cause_field(), _first(), _is_error_row(), _is_placeholder(), is_unmapped_status(), issue_field(), _job_setup_by_table_lot() (+40 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (43): load_config(), config.json 을 읽어 cfg 를 만든다. 상대 경로 기본값은 config.json 이 있는 폴더 기준. GUI 의 prefs 와…, check_or_raise(), ConfigError, dashboard_settings(), fatal(), is_single_name(), normalize_config() (+35 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (47): applySettings(), behindAt(), canAnim(), cc(), countUp(), deckSnap(), enterAnim(), enterView() (+39 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (44): filecmp, copy_app_tree(), _copytree(), _default_branch_name(), _fetch_runtime(), _git_head(), _q(), _import_app_module() (+36 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (41): _advance_cursor(), _assign_device_keys(), collect(), _Dirty, _empty_cache(), _entry_sort_stamp(), _fresh_key(), _load_cache() (+33 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (40): collections, html_parser, collect_one(), copy_ini_for(), copy_report(), diagnose(), find_subdir(), list_folder() (+32 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (41): _assets_snapshot(), _fingerprint(), _load(), _on(), _package_assets_untouched(), Path, dev/tools/graphify_build.py 가드 — 임시 JS 는 절대 남지 않고(테스트는 패키지 폴더에 아무것도 만들지 않고),…, S04 수락 기준: 도구의 코드 경로를 전부 태워도(성공·실패·예외) 패키지 폴더의 이름 집합·template 지문이 그대로다. (+33 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (30): 사용자에게 보이는 문구는 전부 ko.py 에 산다. 호출부는 `i18n.KO.상수` 로 쓴다. 표준 라이브러리만 쓰는 순수 상수 모듈이라…, AOI Capacity — Camtek AOI 장비 가동률 대시보드. 패키지 구성 - collect.py 수집 코어(표준 라이브러리만).…, NAS 읽기 전용 안전장치. ★ 절대 규칙: NAS 원본(Report/Scanresult 가 있는 공유) 아래에는 어떤 파일도 만들거나…, PyQt6 화면. 시각 테마의 단일 출처는 assets/template.html 의 :root 토큰이며 theme.py 가 그 값을 읽어…, 메인 창 — 좌측 NavBar | QStackedWidget(장비 목록 · 수집 · 설정). ★ 이 프로그램은 **수집 전용**이다. 결과…, 수집 페이지 — **지금 상황에 맞는 수집을 고르고 시작**한다(9/23 개편). 실제 실행은 MainWindow 가 워커로 한다. 예전에는…, 장비 목록 편집 — 표 하나가 devices.csv 다. 저장은 이 PC 의 데이터 폴더에만 한다(NAS 에는 절대 쓰지 않는다)., 설정 · 정보 — 표시(테마), 주의 기준, 데이터 폴더, 버전·업데이트, NAS 안내. 주의 기준은 결과 HTML 을 만들 때 함께… (+22 more)

### Community 16 - "Community 16"
Cohesion: 0.08
Nodes (31): Call, 테스트 공통 픽스처. - 모든 테스트는 임시 HOME/LOCALAPPDATA 아래에서 돈다 → 개발자의 실제 설정·캐시를 건드리지 않는다.…, styled_qapp(), 디자인 세션의 추출 스크립트(docs/design/dashboard-redesign/scripts/make_aoi_data.js) 가드. -…, _cfg(), _embedded(), _model(), Path (+23 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (34): 사용자에게 보이는 한국어 문구 — 이 파일에만 둔다. 규칙 - 이름은 `기능_역할` (BTN_, NAV_, COLLECT_, UPDATE_,…, job_alias(), model_version(), template.html 에서 **기계적으로** 뽑는 사실들 — 문서(CLAUDE.md)와 코드가 어긋나는지 볼 때의 코드 쪽 값. Node…, `const JOB_ALIAS={ "원문":"표기명", … };` 블록을 dict 로. 줄마다 항목 하나라는 형식을 검증한다., `const <name>=[ ["CODE",/regex/i], … ];` → [(code, pattern)] — 파이썬…, 두 주석 표식 사이 — 표식이 없으면 예외(조용히 빈 문자열을 검사해 통과하지 않는다)., rules() (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (38): cache_file(), data_root(), default_devices_csv(), devices_csv_path(), _ensure_dir(), ensure_user_files(), install_root(), log_file() (+30 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (37): _cache_summary(), _check(), read_one(), CollectCancelled, _decode_report(), _drive_host(), failed_batch_row(), _issue_dec() (+29 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (38): cache_status(), _embed_rows(), _payload(), 실행별 고유 임시 이름 — 동시에 도는 GUI/CLI 가 서로의 임시 파일을 밟거나 지우지 않게., 방금 쓴 임시 파일을 strict 로 다시 읽어 구조가 맞는지 본다 — 반쯤 쓴 파일이 정상 캐시로 승격되지 않게., 캐시를 **트랜잭션**으로 쓴다(C15): 고유 임시 파일 → flush+fsync → 다시 읽어 검증 → `os.replace`. 어느…, HTML 에 박을 형태로 접는다 — `POOLED_COLS` 는 문자열 풀의 번호로 바꾼다. 장비 30대 × 보관 90일이면 행이 십수만…, 접힌 행 + meta → HTML 에 박을 JSON 문자열. `</` → `<\\/` 는 JSON 으로는 같은 문자열이면서 HTML 파서가… (+30 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (39): barsHtml(), bringToFront(), clock(), closeTop(), cmpDev(), cnt(), collectChip(), cut() (+31 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (11): _c(), DeviceStrip, LoadingOverlay, ProgressStrip, _PulseDot, QColor, QEvent, QObject (+3 more)

### Community 23 - "Community 23"
Cohesion: 0.09
Nodes (36): _backup_roots(), 장비 dict 의 `scan_dirs`(devices.with_dirs 가 붙임) → (경로, 경계 날짜) 목록. 맨 앞(지금 폴더)은 뺀다., backup_cutoff(), dir_key(), date, 폴더 이름·경로의 **Windows 의미** 비교 키 — 대소문자 · `/`↔`\\` · 끝 구분자 차이를 지운다(C05). NAS 는…, 두 폴더 이름(또는 경로)이 Windows 의미로 같은 곳인가., 백업 폴더 이름의 날짜 = **그 이전 것을 담아 둔 경계**. `…_260918` → 2026-09-18, `…_0901` → (해… (+28 more)

### Community 24 - "Community 24"
Cohesion: 0.11
Nodes (32): _promote_in_place(), 비-exe 제자리 적용 — 항목마다 prepared → old_moved → new_moved 로 저널을 남기며 옆으로 치우고 → 새것 →…, _extract(), _fail_move_when(), _loose_app(), parametrize, Path, updater — 버전 비교·브랜치 정규화·CI 게이트·zip 검사·스테이징 적용·저널 롤백·pip 상한. 네트워크·pip 은 전부 모킹(실제… (+24 more)

### Community 25 - "Community 25"
Cohesion: 0.12
Nodes (34): make_cfg(), _lock_replace_for(), 수집 코어의 증분·backfill·보관·취소·진행률 계약., ★ 실장비: 파서를 고쳐도(acaa6ce) 캐시는 Report mtime 만 보고 옛 행을 그대로 내보냈다(상태 재분류 93건). 규칙 번호가…, ★ INI 를 못 찾은 행은 다음 수집에서도 그대로 얼어 있었다(Report mtime 이 그대로라서). `recover` 는 그런 행이 있는…, GUI 는 prefs → cfg["refresh_window_days"] 로 켠다 — 인자와 같은 동작이어야 한다., ★ 후보 캐시가 검증에 걸리면(Report 를 하나도 못 읽음) RebuildRejected — 원 캐시는 한 바이트도 바뀌지 않는다., 저장이 중간에 실패하면(검증 실패·교체 실패) 자기 임시 파일만 지우고 원본은 그대로다. (+26 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (31): _cache_of(), _count_htm_reads(), spy(), _csv(), _fingerprint(), 캐시 정체성·저장 규칙(P3-A · C03 · C04 · C09 · C07). - C03: Report 키 = `(장비 안정 키 |…, OS 가 UNC 를 못 알려 주는 곳(다른 PC 로 옮김)에서는 cfg 의 승인 묶음이 같은 역할을 한다., ★ 폴더 이름·표시명이 같아도 승인된 별칭이 없으면 다른 장비다 — 새 키(`~2`)를 만들고 충돌로 기록한다. 옛 이력은 지우지 않는다. (+23 more)

### Community 27 - "Community 27"
Cohesion: 0.07
Nodes (30): plan_run(), UI 안내용 — 캐시만 보고 이번 실행이 어떤 성격인지 알려준다(NAS 접근 없음). 행을 다시 계산하지 않고 결과를 메모한다.…, RunPlan, _add_report(), _cache_of(), _dev_dir(), _entry_fp(), _entry_of() (+22 more)

### Community 28 - "Community 28"
Cohesion: 0.10
Nodes (24): 헤드리스 실행(작업 스케줄러용). GUI 와 같은 수집 코어를 쓴다. python -m aoi_capacity.cli # config.json…, 첫 실행 부트스트랩 — lite 배포의 의존성(requirements.txt) 설치 판단·실행. exe-lite…, utils — paths(경로) · prefs(설정) · bootstrap(첫 실행 설치) · updater(자동 업데이트)., 사용자 설정(prefs.json) — 이 PC 에만 저장. - 한 개의 flat dataclass + `extra` 탈출구.…, copy, main.py — 로깅은 데이터 폴더의 app.log 로, 개발 트리에서는 pip 부트스트랩을 건드리지 않는다., QtWebEngine 은 더 이상 쓰지 않는다 — 관련 환경변수를 건드리지 않는다., test_apply_env_sets_hidpi_and_no_webengine_flags() (+16 more)

### Community 29 - "Community 29"
Cohesion: 0.07
Nodes (24): _fingerprint(), nas(), parametrize, Path, 샘플 수집 도구(scripts/collect_sample.py) 계약. 현장에서 사용자가 직접 돌리는 도구라 두 가지를 반드시 지켜야 한다.…, AOI-25 는 Report 가 아니라 Reports 다 — 설정 없이도 찾아낸다., 이름을 짐작할 수 없으면 그 폴더 안에 무엇이 있는지 보여 준다., 장비 경로는 사용자가 직접 고치는 값이라 파일 위쪽에 있어야 한다. (+16 more)

### Community 30 - "Community 30"
Cohesion: 0.22
Nodes (28): deps_blocked(), download_and_apply(), last_error(), CI 게이트 → 그 SHA 의 archive zip → 검사·해제 → 허용 목록만 스테이징 → 검증 → (exe) app.new 로…, 직전 적용이 '새 패키지를 설치하지 못해서' 포기됐는지(exe 모드) — UI 가 새 배포본을 받으라고 안내., _app(), _branch_zip(), _exe_install() (+20 more)

### Community 31 - "Community 31"
Cohesion: 0.10
Nodes (27): _candidates(), device_id(), _dirs_of(), display_name(), _entry(), find_subdir(), is_floor4(), _natural() (+19 more)

### Community 32 - "Community 32"
Cohesion: 0.14
Nodes (5): _CheckWorker, DevicesPage, QThread, QWidget, 연결 확인' — NAS 폴더 존재 여부를 UI 스레드 밖에서 본다(읽기만).

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (24): main(), _print(), _progress_printer(), cb(), 갱신 뒤 다시 실행할 인자 — `--update` 만 뺀다(같은 인자로 한 번만 다시 돌고, 자식은 다시 갱신하지 않는다)., 갱신 뒤 **자식 프로세스**로 수집을 다시 실행하고 끝날 때까지 기다린 뒤 그 종료 코드를 돌려준다(C14). Windows 의…, rerun_args(), rerun_without_update() (+16 more)

### Community 34 - "Community 34"
Cohesion: 0.11
Nodes (23): AST, builtins, ctypes, _no_input(), parametrize, C16 — 의존성 설치 실패 안내: pythonw(`sys.stdin is None` → `input()` 이 RuntimeError)·EOF…, PyQt6 import 는 `_run_gui` 안에만 — 설치에 실패한 패키지를 안내 경로에서 다시 요구하지 않는다., test_console_path_waits_for_enter() (+15 more)

### Community 35 - "Community 35"
Cohesion: 0.10
Nodes (22): _active(), _build_html(), _embedded(), _fixture_rows(), _launch(), _meta(), page(), page_factory() (+14 more)

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (23): _cfg(), _cursor_of(), _embedded(), parametrize, ★ 수집 범위 격리 회귀 가드 — 지금 허용 목록은 `scope.DEFAULT_SCOPE`(AOI-1 · 8 · 9 · 25) 다. 두 겹으로…, ★ `폴더 *` 행은 범위 제한 중에도 동작해야 한다 — 실장비에서 4층 5대가 이것 때문에 3일 내내 한 번도 수집되지 않았다. 다만 공유를…, devices.csv 가 없으면 nas_roots 를 `*` 로 본다 — 그래도 공유를 나열하지 않고 허용 이름만 확인한다., C08: 장비 확인(devices_from_rows · _attach_dirs · check_rows)을 read_workers 개씩 동시에… (+15 more)

### Community 37 - "Community 37"
Cohesion: 0.14
Nodes (23): deps_installed(), deps_marker(), ensure_deps(), pip_install_cmd(), Path, 실제 요구사항 줄만(주석·빈 줄 제거). 주석만 바뀐 것을 '의존성 변경' 으로 오인하지 않게., 이 requirements 내용으로 설치가 끝났는가(표식 내용 = 지문). req_text 가 None 이면 존재만 본다., 빠진 것만 채운다 — `--upgrade` 없음(CLAUDE.md 규칙 7). `-s` 로 개인 site-packages 를 배제. (+15 more)

### Community 38 - "Community 38"
Cohesion: 0.14
Nodes (20): _add(), _cache(), _fake_lister(), _name_for(), date, 수집 가속(9/23) — ① 증분 수집의 Report 목록을 이름의 날짜 패턴으로 NAS 가 거르게 ② 읽기를 NAS 마다 번갈아 배정.…, 캐시에 든 Report 이름(원래 철자) — 키의 상대 경로는 소문자로 접혀 있어 path 에서 이름을 꺼낸다., 한 NAS 에 몰리지 않는다: NAS 마다 read_workers 개까지, 여러 NAS 는 동시에. 결과는 입력 순서 그대로. (+12 more)

### Community 39 - "Community 39"
Cohesion: 0.09
Nodes (20): fake_nas(), _no_startup_side_effects(), qapp(), _qt_app(), tmp/nas/X 아래 AOI-9, AOI-10 과 tmp/nas/M-AOI-8(루트가 장비)을 만든다. 반환: (nas_root,…, _no_real_subprocess(), scoped_nas(), fixture() (+12 more)

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (17): _bundle(), _layout(), _marker(), _mk(), Path, exe_launcher.py — 교체 상태기계. 이 런처는 업데이트되지 않으므로 여기 로직이 틀리면 나중에 못 고친다. 핵심 불변식: 어떤…, test_first_run_uses_the_console_python(), test_later_runs_are_windowless() (+9 more)

### Community 41 - "Community 41"
Cohesion: 0.10
Nodes (18): _numbers(), parametrize, `진행상황.md` · `CLAUDE.md` 회귀 가드 — 세션이 바뀌어도 이어서 일할 수 있게 하는 파일이라 형식이 계약이다. 이 파일의…, ★ git 은 기본으로 한글 경로를 `\\354\\247…` 로 내놓는다 — 그대로 비교하면 후크가 늘 막는다., CLAUDE.md 가 적는 숫자는 코드가 정답이다. 그 숫자를 아직 적지 않은 항목(PARSER_VERSION)은 적히는 순간부터 검사된다., 진행상황.md 가 표기명·열 수를 적는다면 같은 숫자여야 한다(적지 않으면 그냥 통과)., 확정된 결정은 번호로 이야기한다 — 빠지거나 겹치면 '사용자가 뭘 정했더라' 를 못 찾는다., 맨 위 항목은 실제로 있는 커밋이어야 한다 — 손으로 적다 틀리면 이력을 못 따라간다. (+10 more)

### Community 42 - "Community 42"
Cohesion: 0.19
Nodes (21): _attach_dirs(), _dedupe_sort(), devices_from_csv(), devices_from_rows(), discover_devices(), _discover_under(), _log(), _norm_root() (+13 more)

### Community 43 - "Community 43"
Cohesion: 0.12
Nodes (20): _version_info(), _app_root(), check_for_update(), current_version(), ensure_version_file(), _git_head(), _git_head_ref(), is_git_checkout() (+12 more)

### Community 44 - "Community 44"
Cohesion: 0.17
Nodes (19): apply_to_app(), color_mode(), colors(), normalize_color_mode(), palettes(), parse_template_tokens(), 테마 — template.html 의 CSS 토큰을 그대로 Qt 로 가져온다. 단일 출처: `assets/template.html` 의…, template.html 에서 :root 와 :root[data-theme="light"] 의 --토큰: #hex 를 뽑는다. (+11 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (20): _carry_over(), newest_of(), _entry_newest(), ini_roots_for(), parse_dt(), 전체 재구축(rebuild): 이번에 **보지 못한** 이력을 원 캐시에서 후보 캐시로 옮긴다 — 지우는 재구축이 아니다. 옮기는 것: (1)…, 같은 자재일 수 있는 행을 묶는 열쇠 — Wafer ID 의 영숫자만 대문자로. 화면의 자재 키(`matKey` = Job 묶음|Report…, 결과 HTML 이 한도를 넘을 때(9/23) 행을 **날짜 구간**으로 나눈다 → [(첫날, 끝날, 그 파일에 넣을 행)] 새 구간부터. -… (+12 more)

### Community 46 - "Community 46"
Cohesion: 0.17
Nodes (14): CollectorSignals, CollectorWorker, QObject, QThread, _collect_signals(), CollectorWorker — 스레드를 띄우지 않고 run() 을 직접 불러 시그널·취소·실패 경로를 검사한다., ★ C06: Excel 이 CSV 를 잡고 있어도 HTML·캐시는 정상 — done 으로 끝내되 상태는…, test_csv_lock_completes_with_warnings_not_failed() (+6 more)

### Community 48 - "Community 48"
Cohesion: 0.13
Nodes (9): _fake_out(), Path, build.py / portable_build.py — 순수 판단 로직(명령 구성·검증 목록·app 복사). 네트워크·PyInstaller…, 다운로드·pip 을 가짜로 바꿔 흐름만 확인: 런타임 준비 → pip → app/ → VERSION, 표식 없음., test_run_build_lite_with_fakes(), test_verify_checks_pass_on_valid_lite_output(), test_verify_full_requires_packages_and_marker(), test_verify_lite_rejects_marker_and_internal() (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.20
Nodes (17): allowed_keys(), allows_row(), describe(), is_allowed(), key(), 수집 허용 장비 범위(scope) — 지금은 30대 전부(`DEFAULT_SCOPE`). ★ 절대 규칙: 허용 목록 밖 장비에는 **파일…, 비교용 키 — 공백·밑줄·하이픈 제거 후 소문자., 설정의 허용 목록. 없거나 비었으면 기본값(빈 목록을 '아무것도 허용 안 함' 으로 오해하지 않는다). (+9 more)

### Community 50 - "Community 50"
Cohesion: 0.15
Nodes (18): _bundled_python(), _discard(), _ensure_deps(), _file_text(), _install_root(), _move(), _pending_dir(), Path (+10 more)

### Community 51 - "Community 51"
Cohesion: 0.20
Nodes (16): embedded(), load(), Path, 보관 샘플(dev/samples/*.html[.gz])에서 원천 행을 꺼내는 **유일한** 헬퍼. - `id="embedded"` script…, → (rows, meta, 파일 sha256). `.gz` 면 풀어서 읽되 sha 는 **파일 그대로** 의 것., read_bytes(), sample_path(), sha256() (+8 more)

### Community 52 - "Community 52"
Cohesion: 0.13
Nodes (15): Aa(), Animation(), Ca(), Da(), ea(), FlipBatch(), la(), ma() (+7 more)

### Community 53 - "Community 53"
Cohesion: 0.17
Nodes (16): _assertThisInitialized(), bt(), gb(), hb(), ic(), jt(), ta(), te() (+8 more)

### Community 54 - "Community 54"
Cohesion: 0.18
Nodes (12): 빈 문자열 = 정상. 아니면 사용자에게 보일 사유. '예외가 안 났다' 이상을 보장하는 관문., _stage_tree(), _verify_staged(), _write_version(), _write_version_to(), _fake_repo(), Path, 업데이트 페이로드 계약 — 스테이징 최상위는 **허용 목록과 정확히 같다**(저장소 루트에 무엇이 있든), 필수 파일이 담기고 개발 전용은… (+4 more)

### Community 55 - "Community 55"
Cohesion: 0.14
Nodes (14): _cli_config(), _count_nas_reads(), count(), spy(), spy_bytes(), _count_report_reads(), spy(), 가짜 NAS 에서 실제로 연 파일 수 — Report(.htm) 와 INI 를 따로 센다. (+6 more)

### Community 56 - "Community 56"
Cohesion: 0.16
Nodes (12): content_sha(), entries(), parametrize, Path, archive/ 보관물 가드(D62) — 지우지 않고 옮긴 파일들이 **원본 그대로**인지. - `archive/SHA256SUMS` 의 모든…, S09: 옛 모듈의 .pyc 가 추적되고 있었다(`__pycache__/aoi_collect.cpython-311.pyc`).…, test_every_archived_file_matches_its_original_fingerprint(), test_everything_under_archive_is_listed() (+4 more)

### Community 57 - "Community 57"
Cohesion: 0.19
Nodes (13): _fingerprint(), _load(), Path, dev/tools/design_bundle.py 가드 — 디자인 프로토타입 번들은 표준 라이브러리만 쓰고, 마크업만 camelCase 를…, (sha256, mtime_ns) — 내용이 같아도 다시 쓰면 mtime 이 바뀌므로 git status 로는 못 잡는 '같은 내용 덮어쓰기'…, S04 가드: 이 모듈의 어떤 테스트도 저장소의 디자인 파일을 다시 쓰지 않는다(sha256·mtime 전후 동일)., 실측 회귀: 스크립트의 `eDay=` 까지 `sc-camel-e-day=` 로 바꾸면 'Missing initializer in const…, S04: build 는 두 출력(단일 HTML · 오프라인 DC)을 넘겨준 경로에만 쓰고 저장소의 추적 파일은 sha256·mtime 까지… (+5 more)

### Community 58 - "Community 58"
Cohesion: 0.15
Nodes (11): _cache_device(), _DeviceIndex, _is_stable_key(), 이번 실행의 장비 목록을 한 번만 색인한다(C09) — 캐시 항목마다 장비 목록을 선형으로 돌며 경로를 정규화하지 않는다. 찾는 순서: 안정…, 캐시에 있는 Report 하나가 지금 수집 대상 장비 중 어디에 속하는지. 파일시스템을 보지 않는다., 출력용 행 — 범위 밖 장비의 캐시는 **지우지 않고 빼기만** 한다. 밀려난 옛 판(`superseded_by`)도 출력에서만 뺀다.…, _rows_from_cache(), path_tail() (+3 more)

### Community 59 - "Community 59"
Cohesion: 0.21
Nodes (8): host_for(), _native(), QEvent, QObject, QWidget, 부모 창 전체를 덮는 오버레이. 한 번에 시트 하나만 띄운다., 모달로 띄우고 누른 버튼을 돌려준다(중첩 이벤트 루프)., SheetHost

### Community 60 - "Community 60"
Cohesion: 0.26
Nodes (10): _full(), _make_zip(), _patch_download(), 최신 코드 받기 도구(scripts/update_code.py) 계약. - 브랜치 이름이 **파일 맨 위**에 있어야 한다(사용자가 직접…, test_main_uses_zip_when_folder_is_not_a_git_checkout(), test_zip_update_check_only_changes_nothing(), test_zip_update_overwrites_changed_keeps_backup_and_never_deletes(), test_zip_update_refuses_incomplete_tree() (+2 more)

### Community 61 - "Community 61"
Cohesion: 0.22
Nodes (13): NamedTuple, app_paths(), _error(), launch_cmd(), Layout, main(), Path, exe_launcher.py — 'exe + app 폴더' 배포의 얇은 런처. **앱 코드 0줄.** 이 파일에 앱 코드를 절대 넣지 마라.… (+5 more)

### Community 62 - "Community 62"
Cohesion: 0.15
Nodes (10): UTF-8(BOM 유무) 또는 한글 Excel 의 cp949 CSV 를 읽어 [{name, root, sub, on, memo}] 로 돌려준다., 이 PC 의 데이터 폴더에 저장한다(utf-8-sig, Excel 호환). NAS 아래 경로면 거부., read_devices_csv(), write_devices_csv(), read_bytes(), 취소되면 아직 시작하지 않은 확인은 하지 않는다 — 이미 들어간 SMB 호출을 끊는다고 주장하지는 않는다., test_cancel_stops_submitting_new_checks(), test_read_csv_cp949_and_utf8_and_aliases() (+2 more)

### Community 63 - "Community 63"
Cohesion: 0.15
Nodes (13): expand_roots(), is_under(), normalize(), 비교용 정규화: 긴 경로 접두 제거 → 절대경로 → normpath → normcase(Windows 는 소문자, / → \\).…, path 가 root 와 같거나 그 아래인가(정규화 후 접두 비교)., Windows 에서 드라이브 문자(X:\\...)가 네트워크 드라이브면 같은 위치의 UNC 경로. 아니면 None. 실패는 조용히 무시., \\\\host\\share\\a\\b → \\\\host\\share (공유 전체를 금지 구역으로)., 등록된 NAS 경로를 금지 구역 목록으로 넓힌다: 네트워크 드라이브는 드라이브 전체 + UNC 동치, UNC 는 공유 루트까지. (+5 more)

### Community 64 - "Community 64"
Cohesion: 0.23
Nodes (12): buildModel(), buildModelLegacy(), buildModelV3(), causeOf(), causeText(), dk(), isPass(), jobKey() (+4 more)

### Community 65 - "Community 65"
Cohesion: 0.22
Nodes (12): base64, build(), bundle_template(), encode_camel_attrs(), main(), offline_variant(), Path, 디자인 프로토타입(docs/design/dashboard-redesign) 빌드 — 오프라인 DC 변형과 **더블클릭으로 열리는 단일… (+4 more)

### Community 66 - "Community 66"
Cohesion: 0.17
Nodes (10): ctx, fs, html, input, path, stub(), vm, ref_fs (+2 more)

### Community 67 - "Community 67"
Cohesion: 0.18
Nodes (5): _Counter, HTMLParser, 스레드 여러 개가 같이 세는 진행 카운터., 모든 <table> 을 행 단위 셀 텍스트 목록으로 모은다(중첩 표는 펼침)., TableParser

### Community 68 - "Community 68"
Cohesion: 0.22
Nodes (11): Report 키의 상대 경로 부분 — 구분자는 `/`, 대소문자는 접는다(SMB 는 대소문자를 구분하지 않는다). 원문 경로는 항목의…, Report 캐시 키 = `<장비 안정 키>|<Report 폴더 아래 상대 경로>`. 드라이브 문자·UNC·Report 폴더…, 옛 절대 경로 키를 상대 경로로 — 장비 경로 아래면 첫 조각(Report 폴더)을 뗀 나머지, 아니면 파일 이름만. 문자열로만 판정한다(OS…, _rel_key(), _rel_under_device(), report_key(), _strip_long_prefix(), parametrize (+3 more)

### Community 69 - "Community 69"
Cohesion: 0.18
Nodes (5): CollectResult, 사용자에게 보여 줄 경고 문장들(ko.py). 종류를 모르는 경고는 원문 오류를 그대로 보여 준다., 접근하지 못한 장비(목록 조회 실패)., 접근은 됐지만 Report 일부를 읽지 못한 장비 — '완료' 로 뭉개면 안 된다., test_stale_token_signals_are_ignored()

### Community 70 - "Community 70"
Cohesion: 0.27
Nodes (8): argparse, changed_files(), check(), is_code(), main(), Path, 코드가 바뀐 변경에 `진행상황.md` 가 함께 있는지 — CI(PR) 용 검사(S14, CLAUDE.md '커밋' 규칙의 두 번째 그물).…, (통과 여부, 이유). 순수 함수 — 테스트가 직접 부른다.

### Community 71 - "Community 71"
Cohesion: 0.33
Nodes (9): build(), graphify_cmds(), inline_scripts(), main(), Path, graphify 코드 지도를 만든다 — 로컬에서도, GitHub Actions(main 푸시마다)에서도 같은 절차. python…, template.html 의 <script> 본문만 이어 붙인다(외부 src 는 없다 — 화면은 바깥 요청 0건)., `inline_js` 는 임시 JS 의 위치. 기본(None)은 호출 시점의 모듈 상수 INLINE_JS — 실제 실행에서는 template… (+1 more)

### Community 72 - "Community 72"
Cohesion: 0.22
Nodes (5): find_pattern(), FoundEntry, `find_pattern` 이 돌려주는 항목 — `os.DirEntry` 에서 수집이 쓰는 부분(name · path · is_file ·…, 폴더 안에서 이름이 `pattern`(Windows 와일드카드 `*` `?`)에 맞는 항목만 — **NAS(SMB 서버)가 거른다**.…, _Stat

### Community 73 - "Community 73"
Cohesion: 0.33
Nodes (9): navCancel(), navGo(), navInd(), navNow(), navParts(), navRest(), navSet(), navState() (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.22
Nodes (9): _fingerprint(), parametrize, ★ 동시에 읽어도 결과가 달라지면 안 된다 — 스레드는 읽기만 하고, 합치는 일은 메인 스레드가 한다., STALE 은 다른 시도가 덮어쓴 INI 라 다시 읽어도 안 돌아오고, 자리표시·실패한 배치는 경로가 없다 — 그런 걸 재시도 대상에 넣으면…, ★ 예전에는 errors='replace' 로 읽어 손상 바이트가 U+FFFD 로 바뀌거나, 못 읽으면 조용히 빈 캐시로 덮어썼다., test_corrupt_cache_is_preserved_as_bad_file_not_overwritten_silently(), test_reading_in_parallel_gives_exactly_the_same_result(), test_recover_targets_only_ini_states_that_can_come_back() (+1 more)

### Community 76 - "Community 76"
Cohesion: 0.28
Nodes (4): Path, 규칙 두 가지를 그대로 지켜본다. ① **범위 밖 장비 폴더는 건드리지 않는다** — 그 폴더나 그 아래를…, Tripwire, wrap()

### Community 77 - "Community 77"
Cohesion: 0.36
Nodes (8): check_rows(), probe(), probe(), _has_report(), _probe_auto(), `_discover_under` 의 읽기 부분 — (찾은 장비들, 로그 문장들). 스레드에서 돌 수 있게 로그를 부르지 않고 돌려준다., UI 의 '연결 확인': 행마다 상태 문자열 키를 돌려준다(ok / auto:<n> / no_report / unreachable /…, test_check_rows_reports_out_of_scope_without_touching()

### Community 78 - "Community 78"
Cohesion: 0.36
Nodes (3): NavBar, QWidget, _repolish()

### Community 79 - "Community 79"
Cohesion: 0.25
Nodes (6): manual_check(), [업데이트 확인] 버튼: ("update", info) | ("latest", {}) | ("held", {"sha","reason"}) |…, test_check_and_manual_hold_when_ci_not_passed(), test_manual_check_reports_tls_failure(), test_manual_check_statuses(), _VerifyFailOpener

### Community 80 - "Community 80"
Cohesion: 0.54
Nodes (7): _example(), _public(), docs/config.example.json 가드(S13) — 헤드리스 설정 예시가 `collect.DEFAULT_CONFIG` 와 조용히…, test_every_default_config_key_is_in_the_example_or_explicitly_excused(), test_example_loads_through_the_cli_loader(), test_example_public_keys_are_a_subset_of_default_config_with_the_same_types(), test_example_scope_and_workers_show_the_real_defaults()

### Community 81 - "Community 81"
Cohesion: 0.29
Nodes (5): QObject, QThread, 업데이트 확인/적용을 UI 밖에서. `mode` ∈ {"check", "apply"}., _UpdateSignals, _UpdateWorker

### Community 82 - "Community 82"
Cohesion: 0.43
Nodes (3): _card(), QWidget, SettingsPage

### Community 84 - "Community 84"
Cohesion: 0.50
Nodes (5): Context(), Db(), Eb(), Et(), fb()

### Community 85 - "Community 85"
Cohesion: 0.40
Nodes (5): (rows, meta) — 열 이름 기반 복원 + 풀 검증., unfold(), 홈 목록은 devices.sort_key 순(AOI-1 · AOI-2 · AOI-3 · AOI-10 — 사전순이면 AOI-10 이 AOI-2…, test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns(), test_unfold_maps_columns_by_name_and_validates_the_pool()

### Community 86 - "Community 86"
Cohesion: 0.40
Nodes (3): fs_spy(), wrap(), _Spy

### Community 87 - "Community 87"
Cohesion: 0.40
Nodes (3): Path, _snapshot(), test_dynamic_no_write_under_nas()

### Community 90 - "Community 90"
Cohesion: 0.50
Nodes (3): is_dark_mode(), QColor, _scrim_color()

### Community 91 - "Community 91"
Cohesion: 0.50
Nodes (4): isolated_data(), Path, 모든 테스트를 임시 홈에서 돌린다. 반환값은 그 홈 경로., set_home()

### Community 92 - "Community 92"
Cohesion: 0.50
Nodes (3): test_git_update_reports_already_up_to_date(), test_git_update_stops_when_working_tree_is_dirty(), fake_git()

### Community 93 - "Community 93"
Cohesion: 0.67
Nodes (3): job_folder_variants(), Report 의 Job 값으로 만들 **정확 경로 후보** — 원문, `2D@XX ` → `2D@XX-`, 끝의 `_0A`/`-0A` 뗀 것,…, test_job_folder_variants_are_exact_names_in_order()

## Knowledge Gaps
- **39 isolated node(s):** `CAUSE_CODES`, `CAUSE_RULES`, `CLOSE`, `devStatus`, `DROPW` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 825 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `make_cfg()` connect `Community 25` to `Community 97`, `Community 36`, `Community 5`, `Community 38`, `Community 9`, `Community 42`, `Community 75`, `Community 12`, `Community 46`, `Community 16`, `Community 23`, `Community 87`, `Community 55`, `Community 26`, `Community 27`, `Community 62`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `collect()` connect `Community 12` to `Community 3`, `Community 9`, `Community 19`, `Community 20`, `Community 23`, `Community 25`, `Community 26`, `Community 27`, `Community 33`, `Community 36`, `Community 38`, `Community 42`, `Community 45`, `Community 46`, `Community 49`, `Community 55`, `Community 58`, `Community 62`, `Community 67`, `Community 68`, `Community 75`, `Community 87`, `Community 97`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `LoadingOverlay` connect `Community 22` to `Community 89`, `Community 47`, `Community 15`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `collect()` (e.g. with `read_one()` and `test_zero_new_rows_but_state_change_still_saves()`) actually correct?**
  _`collect()` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `MainWindow` (e.g. with `CollectPage` and `DevicesPage`) actually correct?**
  _`MainWindow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CAUSE_CODES`, `CAUSE_RULES`, `CLOSE` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.021457821457821456 - nodes in this community are weakly interconnected._