"""updater — 버전 비교·브랜치 정규화·스테이징 적용. 네트워크·pip 은 전부 모킹(실제 프로세스 실행은 차단)."""
from __future__ import annotations

import io
import json
import os
import subprocess
import urllib.error
import zipfile
from pathlib import Path

import pytest

from aoi_capacity import i18n
from aoi_capacity.utils import updater

_STUB_DEFAULT = "default-branch"
_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _stub_default_branch(monkeypatch):
    updater._default_branch_cache.clear()
    monkeypatch.setattr(updater, "_default_branch", lambda repo, timeout=10.0: _STUB_DEFAULT)


@pytest.fixture(autouse=True)
def _no_real_subprocess(monkeypatch):
    def _blocked(cmd, **kw):
        raise AssertionError("real process launch attempted: " + " ".join(str(c) for c in cmd))
    monkeypatch.setattr(subprocess, "call", _blocked)


def _app(tmp_path, monkeypatch, version: dict | None):
    app = tmp_path / "app"
    app.mkdir(exist_ok=True)
    monkeypatch.setattr(updater, "_app_root", lambda: app)
    monkeypatch.setattr(updater, "_git_head", lambda: None)
    if version is not None:
        (app / "VERSION").write_text(json.dumps(version), encoding="utf-8")
    return app


