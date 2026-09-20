"""make_release_zip — 검증 실패면 zip 없음, 통과면 최상위 폴더 하나 + 설치방법.txt(BOM, CRLF), 찌꺼기 제외."""
from __future__ import annotations

import importlib.util as _u
import zipfile
from pathlib import Path, PurePosixPath

_ROOT = Path(__file__).resolve().parents[2]


def _load(rel: str, name: str):
    spec = _u.spec_from_file_location(name, str(_ROOT / rel))
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mrz = _load("scripts/make_release_zip.py", "make_release_zip")


class _FakeBuild:
    def __init__(self, ok: bool):
        self.ok = ok

    def exe_out_dirname(self, lite):
        return "dist/AOI_Capacity_Lite"

    def verify_checks(self, out, lite):
        return [(self.ok, "check-1"), (True, "check-2")]


def _out(tmp_path: Path) -> Path:
    out = tmp_path / "dist" / "AOI_Capacity_Lite"
    (out / "app").mkdir(parents=True)
    (out / "app" / "VERSION").write_text('{"sha":"abcdef0123","branch":"main"}', encoding="utf-8")
    (out / "app" / "main.py").write_text("x", encoding="utf-8")
    (out / "app" / "__pycache__").mkdir()
    (out / "app" / "__pycache__" / "m.pyc").write_bytes(b"x")
    (out / "app.new.part").mkdir()
    (out / "app.new.part" / "junk").write_text("x", encoding="utf-8")
    (out / "AOI_Capacity.exe").write_bytes(b"x")
    return out


def test_zip_basename_and_should_include():
    assert mrz.zip_basename({"sha": "abcdef0123"}, "20260913") == "AOI_Capacity_20260913_abcdef0.zip"
    assert mrz.zip_basename({}, "20260913") == "AOI_Capacity_20260913.zip"
    assert mrz.should_include(PurePosixPath("app/main.py"))
    assert mrz.should_include(PurePosixPath("python/python.exe")) and mrz.should_include(PurePosixPath("python/Lib/site.py"))
    assert mrz.should_include(PurePosixPath("app/aoi_capacity/ui/assets/template.html"))
    assert not mrz.should_include(PurePosixPath("app/__pycache__/x.pyc"))
    assert not mrz.should_include(PurePosixPath("app.new/main.py"))
    assert not mrz.should_include(PurePosixPath("python.tar.gz"))
    # S17: 낱개 pyc · pytest 캐시 · 로그 · 백업 · 스테이징/옛 폴더 · 제자리 백업도 뺀다
    assert not mrz.should_include(PurePosixPath("app/aoi_capacity/loose.pyc"))
    assert not mrz.should_include(PurePosixPath("app/.pytest_cache/v/cache/nodeids"))
    assert not mrz.should_include(PurePosixPath("app/app.log")) and not mrz.should_include(PurePosixPath("build.log"))
    assert not mrz.should_include(PurePosixPath("app/main.py.bak"))
    assert not mrz.should_include(PurePosixPath("app.old/main.py")) and not mrz.should_include(PurePosixPath("app.new.part/x"))
    assert not mrz.should_include(PurePosixPath("app/.update.part/main.py"))
    assert not mrz.should_include(PurePosixPath("app/main.py.old-update"))
    assert not mrz.should_include(PurePosixPath("app/.git/HEAD"))


def _polluted(out: Path) -> None:
    """빌드 PC 잔재: 낱개 pyc · pytest 캐시 · 로그 · 백업 · 옛 폴더 · 제자리 스테이징 — 그리고 지켜야 할 런타임 파일."""
    for rel in ("app/aoi_capacity/loose.pyc", "app/.pytest_cache/v/cache/nodeids", "app/app.log", "build.log",
                "app/main.py.bak", "app.old/main.py", "app/main.py.old-update", "app/.update.part/main.py",
                "python/Lib/site-packages/pkg/__pycache__/m.cpython-311.pyc", "python/pip.log"):
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("junk", encoding="utf-8")
    for rel in ("python/python.exe", "python/Lib/site-packages/pkg/__init__.py", "app/aoi_capacity/__init__.py",
                "app/aoi_capacity/ui/assets/template.html", "app/aoi_capacity/assets/devices.default.csv", "run_aoi.bat"):
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("keep", encoding="utf-8")


def test_polluted_dist_ships_no_cache_log_or_backup_but_keeps_runtime(tmp_path):
    out = _out(tmp_path)
    _polluted(out)
    assert mrz.make_zip(tmp_path, log=lambda m: None, today="20260913", lite=True, build_mod=_FakeBuild(True)) == 0
    names = set(zipfile.ZipFile(out.parent / "AOI_Capacity_20260913_abcdef0.zip").namelist())
    rel = {n.split("/", 1)[1] for n in names}
    for gone in ("app/aoi_capacity/loose.pyc", "app/.pytest_cache/v/cache/nodeids", "app/app.log", "build.log",
                 "app/main.py.bak", "app.old/main.py", "app/main.py.old-update", "app/.update.part/main.py",
                 "python/Lib/site-packages/pkg/__pycache__/m.cpython-311.pyc", "python/pip.log", "app/__pycache__/m.pyc",
                 "app.new.part/junk"):
        assert gone not in rel, gone
    assert not any(n.endswith((".pyc", ".log", ".bak")) or "__pycache__" in n or ".pytest_cache" in n for n in names)
    for kept in ("AOI_Capacity.exe", "run_aoi.bat", "app/main.py", "app/VERSION", "python/python.exe",
                 "python/Lib/site-packages/pkg/__init__.py", "app/aoi_capacity/__init__.py",
                 "app/aoi_capacity/ui/assets/template.html", "app/aoi_capacity/assets/devices.default.csv", mrz.INSTRUCTIONS_NAME):
        assert kept in rel, kept


def test_no_zip_when_verification_fails(tmp_path):
    out = _out(tmp_path)
    logs = []
    assert mrz.make_zip(tmp_path, log=logs.append, today="20260913", lite=True, build_mod=_FakeBuild(False)) == 1
    assert not list((out.parent).glob("*.zip")) and any("check-1" in l for l in logs)


def test_zip_layout_and_instructions(tmp_path):
    out = _out(tmp_path)
    assert mrz.make_zip(tmp_path, log=lambda m: None, today="20260913", lite=True, build_mod=_FakeBuild(True)) == 0
    zp = out.parent / "AOI_Capacity_20260913_abcdef0.zip"
    assert zp.is_file() and not zp.with_suffix(".zip.part").exists()
    names = set(zipfile.ZipFile(zp).namelist())
    assert "AOI_Capacity_Lite/app/main.py" in names and "AOI_Capacity_Lite/AOI_Capacity.exe" in names
    assert f"AOI_Capacity_Lite/{mrz.INSTRUCTIONS_NAME}" in names
    assert not any("__pycache__" in n or "app.new.part" in n for n in names)
    raw = (out / mrz.INSTRUCTIONS_NAME).read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw
    text = raw.decode("utf-8-sig")
    assert "NAS" in text and "%LOCALAPPDATA%" in text and "처음 실행" in text
    assert "처음 실행" not in mrz.instructions_text(lite=False)
