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
    assert '오류 ${fmtSec((it.g.e-it.g.s)/1000)} + 정지(추정)' in HTML   # 툴팁에서는 나눠 보여 준다
    assert "오류·중단 + 그 뒤 정지 (한 막대)" in HTML


def test_embedded_string_pool_is_unfolded_on_load():
    from aoi_capacity import collect

    assert "const P=emb.pool||null,F=new Set(emb.pooled||[]);" in HTML
    assert "P&&F.has(c)?(P[a[i]]??\"\"):a[i]" in HTML
    assert set(collect.POOLED_COLS) < set(collect.OUT_COLS)
