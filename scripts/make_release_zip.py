"""make_release_zip.py — 검증을 통과한 산출물만 배포 zip 으로 묶는다.

    python scripts\\make_release_zip.py --lite     # dist/AOI_Capacity_Lite → dist/AOI_Capacity_<날짜>_<sha7>.zip
    python scripts\\make_release_zip.py

zip 안에는 설치 폴더가 통째로(최상위 폴더 하나) 들어가고, ``설치방법.txt`` 를 함께 넣는다.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Callable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTRUCTIONS_NAME = "설치방법.txt"
ZIP_PREFIX = "AOI_Capacity"
# 최상위에서 통째로 빼는 것 — 스테이징·백업 폴더와 빌드 중간물.
_SKIP_TOP = {"app.new", "app.old", "app.new.part", "app.old.part", ".update.part", "python.tar.gz", "build"}
# 경로 어디에 있든 빼는 폴더 이름과 파일 확장자 — 빌드 PC 의 캐시·로그·백업 잔재와 스테이징(제자리 적용의 `.update.part` 는 app/ 안)이
# 배포본에 실리지 않게.
_SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git", ".idea", ".vscode", ".claude", ".mypy_cache", ".ruff_cache",
              "app.new", "app.old", "app.new.part", "app.old.part", ".update.part"}
_SKIP_SUFFIXES = {".pyc", ".pyo", ".log", ".bak", ".tmp", ".part", ".orig", ".rej"}
_SKIP_NAME_SUFFIXES = (".old-update",)


def read_version(out: Path) -> dict:
    try:
        data = json.loads((out / "app" / "VERSION").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def zip_basename(version: dict, today: str) -> str:
    sha = str((version or {}).get("sha") or "")[:7]
    return f"{ZIP_PREFIX}_{today}_{sha}.zip" if sha else f"{ZIP_PREFIX}_{today}.zip"


def should_include(rel: PurePosixPath) -> bool:
    parts = rel.parts
    if not parts or parts[0] in _SKIP_TOP:
        return False
    if any(p in _SKIP_DIRS for p in parts):
        return False
    if rel.suffix.lower() in _SKIP_SUFFIXES:
        return False
    if any(p.endswith(_SKIP_NAME_SUFFIXES) for p in parts):
        return False
    return True


def instructions_text(lite: bool = False) -> str:
    lines = [
        "AOI Capacity - 설치 및 실행 방법",
        "=" * 40,
        "",
        "1. 이 zip 을 원하는 위치(예: C:\\AOI_Capacity)에 압축 해제합니다.",
        "   - 폴더 경로에 한글이 있어도 됩니다. NAS 나 OneDrive 안은 피하세요.",
        "2. 폴더 안의 AOI_Capacity.exe 를 실행합니다.",
        "   - 백신이 exe 를 막으면 run_aoi.bat 을 대신 실행하세요.",
    ]
    if lite:
        lines += [
            "3. 처음 실행 때는 검은 콘솔 창이 뜨고 필요한 패키지(PyQt6 등, 약 250MB)를 인터넷에서 설치합니다.",
            "   몇 분 걸릴 수 있습니다. 창을 닫지 말고 기다리세요. 두 번째 실행부터는 바로 창이 뜹니다.",
            "   - 설치가 실패하면 인터넷/회사 프록시를 확인한 뒤 다시 실행하면 이어서 진행합니다.",
        ]
    lines += [
        "",
        "데이터 위치",
        "- 설정, 장비 목록(devices.csv), 수집 캐시, 결과 HTML: %LOCALAPPDATA%\\AOI_Capacity",
        "- 설치 폴더(app\\)는 자동 업데이트 때 통째로 교체됩니다. 그 안에 개인 파일을 두지 마세요.",
        "",
        "NAS 안전",
        "- 이 프로그램은 NAS 의 Report 와 WaferInfo.ini 를 읽기만 합니다. NAS 에는 어떤 파일도 만들거나 바꾸지 않습니다.",
        "",
        "업데이트",
        "- 실행할 때 GitHub 의 새 버전을 확인하고 안내합니다. 받은 뒤 다시 실행하면 적용됩니다.",
        "",
        "문제가 생기면",
        "- run_aoi_debug.bat 을 실행해 콘솔의 오류를 확인하거나, %LOCALAPPDATA%\\AOI_Capacity\\app.log 를 보내 주세요.",
        "",
    ]
    return "\r\n".join(lines)


def _load_build_module():
    spec = importlib.util.spec_from_file_location("build", str(Path(__file__).resolve().parent / "build.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect_files(out: Path) -> List[Path]:
    return [p for p in sorted(out.rglob("*"))
            if p.is_file() and should_include(PurePosixPath(p.relative_to(out).as_posix()))]


def make_zip(repo_root: Path = REPO_ROOT, log: Callable = print, today: Optional[str] = None,
             lite: bool = False, build_mod=None) -> int:
    build = build_mod or _load_build_module()
    out = repo_root / build.exe_out_dirname(lite)
    log("[1/3] verifying build output ...")
    bad = [label for good, label in build.verify_checks(out, lite) if not good]
    if bad:
        log("[FAILED] verification failed — no zip created:")
        for label in bad:
            log(f"         - {label}")
        return 1
    log("  [OK] all checks passed")
    log("[2/3] writing instructions ...")
    (out / INSTRUCTIONS_NAME).write_text(instructions_text(lite), encoding="utf-8-sig")   # BOM: 구버전 메모장 대비
    version = read_version(out)
    today = today or date.today().strftime("%Y%m%d")
    zip_path = out.parent / zip_basename(version, today)
    files = collect_files(out)
    log(f"[3/3] zipping {len(files)} files ...")
    tmp = zip_path.with_suffix(".zip.part")
    tmp.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in files:
                z.write(p, str(PurePosixPath(out.name) / p.relative_to(out).as_posix()))
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        log(f"[FAILED] zip error: {exc}")
        return 1
    zip_path.unlink(missing_ok=True)
    tmp.rename(zip_path)           # 완성된 것만 최종 이름을 갖는다
    log(f"[done] {zip_path} ({zip_path.stat().st_size / (1024 * 1024):.0f} MB)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    return make_zip(lite="--lite" in argv)


if __name__ == "__main__":
    raise SystemExit(main())
