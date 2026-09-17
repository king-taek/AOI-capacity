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
    home = HTML[HTML.index("/* ---------- render: home ---------- */"):HTML.index("function selectDev(")]
    assert "deltaHtml(" not in home and "전일" not in home
    assert "nWafer" not in home and "Wafer <b>" not in home


def test_same_wafer_time_is_counted_once():
    """같은 Wafer 가 여러 Report 에 나와도(재검사) WaferInfo.ini 는 하나뿐 — 시간을 두 번 세면 안 된다."""
    assert "d.seen[key]" in HTML and "prev.refs++" in HTML
    assert "시간은 1번만 계산" in HTML
    # ★ 데이터 중복(같은 원본 행·같은 시각 참조)과 실제 반복(시각이 다른 시도)은 다르다 — 같은 시각 참조를 재스캔으로 단정하지 않는다
    assert "d.raw[rawKey]" in HTML and "rawDups" in HTML
    assert "g.dups>1" not in HTML and "dups<2" not in HTML


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
    assert "--rework:" in HTML and "--dup:" in HTML and "--test:" in HTML          # 의미별 색 토큰(다크·라이트 둘 다)
    assert HTML.count("--dup:") == 2 and HTML.count("--test:") == 2
    # 용어(사용자 확정 U02): 검사→가동, 재검사→재스캔, 재작업→Rework, 오류→Error, 시험→Test. 단일 출처 = DISPLAY_META
    assert "const DISPLAY_META={" in HTML and "function legendHtml(" in HTML
    for t, label in (("RUN", "가동"), ("DUP", "중복스캔"), ("RESCAN", "재스캔"), ("REWORK", "Rework"), ("ERROR", "Error"), ("TEST", "Test"), ("OFF", "미가동")):
        assert f'{t}:{{label:"{label}"' in HTML, t
    js = HTML[HTML.index("<script>", HTML.index("__DATA__")):]
    for old in (">재검사<", ">재작업<", "정상 검사", "검사시간", "시험 가동", "오류 발생", "오류·정지", "오류 먼저", "오류 많은 순"):
        assert old not in js, old


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
    assert 'Test ${m.nTest}건 제외' in HTML                 # 몇 건을 뺐는지 밝힌다
    assert '" (가동률 제외)"' in HTML                        # 범례에도 한정어가 남는다(legendHtml)


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
    assert "Error 발생 <b>${hm(new Date(it.g.s))}</b> · Error 구간" in HTML
    assert "그 뒤 정지(추정) ${fmtSec((st.e-st.s)/1000)}" in HTML
    assert "합계 ${fmtSec((st.e-it.g.s)/1000)}" in HTML
    assert '" · 정지(추정)"' in HTML                      # 범례 — '추정' 한정어를 지우지 않는다(legendHtml 의 Error 항목)


def test_a_lot_bar_shows_what_is_mixed_inside_it():
    """★ 한 Lot 에 정상·오류·건너뜀이 섞였는데 통째로 파랗게 칠하면 '다 잘 된 것' 처럼 보인다
    (실물: 9/15 AOI-8 NTM). 막대는 하나로 두되 안을 조각별 색으로 칠하고, 툴팁이 종합해 준다."""
    assert "function lotTip(" in HTML and 'class="part"' in HTML
    assert 'const mark=it=>it.kind==="test"?fillOf("TEST"):it.kind==="err"?"var(--err)":fillOf(it.g.disp);' in HTML
    assert "Wafer ${nWafer}장" in HTML and "배치 ${nBatch}건" in HTML   # Wafer 장수와 통째로 실패한 시도는 따로
    assert '["정상",cnt("RUN")' in HTML and '["중복스캔",cnt("DUP")' in HTML and '["Error",L.err' in HTML   # 무엇이 섞였는지
    # 반복 시도 조각은 포인터 후보다 — 짧아도 직접 고른다. 폭은 시간 비례 그대로(clipX 최소 1.5 단위)
    assert 'if(isRep(it))s+=`<rect class="seg part" tabindex="0" data-i=' in HTML


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
    assert 'else if(it.kind==="test")m.testRun+=u;' in HTML       # 미가동으로도 세지 않는다
    # ★ 시간 분할 U+T+E+S+R=D — 겹침은 우선순위로 한 번만 배정하고 overlap 에 적는다(max(0,…) 로 숨기지 않는다)
    assert "const PRI={err:0,run:1,test:2,stop:3};" in HTML and "m.overlap=Math.max(0,raw-covered);" in HTML
    assert "m.off=Math.max(0,denom-covered);" in HTML


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
    assert '<rect class="hit"' in HTML and 'bindHitLayer(root.querySelector("svg"),m)' in HTML
    assert "(p.x1-p.x0)-(q.x1-q.x0)" in HTML                    # 겹치면 폭이 좁은 막대 우선
    assert "겹친 막대 ${list.length}개 · ↑↓ 로 전환" in HTML        # Tab 은 표준 포커스 이동에 남긴다
    assert 'e.key==="Tab"&&hitCycle' not in HTML
    assert "const pickAt=ev=>{const list=choose(toX(ev));" in HTML   # 클릭은 클릭 좌표에서 다시 고른다(stale 선택 방지)
    # hit 영역을 넓혀도 실제 막대 폭·시간 길이는 바꾸지 않는다
    assert "const[xs,w]=clipX(Lt.s,Lt.e,2);" in HTML                # Lot 막대 최소 2단위
    assert "const[xs,w]=clipX(it.s,e2,2);" in HTML                    # 오류+정지 막대 최소 2단위


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


