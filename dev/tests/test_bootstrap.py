"""bootstrap — 표식 지문·pip 명령·ensure_deps 흐름. 실제 pip 은 절대 돌리지 않는다(가짜 run 주입)."""
from __future__ import annotations

from pathlib import Path

from aoi_capacity import i18n
from aoi_capacity.utils import bootstrap

REQ = "PyQt6>=6.6\n# comment\n\nPyQt6-WebEngine>=6.6\ntruststore>=0.8 ; python_version >= \"3.10\"\n"


def test_req_lines_strip_comments_and_blanks():
    assert bootstrap.req_lines(REQ) == ["PyQt6>=6.6", "PyQt6-WebEngine>=6.6", 'truststore>=0.8 ; python_version >= "3.10"']
    assert bootstrap.req_lines(None) == []


def test_fingerprint_ignores_comment_only_changes():
    assert bootstrap.req_fingerprint(REQ) == bootstrap.req_fingerprint(REQ + "# more\n")
    assert bootstrap.req_fingerprint(REQ) != bootstrap.req_fingerprint(REQ + "psutil\n")


def test_pip_cmd_has_no_upgrade_and_isolates_user_site(tmp_path):
    cmd = bootstrap.pip_install_cmd("py.exe", tmp_path / "requirements.txt")
    assert "--upgrade" not in cmd and "-s" in cmd and cmd[-2:] == ["-r", str(tmp_path / "requirements.txt")]


def test_deps_installed_compares_fingerprint(tmp_path):
    assert not bootstrap.deps_installed(tmp_path, REQ)
    assert bootstrap.write_deps_marker(tmp_path, REQ)
    assert bootstrap.deps_installed(tmp_path, REQ)
    assert bootstrap.deps_installed(tmp_path, None)                 # 비교 대상 없음 → 존재만
    assert not bootstrap.deps_installed(tmp_path, REQ + "psutil\n")   # requirements 바뀜 → 재설치


def _root(tmp_path) -> Path:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "requirements.txt").write_text(REQ, encoding="utf-8")
    return tmp_path


def test_ensure_deps_installs_then_writes_marker(tmp_path):
    root = _root(tmp_path)
    calls, logs = [], []
    ok = bootstrap.ensure_deps(root, "py.exe", run=lambda c: (calls.append(c), 0)[1], log=logs.append)
    assert ok and len(calls) == 1 and calls[0][0] == "py.exe"
    assert bootstrap.deps_marker(root).exists()
    assert logs == [i18n.KO.BOOT_DEPS_INSTALLING, i18n.KO.BOOT_DEPS_DONE]
    # 두 번째는 pip 을 부르지 않는다
    assert bootstrap.ensure_deps(root, "py.exe", run=lambda c: (calls.append(c), 0)[1]) and len(calls) == 1


def test_ensure_deps_failure_leaves_no_marker(tmp_path):
    root = _root(tmp_path)
    logs = []
    assert not bootstrap.ensure_deps(root, "py.exe", run=lambda c: 1, log=logs.append)
    assert not bootstrap.deps_marker(root).exists()
    assert logs[-1] == i18n.KO.BOOT_DEPS_FAILED


def test_ensure_deps_noop_without_install_root(monkeypatch):
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    assert bootstrap.ensure_deps(run=lambda c: (_ for _ in ()).throw(AssertionError("pip must not run")))


def test_ensure_deps_uses_app_home_env(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setenv("AOI_APP_HOME", str(root))
    calls = []
    assert bootstrap.ensure_deps(run=lambda c: (calls.append(c), 0)[1])
    assert calls and calls[0][-1] == str(root / "app" / "requirements.txt")


def test_py_standalone_url_is_windows_install_only():
    assert bootstrap.PY_STANDALONE_URL.startswith("https://github.com/astral-sh/python-build-standalone/")
    assert "x86_64-pc-windows-msvc-install_only" in bootstrap.PY_STANDALONE_URL
