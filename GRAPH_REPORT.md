# Graph Report - AOI-capacity  (2026-09-29)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2482 nodes · 5797 edges · 113 communities (102 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 247 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8362591b`
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
- Community 74
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
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112

## God Nodes (most connected - your core abstractions)
1. `collect()` - 90 edges
2. `make_cfg()` - 81 edges
3. `MainWindow` - 44 edges
4. `rows_for_report()` - 40 edges
5. `write_html()` - 40 edges
6. `h()` - 38 edges
7. `download_and_apply()` - 37 edges
8. `r()` - 36 edges
9. `parse_report()` - 35 edges
10. `render()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `log()`  [INFERRED]
  scripts/internal/portable_build.py → test.py
- `_emit()` --calls--> `progress()`  [INFERRED]
  aoi_capacity/utils/updater.py → test.py
- `window()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `read_one()` --calls--> `progress()`  [INFERRED]
  aoi_capacity/collect.py → test.py
- `test_zero_new_rows_but_state_change_still_saves()` --indirect_call--> `collect()`  [INFERRED]
  dev/tests/test_cache_identity.py → aoi_capacity/collect.py

## Import Cycles
- None detected.

## Communities (113 total, 11 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (63): B(), CAUSE_CODES, CAUSE_RULES, CLOSE, devStatus, di(), DROPW, embCols (+55 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (50): 헤드리스 실행(작업 스케줄러용). GUI 와 같은 수집 코어를 쓴다. python -m aoi_capacity.cli # config.json…, 수집 코어 — Camtek AOI BatchReport(.htm) 와 각 Wafer 의 WaferInfo.ini 를 읽어 원천 행을 만들고…, 출력 직전: `issue_codes` 가 있고 `data_issue` 가 빈 행만 문장을 채운 **사본**으로 바꾼다(캐시 행은 건드리지…, render_issue_rows(), 장비 목록 — devices.csv 읽기/쓰기, 장비 폴더 판정, 표시명·정렬. CSV 열: 장비명, NAS경로, 폴더, 사용, 메모 (영문…, 사용자에게 보이는 문구는 전부 ko.py 에 산다. 호출부는 `i18n.KO.상수` 로 쓴다. 표준 라이브러리만 쓰는 순수 상수 모듈이라…, AOI Capacity — Camtek AOI 장비 가동률 대시보드. 패키지 구성 - collect.py 수집 코어(표준 라이브러리만).…, NAS 읽기 전용 안전장치. ★ 절대 규칙: NAS 원본(Report/Scanresult 가 있는 공유) 아래에는 어떤 파일도 만들거나… (+42 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (70): _a(), Ae(), Ao(), Ba(), be(), cb(), ce(), $d() (+62 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (62): plan_run(), UI 안내용 — 캐시만 보고 이번 실행이 어떤 성격인지 알려준다(NAS 접근 없음). 행을 다시 계산하지 않고 결과를 메모한다.…, RunPlan, make_cfg(), _add_report(), _cache_of(), _dev_dir(), _entry_fp() (+54 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (59): test_ini_memo_lets_concurrent_readers_share_one_open(), slow(), at(), busy(), _clean_batches(), globals_(), _hhmm(), meta() (+51 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (54): output_dir(), output_html(), prefs_file(), load(), migrate(), patch(), Prefs, Any (+46 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (34): _fake_out(), Path, build.py / portable_build.py — 순수 판단 로직(명령 구성·검증 목록·app 복사). 네트워크·PyInstaller…, 다운로드·pip 을 가짜로 바꿔 흐름만 확인: 런타임 준비 → pip → app/ → VERSION, 표식 없음., test_run_build_lite_with_fakes(), test_verify_checks_pass_on_valid_lite_output(), test_verify_full_requires_packages_and_marker(), test_verify_lite_rejects_marker_and_internal() (+26 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (18): _card(), CollectPage, _label(), ModeCard, _PlanWorker, QThread, QWidget, [(글자, 종류)] — 종류: rec(추천 · 초록) · warn(주의 · 노랑) · slow(회색) · "" (파랑). (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (47): applySettings(), behindAt(), canAnim(), cc(), countUp(), deckSnap(), enterAnim(), enterView() (+39 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (42): cache_file(), data_root(), default_devices_csv(), devices_csv_path(), _ensure_dir(), ensure_user_files(), install_root(), log_file() (+34 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (45): filecmp, copy_app_tree(), _copytree(), _default_branch_name(), _fetch_runtime(), _git_head(), _q(), _import_app_module() (+37 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (40): collections, html_parser, collect_one(), copy_ini_for(), copy_report(), diagnose(), find_subdir(), list_folder() (+32 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (41): _assets_snapshot(), _fingerprint(), _load(), _on(), _package_assets_untouched(), Path, dev/tools/graphify_build.py 가드 — 임시 JS 는 절대 남지 않고(테스트는 패키지 폴더에 아무것도 만들지 않고),…, S04 수락 기준: 도구의 코드 경로를 전부 태워도(성공·실패·예외) 패키지 폴더의 이름 집합·template 지문이 그대로다. (+33 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (38): _advance_cursor(), _check(), collect(), CollectCancelled, _mark_device_status(), _mode_args(), Exception, 인자가 None 이면 cfg 값을 쓴다. `full` 은 `rebuild_all` 의 별칭(D60). 돌려주는 값: (refresh 창 일수,… (+30 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (36): _assign_device_keys(), cache_status(), _Dirty, _empty_cache(), _entry_sort_stamp(), _fresh_key(), _load_cache(), _migrate_cursors() (+28 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (37): parse_report(), Report 한 장을 (job, setup, lot, wafer 행, 요약)으로 푼다. ★ Scanresult 경로의 출처는 **Report…, Report 한 장 → Wafer 행들(+ 통째로 실패한 배치면 배치 행 하나). `backups` 가 있으면 INI 를…, rows_for_report(), _live_ini(), 다시 검사하면 INI 가 덮어써져 옛 Report 행에도 '나중 시각' 이 붙는다 — 그 시간은 쓰지 않는다., 검사된 Wafer 가 하나도 없는 시도 — Scanresult 에 흔적이 없어 Batch 시각만이 근거다., AOI-1 은 Report 에 Job/Setup 이 없고 시각이 슬래시·12시간제다 — 파일명 규칙으로 끝까지 돌아야 한다. (+29 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (39): barsHtml(), bringToFront(), clock(), closeTop(), cmpDev(), cnt(), collectChip(), cut() (+31 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (11): _c(), DeviceStrip, LoadingOverlay, ProgressStrip, _PulseDot, QColor, QEvent, QObject (+3 more)

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (36): deps_blocked(), download_and_apply(), _emit(), last_error(), CI 게이트 → 그 SHA 의 archive zip → 검사·해제 → 허용 목록만 스테이징 → 검증 → (exe) app.new 로…, 직전 적용이 '새 패키지를 설치하지 못해서' 포기됐는지(exe 모드) — UI 가 새 배포본을 받으라고 안내., _app(), _branch_zip() (+28 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (29): display_name(), is_floor4(), 폴더명(+ 행 이름·메모 힌트)에서 표시명을 만든다. 폴더명 자체는 바꾸지 않는다. `AOI-1` → `AOI-1` · `1~7 AOI-1`…, 첫 실행 부트스트랩 — lite 배포의 의존성(requirements.txt) 설치 판단·실행. exe-lite…, AST, builtins, Call, 테스트 공통 픽스처. - 모든 테스트는 임시 HOME/LOCALAPPDATA 아래에서 돈다 → 개발자의 실제 설정·캐시를 건드리지 않는다.… (+21 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (33): _active(), _build_html(), _embedded(), _fixture_rows(), _meta(), page(), Path, 결과 HTML 의 클릭 경로를 진짜 Chromium(Playwright)으로 실측한다 — S06(개선 계획 P4, 9/20). 문자열… (+25 more)

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (35): load_config(), config.json 을 읽어 cfg 를 만든다. 상대 경로 기본값은 config.json 이 있는 폴더 기준. GUI 의 prefs 와…, check_or_raise(), ConfigError, dashboard_settings(), fatal(), is_single_name(), normalize_config() (+27 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (32): _cache_device(), _carry_over(), _DeviceIndex, _entry_newest(), 이번 실행의 장비 목록을 한 번만 색인한다(C09) — 캐시 항목마다 장비 목록을 선형으로 돌며 경로를 정규화하지 않는다. 찾는 순서: 안정…, 캐시에 있는 Report 하나가 지금 수집 대상 장비 중 어디에 속하는지. 파일시스템을 보지 않는다., 전체 재구축(rebuild): 이번에 **보지 못한** 이력을 원 캐시에서 후보 캐시로 옮긴다 — 지우는 재구축이 아니다. 옮기는 것: (1)…, device_id() (+24 more)

### Community 23 - "Community 23"
Cohesion: 0.09
Nodes (35): _check_zip_entries(), deps_changed(), _describe_err(), _http_get(), _is_ssl_verify_error(), latest_commit(), _latest_via_api(), _latest_via_atom() (+27 more)

### Community 24 - "Community 24"
Cohesion: 0.10
Nodes (34): _batch_from_rows(), cause_field(), failed_batch_row(), _first(), _is_error_row(), is_unmapped_status(), _lead_error_row(), norm_causes() (+26 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (28): _Counter, _list_new_reports(), nas_group(), 같은 NAS 를 가리키는 경로끼리 같은 값 — 동시 읽기를 NAS 마다 나눠 배정하는 열쇠(`_run`).…, 작업들을 동시에(또는 한 줄로) 돌리고 **입력 순서 그대로** 결과를 돌려준다. `group` 을 주면 작업을 NAS 별로…, 1차 패스: 장비마다 Report 폴더를 한 번 나열(scandir+stat 만)해 읽을 파일을 고른다. NAS 읽기 전용. 장비 30대를 한…, 스레드 여러 개가 같이 세는 진행 카운터., _run() (+20 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (31): _payload(), 실행별 고유 임시 이름 — 동시에 도는 GUI/CLI 가 서로의 임시 파일을 밟거나 지우지 않게., 캐시를 **트랜잭션**으로 쓴다(C15): 고유 임시 파일 → flush+fsync → 다시 읽어 검증 → `os.replace`. 어느…, 접힌 행 + meta → HTML 에 박을 JSON 문자열. `</` → `<\\/` 는 JSON 으로는 같은 문자열이면서 HTML 파서가…, template.html 에 데이터를 넣어 출력 폴더에 HTML 한 장을 쓴다. 고유 임시 파일에 쓴 뒤 교체(원자적), 실패하면 자기 임시…, CSV 는 사람이 읽는 부가 산출물 — 고유 임시 파일에 쓰고 교체하며, 실패하면(Excel 잠금) 자기 임시 파일만 지우고 OSError 를…, _save_cache(), _unique_tmp() (+23 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (31): 방금 쓴 임시 파일을 strict 로 다시 읽어 구조가 맞는지 본다 — 반쯤 쓴 파일이 정상 캐시로 승격되지 않게., read_ini(), _validate_cache_file(), 파일 전체 바이트 — `os.open` + 크기(fstat) + `os.read` 대개 **한 번**. `open(path,…, 파일 전체 바이트(읽기 전용, `_read_all`)., `open(path, "r", encoding=, errors=).read()` 와 같은 결과(보편 줄바꿈: \\r\\n · \\r →…, _read_all(), read_bytes() (+23 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (30): (rows, meta) — 열 이름 기반 복원 + 풀 검증., unfold(), _cache_of(), _count_htm_reads(), spy(), _csv(), _fingerprint(), 캐시 정체성·저장 규칙(P3-A · C03 · C04 · C09 · C07). - C03: Report 키 = `(장비 안정 키 |… (+22 more)

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (28): _backup_roots(), 장비 dict 의 `scan_dirs`(devices.with_dirs 가 붙임) → (경로, 경계 날짜) 목록. 맨 앞(지금 폴더)은 뺀다., _pool_size(), 이 장비 폴더 안의 `Scanresult*` 폴더 전부 — 맨 앞은 지금 쓰는 폴더, 뒤는 백업들(경계 이른 순, 경계를 못 읽은 것은 맨…, 이 장비에서 실제로 쓰는 Report·Scanresult 폴더 이름을 붙인다(장비마다 다르다)., scan_dirs_of(), with_dirs(), make_device() (+20 more)

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (21): _fingerprint(), parametrize, Path, 샘플 수집 도구(scripts/collect_sample.py) 계약. 현장에서 사용자가 직접 돌리는 도구라 두 가지를 반드시 지켜야 한다.…, AOI-25 는 Report 가 아니라 Reports 다 — 설정 없이도 찾아낸다., 이름을 짐작할 수 없으면 그 폴더 안에 무엇이 있는지 보여 준다., 장비 경로는 사용자가 직접 고치는 값이라 파일 위쪽에 있어야 한다., ★ Lot 이 비면 경로에서 그 칸이 사라져 **Setup 폴더 전체**(= 다른 Lot 들)를 나열하게 된다. 실물 AOI-18 에서 그렇게… (+13 more)

### Community 31 - "Community 31"
Cohesion: 0.14
Nodes (5): _CheckWorker, DevicesPage, QThread, QWidget, 연결 확인' — NAS 폴더 존재 여부를 UI 스레드 밖에서 본다(읽기만).

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (25): itertools, platform, random, stat, statistics, _ask(), _ask_int(), _ask_levels() (+17 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (25): _attach_dirs(), _dedupe_sort(), devices_from_csv(), devices_from_rows(), discover_devices(), _discover_under(), _log(), _norm_root() (+17 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (24): build_exe(), clean_stale_output(), _default_run(), _dir_size_mb(), _ensure_venv(), exe_out_dirname(), import_probe_cmd(), _load_portable_impl() (+16 more)

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (23): deps_installed(), deps_marker(), ensure_deps(), pip_install_cmd(), Path, 실제 요구사항 줄만(주석·빈 줄 제거). 주석만 바뀐 것을 '의존성 변경' 으로 오인하지 않게., 이 requirements 내용으로 설치가 끝났는가(표식 내용 = 지문). req_text 가 None 이면 존재만 본다., 빠진 것만 채운다 — `--upgrade` 없음(CLAUDE.md 규칙 7). `-s` 로 개인 site-packages 를 배제. (+15 more)

### Community 37 - "Community 37"
Cohesion: 0.08
Nodes (21): fake_nas(), _no_startup_side_effects(), qapp(), _qt_app(), tmp/nas/X 아래 AOI-9, AOI-10 과 tmp/nas/M-AOI-8(루트가 장비)을 만든다. 반환: (nas_root,…, _no_real_subprocess(), _launch(), page_factory() (+13 more)

### Community 38 - "Community 38"
Cohesion: 0.09
Nodes (19): _IniMemo, issue_text(), 코드 목록 → 사람이 읽는 문장(ko.py). 아는 코드만 문장으로, 모르는 코드는 원문 항목 그대로., 수집 한 번 안에서 같은 WaferInfo.ini 를 **한 번만** 연다. 같은 Wafer 가 여러 Report 에 나오면(재검사) INI…, → ("ok", 필드 dict) · ("missing", None) · ("error", 예외), 파일 존재만(`MoveResultFlag`) — 같은 경로는 한 번만 stat 한다. 읽기 전용., _backup_ini(), 9/15 배치인데 INI 가 `Scanresult_Back up_260918`(9/18 이전을 옮긴 곳)에만 있다 — 첫 확인에 찾고 백업… (+11 more)

### Community 39 - "Community 39"
Cohesion: 0.15
Nodes (22): _is_stable_key(), 출력용 행 — 범위 밖 장비의 캐시는 **지우지 않고 빼기만** 한다. 밀려난 옛 판(`superseded_by`)도 출력에서만 뺀다.…, _rows_from_cache(), allowed_keys(), allows_row(), describe(), is_allowed(), key() (+14 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (17): 사용자에게 보이는 한국어 문구 — 이 파일에만 둔다. 규칙 - 이름은 `기능_역할` (BTN_, NAV_, COLLECT_, UPDATE_,…, 결과 HTML(template.html) 의 **제품 제약** — 자바스크립트를 실행하지 않고 글자로만 보는 것은 여기까지다(S05,…, 옛 장비-일 추정(D15) · PyQt GUI 모드 · 옛 업데이트 상수 · '수집 예정' 자리표시(D08) · 열람 시각 문구(D11)는…, D05: 팝업은 role=dialog · aria-modal · 제목 id(aria-labelledby) 를 갖는다. 포커스가 실제로 그리…, Report 는 사람이 연 그 탭이 연다 — 새 탭에 이 화면의 opener 를 주지 않는다., 제3자 라이브러리(GSAP+Flip · animate.css 일부)를 **인라인**으로 싣는다 — 그 라이선스 머리말의 홈페이지 주소와…, vendor 블록(GSAP·Flip)도 요청 API 를 쓰지 않고, 안에 든 주소는 라이선스·네임스페이스뿐이다., GSAP(+Flip) 와 animate.css 일부를 파일 안에 그대로 싣는다 — 라이선스 머리말을 지우지 않는다. (+9 more)

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (23): _app_root(), check_for_update(), current_version(), _default_branch(), ensure_version_file(), _git_head(), _git_head_ref(), _identity() (+15 more)

### Community 42 - "Community 42"
Cohesion: 0.20
Nodes (17): _bundle(), _layout(), _marker(), _mk(), Path, exe_launcher.py — 교체 상태기계. 이 런처는 업데이트되지 않으므로 여기 로직이 틀리면 나중에 못 고친다. 핵심 불변식: 어떤…, test_first_run_uses_the_console_python(), test_later_runs_are_windowless() (+9 more)

### Community 43 - "Community 43"
Cohesion: 0.10
Nodes (20): _cli_config(), _count_nas_reads(), count(), spy(), spy_bytes(), _count_report_reads(), spy(), 가짜 NAS 에서 실제로 연 파일 수 — Report(.htm) 와 INI 를 따로 센다. (+12 more)

### Community 44 - "Community 44"
Cohesion: 0.17
Nodes (18): apply_to_app(), color_mode(), colors(), normalize_color_mode(), palettes(), parse_template_tokens(), 테마 — template.html 의 CSS 토큰을 그대로 Qt 로 가져온다. 단일 출처: `assets/template.html` 의…, template.html 에서 :root 와 :root[data-theme="light"] 의 --토큰: #hex 를 뽑는다. (+10 more)

### Community 45 - "Community 45"
Cohesion: 0.15
Nodes (20): _bundled_python(), _discard(), _ensure_deps(), _file_text(), _install_root(), _move(), _pending_dir(), _promote_in_place() (+12 more)

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (17): ctypes, _no_input(), parametrize, C16 — 의존성 설치 실패 안내: pythonw(`sys.stdin is None` → `input()` 이 RuntimeError)·EOF…, PyQt6 import 는 `_run_gui` 안에만 — 설치에 실패한 패키지를 안내 경로에서 다시 요구하지 않는다., test_console_path_waits_for_enter(), test_ensure_deps_failure_notifies_with_log_path_and_returns_false(), test_input_failures_fall_back_without_raising() (+9 more)

### Community 47 - "Community 47"
Cohesion: 0.14
Nodes (17): ms_since(), now_s(), op_isdir(), op_isfile(), op_open_read(), op_os_read_once(), op_stat(), 앱과 같은 방식(open 'rb' 전체 읽기). (+9 more)

### Community 48 - "Community 48"
Cohesion: 0.15
Nodes (16): 갱신 뒤 다시 실행할 인자 — `--update` 만 뺀다(같은 인자로 한 번만 다시 돌고, 자식은 다시 갱신하지 않는다)., 갱신 뒤 **자식 프로세스**로 수집을 다시 실행하고 끝날 때까지 기다린 뒤 그 종료 코드를 돌려준다(C14). Windows 의…, rerun_args(), rerun_without_update(), _bat(), C14 — `cli --update` 는 갱신 뒤 exec 가 아니라 **자식 프로세스**로 수집을 다시 돌리고 종료 코드를 그대로 돌려준다.…, 호출로 검사한다(주석·docstring 은 exec 를 설명해도 된다)., test_cli_never_execs() (+8 more)

### Community 49 - "Community 49"
Cohesion: 0.18
Nodes (17): embedded(), load(), Path, 보관 샘플(dev/samples/*.html[.gz])에서 원천 행을 꺼내는 **유일한** 헬퍼. - `id="embedded"` script…, → (rows, meta, 파일 sha256). `.gz` 면 풀어서 읽되 sha 는 **파일 그대로** 의 것., read_bytes(), sample_path(), sha256() (+9 more)

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (17): newest_of(), _embed_rows(), parse_dt(), HTML 에 박을 형태로 접는다 — `POOLED_COLS` 는 문자열 풀의 번호로 바꾼다. 장비 30대 × 보관 90일이면 행이 십수만…, 같은 자재일 수 있는 행을 묶는 열쇠 — Wafer ID 의 영숫자만 대문자로. 화면의 자재 키(`matKey` = Job 묶음|Report…, 결과 HTML 이 한도를 넘을 때(9/23) 행을 **날짜 구간**으로 나눈다 → [(첫날, 끝날, 그 파일에 넣을 행)] 새 구간부터. -…, split_rows_by_day(), build() (+9 more)

### Community 51 - "Community 51"
Cohesion: 0.15
Nodes (11): is_dark_mode(), host_for(), _native(), QColor, QEvent, QObject, QWidget, 부모 창 전체를 덮는 오버레이. 한 번에 시트 하나만 띄운다. (+3 more)

### Community 52 - "Community 52"
Cohesion: 0.14
Nodes (13): content_sha(), entries(), parametrize, Path, archive/ 보관물 가드(D62) — 지우지 않고 옮긴 파일들이 **원본 그대로**인지. - `archive/SHA256SUMS` 의 모든…, S09: 옛 모듈의 .pyc 가 추적되고 있었다(`__pycache__/aoi_collect.cpython-311.pyc`).…, test_every_archived_file_matches_its_original_fingerprint(), test_everything_under_archive_is_listed() (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.13
Nodes (15): Aa(), Animation(), Ca(), Da(), ea(), FlipBatch(), la(), ma() (+7 more)

### Community 54 - "Community 54"
Cohesion: 0.21
Nodes (12): CollectorWorker, QThread, _collect_signals(), CollectorWorker — 스레드를 띄우지 않고 run() 을 직접 불러 시그널·취소·실패 경로를 검사한다., ★ C06: Excel 이 CSV 를 잡고 있어도 HTML·캐시는 정상 — done 으로 끝내되 상태는…, test_csv_lock_completes_with_warnings_not_failed(), locked(), test_failure_is_reported_not_raised() (+4 more)

### Community 55 - "Community 55"
Cohesion: 0.13
Nodes (14): main(), _print(), _progress_printer(), cb(), _gate_info(), manual_check(), 공통 판정: ("update", info) | ("held", {"sha","reason","error"})., [업데이트 확인] 버튼: ("update", info) | ("latest", {}) | ("held", {"sha","reason"}) |… (+6 more)

### Community 56 - "Community 56"
Cohesion: 0.13
Nodes (14): _drive_host(), expand_roots(), 설정의 nas_roots + devices.csv 의 NAS경로(사용 여부 무관) 전부., Windows 에서 드라이브 문자(X:\\...)가 네트워크 드라이브면 같은 위치의 UNC 경로. 아니면 None. 실패는 조용히 무시., \\\\host\\share\\a\\b → \\\\host\\share (공유 전체를 금지 구역으로)., 등록된 NAS 경로를 금지 구역 목록으로 넓힌다: 네트워크 드라이브는 드라이브 전체 + UNC 동치, UNC 는 공유 루트까지., roots_for_cfg(), _share_root() (+6 more)

### Community 57 - "Community 57"
Cohesion: 0.13
Nodes (16): backup_cutoff(), _candidates(), dir_key(), _dirs_of(), find_subdir(), date, 폴더 이름·경로의 **Windows 의미** 비교 키 — 대소문자 · `/`↔`\\` · 끝 구분자 차이를 지운다(C05). NAS 는…, 두 폴더 이름(또는 경로)이 Windows 의미로 같은 곳인가. (+8 more)

### Community 58 - "Community 58"
Cohesion: 0.17
Nodes (16): _assertThisInitialized(), bt(), gb(), hb(), ic(), jt(), ta(), te() (+8 more)

### Community 59 - "Community 59"
Cohesion: 0.18
Nodes (12): 빈 문자열 = 정상. 아니면 사용자에게 보일 사유. '예외가 안 났다' 이상을 보장하는 관문., _stage_tree(), _verify_staged(), _write_version(), _write_version_to(), _fake_repo(), Path, 업데이트 페이로드 계약 — 스테이징 최상위는 **허용 목록과 정확히 같다**(저장소 루트에 무엇이 있든), 필수 파일이 담기고 개발 전용은… (+4 more)

### Community 60 - "Community 60"
Cohesion: 0.12
Nodes (11): `진행상황.md` · `CLAUDE.md` 회귀 가드 — 세션이 바뀌어도 이어서 일할 수 있게 하는 파일이라 형식이 계약이다. 이 파일의…, ★ git 은 기본으로 한글 경로를 `\\354\\247…` 로 내놓는다 — 그대로 비교하면 후크가 늘 막는다., 확정된 결정은 번호로 이야기한다 — 빠지거나 겹치면 '사용자가 뭘 정했더라' 를 못 찾는다., 맨 위 항목은 실제로 있는 커밋이어야 한다 — 손으로 적다 틀리면 이력을 못 따라간다., ★ 문서가 조용히 낡는 걸 막는다 — 수집 범위 대수는 코드가 정답이다., 규칙은 CLAUDE.md 한 곳에만 — 베껴 두면 따로 낡는다., test_decision_numbers_are_unique_and_unbroken(), test_hook_reads_the_korean_file_name_correctly() (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.17
Nodes (14): _fail_move_when(), _loose_app(), parametrize, Path, 비-exe loose 폴더: 항목 4개(파일 2 + 폴더 2). 스테이징 트리는 같은 이름에 새 내용., _move 실패 주입 — predicate(src, dst) 가 참인 첫 호출에서 OSError., _snapshot(), test_latest_self_healing_retries_default_branch() (+6 more)

### Community 62 - "Community 62"
Cohesion: 0.19
Nodes (13): _fingerprint(), _load(), Path, dev/tools/design_bundle.py 가드 — 디자인 프로토타입 번들은 표준 라이브러리만 쓰고, 마크업만 camelCase 를…, (sha256, mtime_ns) — 내용이 같아도 다시 쓰면 mtime 이 바뀌므로 git status 로는 못 잡는 '같은 내용 덮어쓰기'…, S04 가드: 이 모듈의 어떤 테스트도 저장소의 디자인 파일을 다시 쓰지 않는다(sha256·mtime 전후 동일)., 실측 회귀: 스크립트의 `eDay=` 까지 `sc-camel-e-day=` 로 바꾸면 'Missing initializer in const…, S04: build 는 두 출력(단일 HTML · 오프라인 DC)을 넘겨준 경로에만 쓰고 저장소의 추적 파일은 sha256·mtime 까지… (+5 more)

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (11): UTF-8(BOM 유무) 또는 한글 Excel 의 cp949 CSV 를 읽어 [{name, root, sub, on, memo}] 로 돌려준다., 이 PC 의 데이터 폴더에 저장한다(utf-8-sig, Excel 호환). NAS 아래 경로면 거부., read_devices_csv(), write_devices_csv(), 취소되면 아직 시작하지 않은 확인은 하지 않는다 — 이미 들어간 SMB 호출을 끊는다고 주장하지는 않는다., test_cancel_stops_submitting_new_checks(), test_read_csv_cp949_and_utf8_and_aliases(), test_read_csv_without_header_and_comments() (+3 more)

### Community 64 - "Community 64"
Cohesion: 0.15
Nodes (6): QObject, QThread, QWidget, 업데이트 확인/적용을 UI 밖에서. `mode` ∈ {"check", "apply"}., _UpdateSignals, _UpdateWorker

### Community 65 - "Community 65"
Cohesion: 0.19
Nodes (13): job_alias(), model_version(), template.html 에서 **기계적으로** 뽑는 사실들 — 문서(CLAUDE.md)와 코드가 어긋나는지 볼 때의 코드 쪽 값. Node…, `const JOB_ALIAS={ "원문":"표기명", … };` 블록을 dict 로. 줄마다 항목 하나라는 형식을 검증한다., `const <name>=[ ["CODE",/regex/i], … ];` → [(code, pattern)] — 파이썬…, 두 주석 표식 사이 — 표식이 없으면 예외(조용히 빈 문자열을 검사해 통과하지 않는다)., rules(), section() (+5 more)

### Community 66 - "Community 66"
Cohesion: 0.22
Nodes (13): NamedTuple, app_paths(), _error(), launch_cmd(), Layout, main(), Path, exe_launcher.py — 'exe + app 폴더' 배포의 얇은 런처. **앱 코드 0줄.** 이 파일에 앱 코드를 절대 넣지 마라.… (+5 more)

### Community 67 - "Community 67"
Cohesion: 0.23
Nodes (12): buildModel(), buildModelLegacy(), buildModelV3(), causeOf(), causeText(), dk(), isPass(), jobKey() (+4 more)

### Community 68 - "Community 68"
Cohesion: 0.26
Nodes (12): _ci_gate(), _is_full_sha(), (통과, 사유). 대상 SHA 로 필수 워크플로가 **성공 완료**한 실행이 하나라도 있어야 통과. 이전 커밋의 성공·진행 중·건너뜀·취소는…, _run(), _runs(), _serve_runs(), test_atom_fallback_and_error_recording(), fake_get() (+4 more)

### Community 69 - "Community 69"
Cohesion: 0.22
Nodes (12): base64, build(), bundle_template(), encode_camel_attrs(), main(), offline_variant(), Path, 디자인 프로토타입(docs/design/dashboard-redesign) 빌드 — 오프라인 DC 변형과 **더블클릭으로 열리는 단일… (+4 more)

### Community 70 - "Community 70"
Cohesion: 0.24
Nodes (13): allocate(), log(), 조회용 명령(net use · PowerShell Get-*). 실패해도 계속한다., 묶음마다 Report 단위로 섞어 단계별 풀로 나눈다 — 단계끼리 같은 경로를 만지지 않는다., real_collect_summary(), _run(), run_cmd(), _run_real() (+5 more)

### Community 71 - "Community 71"
Cohesion: 0.17
Nodes (12): _cache_summary(), _needs_recovery(), 누락 복구 대상인가 — INI 를 못 찾았거나 읽다 실패한 행이 하나라도 있는 Report. 밀려난 옛 판(superseded)은 대상이…, 계획 조회에 필요한 것만 — Report 수 · 장비 커서 수 · 누락 복구 대상 수 · Report 수정시각 목록(refresh 창…, 동시에 몇 개를 읽을지. 설정이 1 이하면 한 줄로 읽는다(예전 동작)., _workers(), parametrize, STALE 은 다른 시도가 덮어쓴 INI 라 다시 읽어도 안 돌아오고, 자리표시·실패한 배치는 경로가 없다 — 그런 걸 재시도 대상에 넣으면… (+4 more)

### Community 72 - "Community 72"
Cohesion: 0.17
Nodes (12): job_folder_variants(), lot_tokens(), Lot 이름에서 작업 표기를 읽는다. 토큰이 통째로 맞을 때만 — `RETURN`·`REX`·`TESTER`·`RW` 는 걸리지 않는다.…, Report 의 Job 값으로 만들 **정확 경로 후보** — 원문, `2D@XX ` → `2D@XX-`, 끝의 `_0A`/`-0A` 뗀 것,…, scan_type(), parametrize, test_job_folder_variants_are_exact_names_in_order(), test_norm_status() (+4 more)

### Community 73 - "Community 73"
Cohesion: 0.17
Nodes (10): ctx, fs, html, input, path, stub(), vm, ref_fs (+2 more)

### Community 74 - "Community 74"
Cohesion: 0.23
Nodes (11): _git(), _load(), parametrize, Path, dev/tools/progress_doc_check.py 가드(S14) — 코드+문서 통과 · 코드만 실패 · 문서만 통과, 그리고 실제…, 로컬 후크(dev/hooks/pre-commit)와 CI 검사가 같은 코드 경로를 본다 — 한쪽만 통과하는 변경이 없게., 두 커밋짜리 브랜치: 첫 커밋이 코드, 둘째 커밋이 문서 — 마지막 커밋만 보면 '코드 없음' 으로 잘못 통과하고, 범위로 보면 동반으로…, test_check_requires_the_doc_only_when_code_changed() (+3 more)

### Community 75 - "Community 75"
Cohesion: 0.29
Nodes (9): part_re(), `part_name` 이 만든 이름만 맞는 정규식 — 옛 분할 파일을 찾아 정리할 때 이 모양 밖의 파일은 절대 건드리지 않는다., _cfg(), _embedded(), _model(), Path, 결과 HTML 분할(9/23) — 한도(`split_mb`)를 넘으면 기간별 자립형 HTML 여러 장. - 가장 최근 구간이 원래 이름, 옛…, test_no_split_below_the_limit_and_stale_parts_are_cleaned_but_nothing_else() (+1 more)

### Community 76 - "Community 76"
Cohesion: 0.18
Nodes (5): CollectResult, 사용자에게 보여 줄 경고 문장들(ko.py). 종류를 모르는 경고는 원문 오류를 그대로 보여 준다., 접근하지 못한 장비(목록 조회 실패)., 접근은 됐지만 Report 일부를 읽지 못한 장비 — '완료' 로 뭉개면 안 된다., test_stale_token_signals_are_ignored()

### Community 77 - "Community 77"
Cohesion: 0.22
Nodes (10): analyze(), _diff(), dist(), _dt_of(), med_ci(), parse_ini_bytes(), pct(), collect.read_ini 와 같은 규칙으로 이미 읽은 바이트를 푼다(다시 열지 않는다). (+2 more)

### Community 78 - "Community 78"
Cohesion: 0.27
Nodes (10): check_rows(), probe(), probe(), _entry(), _has_report(), _probe_auto(), 장비 하나 — 표시명/경로/안정 키/예전 이름 후보., `_discover_under` 의 읽기 부분 — (찾은 장비들, 로그 문장들). 스레드에서 돌 수 있게 로그를 부르지 않고 돌려준다. (+2 more)

### Community 79 - "Community 79"
Cohesion: 0.27
Nodes (8): argparse, changed_files(), check(), is_code(), main(), Path, 코드가 바뀐 변경에 `진행상황.md` 가 함께 있는지 — CI(PR) 용 검사(S14, CLAUDE.md '커밋' 규칙의 두 번째 그물).…, (통과 여부, 이유). 순수 함수 — 테스트가 직접 부른다.

### Community 80 - "Community 80"
Cohesion: 0.33
Nodes (9): build(), graphify_cmds(), inline_scripts(), main(), Path, graphify 코드 지도를 만든다 — 로컬에서도, GitHub Actions(main 푸시마다)에서도 같은 절차. python…, template.html 의 <script> 본문만 이어 붙인다(외부 src 는 없다 — 화면은 바깥 요청 0건)., `inline_js` 는 임시 JS 의 위치. 기본(None)은 호출 시점의 모듈 상수 INLINE_JS — 실제 실행에서는 template… (+1 more)

### Community 81 - "Community 81"
Cohesion: 0.22
Nodes (9): _issue_dec(), _issue_enc(), issue_field(), parse_issue_codes(), 인자 안의 구분 문자만 이스케이프한다(경로·한글은 그대로 읽히게) — 되돌리기는 `_issue_dec`., [(코드, *인자)] → `issue_codes` 열 값. 예:…, `issue_codes` 열 값 → [(코드, [인자…])]. 빈 값이면 []. 모르는 코드도 그대로 돌려준다(버리지 않는다)., parametrize (+1 more)

### Community 82 - "Community 82"
Cohesion: 0.25
Nodes (9): _list_all(), one(), `since`(커서) 이후에 생겼을 수 있는 Report 의 이름 패턴 — 커서 날짜 하루 전부터 오늘 하루 뒤까지(설비 시계 차이 여유).…, Report 폴더 전체 나열 — `FULL_LISTER`(Windows 대량 조회)가 있으면 그것, 실패하면 scandir(폴더가 없으면…, report_name_patterns(), scandir(), _list_files(), progress() (+1 more)

### Community 83 - "Community 83"
Cohesion: 0.22
Nodes (5): find_pattern(), FoundEntry, `find_pattern` 이 돌려주는 항목 — `os.DirEntry` 에서 수집이 쓰는 부분(name · path · is_file ·…, 폴더 안에서 이름이 `pattern`(Windows 와일드카드 `*` `?`)에 맞는 항목만 — **NAS(SMB 서버)가 거른다**.…, _Stat

### Community 84 - "Community 84"
Cohesion: 0.33
Nodes (9): navCancel(), navGo(), navInd(), navNow(), navParts(), navRest(), navSet(), navState() (+1 more)

### Community 85 - "Community 85"
Cohesion: 0.28
Nodes (4): Path, 규칙 두 가지를 그대로 지켜본다. ① **범위 밖 장비 폴더는 건드리지 않는다** — 그 폴더나 그 아래를…, Tripwire, wrap()

### Community 87 - "Community 87"
Cohesion: 0.25
Nodes (3): HTMLParser, 모든 <table> 을 행 단위 셀 텍스트 목록으로 모은다(중첩 표는 펼침)., TableParser

### Community 88 - "Community 88"
Cohesion: 0.36
Nodes (3): NavBar, QWidget, _repolish()

### Community 89 - "Community 89"
Cohesion: 0.54
Nodes (7): _example(), _public(), docs/config.example.json 가드(S13) — 헤드리스 설정 예시가 `collect.DEFAULT_CONFIG` 와 조용히…, test_every_default_config_key_is_in_the_example_or_explicitly_excused(), test_example_loads_through_the_cli_loader(), test_example_public_keys_are_a_subset_of_default_config_with_the_same_types(), test_example_scope_and_workers_show_the_real_defaults()

### Community 90 - "Community 90"
Cohesion: 0.29
Nodes (7): _out_of_scope_meta(), 화면에 '수집 안 함' 으로 보여 줄 장비들. devices.csv 텍스트만 읽고 NAS 에는 접근하지 않는다., _natural(), 홈 기본 순서 — AOI-1 … AOI-25 다음에 4F-AOI-01 … 4F-AOI-05. 사전식(AOI-1, AOI-10, AOI-2)이…, 수집하지 않는(범위 밖) 장비 이름 — 화면에 '수집 안 함' 으로 보여 주기 위한 목록. NAS 접근 없음., skipped_by_scope(), sort_key()

### Community 91 - "Community 91"
Cohesion: 0.43
Nodes (3): _card(), QWidget, SettingsPage

### Community 92 - "Community 92"
Cohesion: 0.29
Nodes (7): _numbers(), parametrize, CLAUDE.md 가 적는 숫자는 코드가 정답이다. 그 숫자를 아직 적지 않은 항목(PARSER_VERSION)은 적히는 순간부터 검사된다., 진행상황.md 가 표기명·열 수를 적는다면 같은 숫자여야 한다(적지 않으면 그냥 통과)., test_numbers_in_claude_md_match_the_code(), test_progress_doc_numbers_match_the_code(), test_required_section_exists()

### Community 93 - "Community 93"
Cohesion: 0.43
Nodes (6): git_sha(), main(), measure(), model_version(), Path, 보관 샘플 하나를 결과 화면 모델(template.html 의 buildModel)로 **실제로 집계**해 요약 수치를 낸다 — 전후 비교표의…

### Community 94 - "Community 94"
Cohesion: 0.33
Nodes (4): _cache(), _picked(), test_bulk_listing_failure_falls_back_to_scandir(), test_full_listing_uses_the_bulk_lister_and_picks_the_same_reports()

### Community 95 - "Community 95"
Cohesion: 0.53
Nodes (6): _extract(), test_safe_extract_accepts_github_layout_and_short_sha_root(), test_safe_extract_caps_file_count_and_total_size(), test_safe_extract_rejects_hostile_entries_without_writing(), test_safe_extract_rejects_symlinks(), _zip_of()

### Community 97 - "Community 97"
Cohesion: 0.40
Nodes (5): ini_roots_for(), 이 배치의 INI 가 있을 폴더부터 — 현장은 어느 날짜 기준 **그 이전** Scanresult 를 통째로 백업 폴더로 옮기므로, 배치…, 배치 시작일이 경계보다 이른 **첫** 백업이 1순위, 그다음 지금 폴더, 나머지 백업, 경계 없는 백업은 맨 뒤., test_ini_roots_start_with_the_backup_whose_cutoff_is_after_the_batch(), ScanRoots

### Community 98 - "Community 98"
Cohesion: 0.40
Nodes (5): _is_placeholder(), _job_setup_by_table_lot(), `Job/Setup` 도 없고 `REPORT_RE`(4자리 Setup) 에도 안 맞는 파일명에서 job·setup 을 되찾는다. 파일명은…, INI 경로를 만들 수 없는 자리표시 행 — `LoadPort A` / `Slot 3`, Wafer ID 나 Lot 이 빈 행. ★ Lot 이…, test_job_setup_by_table_lot()

### Community 99 - "Community 99"
Cohesion: 0.50
Nodes (5): Context(), Db(), Eb(), Et(), fb()

### Community 100 - "Community 100"
Cohesion: 0.40
Nodes (3): fs_spy(), wrap(), _Spy

### Community 102 - "Community 102"
Cohesion: 0.50
Nodes (5): _run_level(), one(), stage_sweep(), go(), _take()

### Community 103 - "Community 103"
Cohesion: 0.50
Nodes (4): isolated_data(), Path, 모든 테스트를 임시 홈에서 돌린다. 반환값은 그 홈 경로., set_home()

### Community 105 - "Community 105"
Cohesion: 0.67
Nodes (3): read_one(), _decode_report(), Report 본문 — NAS 용 관대한 디코딩(손상 바이트는 U+FFFD)과 텍스트 모드와 같은 줄바꿈 정규화. 지문(SHA256)은 원본…

### Community 106 - "Community 106"
Cohesion: 0.67
Nodes (3): `TB500_RDL2 - Multi/Setup1` → (`TB500_RDL2 - Multi`, `Setup1`). 마지막 `/` 로만 가른다., split_job_setup(), test_job_setup_split_keeps_slashes_in_job()

## Knowledge Gaps
- **39 isolated node(s):** `CAUSE_CODES`, `CAUSE_RULES`, `CLOSE`, `devStatus`, `DROPW` (+34 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 861 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SheetHost` connect `Community 51` to `Community 64`, `Community 1`, `Community 34`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `Community 34` to `Community 64`, `Community 1`, `Community 5`, `Community 7`, `Community 9`, `Community 76`, `Community 17`, `Community 51`, `Community 54`, `Community 88`, `Community 91`, `Community 31`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `LoadingOverlay` connect `Community 17` to `Community 64`, `Community 1`, `Community 34`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `collect()` (e.g. with `read_one()` and `test_zero_new_rows_but_state_change_still_saves()`) actually correct?**
  _`collect()` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `MainWindow` (e.g. with `CollectPage` and `DevicesPage`) actually correct?**
  _`MainWindow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CAUSE_CODES`, `CAUSE_RULES`, `CLOSE` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.021457821457821456 - nodes in this community are weakly interconnected._