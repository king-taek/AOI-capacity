"""AOI Capacity 진입점.

순서: 로깅 → (exe 배포면) 의존성 확인·설치 → 그 뒤에만 PyQt6 import → 테마 → MainWindow.
PyQt6 import 는 `_run_gui()` 안에 둔다 — 첫 실행 부트스트랩이 끝나기 전에는 패키지가 없을 수 있다.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from aoi_capacity import APP_ID, i18n  # noqa: E402
from aoi_capacity.utils import paths, prefs  # noqa: E402

LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 3


def _setup_logging() -> logging.Logger:
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
    if os.environ.get("AOI_DEBUG") == "1" or sys.stderr is not None and sys.stderr.isatty():
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    logger._aoi_configured = True  # type: ignore[attr-defined]
    return logger


def _ensure_deps_installed(logger: logging.Logger) -> bool:
    """exe 배포(설치 루트가 있을 때)만 requirements 를 확인한다. 개발 트리에서는 아무것도 하지 않는다."""
    if paths.install_root() is None:
        return True
    try:
        from aoi_capacity.utils import bootstrap
    except Exception as exc:  # noqa: BLE001 - 손상된 트리
        logger.info("bootstrap unavailable: %s", exc)
        return True

    def say(msg: str) -> None:
        logger.info(msg)
        print(msg, flush=True)

    ok = bootstrap.ensure_deps(log=say)
    if not ok:
        hint = i18n.KO.BOOT_LOG_HINT_FMT.format(path=paths.log_file())
        say(hint)
        how = _pause_or_notify(i18n.KO.BOOT_PRESS_ENTER, i18n.KO.BOOT_DEPS_FAILED + "\n\n" + hint)
        logger.info("deps install failed; user notified via %s", how)
    return ok


def _message_box(text: str, title: str) -> bool:
    """Windows 표준 MessageBoxW(ctypes) — 표준 라이브러리만 쓴다(PyQt6 는 설치에 실패한 그 패키지라 다시 import 하지 않는다).
    Windows 가 아니거나 호출이 안 되면 False."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        windll = getattr(ctypes, "windll", None)
        if windll is None:
            return False
        windll.user32.MessageBoxW(None, str(text), str(title), 0x10 | 0x40000)   # MB_ICONERROR | MB_TOPMOST
        return True
    except Exception:  # noqa: BLE001 - 안내 경로에서 새 예외를 만들지 않는다
        return False


def _pause_or_notify(prompt: str, notice: str) -> str:
    """의존성 설치 실패 안내(C16). 콘솔이 있으면 Enter 를 기다리고, stdin 이 없거나(pythonw 는 `sys.stdin is None` 이라
    `input()` 이 EOFError 가 아니라 RuntimeError 를 낸다) 닫혔으면 Windows MessageBox, 그것도 안 되면 print.
    돌려주는 값은 어떤 길로 안내했는지("input" · "messagebox" · "print") — 로그용."""
    if sys.stdin is not None:
        try:
            input(prompt)
            return "input"
        except (EOFError, RuntimeError, OSError):
            pass
    if _message_box(notice, i18n.KO.APP_TITLE):
        return "messagebox"
    try:
        print(notice, flush=True)
    except Exception:  # noqa: BLE001
        pass
    return "print"


def _apply_env(p: prefs.Prefs) -> None:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")


def _run_gui(logger: logging.Logger) -> int:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont, QIcon
    from PyQt6.QtWidgets import QApplication

    from aoi_capacity.ui import theme
    from aoi_capacity.ui.main_window import MainWindow

    QApplication.setApplicationName(APP_ID)
    QApplication.setApplicationDisplayName(i18n.KO.APP_TITLE)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont(theme.FONT_BODY.split(",")[0].strip('"'), 10))
    icon = paths.logo_path("logo.ico")
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    p = prefs.load()
    theme.apply_to_app(app, p.color_mode)
    if paths.ensure_user_files():
        logger.info("copied default devices.csv to %s", paths.devices_csv_path())
    win = MainWindow()
    win.show()
    return int(app.exec())


def main() -> int:
    logger = _setup_logging()
    logger.info("start %s python=%s data=%s", APP_ID, sys.version.split()[0], paths.data_root())
    if not _ensure_deps_installed(logger):
        return 2
    _apply_env(prefs.load())
    try:
        return _run_gui(logger)
    except Exception:  # noqa: BLE001
        logger.exception("fatal")
        raise


if __name__ == "__main__":
    sys.exit(main())
