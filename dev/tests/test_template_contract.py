"""결과 HTML(template.html) 계약 — 자바스크립트를 실행하지 않고 문자열로만 검사한다.

이 파일 한 장은 사용자가 **더블클릭해서 여는 화면**이다. 그래서
- 데이터는 `__DATA__` 자리에 박혀 들어가고,
- 바깥으로 나가는 요청(폰트·스크립트·fetch)이 한 건도 없어야 하며,
- 브라우저가 NAS 를 직접 읽는 경로(폴더 API)는 없어야 한다(수집은 Python 수집기만 한다).
"""
from __future__ import annotations

from aoi_capacity.utils import paths

HTML = paths.template_path().read_text(encoding="utf-8")


def test_data_placeholder_present_once():
    assert HTML.count("__DATA__") == 1


def test_no_network_use_at_all():
    for bad in ("fetch(", "api.github.com", "fonts.googleapis.com", "XMLHttpRequest",
                "<script src=", '<link rel="stylesheet"', "http://", "https://"):
        assert bad not in HTML, bad


def test_browser_never_reads_the_nas_itself():
    """★ 수집은 Python 수집기만 한다 — 브라우저 폴더 API 경로는 남아 있지 않다."""
    for bad in ("showDirectoryPicker", "getDirectoryHandle", "getFileHandle", "collectAll",
                "indexedDB", "queryPermission", "nasList"):
        assert bad not in HTML, bad


def test_no_pyqt_gui_mode_left():
    """앱 안에 끼워 넣던 GUI 모드(?gui=1)는 사라졌다 — 언제나 그냥 정적 화면이다."""
    for bad in ('data-gui', 'Q.get("gui")', "btnRunTop"):
        assert bad not in HTML, bad


def test_entry_points_the_app_and_user_need():
    for fn in ("function setTheme(m)", "function setThresholds(", "function go(", "function saveHtml(",
               "function loadDemo(", "function cmpDev("):
        assert fn in HTML


def test_home_has_no_previous_day_comparison_or_wafer_count():
    home = HTML[HTML.index("/* ---------- render: home ---------- */"):HTML.index("/* ---------- render: trend")]
    assert "deltaHtml(" not in home and "전일" not in home
    assert "nWafer" not in home and "Wafer <b>" not in home


def test_same_wafer_time_is_counted_once():
    """같은 Wafer 가 여러 Report 에 나와도(재검사) WaferInfo.ini 는 하나뿐 — 시간을 두 번 세면 안 된다."""
    assert "d.seen[key]" in HTML and "prev.dups++" in HTML
    assert "시간은 1번만 계산" in HTML


def test_status_rules_match_the_python_side():
    """실장비에 실제로 있는 표기 — 파이썬과 같은 규칙이어야 한다(Scan 2D Error. 등)."""
    for token in ("scan\\s*(?:2d|3d)?\\s*error", "alignment\\s+error", "wafer\\s+lost", "WAFER_LOST", "ALIGN_ERROR"):
        assert token in HTML, token


def test_parses_every_date_format_seen_on_real_machines():
    """AOI-1 의 `9/16/2026 1:54:03 PM` 도 읽어야 한다(파이썬 DT_FORMATS 와 짝)."""
    assert "(AM|PM)?" in HTML and "\\/(\\d{1,2})\\/" in HTML


def test_rescan_and_rework_are_shown_apart():
    """Lot 이름의 RE 는 노랑, REWORK 는 보라 — 둘 다 정상 가동으로 세고 색으로만 구분한다."""
    assert 'r.scan_type==="RESCAN"' in HTML and 'r.scan_type==="REWORK"' in HTML
    assert "--rework:" in HTML and "다시 검사 (RE)" in HTML and "재작업 (REWORK)" in HTML


def test_scope_notice_is_rendered_from_meta():
    assert "meta.scope" in HTML and "수집 범위" in HTML and "수집 안 함" in HTML


def test_no_stale_update_base_constant():
    assert "UPDATE_BASE=" not in HTML


