"""바로가기 아이콘 진단(11/4 임시) — 파일 해석과 규칙 1(쓰기 함수 첫 줄 assert_local). Windows 호출 부분은 실제 PC 에서만 돈다."""
from __future__ import annotations

import ast
import struct
import zipfile
from pathlib import Path

from aoi_capacity import icon_diag
from aoi_capacity.utils import paths


def _lnk(net: str, suffix: str, icon: str) -> bytes:
    clsid = bytes.fromhex("0114020000000000c000000000000046")
    head = struct.pack("<I", 0x4C) + clsid + struct.pack("<II", 0x2 | 0x40 | 0x80, 0x20) + b"\0" * 24 + struct.pack("<IiIH", 0, 0, 1, 0) + b"\0" * 10
    assert len(head) == 76
    netb = net.encode("cp949") + b"\0"
    cnrl = struct.pack("<IIIII", 0x14 + len(netb), 0, 0x14, 0, 0) + netb
    sfx = suffix.encode("cp949") + b"\0"
    li_body = cnrl + sfx
    li = struct.pack("<IIIIIII", 0x1C + len(li_body), 0x1C, 2, 0, 0, 0x1C, 0x1C + len(cnrl)) + li_body
    sd = struct.pack("<H", len(icon)) + icon.encode("utf-16-le")
    return head + li + sd + struct.pack("<I", 0)


def test_parse_lnk_reads_network_target_and_unicode_icon():
    icon = r"\\k5cifsn2\k5tsvdata$\Eng'r\HT Lim\LOT 추적\AOI.ico"
    p = icon_diag.parse_lnk(_lnk(r"\\k5cifsn2\k5tsvdata$", r"Eng'r\HT Lim\AOI_LOT.html", icon))
    assert "error" not in p, p
    assert p["target"] == r"\\k5cifsn2\k5tsvdata$\Eng'r\HT Lim\AOI_LOT.html"
    assert p["icon_location"] == icon
    assert {"HasLinkInfo", "HasIconLocation", "IsUnicode"} <= set(p["flags"])


def test_parse_lnk_rejects_garbage():
    assert "error" in icon_diag.parse_lnk(b"[InternetShortcut]\r\n")


def test_ico_frames_tell_png_from_bmp():
    png = icon_diag.ico_frames(paths.logo_path("logo.ico").read_bytes())
    bmp = icon_diag.ico_frames(paths.logo_path("logo_bmp.ico").read_bytes())
    assert png and all(f["fmt"] == "PNG" for f in png)
    assert bmp and all(f["fmt"] == "BMP" for f in bmp)
    assert icon_diag.ico_frames(b"junk") == []


def test_run_without_windows_still_writes_report_zip(tmp_path):
    cfg = {"publish_dir": "", "publish_full_dir": "", "nas_roots": [str(tmp_path / "nas")]}
    res = icon_diag.run(cfg, out_root=str(tmp_path / "out"))
    with zipfile.ZipFile(res["zip"]) as z:
        names = z.namelist()
    assert "report.html" in names and "report.json" in names
    assert any(n.startswith("tests/8 url BMP") for n in names)
    assert Path(res["report"]).is_file()
    assert any("PNG" in s for s in res["summary"])


def test_writes_only_in_functions_that_guard_first():
    tree = ast.parse(Path(icon_diag.__file__).read_text(encoding="utf-8"))
    name = lambda c: (c.func.value.id + "." + c.func.attr) if isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) else (c.func.id if isinstance(c.func, ast.Name) else "")
    guarded = set()
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) else fn.body
        if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Call) and name(body[0].value) == "nas_guard.assert_local":
            guarded.add(fn)
    bad = []
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        for c in (n for n in ast.walk(fn) if isinstance(n, ast.Call)):
            nm = name(c)
            mode = c.args[1].value if nm == "open" and len(c.args) > 1 and isinstance(c.args[1], ast.Constant) else ""
            writes = nm in {"os.remove", "os.replace", "os.rename", "os.makedirs", "os.mkdir", "zipfile.ZipFile", "os.unlink"} or nm.startswith("shutil.") \
                or any(ch in str(mode) for ch in "wax+")
            if writes and fn not in guarded:
                bad.append(f"{nm} in {fn.name}")
    assert not bad, bad
