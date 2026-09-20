"""updater — 버전 비교·브랜치 정규화·CI 게이트·zip 검사·스테이징 적용·저널 롤백·pip 상한.
네트워크·pip 은 전부 모킹(실제 프로세스 실행은 autouse 가드가 차단)."""
from __future__ import annotations

import io
import json
import os
import ssl
import subprocess
import urllib.error
import zipfile
from pathlib import Path

import pytest

from aoi_capacity import i18n
from aoi_capacity.utils import updater

_STUB_DEFAULT = "default-branch"
_ROOT = Path(__file__).resolve().parents[2]
SHA_OLD = "0" * 40
SHA_NEW = "abcdef0123456789abcdef0123456789abcdef01"
SHA_OTHER = "1234567890abcdef1234567890abcdef12345678"


@pytest.fixture(autouse=True)
def _stub_default_branch(monkeypatch):
    updater._default_branch_cache.clear()
    monkeypatch.setattr(updater, "_default_branch", lambda repo, timeout=10.0: _STUB_DEFAULT)


@pytest.fixture(autouse=True)
def _no_real_subprocess(monkeypatch):
    """실제 프로세스는 한 번도 뜨지 않는다 — call · run · Popen 전부(check_output 도 Popen 을 쓴다)."""
    def _blocked(cmd, *a, **kw):
        raise AssertionError("real process launch attempted: " + " ".join(str(c) for c in cmd))
    monkeypatch.setattr(subprocess, "call", _blocked)
    monkeypatch.setattr(subprocess, "run", _blocked)
    monkeypatch.setattr(subprocess, "Popen", _blocked)


@pytest.fixture
def gate_ok(monkeypatch):
    """CI 게이트 통과 — 게이트 자체를 보는 테스트가 아닐 때."""
    seen = []
    monkeypatch.setattr(updater, "_ci_gate", lambda repo, sha, timeout=15.0: (seen.append(sha), (True, ""))[1])
    return seen


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


def test_check_detects_new_commit_and_keeps_explicit_branch(tmp_path, monkeypatch, gate_ok):
    _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "release", "repo": "o/r"})
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": SHA_NEW, "message": "fix"})
    info = updater.check_for_update()
    assert info["sha"] == SHA_NEW and info["branch"] == "release" and info["repo"] == "o/r" and info["current"]
    assert gate_ok == [SHA_NEW]


def test_check_none_when_up_to_date_or_git_or_pending(tmp_path, monkeypatch, gate_ok):
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
    assert gate_ok == []


def test_check_seeds_version_and_offers_latest_when_unknown(tmp_path, monkeypatch, gate_ok):
    app = _app(tmp_path, monkeypatch, None)
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": SHA_NEW})
    info = updater.check_for_update()
    assert info and info["current_unknown"] and not info["current"] and info["branch"] == _STUB_DEFAULT
    seeded = json.loads((app / "VERSION").read_text(encoding="utf-8"))
    assert seeded["sha"] == "" and seeded["repo"] == updater.DEFAULT_REPO


def test_resolve_branch_normalizes_legacy_to_default():
    assert updater._resolve_branch("claude/old-work") == _STUB_DEFAULT
    assert updater._resolve_branch("main") == _STUB_DEFAULT
    assert updater._resolve_branch("") == _STUB_DEFAULT
    assert updater._resolve_branch("release") == "release"


def test_manual_check_statuses(tmp_path, monkeypatch, gate_ok):
    _app(tmp_path, monkeypatch, {"sha": "SAME", "branch": "release", "repo": "o/r"})
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": "SAME"})
    assert updater.manual_check() == ("latest", {})
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": SHA_NEW, "message": "m"})
    st, info = updater.manual_check()
    assert st == "update" and info["sha"] == SHA_NEW
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


def test_default_branch_constant_matches_remote_default():
    assert updater.DEFAULT_BRANCH == "main"
    assert updater.DEFAULT_REPO == "king-taek/AOI-capacity"


# ── TLS(C01): 검증 실패는 우회 없이 멈춘다 ──
def test_ssl_context_is_always_verifying():
    ctx = updater._ssl_context()
    assert ctx is None or ctx.verify_mode == ssl.CERT_REQUIRED
    assert not hasattr(updater, "insecure_fallback_used") and not hasattr(updater, "_OPENER_INSECURE")
    src = (_ROOT / "aoi_capacity/utils/updater.py").read_text(encoding="utf-8")
    assert "CERT_NONE" not in src and "AOI_UPDATE_INSECURE" not in src and "check_hostname = False" not in src


