"""template.html 에서 **기계적으로** 뽑는 사실들 — 문서(CLAUDE.md)와 코드가 어긋나는지 볼 때의 코드 쪽 값.

Node 없이 정규식으로 읽는다. 형식이 바뀌어 못 읽으면 조용히 0 을 주지 않고 예외를 던진다.
(런타임 값과 같은지는 test_dashboard_js.py 가 하네스의 globals 모드로 한 번 더 대조한다.)
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "aoi_capacity" / "ui" / "assets" / "template.html"


def text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def model_version(html: str | None = None) -> int:
    m = re.search(r"^const MODEL_VERSION=(\d+);", html or text(), re.M)
    if not m:
        raise ValueError("template 에 `const MODEL_VERSION=<n>;` 줄이 없다")
    return int(m.group(1))


def job_alias(html: str | None = None) -> dict:
    """`const JOB_ALIAS={ "원문":"표기명", … };` 블록을 dict 로. 줄마다 항목 하나라는 형식을 검증한다."""
    h = html or text()
    a = h.index("const JOB_ALIAS={")
    b = h.index("};", a)
    body = h[a + len("const JOB_ALIAS={"):b]
    pairs = re.findall(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', body)
    lines = [l for l in body.splitlines() if l.strip()]
    if not pairs or len(pairs) != len(lines):
        raise ValueError(f"JOB_ALIAS 블록을 읽지 못했다(항목 {len(pairs)} · 줄 {len(lines)})")
    return dict(pairs)


def rules(name: str, src: str | None = None) -> list:
    """`const <name>=[ ["CODE",/regex/i], … ];` → [(code, pattern)] — 파이썬 `collect._CAUSE_RULES` 와 같은 모양."""
    s = src or text()
    body = s[s.index(f"const {name}="):]
    body = body[:body.index("];") + 1]
    return re.findall(r'\["([A-Z_]+)",/(.*?)/i\]', body)


def section(html: str, start: str, end: str) -> str:
    """두 주석 표식 사이 — 표식이 없으면 예외(조용히 빈 문자열을 검사해 통과하지 않는다)."""
    a = html.index(start)
    b = html.index(end, a)
    return html[a:b]