def test_status_classification_matches_the_python_side():
    """★ 같은 Report 를 파이썬과 브라우저가 다르게 읽으면 안 된다 — 코드 순서까지 같아야 한다.

    반송 실패('… Batch Aborted. Skipped.')처럼 문구가 겹치는 표기가 있어 **순서가 곧 의미**다."""
    import re

    from aoi_capacity import collect

    body = HTML[HTML.index("function normStatus"):HTML.index("const isErr=")]
    js_codes = re.findall(r'return"([A-Z_]+)"', body)
    assert js_codes[0] == "PASS" and 't?"OTHER":""' in body
    assert js_codes[1:] == [c for c, _ in collect._STATUS_RULES]

    err_codes = [c for c, _ in collect._STATUS_RULES if c != "SKIPPED"]
    is_err = HTML[HTML.index("const isErr="):].split("\n")[0]
    for code in err_codes:
        assert f'"{code}"' in is_err, f"isErr 에 {code} 없음"
        assert re.search(rf"\b{code}:", HTML), f"ERR_KO 에 {code} 한국어 이름 없음"


def test_home_cards_sort_with_cmp_dev_not_alphabetically():
    """★ 사전식으로 정렬하면 `4F-AOI-01` 이 `AOI-1` 앞으로 온다 — 홈 정렬은 devices.sort_key 와 같아야 한다."""
    assert "localeCompare" not in HTML
    assert 'ui.sort==="name"?cmpDev(a.n,b.n)' in HTML


def test_test_lots_are_excluded_from_the_utilisation_numbers():
    """★ 사용자 확정: Lot 이름이 TEST 인 시험 가동은 가동률에 넣지 않는다 — 다만 화면에서 사라지지도 않는다."""
    from aoi_capacity import collect

    assert collect.scan_type("GVG-RDL3 TEST") == "TEST" and collect.EXCLUDED_SCAN_TYPES == ("TEST",)
    assert 'test:r.scan_type==="TEST"' in HTML            # 구간에 표시가 붙고
    assert 'if(g.test){' in HTML and 'm.nTest++' in HTML   # run/err/stop 어디에도 더하지 않는다
    assert '시험 가동 ${m.nTest}건 제외' in HTML            # 몇 건을 뺐는지 밝힌다
    assert "시험 가동 (TEST · 가동률 제외)" in HTML         # 범례에도 있다


def test_report_opens_on_double_click_without_any_request_from_the_page():
    """★ 상태바를 더블클릭하면 그 BatchReport 를 새 탭으로 연다.

    여는 주체는 사람이 연 그 탭이지 이 화면이 아니다 — 화면은 여전히 요청을 한 건도 보내지 않는다
    (`test_no_network_use_at_all` 이 계속 지킨다). 경로는 수집기가 넣어 준 값으로만 만든다."""
    assert "function reportUrl(" in HTML and "function openReport(" in HTML
    assert "el.ondblclick=" in HTML                       # 단일 클릭은 그대로 오류 표 연결
    assert 'd.report_dir||"Report"' in HTML                # 장비마다 다른 Report 폴더 이름
    assert '(unc?"file://":"file:///")' in HTML            # UNC(\\\\10.x) 와 드라이브 문자 둘 다
    assert "encodeURIComponent" in HTML                    # Lot 이름의 '#'·공백이 있어도 열린다
    assert "더블클릭" in HTML


def test_error_and_the_stop_after_it_are_drawn_as_one_bar():
    """사용자 확정: 오류 발생과 그 뒤 정지는 막대 하나로 이어 그린다(숫자는 그대로 따로 센다)."""
    assert "const stopOf=g=>m.items.find(" in HTML
    assert "errIt.forEach(it=>{const sp=stopOf(it.g),e2=sp?Math.max(it.e,sp.e):it.e;" in HTML
    # 한 막대로 그리되 툴팁에서는 언제·무슨 오류·얼마나 기다렸는지를 나눠 적는다(사용자 확정)
    assert "오류 발생 <b>${hm(new Date(it.g.s))}</b> · 오류 구간" in HTML
    assert "그 뒤 정지(추정) ${fmtSec((st.e-st.s)/1000)}" in HTML
    assert "합계 ${fmtSec((st.e-it.g.s)/1000)}" in HTML
    assert "오류·중단 + 그 뒤 정지 (한 막대)" in HTML


