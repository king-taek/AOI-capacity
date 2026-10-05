"""app.log 설정 한 곳 — GUI(main.py)와 CLI(cli.py)가 같이 쓴다(10/5: 수집 상세 로그를 HTML 대신 app.log 에 남긴다).

로거 `aoi` 아래 전부(`aoi.collect` 등)가 데이터 폴더의 app.log 로 간다. 5MB 넘으면 .1~.5 로 돌린다(상세 로그가 길어져 1MB 에서 늘림).
두 번 불러도 핸들러가 늘지 않는다."""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys

from . import paths

LOG_MAX_BYTES = 5_000_000
LOG_BACKUPS = 5


def setup_logging(console: bool = True) -> logging.Logger:
    """console=False(CLI) 면 터미널로는 내보내지 않는다 — CLI 는 자기 출력이 따로 있어 같은 줄이 두 번 찍힌다."""
    logger = logging.getLogger("aoi")
    if getattr(logger, "_aoi_configured", False):
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        fh = logging.handlers.RotatingFileHandler(paths.log_file(), maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS,
                                                  encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass
    if console and (os.environ.get("AOI_DEBUG") == "1" or sys.stderr is not None and sys.stderr.isatty()):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    logger._aoi_configured = True  # type: ignore[attr-defined]
    return logger