class _VerifyFailOpener:
    def __init__(self):
        self.calls = 0

    def open(self, req, timeout=None):
        self.calls += 1
        raise urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed: self signed"))


def test_ssl_verify_failure_stops_check_with_reason_and_no_retry(monkeypatch):
    op = _VerifyFailOpener()
    monkeypatch.setattr(updater, "_opener", lambda: op)
    built = []
    monkeypatch.setattr(updater, "_make_opener", lambda *a, **k: built.append(a) or op)
    assert updater.latest_commit("o/r", "b") is None
    assert op.calls == 1                                    # api 한 번 — atom 으로도, 무검증으로도 다시 가지 않는다
    assert built == []
    assert updater.last_error().startswith(i18n.KO.UPDATE_ERR_TLS_VERIFY_FMT.split("{")[0])
    assert "api.github.com" in updater.last_error()


def test_ssl_verify_failure_stops_apply_and_keeps_app(tmp_path, monkeypatch, gate_ok):
    app = _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    (app / "main.py").write_text("old", encoding="utf-8")
    op = _VerifyFailOpener()
    monkeypatch.setattr(updater, "_opener", lambda: op)
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert op.calls == 1
    assert updater.last_error().startswith(i18n.KO.UPDATE_ERR_TLS_VERIFY_FMT.split("{")[0])
    assert (app / "main.py").read_text(encoding="utf-8") == "old"
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == SHA_OLD
    assert not (app / ".update.part").exists()


def test_manual_check_reports_tls_failure(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "release", "repo": "o/r"})
    monkeypatch.setattr(updater, "_opener", lambda: _VerifyFailOpener())
    st, info = updater.manual_check()
    assert st == "unknown" and info["error"].startswith(i18n.KO.UPDATE_ERR_TLS_VERIFY_FMT.split("{")[0])


# ── CI 게이트(D61) ──
def _runs(*runs):
    return json.dumps({"total_count": len(runs), "workflow_runs": list(runs)}).encode("utf-8")


def _run(sha=SHA_NEW, status="completed", conclusion="success", event="push", name="tests", path=".github/workflows/tests.yml"):
    return {"head_sha": sha, "status": status, "conclusion": conclusion, "event": event, "name": name, "path": path}


def _serve_runs(monkeypatch, body, urls=None):
    def fake_get(url, headers, timeout):
        if urls is not None:
            urls.append(url)
        if isinstance(body, Exception):
            raise body
        return body
    monkeypatch.setattr(updater, "_http_get", fake_get)


def test_ci_gate_passes_only_on_completed_success_for_that_sha(monkeypatch):
    urls = []
    _serve_runs(monkeypatch, _runs(_run()), urls)
    assert updater._ci_gate("o/r", SHA_NEW) == (True, "")
    assert urls and "actions/workflows/tests.yml/runs" in urls[0] and f"head_sha={SHA_NEW}" in urls[0]


@pytest.mark.parametrize("runs, expected", [
    ([], "UPDATE_CI_NO_RUN"),
    ([_run(status="in_progress", conclusion=None)], "UPDATE_CI_PENDING"),
    ([_run(status="queued", conclusion=None)], "UPDATE_CI_PENDING"),
    ([_run(conclusion="failure")], "UPDATE_CI_FAILED"),
    ([_run(conclusion="cancelled")], "UPDATE_CI_FAILED"),
    ([_run(conclusion="skipped")], "UPDATE_CI_FAILED"),
    ([_run(sha=SHA_OTHER)], "UPDATE_CI_NO_RUN"),                        # 이전 커밋의 성공은 성공이 아니다
    ([_run(event="pull_request")], "UPDATE_CI_NO_RUN"),                 # 신뢰하지 않는 event
    ([_run(name="graphify", path=".github/workflows/graphify.yml")], "UPDATE_CI_NO_RUN"),
    ([_run(conclusion="failure"), _run(status="in_progress", conclusion=None)], "UPDATE_CI_PENDING"),
])
def test_ci_gate_holds_on_pending_failed_or_missing(monkeypatch, runs, expected):
    _serve_runs(monkeypatch, _runs(*runs))
    ok, reason = updater._ci_gate("o/r", SHA_NEW)
    assert not ok and reason == getattr(i18n.KO, expected)


def test_ci_gate_success_after_failed_rerun_counts(monkeypatch):
    _serve_runs(monkeypatch, _runs(_run(conclusion="failure"), _run(conclusion="success")))
    assert updater._ci_gate("o/r", SHA_NEW)[0]


