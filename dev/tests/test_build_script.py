"""build.py / portable_build.py — 순수 판단 로직(명령 구성·검증 목록·app 복사). 네트워크·PyInstaller 없음."""
from __future__ import annotations

import importlib.util as _u
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _load(rel: str, name: str):
    spec = _u.spec_from_file_location(name, str(_ROOT / rel))
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build = _load("scripts/build.py", "build")
pb = _load("scripts/internal/portable_build.py", "portable_build")


def _fake_out(tmp_path: Path, lite: bool) -> Path:
    out = tmp_path / "dist" / "AOI_Capacity_Lite"
    (out / "python").mkdir(parents=True)
    (out / "python" / "python.exe").write_bytes(b"x")
    (out / "python" / "pythonw.exe").write_bytes(b"x")
    (out / "AOI_Capacity.exe").write_bytes(b"x" * 1024)
    pb.copy_app_tree(_ROOT, out)
    (out / "app" / "aoi_capacity" / "utils" / "updater.py").touch(exist_ok=True)
    (out / "app" / "VERSION").write_text(pb.version_stamp("abc", "main"), encoding="utf-8")
    for bat in ("run_aoi.bat", "run_aoi_debug.bat"):
        (out / bat).write_text("@echo off", encoding="ascii")
    if not lite:
        sp = pb.site_packages_dir(out)
        sp.mkdir(parents=True)
        for d in ("PyQt6-6.7.0.dist-info", "PyQt6_WebEngine-6.7.0.dist-info"):
            (sp / d).mkdir()
        (sp / "big.bin").write_bytes(b"\0" * (151 * 1024 * 1024))
        (out / ".deps_installed").write_text("fp", encoding="utf-8")
    return out


def test_pure_commands():
    assert build.pyinstaller_cmd("py", Path("x.spec"), Path("dist"))[1:4] == ["-m", "PyInstaller", "--noconfirm"]
    assert build.pip_install_cmd("py", "pyinstaller>=6")[-1] == "pyinstaller>=6"
    assert build.exe_out_dirname(True).endswith("_Lite") and not build.exe_out_dirname(False).endswith("_Lite")
    assert build.output_path("exe-lite").name == "AOI_Capacity_Lite"


def test_preflight_clean_on_repo():
    assert build.preflight_problems(_ROOT) == []


def test_preflight_catches_launcher_importing_app(tmp_path):
    for rel in build._REQUIRED_SOURCES:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    (tmp_path / "scripts" / "exe_launcher.py").write_text("from aoi_capacity import collect\n", encoding="utf-8")
    assert any("zero-app-code" in s for s in build.preflight_problems(tmp_path))


def test_stale_paths_keep_python_runtime(tmp_path):
    (tmp_path / "python").mkdir()
    (tmp_path / "_internal").mkdir()
    (tmp_path / "app.new.part").mkdir()
    names = {p.name for p in build.stale_paths(tmp_path)}
    assert names == {"_internal", "app.new.part"}


def test_verify_checks_pass_on_valid_lite_output(tmp_path):
    out = _fake_out(tmp_path, lite=True)
    bad = [l for ok, l in build.verify_checks(out, lite=True) if not ok]
    assert bad == []


def test_verify_lite_rejects_marker_and_internal(tmp_path):
    out = _fake_out(tmp_path, lite=True)
    (out / ".deps_installed").write_text("fp", encoding="utf-8")
    (out / "_internal").mkdir()
    bad = [l for ok, l in build.verify_checks(out, lite=True) if not ok]
    assert any(".deps_installed" in l for l in bad) and any("_internal" in l for l in bad)


def test_verify_full_requires_packages_and_marker(tmp_path):
    out = _fake_out(tmp_path, lite=False)
    assert [l for ok, l in build.verify_checks(out, lite=False) if not ok] == []
    (out / ".deps_installed").unlink()
    bad = [l for ok, l in build.verify_checks(out, lite=False) if not ok]
    assert any(".deps_installed" in l for l in bad)


