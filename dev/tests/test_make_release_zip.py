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
    assert not mrz.should_include(PurePosixPath("app/__pycache__/x.pyc"))
    assert not mrz.should_include(PurePosixPath("app.new/main.py"))
    assert not mrz.should_include(PurePosixPath("python.tar.gz"))


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
