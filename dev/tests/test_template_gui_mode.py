"""template.html 과 앱 사이의 문자열 계약 — 자바스크립트를 실행하지 않고 문자열로만 검사한다."""
from __future__ import annotations

import re

from aoi_capacity.utils import paths

HTML = paths.template_path().read_text(encoding="utf-8")


def test_data_placeholder_present_once():
    assert HTML.count("__DATA__") == 1


def test_gui_flag_from_query():
    assert 'GUI=Q.get("gui")==="1"' in HTML
    assert 'dataset.gui="1"' in HTML


def test_gui_mode_hides_browser_only_chrome():
    assert re.search(r':root\[data-gui="1"\] \.side[^{]*#btnRunTop[^{]*#btnTheme\{display:none\}', HTML)
    assert ':root[data-gui="1"] .app{grid-template-columns:1fr}' in HTML


def test_app_callable_js_entry_points_exist():
    for fn in ("function setTheme(m)", "function setThresholds(", "function go("):
        assert fn in HTML


def test_no_network_use_at_all():
    """★ 더블클릭해서 여는 정적 파일 — 바깥으로 나가는 요청이 한 건도 없어야 한다."""
    for bad in ("fetch(", "api.github.com", "fonts.googleapis.com", "XMLHttpRequest", "<script src=", "<link rel=\"stylesheet\""):
        assert bad not in HTML, bad


def test_browser_only_chrome_still_gated_by_gui_flag():
    assert "if(!GUI){" in HTML and "loadNas();renderDevs();restoreHandles();" in HTML


def test_gui_badge_and_theme_from_query():
    assert 'meta.mode==="gui"' in HTML
    assert 'Q.get("theme")==="light"' in HTML
    assert 'Q.get("th_util")' in HTML and 'Q.get("th_err")' in HTML


def test_no_stale_update_base_constant():
    assert "UPDATE_BASE=" not in HTML