def test_ci_gate_holds_when_query_fails_or_sha_is_short(monkeypatch):
    _serve_runs(monkeypatch, urllib.error.HTTPError("u", 403, "blocked", {}, None))
    ok, reason = updater._ci_gate("o/r", SHA_NEW)
    assert not ok and reason.startswith(i18n.KO.UPDATE_CI_QUERY_FAILED_FMT.split("{")[0]) and "403" in reason
    _serve_runs(monkeypatch, b"<html>not json</html>")
    assert not updater._ci_gate("o/r", SHA_NEW)[0]
    calls = []
    _serve_runs(monkeypatch, _runs(_run()), calls)
    ok, reason = updater._ci_gate("o/r", SHA_NEW[:7])
    assert not ok and reason == i18n.KO.UPDATE_ERR_BAD_SHA_FMT.format(sha=SHA_NEW[:7]) and calls == []


def test_check_and_manual_hold_when_ci_not_passed(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "release", "repo": "o/r"})
    monkeypatch.setattr(updater, "latest_commit", lambda repo, branch, timeout=15.0: {"sha": SHA_NEW, "message": "m"})
    monkeypatch.setattr(updater, "_ci_gate", lambda repo, sha, timeout=15.0: (False, i18n.KO.UPDATE_CI_PENDING))
    assert updater.check_for_update() is None
    assert updater.last_error() == i18n.KO.UPDATE_CI_PENDING
    st, info = updater.manual_check()
    assert st == "held" and info["sha"] == SHA_NEW and info["reason"] == i18n.KO.UPDATE_CI_PENDING


