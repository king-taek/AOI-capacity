"""main.py — 로깅은 데이터 폴더의 app.log 로, 개발 트리에서는 pip 부트스트랩을 건드리지 않는다."""
from __future__ import annotations

import logging

import main as app_main
from aoi_capacity.utils import paths


def test_setup_logging_writes_to_data_root():
    logger = app_main._setup_logging()
    logger.info("hello-from-test")
    for h in logger.handlers:
        h.flush()
    assert paths.log_file().exists()
    assert "hello-from-test" in paths.log_file().read_text(encoding="utf-8")
    assert app_main._setup_logging() is logger            # 두 번 불러도 핸들러가 늘지 않는다
    assert sum(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers) == 1


def test_ensure_deps_is_noop_in_dev_tree(monkeypatch):
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    assert paths.install_root() is None
    assert app_main._ensure_deps_installed(logging.getLogger("aoi")) is True


def test_software_render_flag_sets_env(monkeypatch):
    from aoi_capacity.utils import prefs

    monkeypatch.delenv("QTWEBENGINE_CHROMIUM_FLAGS", raising=False)
    app_main._apply_env(prefs.Prefs(web_software_render=True))
    assert "--disable-gpu" in app_main._apply_env.__globals__["os"].environ["QTWEBENGINE_CHROMIUM_FLAGS"]
