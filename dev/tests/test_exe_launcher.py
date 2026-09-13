"""exe_launcher.py — 교체 상태기계. 이 런처는 업데이트되지 않으므로 여기 로직이 틀리면 나중에 못 고친다.
핵심 불변식: 어떤 실패 경로에서도 앱은 살아남는다."""
from __future__ import annotations

import importlib.util as _u
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = _u.spec_from_file_location("exe_launcher", str(_ROOT / "scripts" / "exe_launcher.py"))
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


launcher = _load()


def _mk(d: Path, marker: str) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "main.py").write_text(marker, encoding="utf-8")
    return d


def _marker(d: Path) -> str:
    return (d / "main.py").read_text(encoding="utf-8")


def _layout(tmp_path):
    return launcher.app_paths(tmp_path / "AOI_Capacity.exe")


def test_app_paths_are_relative_to_the_exe(tmp_path):
    root = tmp_path / "AOI_Capacity"
    lay = launcher.app_paths(root / "AOI_Capacity.exe")
    assert lay.root == root and lay.app == root / "app" and lay.new == root / "app.new"
    assert lay.old == root / "app.old" and lay.pythonw == root / "python" / "pythonw.exe"
    assert lay.marker == root / ".deps_installed" and lay.main_py == root / "app" / "main.py"


def test_app_home_signal_matches_paths_module():
    from aoi_capacity.utils import paths
    assert launcher.APP_HOME_ENV == paths.APP_HOME_ENV == "AOI_APP_HOME"
    assert launcher.EXE_NAME == paths.EXE_NAME


def test_launcher_contains_no_app_code_network_or_pip():
    src = (_ROOT / "scripts" / "exe_launcher.py").read_text(encoding="utf-8")
    body = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    for banned in ("import aoi_capacity", "from aoi_capacity", "urllib", "requests", "zipfile", "pip install"):
        assert banned not in body, banned


def test_swap_applies_pending_update(tmp_path):
    lay = _layout(tmp_path)
    _mk(lay.app, "old"); _mk(lay.new, "new")
    launcher.swap_pending(lay)
    assert _marker(lay.app) == "new" and not lay.new.exists() and not lay.old.exists()


def test_swap_is_noop_without_pending_update(tmp_path):
    lay = _layout(tmp_path)
    _mk(lay.app, "old")
    launcher.swap_pending(lay)
    assert _marker(lay.app) == "old"


def test_swap_purges_stale_backup_then_applies(tmp_path):
    lay = _layout(tmp_path)
    _mk(lay.app, "old"); _mk(lay.new, "new"); _mk(lay.old, "stale")
    launcher.swap_pending(lay)
    assert _marker(lay.app) == "new" and not lay.old.exists()


def test_swap_resumes_when_interrupted_between_renames(tmp_path):
    lay = _layout(tmp_path)
    _mk(lay.old, "old"); _mk(lay.new, "new")
    launcher.swap_pending(lay)
    assert _marker(lay.app) == "new" and not lay.old.exists() and not lay.new.exists()


def test_swap_rolls_back_when_only_backup_survives(tmp_path):
    lay = _layout(tmp_path)
    _mk(lay.old, "old")
    launcher.swap_pending(lay)
    assert _marker(lay.app) == "old" and not lay.old.exists()


def test_swap_keeps_old_app_when_first_rename_fails(tmp_path, monkeypatch):
    lay = _layout(tmp_path)
    _mk(lay.app, "old"); _mk(lay.new, "new")
    monkeypatch.setattr(Path, "rename", lambda self, t: (_ for _ in ()).throw(OSError("in use")))
    launcher.swap_pending(lay)
    assert _marker(lay.app) == "old" and _marker(lay.new) == "new"


def test_swap_rolls_back_when_second_rename_fails(tmp_path, monkeypatch):
    lay = _layout(tmp_path)
    _mk(lay.app, "old"); _mk(lay.new, "new")
    real = Path.rename
    calls = {"n": 0}

    def _fail_second(self, target):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("locked")
        return real(self, target)

    monkeypatch.setattr(Path, "rename", _fail_second)
    launcher.swap_pending(lay)
    assert _marker(lay.app) == "old"


def test_swap_defers_when_stale_backup_cannot_be_purged(tmp_path, monkeypatch):
    lay = _layout(tmp_path)
    _mk(lay.app, "old"); _mk(lay.new, "new"); _mk(lay.old, "stale")
    monkeypatch.setattr(launcher.shutil, "rmtree", lambda *a, **k: None)
    launcher.swap_pending(lay)
    assert _marker(lay.app) == "old" and _marker(lay.new) == "new"


def _bundle(tmp_path):
    (tmp_path / "python").mkdir(parents=True, exist_ok=True)
    (tmp_path / "python" / "python.exe").write_bytes(b"x")
    (tmp_path / "python" / "pythonw.exe").write_bytes(b"x")
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "main.py").write_text("x", encoding="utf-8")
    return launcher.app_paths(tmp_path / "AOI_Capacity.exe")


def test_first_run_uses_the_console_python(tmp_path):
    lay = _bundle(tmp_path)
    assert launcher.launch_cmd(lay)[0].endswith("python.exe")
    assert launcher.launch_cmd(lay)[1].endswith("main.py")


def test_later_runs_are_windowless(tmp_path):
    lay = _bundle(tmp_path)
    lay.marker.write_text("fp", encoding="utf-8")
    assert launcher.launch_cmd(lay)[0].endswith("pythonw.exe")


def test_missing_console_python_falls_back_to_pythonw(tmp_path):
    lay = _bundle(tmp_path)
    lay.python.unlink()
    assert launcher.launch_cmd(lay)[0].endswith("pythonw.exe")