def test_a_lot_bar_shows_what_is_mixed_inside_it():
    """★ 한 Lot 에 정상·오류·건너뜀이 섞였는데 통째로 파랗게 칠하면 '다 잘 된 것' 처럼 보인다
    (실물: 9/15 AOI-8 NTM). 막대는 하나로 두되 안을 조각별 색으로 칠하고, 툴팁이 종합해 준다."""
    assert "function lotTip(" in HTML and 'class="part"' in HTML
    assert 'const mark=it=>it.kind==="test"?"var(--prev)":it.kind==="err"?"var(--err)"' in HTML
    assert "Wafer ${nWafer}장" in HTML and "배치 ${nBatch}건" in HTML   # Wafer 장수와 통째로 실패한 시도는 따로
    assert "정상 검사" in HTML and "오류·중단" in HTML   # 무엇이 섞였는지


def test_lot_bars_split_by_the_exact_name_and_by_any_real_gap():
    """★ 사용자 확정: 따로 돌린 것이면 따로 보여야 한다.

    `TTP DIA`·`TTP-DIA`, `GUX-PIDS3`·`GUX-PIDS3 RE`, `DYD-FS`·`DYD-FS REWORK` 는 전부 다른 막대다 —
    재스캔·재작업은 실가동률을 깎은 원인이라 합쳐 버리면 화면에서 사라진다.
    같은 Lot 이어도 중간에 시간이 비면(60초 초과) 나눈다."""
    assert "const lotKey=(lot,isTest)=>" in HTML and "String(lot||\"\")" in HTML
    assert "LOT_MARKS" not in HTML                       # 이름에서 지우는 토큰이 더는 없다
    assert "const LOT_GAP_SEC=60;" in HTML and "it.s-L.e<=LOT_GAP_SEC*1000" in HTML
    assert "L.key===key" in HTML
    assert 'isTest?"TEST\\u0000":""' in HTML            # 시험 가동만은 섞지 않는다(가동률에서 빠지므로)


def test_no_period_over_period_comparison_anywhere():
    """사용자 확정: 전주·전월 대비는 지웠다. 되살아나면 이 가드가 잡는다."""
    for gone in ("deltaHtml", "prevKeys", "periodPrev(unit,anchor)", "이전 기간", "이전 주", "이전 월",
                 "하락 큰 순", "hbar prev", "class=\"delta"):
        assert gone not in HTML, gone
    assert "periodPrev" in HTML                          # 추이 막대의 '앞 기간으로 이동' 에는 아직 쓴다


def test_denominator_is_a_fixed_day_but_today_stops_at_the_last_scan():
    """사용자 확정: 분모는 하루 24시간 고정. 오늘만 **마지막으로 스캔된 시각**까지로 끊는다."""
    assert "function dayLastScan(" in HTML
    assert "const b=isToday(k)?Math.max(a,lastScan||now):a+DAY;" in HTML
    # 장비 시계가 PC 보다 앞서 있어도 마지막 스캔을 잘라 내지 않는다(now 로 다시 줄이지 않는다)
    assert "Math.min(now,Math.max(a,lastScan" not in HTML


def test_test_lots_count_in_the_denominator_but_not_in_the_numerator():
    """사용자 확정: 시험 가동은 양산이 아니라 실가동(분자)에서 빼되, 분모(24시간)에서는 빼지 않는다."""
    assert "m.util=denom>0?m.run/denom*100:0;" in HTML          # 분자는 run 만
    assert "m.hasData=m.nWafer>0||m.nErr>0||m.nTest>0;" in HTML  # 시험만 돈 날도 '데이터 없음' 이 아니다
    assert "m.testRun+=(c[1]-c[0])/1000" in HTML                # 미가동으로도 세지 않는다


def test_embedded_string_pool_is_unfolded_on_load():
    from aoi_capacity import collect

    assert "const P=emb.pool||null,F=new Set(emb.pooled||[]);" in HTML
    assert "P&&F.has(c)?(P[a[i]]??\"\"):a[i]" in HTML
    assert set(collect.POOLED_COLS) < set(collect.OUT_COLS)


def test_save_html_keeps_every_collector_column_and_the_pool():
    """★ 저장 버튼이 열을 골라 담으면 kind·scan_type·report 가 사라져 TEST 가 실가동에 섞이고(실데이터 +150,204초)
    배치 표시·Report 열기가 없어진다. 수집기가 준 열 목록과 문자열 풀 구조를 그대로 다시 접어야 한다."""
    body = HTML[HTML.index("function saveHtml("):HTML.index("/* ---------- boot")]
    assert '"device","lot","wafer_id"' not in body          # 열을 손으로 고르지 않는다
    assert "embCols" in body and "embPooled" in body         # 로더가 받은 계약 그대로
    assert "pooled,pool,rows" in body                        # collect._embed_rows 와 같은 모양
    assert "embCols=emb.cols.slice()" in HTML