def test_verify_rejects_big_launcher_and_missing_template_placeholder(tmp_path):
    out = _fake_out(tmp_path, lite=True)
    (out / "AOI_Capacity.exe").write_bytes(b"\0" * (31 * 1024 * 1024))
    tpl = out / "app" / "aoi_capacity" / "ui" / "assets" / "template.html"
    tpl.write_text(tpl.read_text(encoding="utf-8").replace("__DATA__", "{}"), encoding="utf-8")
    bad = [l for ok, l in build.verify_checks(out, lite=True) if not ok]
    assert any("launcher exe" in l for l in bad) and any("__DATA__" in l for l in bad)


def test_copy_app_tree_excludes_pycache_and_dev(tmp_path):
    out = tmp_path / "o"
    app = pb.copy_app_tree(_ROOT, out)
    assert (app / "main.py").is_file() and (app / "requirements.txt").is_file()
    assert (app / "aoi_capacity" / "ui" / "assets" / "template.html").is_file()
    assert not list((app / "aoi_capacity").rglob("__pycache__"))
    assert not (app / "dev").exists() and not (app / "docs").exists()


def test_required_dists_and_missing_packages(tmp_path):
    req = "PyQt6>=6.6\nPyQt6-WebEngine>=6.6\ntruststore>=0.8 ; python_version >= \"3.10\"\n"
    assert pb.required_dists(req) == ["pyqt6", "pyqt6_webengine"]
    (tmp_path / "requirements.txt").write_text(req, encoding="utf-8")
    assert pb.missing_packages(tmp_path, tmp_path / "requirements.txt") == ["pyqt6", "pyqt6_webengine"]
    sp = pb.site_packages_dir(tmp_path)
    sp.mkdir(parents=True)
    (sp / "PyQt6-6.7.0.dist-info").mkdir()
    assert pb.missing_packages(tmp_path, tmp_path / "requirements.txt") == ["pyqt6_webengine"]


def test_version_stamp_json():
    d = json.loads(pb.version_stamp("abc", "main"))
    assert d == {"sha": "abc", "branch": "main", "repo": "king-taek/AOI-capacity"}


def test_run_build_lite_with_fakes(tmp_path):
    """다운로드·pip 을 가짜로 바꿔 흐름만 확인: 런타임 준비 → pip → app/ → VERSION, 표식 없음."""
    repo = tmp_path / "repo"
    (repo / "aoi_capacity").mkdir(parents=True)
    (repo / "aoi_capacity" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "main.py").write_text("", encoding="utf-8")
    (repo / "requirements.txt").write_text("PyQt6\n", encoding="utf-8")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "run_aoi.bat").write_text("@echo off", encoding="ascii")
    out = repo / "dist" / "AOI_Capacity_Lite"
    ppy = pb.portable_python(out)
    calls, logs = [], []

    def fake_fetch(url, dst):
        import tarfile
        src = tmp_path / "py"
        ppy_src = src / "python" / ppy.relative_to(out / "python")
        ppy_src.parent.mkdir(parents=True, exist_ok=True)
        import os as _os; ppy_src.write_bytes(_os.urandom(1_100_000))
        with tarfile.open(dst, "w:gz") as tf:
            tf.add(src / "python", arcname="python")

    rc = pb.run_build(repo, "http://example/py.tgz", run=lambda c, cwd=None: (calls.append(c), 0)[1], log=logs.append,
                      out_dirname="dist/AOI_Capacity_Lite", install_deps=False, fetch=fake_fetch)
    assert rc == 0, logs
    assert ppy.exists() and (out / "app" / "main.py").is_file() and (out / "run_aoi.bat").is_file()
    assert not (out / ".deps_installed").exists()
    assert not (out / "python.tar.gz").exists()
    assert len(calls) == 1 and "pip" in calls[0]                 # pip 자체 업그레이드만, 의존성 설치 없음
    ver = json.loads((out / "app" / "VERSION").read_text(encoding="utf-8"))
    assert set(ver) == {"sha", "branch", "repo"}
