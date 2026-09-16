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


def test_scope_notice_is_rendered_from_meta():
    assert "meta.scope" in HTML and "수집 범위" in HTML and "수집 안 함" in HTML


def test_no_stale_update_base_constant():
    assert "UPDATE_BASE=" not in HTML