def test_apply_refuses_without_ci_pass_and_never_downloads(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    monkeypatch.setattr(updater, "_ci_gate", lambda repo, sha, timeout=15.0: (False, i18n.KO.UPDATE_CI_FAILED))
    monkeypatch.setattr(updater, "_urlopen", lambda *a: (_ for _ in ()).throw(AssertionError("download attempted")))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert updater.last_error() == i18n.KO.UPDATE_CI_FAILED
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == SHA_OLD


# ── 적용 ──
def _branch_zip(tmp_path, drop=(), extra=None, top=f"AOI-capacity-{SHA_NEW}/") -> bytes:
    """저장소 트리를 흉내 낸 GitHub archive zip(최상위 <repo>-<sha>/). 루트에 잡파일도 섞는다."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        files = {
            "main.py": "print('new')", "requirements.txt": "PyQt6>=6.6\n",
            "aoi_capacity/__init__.py": "", "aoi_capacity/ui/main_window.py": "# new",
            "aoi_capacity/ui/style.qss": (_ROOT / "aoi_capacity/ui/style.qss").read_text(encoding="utf-8"),
            "aoi_capacity/ui/assets/template.html": "<html>__DATA__</html>",
            "aoi_capacity/utils/updater.py": "# u", "aoi_capacity/assets/devices.default.csv": "name\n",
            "scripts/run_aoi.bat": "@echo off", "scripts/build.py": "# dev only",
            "dev/tests/test_x.py": "# dev", "docs/demo.html": "x", "CLAUDE.md": "x", ".gitignore": "x",
            "진행상황.md": "x", "v6home.png": "x", ".graphifyignore": "x", "pytest.ini": "x",
            "aoi_capacity/__pycache__/x.pyc": "junk", "aoi_capacity/debug.log": "junk",
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


def _serve(monkeypatch, data: bytes, urls=None):
    def fake(url, headers, timeout):
        if urls is not None:
            urls.append(url)
        return _FakeResp(data)
    monkeypatch.setattr(updater, "_urlopen", fake)
    monkeypatch.setattr(updater, "_ci_gate", lambda repo, sha, timeout=15.0: (True, ""))


def test_in_place_apply_builds_full_tree_and_skips_dev(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    (app / "aoi_capacity").mkdir()
    (app / "aoi_capacity" / "removed_upstream.py").write_text("old", encoding="utf-8")
    (app / "requirements.txt").write_text("PyQt6>=6.5\n", encoding="utf-8")
    urls = []
    _serve(monkeypatch, _branch_zip(tmp_path), urls)
    phases = []
    assert updater.download_and_apply("o/r", "b", SHA_NEW, progress=lambda d, t, p: phases.append(p)), updater.last_error()
    assert urls == [f"https://github.com/o/r/archive/{SHA_NEW}.zip"]           # 브랜치 HEAD 가 아니라 확인한 SHA
    assert (app / "main.py").read_text(encoding="utf-8") == "print('new')"
    assert not (app / "aoi_capacity" / "removed_upstream.py").exists()          # 상류 삭제 전파
    assert not (app / "dev").exists() and not (app / "docs").exists() and not (app / "CLAUDE.md").exists()
    assert not (app / "진행상황.md").exists() and not (app / "v6home.png").exists() and not (app / ".graphifyignore").exists()
    assert (app / "scripts" / "run_aoi.bat").is_file() and not (app / "scripts" / "build.py").exists()
    assert not (app / "aoi_capacity" / "__pycache__").exists() and not (app / "aoi_capacity" / "debug.log").exists()
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == SHA_NEW
    assert updater.deps_changed() is True
    assert i18n.KO.UPDATE_PHASE_DOWNLOAD in phases and phases[-1] == i18n.KO.UPDATE_PHASE_DONE
    assert not (app / ".update.part").exists()
    assert not list(app.glob("*.old-update"))


def test_verification_rejects_incomplete_tree_and_keeps_old_version(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    (app / "main.py").write_text("old", encoding="utf-8")
    _serve(monkeypatch, _branch_zip(tmp_path, drop=("aoi_capacity/ui/main_window.py",)))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert "main_window.py" in updater.last_error()
    assert (app / "main.py").read_text(encoding="utf-8") == "old"
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == SHA_OLD
    assert not (app / ".update.part").exists()


def test_verification_rejects_template_without_data_placeholder(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"aoi_capacity/ui/assets/template.html": "<html></html>"}))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert i18n.KO.UPDATE_ERR_TEMPLATE_DATA in updater.last_error()


def test_apply_rejects_short_sha_before_any_network(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.setattr(updater, "_urlopen", lambda *a: (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setattr(updater, "_ci_gate", lambda *a, **k: (_ for _ in ()).throw(AssertionError("gate")))
    assert not updater.download_and_apply("o/r", "b", "NEW")
    assert updater.last_error() == i18n.KO.UPDATE_ERR_BAD_SHA_FMT.format(sha="new")


def _exe_install(tmp_path, monkeypatch, marker=True):
    root = tmp_path / "inst"
    app = root / "app"
    app.mkdir(parents=True)
    (app / "main.py").write_text("old", encoding="utf-8")
    (app / "requirements.txt").write_text("PyQt6>=6.6\n", encoding="utf-8")
    (app / "VERSION").write_text(json.dumps({"sha": SHA_OLD, "branch": "b", "repo": "o/r"}), encoding="utf-8")
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
    assert updater.download_and_apply("o/r", "b", SHA_NEW), updater.last_error()
    assert (app / "main.py").read_text(encoding="utf-8") == "old"                        # 실행 중인 app/ 그대로
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == SHA_OLD   # 살아있는 VERSION 그대로
    new = root / "app.new"
    assert (new / "main.py").read_text(encoding="utf-8") == "print('new')"
    assert json.loads((new / "VERSION").read_text(encoding="utf-8"))["sha"] == SHA_NEW
    assert {p.name for p in new.iterdir()} == set(updater.STAGED_TOP_LEVEL)
    assert not (root / "app.new.part").exists()
    assert updater.update_pending()


# ── pip(C10): 상한·자식 종료·표식 ──
class _FakePopen:
    """pip 대역. waits_before_exit 번 wait 가 TimeoutExpired 를 낸 뒤 rc 로 끝난다(None 이면 영원히 안 끝남)."""
    instances: list = []

    def __init__(self, cmd, rc=0, waits_before_exit=0, kill_raises=None, **kw):
        self.cmd, self.rc, self.left, self.kill_raises = cmd, rc, waits_before_exit, kill_raises
        self.killed = False
        self.waits = 0
        _FakePopen.instances.append(self)

    def wait(self, timeout=None):
        self.waits += 1
        if self.killed:
            return -9
        if self.left is None or self.left > 0:
            if self.left is not None:
                self.left -= 1
            raise subprocess.TimeoutExpired(self.cmd, timeout or 0)
        return self.rc

    def kill(self):
        if self.kill_raises:
            raise self.kill_raises
        self.killed = True


def _fake_pip(monkeypatch, **behaviour):
    _FakePopen.instances = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: _FakePopen(cmd, **behaviour))
    return _FakePopen.instances


def test_new_packages_are_installed_then_the_update_applies(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch)
    (root / "python").mkdir()
    (root / "python" / "python.exe").write_bytes(b"x")
    procs = _fake_pip(monkeypatch, rc=0, waits_before_exit=2)
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"requirements.txt": "PyQt6>=6.6\npsutil\n"}))
    assert updater.download_and_apply("o/r", "b", SHA_NEW), updater.last_error()
    assert len(procs) == 1 and procs[0].cmd[0].endswith("python.exe") and "--upgrade" not in procs[0].cmd
    assert not procs[0].killed
    assert (root / "app.new").exists() and not updater.deps_blocked()
    from aoi_capacity.utils import bootstrap
    assert bootstrap.deps_installed(root, "PyQt6>=6.6\npsutil\n")


def test_failed_package_install_leaves_the_old_version_running(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch)
    _fake_pip(monkeypatch, rc=1)
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"requirements.txt": "PyQt6>=6.6\npsutil\n"}))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert updater.deps_blocked() and "pip" in updater.last_error()
    assert not (root / "app.new").exists() and not (root / "app.new.part").exists()
    assert (app / "main.py").read_text(encoding="utf-8") == "old"


def test_pip_timeout_kills_child_and_writes_no_marker(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch, marker=False)
    procs = _fake_pip(monkeypatch, waits_before_exit=None)                     # 영원히 안 끝나는 pip
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"requirements.txt": "PyQt6>=6.6\npsutil\n"}))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW, pip_timeout=0.001)
    assert procs[0].killed and procs[0].waits >= 2                              # kill 뒤 wait 까지
    assert updater.deps_blocked()
    assert updater.last_error() == i18n.KO.UPDATE_ERR_PIP_TIMEOUT_FMT.format(sec=0)
    assert not (root / ".deps_installed").exists()
    assert not (root / "app.new").exists() and not (root / "app.new.part").exists()
    assert (app / "main.py").read_text(encoding="utf-8") == "old"


def test_pip_cancel_kills_child(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch, marker=False)
    procs = _fake_pip(monkeypatch, waits_before_exit=None)
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"requirements.txt": "PyQt6>=6.6\npsutil\n"}))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW, cancel=lambda: True)
    assert procs[0].killed and updater.last_error() == i18n.KO.UPDATE_ERR_PIP_CANCELLED
    assert not (root / ".deps_installed").exists() and not (root / "app.new").exists()


def test_pip_kill_failure_is_reported_not_swallowed(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch, marker=False)
    _fake_pip(monkeypatch, waits_before_exit=None, kill_raises=PermissionError("access denied"))
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"requirements.txt": "PyQt6>=6.6\npsutil\n"}))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW, pip_timeout=0.001)
    err = updater.last_error()
    assert err.startswith(i18n.KO.UPDATE_ERR_PIP_TIMEOUT_FMT.split("{")[0]) and "access denied" in err
    assert not (root / ".deps_installed").exists() and not (root / "app.new").exists()


def test_pip_start_failure_is_reported(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch, marker=False)
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: (_ for _ in ()).throw(FileNotFoundError("python.exe")))
    _serve(monkeypatch, _branch_zip(tmp_path, extra={"requirements.txt": "PyQt6>=6.6\npsutil\n"}))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert updater.last_error().startswith(i18n.KO.UPDATE_ERR_PIP_START_FMT.split("{")[0])
    assert not (root / ".deps_installed").exists()


def test_unchanged_requirements_never_run_pip(tmp_path, monkeypatch):
    root, app = _exe_install(tmp_path, monkeypatch)
    _serve(monkeypatch, _branch_zip(tmp_path))      # requirements 동일 → Popen 이 불리면 autouse 가드가 터진다
    assert updater.download_and_apply("o/r", "b", SHA_NEW), updater.last_error()


def test_bad_zip_is_reported(tmp_path, monkeypatch):
    _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    _serve(monkeypatch, b"<html>blocked</html>")
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert updater.last_error() == i18n.KO.UPDATE_ERR_BAD_ZIP


# ── zip 방어 ──
def _zip_of(entries: dict, symlinks=()) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, body in entries.items():
            z.writestr(name, body)
        for name, target in symlinks:
            zi = zipfile.ZipInfo(name)
            zi.external_attr = (0o120777 << 16)
            z.writestr(zi, target)
    return buf.getvalue()


def _extract(tmp_path, data: bytes, sha=SHA_NEW):
    zp = tmp_path / "in.zip"
    zp.write_bytes(data)
    return updater._safe_extract(zp, tmp_path / "out", sha, lambda *a: None)


@pytest.mark.parametrize("entries, key", [
    ({"/etc/x": "a"}, "UPDATE_ERR_ZIP_ENTRY_FMT"),
    ({f"AOI-capacity-{SHA_NEW}/../x.py": "a"}, "UPDATE_ERR_ZIP_ENTRY_FMT"),
    ({f"AOI-capacity-{SHA_NEW}/a/../../x.py": "a"}, "UPDATE_ERR_ZIP_ENTRY_FMT"),
    ({"C:/Windows/x.py": "a"}, "UPDATE_ERR_ZIP_ENTRY_FMT"),
    ({"\\\\server\\share\\x.py": "a"}, "UPDATE_ERR_ZIP_ENTRY_FMT"),
    ({f"AOI-capacity-{SHA_NEW}/a.py": "a", f"other-{SHA_NEW}/b.py": "b"}, "UPDATE_ERR_ZIP_ROOTS_FMT"),
    ({f"AOI-capacity-{SHA_OTHER}/a.py": "a"}, "UPDATE_ERR_ZIP_ROOT_SHA_FMT"),
    ({"AOI-capacity-main/a.py": "a"}, "UPDATE_ERR_ZIP_ROOT_SHA_FMT"),
    ({f"AOI-capacity-{SHA_NEW}/Main.py": "a", f"AOI-capacity-{SHA_NEW}/main.py": "b"}, "UPDATE_ERR_ZIP_CASE_FMT"),
])
def test_safe_extract_rejects_hostile_entries_without_writing(tmp_path, entries, key):
    with pytest.raises(updater.UpdateError) as ei:
        _extract(tmp_path, _zip_of(entries))
    assert str(ei.value).startswith(getattr(i18n.KO, key).split("{")[0])
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").rglob("*"))


def test_safe_extract_rejects_symlinks(tmp_path):
    with pytest.raises(updater.UpdateError):
        _extract(tmp_path, _zip_of({f"AOI-capacity-{SHA_NEW}/a.py": "a"}, symlinks=[(f"AOI-capacity-{SHA_NEW}/lnk", "/etc/passwd")]))
    assert not (tmp_path / "out").exists()


def test_safe_extract_caps_file_count_and_total_size(tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "ZIP_MAX_FILES", 3)
    many = {f"AOI-capacity-{SHA_NEW}/f{i}.py": "x" for i in range(4)}
    with pytest.raises(updater.UpdateError) as ei:
        _extract(tmp_path, _zip_of(many))
    assert str(ei.value).startswith(i18n.KO.UPDATE_ERR_ZIP_TOO_BIG_FMT.split("{")[0])
    monkeypatch.setattr(updater, "ZIP_MAX_FILES", 5000)
    monkeypatch.setattr(updater, "ZIP_MAX_BYTES", 10)
    with pytest.raises(updater.UpdateError):
        _extract(tmp_path, _zip_of({f"AOI-capacity-{SHA_NEW}/big.bin": "x" * 11}))


def test_zip_limits_are_sane():
    assert updater.ZIP_MAX_FILES == 5000 and updater.ZIP_MAX_BYTES == 300 * 1024 * 1024
    assert updater.PIP_TIMEOUT_SEC == 600.0


def test_safe_extract_accepts_github_layout_and_short_sha_root(tmp_path):
    root = _extract(tmp_path, _zip_of({f"AOI-capacity-{SHA_NEW}/": "", f"AOI-capacity-{SHA_NEW}/a/b.py": "ok"}))
    assert root.name == f"AOI-capacity-{SHA_NEW}" and (root / "a" / "b.py").read_text(encoding="utf-8") == "ok"
    (tmp_path / "2").mkdir()
    root2 = _extract(tmp_path / "2", _zip_of({f"AOI-capacity-{SHA_NEW[:7]}/a.py": "ok"}))
    assert root2.name == f"AOI-capacity-{SHA_NEW[:7]}"


def test_apply_rejects_zip_whose_root_is_another_commit(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    (app / "main.py").write_text("old", encoding="utf-8")
    _serve(monkeypatch, _branch_zip(tmp_path, top=f"AOI-capacity-{SHA_OTHER}/"))
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert updater.last_error().startswith(i18n.KO.UPDATE_ERR_ZIP_ROOT_SHA_FMT.split("{")[0])
    assert (app / "main.py").read_text(encoding="utf-8") == "old"
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == SHA_OLD


# ── 제자리 적용 저널·롤백(N02) ──
def _loose_app(tmp_path, monkeypatch):
    """비-exe loose 폴더: 항목 4개(파일 2 + 폴더 2). 스테이징 트리는 같은 이름에 새 내용."""
    app = _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    (app / "main.py").write_text("old main", encoding="utf-8")
    (app / "requirements.txt").write_text("old req", encoding="utf-8")
    (app / "aoi_capacity").mkdir()
    (app / "aoi_capacity" / "x.py").write_text("old x", encoding="utf-8")
    (app / "scripts").mkdir()
    (app / "scripts" / "run.bat").write_text("old bat", encoding="utf-8")
    (app / "user_note.txt").write_text("mine", encoding="utf-8")            # 스테이징에 없는 파일은 건드리지 않는다
    staging = app / ".update.part"
    staging.mkdir()
    (staging / "main.py").write_text("new main", encoding="utf-8")
    (staging / "requirements.txt").write_text("new req", encoding="utf-8")
    (staging / "aoi_capacity").mkdir()
    (staging / "aoi_capacity" / "y.py").write_text("new y", encoding="utf-8")
    (staging / "scripts").mkdir()
    (staging / "scripts" / "run.bat").write_text("new bat", encoding="utf-8")
    (staging / "VERSION").write_text("{}", encoding="utf-8")
    return app, staging


def _snapshot(app: Path) -> dict:
    return {str(p.relative_to(app)): (p.read_text(encoding="utf-8") if p.is_file() else None)
            for p in sorted(app.rglob("*")) if ".update.part" not in p.parts}


def _fail_move_when(monkeypatch, predicate, exc=None):
    """_move 실패 주입 — predicate(src, dst) 가 참인 첫 호출에서 OSError."""
    real = updater._move
    fired = []

    def fake(src, dst):
        if not fired and predicate(Path(src), Path(dst)):
            fired.append((src, dst))
            raise exc or PermissionError(f"locked: {dst}")
        real(src, dst)
    monkeypatch.setattr(updater, "_move", fake)
    return fired


# 정렬된 항목 순서: VERSION · aoi_capacity · main.py · requirements.txt · scripts
@pytest.mark.parametrize("victim", ["VERSION", "main.py", "scripts"], ids=["first", "middle", "last"])
def test_rollback_restores_everything_when_new_move_fails(tmp_path, monkeypatch, victim):
    app, staging = _loose_app(tmp_path, monkeypatch)
    before = _snapshot(app)
    fired = _fail_move_when(monkeypatch, lambda s, d: d.name == victim and s.parent == staging)      # old 는 치운 뒤, 새것 이동에서 실패
    with pytest.raises(updater.UpdateError) as ei:
        updater._promote_in_place(staging, app, lambda *a: None)
    assert fired and not isinstance(ei.value, updater.RollbackError)
    assert str(ei.value).startswith(i18n.KO.UPDATE_ERR_APPLY_ROLLED_BACK_FMT.split("{")[0]) and "locked" in str(ei.value)
    assert _snapshot(app) == before
    assert not list(app.glob("*.old-update"))


@pytest.mark.parametrize("victim", ["aoi_capacity", "main.py", "scripts"], ids=["first-old", "middle-old", "last-old"])
def test_rollback_restores_everything_when_old_rename_fails(tmp_path, monkeypatch, victim):
    app, staging = _loose_app(tmp_path, monkeypatch)
    before = _snapshot(app)
    fired = _fail_move_when(monkeypatch, lambda s, d: d.name == victim + ".old-update")
    with pytest.raises(updater.UpdateError):
        updater._promote_in_place(staging, app, lambda *a: None)
    assert fired and _snapshot(app) == before and not list(app.glob("*.old-update"))


def test_apply_reports_failure_and_keeps_old_version_when_promote_fails(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, {"sha": SHA_OLD, "branch": "b", "repo": "o/r"})
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    (app / "main.py").write_text("old", encoding="utf-8")
    (app / "aoi_capacity").mkdir()
    (app / "aoi_capacity" / "old.py").write_text("old", encoding="utf-8")
    _serve(monkeypatch, _branch_zip(tmp_path))
    _fail_move_when(monkeypatch, lambda s, d: d.name == "main.py" and s.name == "main.py" and "old-update" not in d.name)
    assert not updater.download_and_apply("o/r", "b", SHA_NEW)
    assert updater.last_error().startswith(i18n.KO.UPDATE_ERR_APPLY_ROLLED_BACK_FMT.split("{")[0])
    assert (app / "main.py").read_text(encoding="utf-8") == "old"
    assert (app / "aoi_capacity" / "old.py").exists()
    assert json.loads((app / "VERSION").read_text(encoding="utf-8"))["sha"] == SHA_OLD
    assert not (app / ".update.part").exists() and not list(app.glob("*.old-update"))


def test_rollback_failure_keeps_backups_and_names_the_files(tmp_path, monkeypatch):
    app, staging = _loose_app(tmp_path, monkeypatch)
    real = updater._move

    def fake(src, dst):
        src, dst = Path(src), Path(dst)
        if dst.name == "requirements.txt" and src.parent == staging:
            raise PermissionError("locked: requirements.txt")                      # 적용 중 실패
        if dst.name == "main.py" and src.name == "main.py.old-update":
            raise PermissionError("cannot restore main.py")                        # 롤백 중 실패
        real(src, dst)
    monkeypatch.setattr(updater, "_move", fake)
    with pytest.raises(updater.RollbackError) as ei:
        updater._promote_in_place(staging, app, lambda *a: None)
    msg = str(ei.value)
    assert msg.startswith(i18n.KO.UPDATE_ERR_ROLLBACK_FMT.split("{")[0])
    assert "main.py" in msg and "main.py.old-update" in msg and "cannot restore main.py" in msg and "locked: requirements.txt" in msg
    assert str(app) in msg
    assert (app / "main.py.old-update").read_text(encoding="utf-8") == "old main"   # 백업은 살아 있다
    assert not (app / "main.py").exists()                                           # 새것은 치웠고 복구는 사람 몫
    assert (app / "requirements.txt").read_text(encoding="utf-8") == "old req"      # 현재 항목은 되돌렸다
    assert (app / "aoi_capacity" / "x.py").exists() and not (app / "aoi_capacity" / "y.py").exists()
    assert (app / "scripts" / "run.bat").read_text(encoding="utf-8") == "old bat"
    assert (app / "user_note.txt").read_text(encoding="utf-8") == "mine"


def test_promote_success_replaces_all_and_leaves_no_backups(tmp_path, monkeypatch):
    app, staging = _loose_app(tmp_path, monkeypatch)
    updater._promote_in_place(staging, app, lambda *a: None)
    assert (app / "main.py").read_text(encoding="utf-8") == "new main"
    assert (app / "aoi_capacity" / "y.py").exists() and not (app / "aoi_capacity" / "x.py").exists()
    assert (app / "scripts" / "run.bat").read_text(encoding="utf-8") == "new bat"
    assert (app / "user_note.txt").read_text(encoding="utf-8") == "mine"
    assert not list(app.glob("*.old-update"))


def test_promote_recovers_a_backup_left_by_an_earlier_failed_rollback(tmp_path, monkeypatch):
    app, staging = _loose_app(tmp_path, monkeypatch)
    (app / "main.py").rename(app / "main.py.old-update")                      # 지난번: 원본은 옆에, 제자리는 비었다
    _fail_move_when(monkeypatch, lambda s, d: d.name == "scripts" and s.parent == staging)
    with pytest.raises(updater.UpdateError):
        updater._promote_in_place(staging, app, lambda *a: None)
    assert (app / "main.py").read_text(encoding="utf-8") == "old main"          # 되살린 원본이 롤백 뒤에도 제자리
    assert not (app / "main.py.old-update").exists()


def test_current_version_prefers_git_head_over_a_stale_version_file(tmp_path, monkeypatch):
    """git 작업 폴더에서는 HEAD 가 버전이다 — VERSION 파일은 옛 빌드가 남긴 값(현장 10일치 결과가 v9be6d0d 로 찍힌 원인)."""
    root = tmp_path / "app"
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (root / ".git" / "refs" / "heads" / "main").write_text("a" * 40 + "\n", encoding="utf-8")
    (root / "VERSION").write_text(json.dumps({"sha": "9be6d0dca367dc3ccc308ebe937c8f566b0c0b17", "branch": "main", "repo": "king-taek/AOI-capacity"}), encoding="utf-8")
    monkeypatch.setattr(updater, "_app_root", lambda: root)
    v = updater.current_version()
    assert v["sha"] == "a" * 40 and v["branch"] == "main" and v["repo"] == "king-taek/AOI-capacity"
    # packed-refs 만 있는 저장소도 읽는다
    (root / ".git" / "refs" / "heads" / "main").unlink()
    (root / ".git" / "packed-refs").write_text("# pack-refs with: peeled\n" + "b" * 40 + " refs/heads/main\n", encoding="utf-8")
    assert updater.current_version()["sha"] == "b" * 40
    # git 폴더가 아니면 VERSION 그대로
    import shutil
    shutil.rmtree(root / ".git")
    assert updater.current_version()["sha"].startswith("9be6d0d")
