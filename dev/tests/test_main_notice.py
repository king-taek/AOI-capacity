"""C16 — 의존성 설치 실패 안내: pythonw(`sys.stdin is None` → `input()` 이 RuntimeError)·EOF 에서도 새 예외 없이
표준 라이브러리 경로(Windows MessageBoxW 또는 print)로 알리고 app.log 경로를 짧게 적는다. PyQt6 는 다시 import 하지 않는다."""
from __future__ import annotations

import ast
import builtins
import ctypes
import io
import logging
import types
from pathlib import Path

import pytest

import main as app_main
from aoi_capacity import i18n
from aoi_capacity.utils import bootstrap, paths


def _no_input(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a, **k: (_ for _ in ()).throw(AssertionError("input() must not be called")))


def test_stdin_none_skips_input_and_prints_when_no_messagebox(monkeypatch, capsys):
    monkeypatch.setattr(app_main.sys, "stdin", None)
    monkeypatch.setattr(app_main.os, "name", "posix")
    _no_input(monkeypatch)
    assert app_main._pause_or_notify("prompt", "notice text") == "print"
    assert "notice text" in capsys.readouterr().out


@pytest.mark.parametrize("exc", [EOFError, RuntimeError("input(): lost sys.stdin"), OSError])
def test_input_failures_fall_back_without_raising(monkeypatch, capsys, exc):
    monkeypatch.setattr(app_main.sys, "stdin", io.StringIO(""))
    monkeypatch.setattr(app_main.os, "name", "posix")
    monkeypatch.setattr(builtins, "input", lambda *a, **k: (_ for _ in ()).throw(exc))
    assert app_main._pause_or_notify("prompt", "notice text") == "print"
    assert "notice text" in capsys.readouterr().out


def test_console_path_waits_for_enter(monkeypatch, capsys):
    monkeypatch.setattr(app_main.sys, "stdin", io.StringIO("\n"))
    seen = []
    monkeypatch.setattr(builtins, "input", lambda p="": (seen.append(p), "")[1])
    assert app_main._pause_or_notify(i18n.KO.BOOT_PRESS_ENTER, "notice") == "input"
    assert seen == [i18n.KO.BOOT_PRESS_ENTER] and "notice" not in capsys.readouterr().out


def test_windows_uses_messagebox_when_stdin_is_none(monkeypatch, capsys):
    calls = []

    class _User32:
        @staticmethod
        def MessageBoxW(hwnd, text, title, flags):
            calls.append((hwnd, text, title, flags))
            return 1

    monkeypatch.setattr(ctypes, "windll", types.SimpleNamespace(user32=_User32), raising=False)
    monkeypatch.setattr(app_main.os, "name", "nt")
    monkeypatch.setattr(app_main.sys, "stdin", None)
    _no_input(monkeypatch)
    assert app_main._pause_or_notify("prompt", "notice text") == "messagebox"
    assert calls == [(None, "notice text", i18n.KO.APP_TITLE, 0x10 | 0x40000)]
    assert "notice text" not in capsys.readouterr().out


def test_windows_without_windll_or_a_failing_box_prints_instead(monkeypatch, capsys):
    monkeypatch.setattr(app_main.os, "name", "nt")
    monkeypatch.setattr(app_main.sys, "stdin", None)
    _no_input(monkeypatch)
    monkeypatch.delattr(ctypes, "windll", raising=False)
    assert app_main._pause_or_notify("prompt", "notice A") == "print"

    class _Boom:
        @staticmethod
        def MessageBoxW(*a):
            raise OSError("no desktop")

    monkeypatch.setattr(ctypes, "windll", types.SimpleNamespace(user32=_Boom), raising=False)
    assert app_main._pause_or_notify("prompt", "notice B") == "print"
    out = capsys.readouterr().out
    assert "notice A" in out and "notice B" in out


def test_ensure_deps_failure_notifies_with_log_path_and_returns_false(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(paths, "install_root", lambda: tmp_path)
    monkeypatch.setattr(bootstrap, "ensure_deps", lambda **k: (k["log"](i18n.KO.BOOT_DEPS_FAILED), False)[1])
    monkeypatch.setattr(app_main.sys, "stdin", None)
    monkeypatch.setattr(app_main.os, "name", "posix")
    _no_input(monkeypatch)
    assert app_main._ensure_deps_installed(logging.getLogger("aoi")) is False
    out = capsys.readouterr().out
    assert i18n.KO.BOOT_DEPS_FAILED in out and str(paths.log_file()) in out
    assert i18n.KO.BOOT_LOG_HINT_FMT.format(path=paths.log_file()) in out


def test_notice_path_never_imports_pyqt6():
    """PyQt6 import 는 `_run_gui` 안에만 — 설치에 실패한 패키지를 안내 경로에서 다시 요구하지 않는다."""
    src = (paths._project_root() / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    owners = {}
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                if any(n.startswith("PyQt6") for n in names):
                    owners.setdefault(fn.name, []).append(names)
    assert set(owners) == {"_run_gui"}, owners
    for name in ("_pause_or_notify", "_message_box", "_ensure_deps_installed"):
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
        mods = [a.name for n in ast.walk(fn) if isinstance(n, ast.Import) for a in n.names]
        mods += [n.module or "" for n in ast.walk(fn) if isinstance(n, ast.ImportFrom)]
        assert all(m.split(".")[0] in ("ctypes", "aoi_capacity") for m in mods), (name, mods)