def test_single_click_pins_a_detail_panel_and_double_click_still_opens_the_report():
    """hover 는 짧게, 원문·파일명·INI 상태·Report 목록은 클릭(또는 Enter)으로 고정한 상세에서 본다.
    더블클릭으로 Report 를 여는 계약(D15)은 그대로다."""
    assert 'id="segDetail"' in HTML and "function pinSeg(" in HTML and "function closeSeg(" in HTML
    assert "el.onclick=()=>{pinEl(el);" in HTML and 'if(ev.key==="Enter"){ev.preventDefault();el.onclick();}' in HTML
    assert "el.ondblclick=ev=>{ev.preventDefault();openReport(rowOf(el));};" in HTML
    assert "Report 열기</button>" in HTML and "function copyText(" in HTML
    assert "INI_KO={EXACT:" in HTML and "시간 미확인 · INI 가 다시 검사로 덮어써짐" in HTML   # 시각 누락의 원인을 말한다
    assert 'if(sd&&!sd.hidden)closeSeg();else if(selDev)selectDev(null);else if(ui.loss!=null)setLoss(null);' in HTML   # ESC 는 상세부터 닫는다


def test_multi_report_lot_lists_every_report():
    """Lot 막대 하나에 Report 가 둘 이상이면(실데이터 7개) 대표 하나만 몰래 열지 않고 목록으로 고르게 한다."""
    assert "const reportsOf=parts=>" in HTML and "원본 ${nr}개" in HTML
    assert "window._m._pin.reports[${i}]" in HTML


def test_narrow_windows_keep_a_way_to_every_page():
    """820px 미만에서 사이드바가 사라지면 추이·비교·설정에 갈 길이 없었다(실측). 상단 4탭이 대신한다."""
    assert '<nav class="tabs" id="tabs"' in HTML
    tabs = HTML[HTML.index('<nav class="tabs"'):HTML.index("</nav>", HTML.index('<nav class="tabs"'))]
    assert all(f'data-v="{v}"' in tabs for v in ("home", "trend", "compare", "set"))
    css = HTML[:HTML.index("</style>")]
    assert ".tabs{display:none;" in css and ".tabs{display:flex}" in css
    assert "#detTl .chart{min-width:900px}" in css          # 타임라인은 축소 대신 가로 스크롤


def test_screen_copy_is_short_but_keeps_the_qualifiers():
    assert ">사본 저장</button>" in HTML and "HTML로 저장" not in HTML
    assert '<span class="sub">표시 · 보관</span>' in HTML
    assert "수집 프로그램에서 ‘지금 수집’ 을 누른 뒤 이 화면을 새로고침(F5)하세요." in HTML
    assert 'gen+" 수집"' in HTML                                # 9/16 21:01 수집
    for keep in ("정지(추정)", "가동률 제외", "수집 안 함", "시간 미확인"):
        assert keep in HTML, keep


def test_zoom_band_reuses_day_metrics_and_draws_nothing_new():
    """★ 확대 타임라인은 같은 dayMetrics 결과를 잘라 다시 그릴 뿐이다 — 숫자·Lot 경계·60초 분할이 바뀌면 안 된다."""
    body = HTML[HTML.index("function renderDetail("):HTML.index("function hlSeg(")]
    assert body.count("dayMetrics(") == 1                                   # 상세 화면에서 집계는 한 번
    assert "drawBand(m,a,a+DAY," in body                                    # 개요
    assert "drawBand(m,z.s,z.e," in HTML                                    # 확대 — 같은 m
    assert "function drawBand(m,t0,t1,o)" in HTML and "function wireSegs(" in HTML
    assert 'id="zoomTl"' in HTML and "function bindZoomDrag(" in HTML
    assert "const ZOOM_MIN=10*60e3,ZOOM_MAX=6*3.6e6;" in HTML
    assert "Math.max(a,Math.min(s0,e0)),e1=Math.min(a+DAY,Math.max(s0,e0))" in HTML   # 그날 안으로 자른다
    assert "createElementNS" not in HTML                                     # 네임스페이스 URL 조차 담지 않는다