def test_today_basis_wording_is_last_scan_not_now():
    """사용자 확정(D17): 오늘 분모는 '지금' 이 아니라 그날 마지막 스캔까지다 — 화면 문구도 그렇게 말해야
    다음 날 열었을 때 숫자가 달라지는 이유가 설명된다."""
    for bad in ("현재까지", "00:00 ~ 현재", "hm(new Date())} 기준"):
        assert bad not in HTML, bad
    assert "마지막 스캔 기준" in HTML


def test_readme_and_settings_help_follow_the_confirmed_rules():
    from pathlib import Path
    from aoi_capacity.i18n import ko

    readme = Path(__file__).resolve().parents[2].joinpath("README.md").read_text(encoding="utf-8")
    for bad in ("이전 기간 비교", "현재 시각까지"):
        assert bad not in readme, bad
        assert bad not in ko.SET_UTIL_DEFINITION, bad
    assert "마지막 스캔" in readme and "마지막 스캔" in ko.SET_UTIL_DEFINITION


def test_home_distinguishes_unreachable_and_partial_devices_from_no_data():
    """수집기가 적어 준 장비별 수집 상태(`meta.devices[].status`)를 홈 카드·표가 보여 준다 —
    '데이터 없음' 은 실제 미가동일 수도, 수집이 안 된 것일 수도 있어 구분 없이 두면 안 된다."""
    assert 'if(d.status)devStatus[d.name]=' in HTML
    assert 'status==="unreachable"' in HTML and "수집 실패" in HTML
    assert 'status==="partial"' in HTML and "일부 누락" in HTML
    assert ".st.warn{" in HTML


def test_settings_tab_shows_collector_timing_when_present():
    assert "function renderTiming(" in HTML and 'id="timingCard" hidden' in HTML
    assert "meta.timing||{}" in HTML and "INI 요청" in HTML


def test_timeline_has_a_pointer_hit_layer_with_a_max_distance():
    """★ 실측: 막대의 반응 영역이 그려진 폭과 같아 1440px 창에서 최소 1.9px 였다. 시각 막대는 그대로 두고
    맨 위의 투명 층이 가장 가까운 막대를 고른다 — 최대 거리 밖은 잡지 않고, 겹치면 좁은 쪽이 이긴다."""
    assert "const HIT_MAX_PX=6;" in HTML and "function bindHitLayer(" in HTML
    assert '<rect class="hit"' in HTML and "bindHitLayer($(\"#detTl svg\"),m)" in HTML
    assert "(p.x1-p.x0)-(q.x1-q.x0)" in HTML                    # 겹치면 폭이 좁은 막대 우선
    assert "겹친 막대 ${list.length}개 · Tab 으로 전환" in HTML
    # hit 영역을 넓혀도 실제 막대 폭·시간 길이는 바꾸지 않는다
    assert "const w=Math.max(2,x(L.e)-x(L.s));" in HTML
    assert 'width="${Math.max(2,x(e2)-x(it.s)).toFixed(1)}"' in HTML


def test_tooltip_is_clamped_on_all_four_sides():
    assert "x=Math.max(8,Math.min(x,innerWidth-w-8));y=Math.max(8,Math.min(y,innerHeight-h-8));" in HTML


def test_hover_tooltips_are_short_and_carry_no_file_names():
    """hover 는 3줄(대상 / 시각·기간 / 핵심 상태) + 안내 한 줄. 파일명·원문·계산식은 상세에서 본다."""
    assert "function segTip(" in HTML and "const tipHint=" in HTML
    assert "더블클릭하면 Report 를 엽니다 · " not in HTML and "openHint" not in HTML
    assert "${esc(r.report)}" not in HTML[HTML.index("function lotTip("):HTML.index("function renderDetail(")]


def test_hover_does_not_move_the_target():
    """hover 에서 요소가 움직이면 경계에서 mouseleave 가 되풀이된다 — 색·그림자만 바뀐다."""
    css = HTML[:HTML.index("</style>")]
    assert "translateY(-2px)" not in css and "translateY(-1px)" not in css and "translateX(2px)" not in css
    assert "animation:silk-in .15s" in css and ".12s var(--silk)" in css
    assert 'const smooth=()=>matchMedia("(prefers-reduced-motion: reduce)")' in HTML
