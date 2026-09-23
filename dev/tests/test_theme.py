"""테마 — HTML :root 토큰이 단일 출처. FALLBACK 은 파싱 값과 같아야 하고, QSS 에 치환되지 않은 $ 가 남으면 안 된다."""
from __future__ import annotations

import re

from aoi_capacity.ui import theme
from aoi_capacity.utils import paths


def test_fallback_matches_template_tokens():
    parsed = theme.parse_template_tokens(paths.template_path().read_text(encoding="utf-8"))
    for mode in theme.MODES:
        assert parsed[mode] == theme.FALLBACK[mode], f"{mode}: template.html 토큰과 theme.FALLBACK 이 다릅니다"


def test_render_qss_has_no_unsubstituted_tokens():
    for mode in theme.MODES:
        qss = theme.render_qss(mode)
        assert "$" not in qss
        assert qss.strip()


def test_modes_differ_and_normalize():
    assert theme.colors("dark")["bg"] != theme.colors("light")["bg"]
    assert theme.normalize_color_mode("LIGHT") == "light"
    assert theme.normalize_color_mode(None) == "light"          # 9/23: 결과 HTML 과 같은 라이트가 기본
    assert theme.normalize_color_mode("weird") == "light"
    assert theme.normalize_color_mode("DARK") == "dark"


def test_all_hex_colors():
    for mode in theme.MODES:
        for k, v in theme.palettes()[mode].items():
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", v), (mode, k, v)
