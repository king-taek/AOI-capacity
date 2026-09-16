"""결과 HTML 한 장 — 어디에 있고, 없으면 빈 화면이라도 만들어 둔다.

이 프로그램은 **수집기**다. 화면은 여기서 만든 `AOI_capacity.html` 을 사용자가 **직접 더블클릭**해서 본다
(Python·로컬 서버·QtWebEngine 이 필요 없다). GUI 의 '결과 화면 열기' 버튼은 그 파일을 기본 브라우저로
띄워 주는 편의 기능일 뿐, 화면이 뜨는 조건이 아니다.
"""
from __future__ import annotations

import time
from pathlib import Path

from . import paths, prefs


def html_path() -> Path:
    return paths.output_html(prefs.load().output_dir)


def exists() -> bool:
    return html_path().is_file()


def last_collect_time() -> float:
    """결과 파일의 수정시각(초). 아직 없으면 0."""
    try:
        return html_path().stat().st_mtime
    except OSError:
        return 0.0


def ensure_html() -> Path:
    """아직 한 번도 수집하지 않았으면 빈 데이터로 한 장 만들어 둔다 — 파일을 열었을 때 안내라도 보이게."""
    path = html_path()
    if not path.exists():
        from .. import collect

        collect.write_html(prefs.to_collect_cfg(prefs.load()), [], [], [], time.time(), mode="gui")
    return path
