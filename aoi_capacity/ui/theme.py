"""테마 — template.html 의 CSS 토큰을 그대로 Qt 로 가져온다.

단일 출처: `assets/template.html` 의 `:root{…}`(dark) 와 `:root[data-theme="light"]{…}`.
런타임에 그 파일을 파싱해 팔레트를 만들고, 파싱이 불가능한 비상시에만 아래 `FALLBACK` 을 쓴다.
회귀 가드: dev/tests/test_theme.py 가 FALLBACK == 파싱 결과 임을 단언한다(드리프트 방지).

QSS 는 `style.qss` 의 `$토큰` 을 `string.Template.substitute` 로 채운다 — 미정의 토큰은 KeyError 로 즉시 드러난다.
"""
from __future__ import annotations

import re
from string import Template
from typing import Dict, Optional

from ..utils import paths

MODES = ("dark", "light")
_mode = "dark"

# template.html :root 토큰명 → theme 키 (CSS 의 --raise 는 파이썬 예약어가 아니지만 일관되게 raise_ 로)
_TOKEN_KEYS = {
    "bg": "bg", "surface": "surface", "surface-2": "surface_2", "raise": "raise_",
    "ink": "ink", "ink-2": "ink_2", "ink-3": "ink_3", "line": "line", "line-2": "line_2",
    "accent": "accent", "accent-2": "accent_2", "accent-ink": "accent_ink", "accent-soft": "accent_soft",
    "run": "run", "err": "err", "off": "off", "nodata": "nodata", "prev": "prev",
    "good": "good", "good-soft": "good_soft", "warn": "warn", "warn-soft": "warn_soft",
    "crit": "crit", "crit-ink": "crit_ink", "crit-soft": "crit_soft",
}

FALLBACK: Dict[str, Dict[str, str]] = {
    "dark": {
        "bg": "#0F1319", "surface": "#141920", "surface_2": "#1A2130", "raise_": "#1E2838",
        "ink": "#E4EEF8", "ink_2": "#8AAEC8", "ink_3": "#5C7086", "line": "#1E3050", "line_2": "#2A4060",
        "accent": "#4A9EE8", "accent_2": "#7EC8F0", "accent_ink": "#0F1319", "accent_soft": "#0D2A44",
        "run": "#4A9EE8", "err": "#E85A5A", "off": "#243040", "nodata": "#182030", "prev": "#3A4A60",
        "good": "#3DCC8E", "good_soft": "#0F2E24", "warn": "#E0A82E", "warn_soft": "#332608",
        "crit": "#E85A5A", "crit_ink": "#F08080", "crit_soft": "#3A1818",
    },
    "light": {
        "bg": "#f2f5f9", "surface": "#ffffff", "surface_2": "#f7f9fc", "raise_": "#e9eef5",
        "ink": "#0f1720", "ink_2": "#4b5865", "ink_3": "#7a8794", "line": "#dde3ea", "line_2": "#c6d0dc",
        "accent": "#2A6AAA", "accent_2": "#4A9EE8", "accent_ink": "#ffffff", "accent_soft": "#e1eefb",
        "run": "#2A6AAA", "err": "#d64545", "off": "#d3dbe5", "nodata": "#eef2f7", "prev": "#b9c4d2",
        "good": "#1f9e6a", "good_soft": "#dff4ea", "warn": "#d99a12", "warn_soft": "#fff1cf",
        "crit": "#d64545", "crit_soft": "#fbe3e3", "crit_ink": "#a02525",
    },
}
# HTML 에는 없는, Qt 전용 보조 토큰
EXTRA: Dict[str, Dict[str, str]] = {
    "dark": {"console_bg": "#0A0E14", "console_ink": "#c8d3de", "scrim": "rgba(15,19,25,170)", "good_ink": "#3DCC8E", "warn_ink": "#F0C25A"},
    "light": {"console_bg": "#0f1720", "console_ink": "#dfe6ee", "scrim": "rgba(15,23,32,110)", "good_ink": "#106b46", "warn_ink": "#7a5200"},
}
FONT_DISPLAY = '"Outfit", "Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif'
FONT_BODY = '"DM Sans", "Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif'
FONT_MONO = '"Cascadia Mono", "Consolas", "D2Coding", monospace'
FONT_FAMILIES = ["DM Sans", "Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo"]

_parsed: Optional[Dict[str, Dict[str, str]]] = None
_qss_cache: Dict[str, str] = {}


def parse_template_tokens(html: str) -> Dict[str, Dict[str, str]]:
    """template.html 에서 :root 와 :root[data-theme="light"] 의 --토큰: #hex 를 뽑는다."""
    out: Dict[str, Dict[str, str]] = {"dark": {}, "light": {}}
    for mode, pat in (("dark", r":root\{(.*?)\}"), ("light", r':root\[data-theme="light"\]\{(.*?)\}')):
        m = re.search(pat, html, re.S)
        if not m:
            continue
        for name, hexv in re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", m.group(1)):
            key = _TOKEN_KEYS.get(name)
            if key:
                out[mode][key] = hexv
    return out


def palettes() -> Dict[str, Dict[str, str]]:
    """{'dark': {...}, 'light': {...}} — HTML 파싱 우선, 실패 시 FALLBACK."""
    global _parsed
    if _parsed is None:
        try:
            parsed = parse_template_tokens(paths.template_path().read_text(encoding="utf-8"))
            ok = all(set(parsed[m]) >= set(FALLBACK[m]) for m in MODES)
            _parsed = parsed if ok else {m: dict(FALLBACK[m]) for m in MODES}
        except Exception:  # noqa: BLE001
            _parsed = {m: dict(FALLBACK[m]) for m in MODES}
    return _parsed


def normalize_color_mode(mode: Optional[str]) -> str:
    return "light" if str(mode or "").lower() == "light" else "dark"


def set_color_mode(mode: str) -> None:
    global _mode
    _mode = normalize_color_mode(mode)


def color_mode() -> str:
    return _mode


def is_dark_mode() -> bool:
    return _mode == "dark"


def colors(mode: Optional[str] = None) -> Dict[str, str]:
    m = normalize_color_mode(mode or _mode)
    c = dict(palettes()[m])
    c.update(EXTRA[m])
    c.update({"font_display": FONT_DISPLAY, "font_body": FONT_BODY, "font_mono": FONT_MONO})
    return c


def render_qss(mode: Optional[str] = None) -> str:
    m = normalize_color_mode(mode or _mode)
    if m not in _qss_cache:
        qss = paths.resource_path("aoi_capacity/ui/style.qss").read_text(encoding="utf-8")
        _qss_cache[m] = Template(qss).substitute(colors(m))
    return _qss_cache[m]


def apply_to_app(app, mode: Optional[str] = None) -> None:
    if mode:
        set_color_mode(mode)
    app.setStyleSheet(render_qss())
