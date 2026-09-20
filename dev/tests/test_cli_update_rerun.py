"""C14 — `cli --update` 는 갱신 뒤 exec 가 아니라 **자식 프로세스**로 수집을 다시 돌리고 종료 코드를 그대로 돌려준다.
Windows 의 os.execv 는 부모를 즉시 끝내 작업 스케줄러가 자식이 돌기도 전에 '완료' 로 기록했다.
`scripts/run_collect.bat` 은 PYTHONNOUSERSITE=1 · ERRORLEVEL 보존 · 로컬 collect.log 크기 회전.
실제 프로세스는 절대 띄우지 않는다(autouse 가드)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aoi_capacity import cli, collect, i18n
from aoi_capacity.utils import paths, updater


@pytest.fixture(autouse=True)
def _no_real_subprocess(monkeypatch):
    def _blocked(cmd, *a, **kw):
        raise AssertionError("real process launch attempted: " + " ".join(str(c) for c in cmd))
    monkeypatch.setattr(subprocess, "call", _blocked)
    monkeypatch.setattr(subprocess, "run", _blocked)
    monkeypatch.setattr(subprocess, "Popen", _blocked)


def test_rerun_args_strip_only_update_and_keep_everything_else(monkeypatch):
    assert cli.rerun_args(["--update", "--config", "C:\\경로 공백\\config.json", "--backfill", "--update"]) == \
        ["--config", "C:\\경로 공백\\config.json", "--backfill"]
    assert cli.rerun_args([]) == []                                        # 빈 argv 는 sys.argv 로 바꿔치기하지 않는다
    monkeypatch.setattr(sys, "argv", ["cli", "--update", "--recover"])
    assert cli.rerun_args(None) == ["--recover"]


def test_rerun_without_update_waits_for_the_child_and_returns_its_exit_code(capsys):
    seen = []

    def fake_run(cmd):
        seen.append(list(cmd))
        return 3

    assert cli.rerun_without_update(["--update", "--config", "D:\\한글 폴더\\config.json"], run=fake_run) == 3
    assert seen == [[sys.executable, "-m", "aoi_capacity.cli", "--config", "D:\\한글 폴더\\config.json"]]   # 인자 목록 그대로(셸 인용 없음)
    assert i18n.KO.CLI_UPDATE_RERUN_DONE_FMT.format(code=3) in capsys.readouterr().out


def test_default_runner_uses_subprocess_run_and_propagates_returncode(monkeypatch):
    calls = []

    class _Done:
        returncode = 1

    def fake_run(cmd, check=False, **kw):
        calls.append((list(cmd), check))
        return _Done()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert cli.rerun_without_update(["--update"]) == 1
    assert calls == [([sys.executable, "-m", "aoi_capacity.cli"], False)]


def _updated(monkeypatch):
    monkeypatch.setattr(updater, "is_git_checkout", lambda: False)
    monkeypatch.setattr(updater, "manual_check", lambda: ("update", {"repo": "o/r", "branch": "main", "sha": "a" * 40}))
    monkeypatch.setattr(updater, "download_and_apply", lambda repo, branch, sha, *a, **k: True)
    monkeypatch.setattr(updater, "update_pending", lambda: False)


def test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent(tmp_path, monkeypatch, capsys):
    _updated(monkeypatch)
    children = []

    class _Done:
        returncode = 3

    def fake_run(cmd, check=False, **kw):
        children.append(list(cmd))
        return _Done()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(collect, "collect", lambda *a, **k: (_ for _ in ()).throw(AssertionError("parent must not collect after update")))
    conf = str(tmp_path / "경로 공백" / "config.json")
    assert cli.main(["--update", "--config", conf, "--backfill"]) == 3            # 자식의 실패 코드가 그대로 부모의 종료 코드
    assert children == [[sys.executable, "-m", "aoi_capacity.cli", "--config", conf, "--backfill"]]
    assert "--update" not in children[0]                                           # 자식은 다시 갱신하지 않는다(루프 없음)
    out = capsys.readouterr().out
    assert i18n.KO.CLI_UPDATE_DONE_RERUN in out


@pytest.mark.parametrize("status,info", [("latest", {}), ("held", {"sha": "b" * 40, "reason": "CI 대기"}), ("error", {"error": "offline"})])
def test_main_without_a_new_version_collects_in_place(tmp_path, fake_nas, monkeypatch, capsys, status, info):
    nas, csv_path = fake_nas
    monkeypatch.setattr(updater, "is_git_checkout", lambda: False)
    monkeypatch.setattr(updater, "manual_check", lambda: (status, info))
    monkeypatch.setattr(updater, "download_and_apply", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no download")))
    conf = tmp_path / "config.json"
    out = tmp_path / "out"
    conf.write_text(json.dumps({"devices_csv": str(csv_path), "cache_file": str(out / "c.json"), "output_dir": str(out),
                                "scope_devices": ["*"]}), encoding="utf-8")
    assert cli.main(["--update", "--config", str(conf)]) == cli.EXIT_OK
    assert (out / "AOI_capacity.html").exists()


def test_update_step_exception_is_ignored_and_collect_still_runs(tmp_path, fake_nas, monkeypatch, capsys):
    nas, csv_path = fake_nas
    monkeypatch.setattr(updater, "is_git_checkout", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    conf = tmp_path / "config.json"
    out = tmp_path / "out"
    conf.write_text(json.dumps({"devices_csv": str(csv_path), "cache_file": str(out / "c.json"), "output_dir": str(out),
                                "scope_devices": ["*"]}), encoding="utf-8")
    assert cli.main(["--update", "--config", str(conf)]) == cli.EXIT_OK
    assert i18n.KO.CLI_UPDATE_STEP_ERROR_FMT.format(error="boom") in capsys.readouterr().out


def test_cli_never_execs():
    """호출로 검사한다(주석·docstring 은 exec 를 설명해도 된다)."""
    import ast
    tree = ast.parse((paths._project_root() / "aoi_capacity" / "cli.py").read_text(encoding="utf-8"))
    calls = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert not [c for c in calls if c.startswith(("execv", "execl", "spawn"))]


# ── run_collect.bat ───────────────────────────────────────────────────────────
def _bat() -> str:
    return (paths._project_root() / "scripts" / "run_collect.bat").read_text(encoding="utf-8")


def test_run_collect_bat_isolates_user_site_and_preserves_the_exit_code():
    bat = _bat()
    assert 'set "PYTHONNOUSERSITE=1"' in bat
    assert 'set "RC=%ERRORLEVEL%"' in bat and "exit /b %RC%" in bat
    body = bat.split('"%PY%" -m aoi_capacity.cli')[1]
    assert body.index("%ERRORLEVEL%") < body.index("exit /b")                  # 파이썬 바로 뒤에서 코드를 잡는다
    assert "pause" not in bat.lower()                                           # 스케줄러에서 멈추지 않는다
    assert all(ord(ch) < 128 for ch in bat), "cp949 콘솔에서 깨진다 — ASCII 만"


def test_run_collect_bat_rotates_a_local_log_with_a_size_and_count_cap():
    bat = _bat()
    assert "%LOCALAPPDATA%\\AOI_Capacity" in bat and "collect.log" in bat
    assert 'set "LOG_MAX_BYTES=' in bat and 'set "LOG_KEEP=' in bat
    assert "%%~zF GTR %LOG_MAX_BYTES%" in bat and "call :rotate" in bat
    assert ':rotate' in bat and 'ren "%LOG%" "collect.log.1"' in bat and 'del /q "%LOG%.%LOG_KEEP%"' in bat
    assert '>> "%LOG%" 2>&1' in bat                                             # 로그는 여전히 로컬 파일 하나에 붙인다(회전 뒤)
    assert "\\\\10." not in bat and "X:\\" not in bat                          # NAS 경로에 쓰지 않는다