# ── 버전·확인 ──
def test_current_version_reads_json(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": "abc", "branch": "release", "repo": "o/r"})
    assert updater.current_version()["sha"] == "abc"


def test_check_detects_new_commit_and_keeps_explicit_branch(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": "OLD", "branch": "release", "repo": "o/r"})
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": "NEW", "message": "fix"})
    info = updater.check_for_update()
    assert info["sha"] == "NEW" and info["branch"] == "release" and info["repo"] == "o/r" and info["current"]


def test_check_none_when_up_to_date_or_git_or_pending(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, {"sha": "SAME", "branch": "release", "repo": "o/r"})
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": "SAME"})
    assert updater.check_for_update() is None
    monkeypatch.setattr(updater, "latest_commit", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network")))
    (app / ".git").mkdir()
    assert updater.check_for_update() is None                      # git 작업트리: 네트워크도 안 탄다
    (app / ".git").rmdir()
    monkeypatch.setenv("AOI_APP_HOME", str(tmp_path))
    (tmp_path / "app.new").mkdir()
    assert updater.check_for_update() is None                      # 이미 받아둠


def test_check_seeds_version_and_offers_latest_when_unknown(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, None)
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": "NEW"})
    info = updater.check_for_update()
    assert info and info["current_unknown"] and not info["current"] and info["branch"] == _STUB_DEFAULT
    seeded = json.loads((app / "VERSION").read_text(encoding="utf-8"))
    assert seeded["sha"] == "" and seeded["repo"] == updater.DEFAULT_REPO


def test_resolve_branch_normalizes_legacy_to_default():
    assert updater._resolve_branch("claude/old-work") == _STUB_DEFAULT
    assert updater._resolve_branch("main") == _STUB_DEFAULT
    assert updater._resolve_branch("") == _STUB_DEFAULT
    assert updater._resolve_branch("release") == "release"


def test_manual_check_statuses(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": "SAME", "branch": "release", "repo": "o/r"})
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": "SAME"})
    assert updater.manual_check() == ("latest", {})
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": "NEW", "message": "m"})
    st, info = updater.manual_check()
    assert st == "update" and info["sha"] == "NEW"
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: None)
    st, info = updater.manual_check()
    assert st == "unknown" and info["error"]


def test_latest_self_healing_retries_default_branch(monkeypatch):
    seen = []

    def fake(repo, branch, timeout=15.0):
        seen.append(branch)
        return {"sha": "X"} if branch == _STUB_DEFAULT else None

    monkeypatch.setattr(updater, "latest_commit", fake)
    info, branch = updater._latest_self_healing("o/r", "gone")
    assert info["sha"] == "X" and branch == _STUB_DEFAULT and seen == ["gone", _STUB_DEFAULT]


def test_atom_fallback_and_error_recording(monkeypatch):
    def fake_get(url, headers, timeout):
        if "api.github.com" in url:
            raise urllib.error.HTTPError(url, 403, "blocked", {}, None)
        return b'<feed><id>tag:github.com,2008:Grit::Commit/0123456789abcdef0123456789abcdef01234567</id></feed>'

    monkeypatch.setattr(updater, "_http_get", fake_get)
    assert updater.latest_commit("o/r", "b")["sha"] == "0123456789abcdef0123456789abcdef01234567"
    monkeypatch.setattr(updater, "_http_get", lambda *a: (_ for _ in ()).throw(urllib.error.HTTPError("u", 403, "x", {}, None)))
    assert updater.latest_commit("o/r", "b") is None
    assert "403" in updater.last_error()


def test_ssl_contexts():
    import ssl
    assert updater._ssl_context(insecure=True).verify_mode == ssl.CERT_NONE
    ctx = updater._ssl_context()
    assert ctx is None or ctx.verify_mode == ssl.CERT_REQUIRED


def test_default_branch_constant_matches_remote_default():
    assert updater.DEFAULT_BRANCH == "main"
    assert updater.DEFAULT_REPO == "king-taek/AOI-capacity"


# ── 적용 ──
def _branch_zip(tmp_path, drop=(), extra=None) -> bytes:
    """저장소 트리를 흉내 낸 GitHub 브랜치 zip(최상위 <repo>-<branch>/)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        top = "AOI-capacity-branch/"
        files = {
            "main.py": "print('new')", "requirements.txt": "PyQt6>=6.6\n",
            "aoi_capacity/__init__.py": "", "aoi_capacity/ui/main_window.py": "# new",
            "aoi_capacity/ui/style.qss": (_ROOT / "aoi_capacity/ui/style.qss").read_text(encoding="utf-8"),
            "aoi_capacity/ui/assets/template.html": "<html>__DATA__</html>",
            "aoi_capacity/utils/updater.py": "# u", "aoi_capacity/assets/devices.default.csv": "name\n",
            "scripts/run_aoi.bat": "@echo off", "scripts/build.py": "# dev only",
            "dev/tests/test_x.py": "# dev", "docs/demo.html": "x", "CLAUDE.md": "x", ".gitignore": "x",
            "aoi_capacity/__pycache__/x.pyc": "junk",
        }
        files.update(extra or {})
        for rel, body in files.items():
            if rel in drop:
                continue
            z.writestr(top + rel, body)
    return buf.getvalue()


class _FakeResp:
    def __init__(self, data: bytes):
        self._b = io.BytesIO(data)
        self.headers = {"Content-Length": str(len(data))}

    def read(self, n=-1):
        return self._b.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _serve(monkeypatch, data: bytes):
    monkeypatch.setattr(updater, "_urlopen", lambda url, headers, timeout: _FakeResp(data))


def test_in_place_apply_builds_full_tree_and_skips_dev(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, {"sha": "OLD", "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    (app / "aoi_capacity").mkdir()
    (app / "aoi_capacity" / "removed_upstream.py").write_text("old", encoding="utf-8")
    (app / "requirements.txt").write_text("PyQt6>=6.5\n", encoding="utf-8")
    _serve(monkeypatch, _branch_zip(tmp_path))
    phases = []
    assert updater.download_and_apply("o/r", "b", "NEW", progress=lambda d, t, p: phases.append(p)), updater.last_error()
    assert (app / "main.py").read_text(encoding="utf-8") == "print('new')"
    assert not (app / "aoi_capacity" / "removed_upstream.py").exists()          # 상류 삭제 전파
    assert not (app / "dev").exists() and not (app / "docs").exists() and not (app / "CLAUDE.md").exists()
    assert (app / "scripts" / "run_aoi.bat").is_file() and not (app / "scripts" / "build.py").exists()
    assert not (app / "aoi_capacity" / "__pycache__").exists()
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == "NEW"
    assert updater.deps_changed() is True
    assert i18n.KO.UPDATE_PHASE_DOWNLOAD in phases and phases[-1] == i18n.KO.UPDATE_PHASE_DONE
    assert not (app / ".update.part").exists()


def test_verification_rejects_incomplete_tree_and_keeps_old_version(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, {"sha": "OLD", "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    (app / "main.py").write_text("old", encoding="utf-8")
    _serve(monkeypatch, _branch_zip(tmp_path, drop=("aoi_capacity/ui/main_window.py",)))
    assert not updater.download_and_apply("o/r", "b", "NEW")
    assert "main_window.py" in updater.last_error()
    assert (app / "main.py").read_text(encoding="utf-8") == "old"
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == "OLD"
    assert not (app / ".update.part").exists()


def test_verification_rejects_template_without_data_placeholder(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": "OLD", "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"aoi_capacity/ui/assets/template.html": "<html></html>"}))
    assert not updater.download_and_apply("o/r", "b", "NEW")
    assert i18n.KO.UPDATE_ERR_TEMPLATE_DATA in updater.last_error()


def _exe_install(tmp_path, monkeypatch, marker=True):
    root = tmp_path / "inst"
    app = root / "app"
    app.mkdir(parents=True)
    (app / "main.py").write_text("old", encoding="utf-8")
    (app / "requirements.txt").write_text("PyQt6>=6.6\n", encoding="utf-8")
    (app / "VERSION").write_text(json.dumps({"sha": "OLD", "branch": "b", "repo": "o/r"}), encoding="utf-8")
    monkeypatch.setattr(updater, "_app_root", lambda: app)
    monkeypatch.setattr(updater, "_git_head", lambda: None)
    monkeypatch.setenv("AOI_APP_HOME", str(root))
    if marker:
        from aoi_capacity.utils import bootstrap
        bootstrap.write_deps_marker(root, "PyQt6>=6.6\n")
    return root, app


def test_staged_update_leaves_running_app_untouched(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch)
    _serve(monkeypatch, _branch_zip(tmp_path))
    assert updater.download_and_apply("o/r", "b", "NEW"), updater.last_error()
    assert (app / "main.py").read_text(encoding="utf-8") == "old"                        # 실행 중인 app/ 그대로
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == "OLD"     # 살아있는 VERSION 그대로
    new = root / "app.new"
    assert (new / "main.py").read_text(encoding="utf-8") == "print('new')"
    assert json.loads((new / "VERSION").read_text(encoding="utf-8"))["sha"] == "NEW"
    assert not (root / "app.new.part").exists()
    assert updater.update_pending()


def test_new_packages_are_installed_then_the_update_applies(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch)
    (root / "python").mkdir()
    (root / "python" / "python.exe").write_bytes(b"x")
    calls = []
    monkeypatch.setattr(subprocess, "call", lambda cmd, **kw: (calls.append(cmd), 0)[1])
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"requirements.txt": "PyQt6>=6.6\npsutil\n"}))
    assert updater.download_and_apply("o/r", "b", "NEW"), updater.last_error()
    assert len(calls) == 1 and calls[0][0].endswith("python.exe") and "--upgrade" not in calls[0]
    assert (root / "app.new").exists() and not updater.deps_blocked()


def test_failed_package_install_leaves_the_old_version_running(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch)
    monkeypatch.setattr(subprocess, "call", lambda cmd, **kw: 1)
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"requirements.txt": "PyQt6>=6.6\npsutil\n"}))
    assert not updater.download_and_apply("o/r", "b", "NEW")
    assert updater.deps_blocked() and "pip" in updater.last_error()
    assert not (root / "app.new").exists() and not (root / "app.new.part").exists()
    assert (app / "main.py").read_text(encoding="utf-8") == "old"


def test_unchanged_requirements_never_run_pip(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch)
    _serve(monkeypatch, _branch_zip(tmp_path))      # requirements 동일 → subprocess.call 이 불리면 autouse 가드가 터진다
    assert updater.download_and_apply("o/r", "b", "NEW"), updater.last_error()


def test_bad_zip_is_reported(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": "OLD", "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    _serve(monkeypatch, b"<html>blocked</html>")
    assert not updater.download_and_apply("o/r", "b", "NEW")
    assert updater.last_error() == i18n.KO.UPDATE_ERR_BAD_ZIP
