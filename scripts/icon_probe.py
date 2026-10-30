"""바로가기 아이콘 시험(10/30 임시) — 어떤 방식이면 .url 바로가기에 아이콘이 보이는지 가른다.

만드는 것(전부 해가 없는 시험 바로가기이고 눌러도 C:\\ 폴더만 열린다)
  내 바탕화면의 `AOI_아이콘시험\\`   1 로컬 경로 + PNG 아이콘 · 2 로컬 경로 + BMP 아이콘 · 3 공유 경로 + PNG · 4 공유 경로 + BMP · 5 공유 경로(슬래시) + BMP
  공유 폴더의 `_aoi_icon_test\\`    아이콘 파일 둘과 3 · 4 · 5 의 복사본(공유 폴더에서 열었을 때를 보려고)
바탕화면 폴더를 열어 **아이콘이 보이는 번호**를 알려 주면 된다. 다 보고 나면 `--clean` 으로 지운다.

★ 쓰기는 내 바탕화면 시험 폴더와 `<공유>\\_aoi_icon_test\\` 뿐이다(장비 NAS 에는 쓰지 않는다). 표준 라이브러리만 쓴다.
    python icon_probe.py                 # 시험 바로가기 만들기
    python icon_probe.py --clean         # 이 도구가 만든 것 지우기
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

SHARE = r"\\10.142.80.167\1.Engr\0. 전산 X\임현택 ENG'R"
SHARE_SUB = "_aoi_icon_test"
LOCAL_SUB = "AOI_아이콘시험"
ASSETS = Path(__file__).resolve().parent.parent / "aoi_capacity" / "ui" / "assets"
ICO_PNG, ICO_BMP = "ico_png.ico", "ico_bmp.ico"
TARGET = "file:///C:/"


def _ansi() -> str:
    return "mbcs" if os.name == "nt" else "cp949"


def _write(path: Path, text: str) -> None:
    path.write_bytes(text.encode(_ansi(), "replace"))


def _url(icon: str) -> str:
    return f"[InternetShortcut]\r\nURL={TARGET}\r\nIconFile={icon}\r\nIconIndex=0\r\n"


def _desktop() -> Path:
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    d = home / "Desktop"
    return d if d.is_dir() else home


def clean(local: Path, share: Path) -> None:
    for d in (local, share / SHARE_SUB):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            print("지움:", d)


def make(local: Path, share: Path) -> int:
    src_png, src_bmp = ASSETS / "logo.ico", ASSETS / "logo_bmp.ico"
    for p in (src_png, src_bmp):
        if not p.is_file():
            print("아이콘 파일이 없습니다(업데이트가 끝났는지 확인):", p)
            return 2
    sdir = share / SHARE_SUB
    local.mkdir(parents=True, exist_ok=True)
    for name, src in ((ICO_PNG, src_png), (ICO_BMP, src_bmp)):
        shutil.copy2(src, local / name)
    try:
        sdir.mkdir(parents=True, exist_ok=True)
        for name, src in ((ICO_PNG, src_png), (ICO_BMP, src_bmp)):
            shutil.copy2(src, sdir / name)
        shared_ok = True
    except OSError as exc:
        print("공유 폴더에 쓰지 못했습니다:", exc)
        shared_ok = False
    unc = lambda n: str(sdir / n)
    slash = lambda n: "//" + str(sdir / n).lstrip("\\").replace("\\", "/")
    items = [
        ("1_로컬경로_PNG.url", _url(str(local / ICO_PNG))),
        ("2_로컬경로_BMP.url", _url(str(local / ICO_BMP))),
        ("3_공유경로_PNG.url", _url(unc(ICO_PNG))),
        ("4_공유경로_BMP.url", _url(unc(ICO_BMP))),
        ("5_공유경로_슬래시_BMP.url", _url(slash(ICO_BMP))),
    ]
    for name, text in items:
        _write(local / name, text)
        if shared_ok and name[0] in "345":
            _write(sdir / name, text)
    _write(local / "시험_안내.txt",
           "아이콘이 보이는 번호를 알려 주세요(1~5, 이 폴더의 파일 / 공유 폴더 안의 3·4·5 도 따로 봐 주세요).\n"
           "1 로컬 경로 + PNG 아이콘 · 2 로컬 경로 + BMP 아이콘 · 3 공유 경로 + PNG · 4 공유 경로 + BMP · 5 공유 경로(슬래시) + BMP\n"
           f"공유 폴더 위치: {sdir}\n")
    print("만들었습니다:", local)
    if shared_ok:
        print("공유 폴더:", sdir)
    print("탐색기에서 아이콘이 보이는 번호를 알려 주세요. (안 보이면 F5 로 새로 고침)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="바로가기 아이콘 시험")
    ap.add_argument("--share", default=SHARE)
    ap.add_argument("--local", default="")
    ap.add_argument("--clean", action="store_true")
    a = ap.parse_args(argv)
    local = Path(a.local) if a.local else _desktop() / LOCAL_SUB
    share = Path(a.share)
    if a.clean:
        clean(local, share)
        return 0
    return make(local, share)


if __name__ == "__main__":
    sys.exit(main())