def test_detail_panel_mounts_right_under_the_selected_device():
    """★ 사용자 확정(U05): 상세는 장비 목록 맨 아래가 아니라 **클릭한 장비 버튼 바로 아래**. 패널은 하나뿐이고
    선택한 장비의 자리(.dmount)로 옮겨 붙는다 — 카드는 .ditem 이 한 줄 전체로 넓어지고, 표는 바로 다음 행이다."""
    assert 'id="detPark" hidden' in HTML and "function parkDetail(" in HTML and "function mountDetail(" in HTML
    assert '<div class="dmount" id="${devId(n)}-mount"></div>' in HTML
    assert '<tr class="detrow"><td colspan="${nCol}">' in HTML
    assert ".ditem.open{display:block;grid-column:1/-1}" in HTML and "grid-auto-flow" not in HTML
    assert '<button class="card dev ' in HTML and 'aria-expanded="${selDev===n}" aria-controls="detail"' in HTML
    assert 'if(ui.view==="cards")$("#homeTbody").innerHTML="";else $("#cards").innerHTML="";' in HTML   # 숨은 쪽에 같은 id 를 남기지 않는다
    assert "[hidden]{display:none!important}" in HTML
    assert "onclick=\"selectDev('" not in HTML                   # 장비 이름을 인라인 onclick 에 끼워 넣지 않는다


def test_cross_device_material_history_is_global_and_explained():
    """★ 사용자 확정(U01·U03): 같은 자재를 이어서 다시 스캔하면 중복스캔, 다른 장비에서 다시 스캔하면 재스캔.
    관계는 조회 날짜·장비 필터와 무관하게 로드한 전체 행에서 한 번 계산하고, 판정 근거와 신뢰도를 남긴다."""
    assert "function materialIndex(" in HTML and "M._index=materialIndex(attempts);" in HTML
    assert "const materialKey=r=>`${normLot(r.lot)}|${String(r.wafer_id||\"\").trim()}`;" in HTML
    assert 'const MARK_TOKENS=new Set(["RE","RESCAN","REWORK","TEST"]);' in HTML
    for rel in ("FIRST_OBSERVED", "SAME_DEVICE_REPEAT", "SAME_DEVICE_RESCAN", "CROSS_DEVICE_RESCAN", "TOKEN_RESCAN", "UNRESOLVED"):
        assert f"{rel}:" in HTML, rel
    assert 'a.conf=p.pk===a.pk?"confirmed":"inferred";' in HTML   # Recipe 가 다르면 확정이 아니라 추정(실물 BS / BS_1)
    assert "function dispOf(g)" in HTML and "const CLASS_VERSION=" in HTML
    assert "function historyHtml(" in HTML and 'add("판정 근거"' in HTML and 'add("앞선 시도"' in HTML


def test_loss_reason_chart_reuses_day_metrics_and_sums_to_the_average():
    """★ 사용자 확정(U04): 가동률 저하 사유 차트 → 사유 상세 → 장비별 기여 → 이벤트 → 장비 상세로 이동·복귀.
    사유 %p 는 평균 정의(100/N × Σ L/D)라 합이 100 − 평균 가동률이다. 반복 가동은 저하 사유에 넣지 않는다."""
    assert 'id="lossCard"' in HTML and "function lossCalc(" in HTML and "function renderLossDetail(" in HTML
    assert "100/N*withData.reduce(" in HTML
    assert '{id:"err",' in HTML and '{id:"stop",' in HTML and '{id:"testRun",' in HTML and '{id:"off",label:"미가동 · 사유 미확인"' in HTML
    assert "min-height:44px" in HTML and 'aria-pressed="${ui.loss===i}"' in HTML
    assert "function lossBack(" in HTML and 'id="detBack"' in HTML
    assert 'id="repCard"' in HTML and "저하 사유에 다시 더하지 않습니다" in HTML
    assert "const LOSS_PAGE=50;" in HTML                          # 이벤트가 많으면 나눠 그린다


def test_terminology_registry_is_used_in_settings_and_saved_copies_keep_columns():
    assert 'id="ruleCard"' in HTML and "function renderRules(" in HTML
    assert "embCols=emb.cols.slice()" in HTML                       # 저장 계약은 그대로(파생 필드는 저장하지 않고 다시 계산)
    assert "classification" not in HTML.lower() or "CLASS_VERSION" in HTML
