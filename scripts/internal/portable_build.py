"""portable_build.py — 번들 런타임(python/) + 앱 소스(app/) 배치. ``scripts/build.py`` 가 부른다.

레이아웃(설치 루트):  AOI_Capacity.exe · python\\ · app\\(aoi_capacity/ · main.py · requirements.txt · VERSION)
                    · run_aoi.bat · run_aoi_debug.bat · run_collect.bat · (.deps_installed — 전체 배포만)

``install_deps=False`` 가 **lite 배포** — 라이브러리를 번들에 넣지 않고 사용자 PC 의 첫 실행 때 pip 로 받는다.
★ 이때 ``.deps_installed`` 표식을 **쓰지 않는 것이 핵심** — 표식 부재가 앱에게 '아직 설치 안 됨' 을 알리는 유일한 신호다.

순수 판단(요구사항 추출·누락 검사·VERSION 문자열)은 부수효과 없이 분리해 헤드리스 테스트가 가능하다.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional, Tuple

OUT_DIRNAME = "dist/AOI_Capacity"
REPO_SLUG = "king-taek/AOI-capacity"
DEFAULT_BATS = ("run_aoi.bat", "run_aoi_debug.bat", "run_collect.bat")
_MIN_RUNTIME_BYTES = 1_000_000     # 이보다 작으면 프록시 차단 페이지(HTML)를 받은 것


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _import_app_module(name: str):
    """앱 패키지 모듈 — 요구사항 정규화·기본 브랜치를 앱과 **같은 함수/상수**로 쓴다."""
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import importlib
    return importlib.import_module(f"aoi_capacity.utils.{name}")


def _default_branch_name() -> str:
    try:
        return str(_import_app_module("updater").DEFAULT_BRANCH)
    except Exception:  # noqa: BLE001 - updater 가 아직 없거나 깨짐
        return ""


def portable_python(out_dir: Path) -> Path:
    if os.name == "nt":
        return Path(out_dir) / "python" / "python.exe"
    return Path(out_dir) / "python" / "bin" / "python3"


def _isolated(python_exe: Path, *args) -> List[str]:
    """동봉 파이썬을 개발 PC 로부터 격리해 실행(-s: user site 제외). -I 는 PYTHONUTF8 까지 무시하므로 쓰지 않는다."""
    return [str(python_exe), "-s", *[str(a) for a in args]]


def site_packages_dir(out: Path) -> Path:
    if os.name == "nt":
        return Path(out) / "python" / "Lib" / "site-packages"
    base = Path(out) / "python" / "lib"
    cands = sorted(base.glob("python3.*")) if base.is_dir() else []
    return (cands[0] if cands else base / "python3") / "site-packages"


def _normalize_dist(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).strip().lower()


def required_dists(req_text: str) -> List[str]:
    """requirements 본문에서 배포명만 정규화해 뽑는다. 환경 마커가 붙은 줄은 조건부라 제외."""
    bootstrap = _import_app_module("bootstrap")
    out = []
    for line in bootstrap.req_lines(req_text):
        if ";" in line:
            continue
        name = _normalize_dist(re.split(r"[<>=!~\[]", line, 1)[0])
        if name:
            out.append(name)
    return out


def missing_packages(out: Path, req_file: Path) -> List[str]:
    """번들에 실제로 설치되지 않은 배포명. pip 의 rc 는 믿지 않고 .dist-info 를 직접 센다."""
    try:
        req_text = Path(req_file).read_text(encoding="utf-8")
    except OSError:
        return []
    sp = site_packages_dir(out)
    if not sp.is_dir():
        return required_dists(req_text) or ["(site-packages missing)"]
    have = {_normalize_dist(p.name.split("-")[0]) for p in sp.glob("*.dist-info")}
    return [n for n in required_dists(req_text) if n not in have]


def version_stamp(sha: str, branch: str, repo: str = REPO_SLUG) -> str:
    return json.dumps({"sha": sha, "branch": branch, "repo": repo})


def _git_head(repo_root: Path) -> Tuple[str, str]:
    def _q(args):
        try:
            return subprocess.check_output(["git", "-C", str(repo_root), *args],
                                           stderr=subprocess.DEVNULL, timeout=5).decode().strip()
        except Exception:  # noqa: BLE001
            return ""
    return _q(["rev-parse", "HEAD"]), _q(["rev-parse", "--abbrev-ref", "HEAD"])


def _copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))


def write_deps_marker(repo_root: Path, out: Path) -> bool:
    try:
        bootstrap = _import_app_module("bootstrap")
        req = (repo_root / "requirements.txt").read_text(encoding="utf-8")
        return bootstrap.write_deps_marker(out, req) and bootstrap.deps_marker(out).exists()
    except Exception:  # noqa: BLE001
        return False


def _fetch_runtime(py_url: str, out: Path, log: Callable, fetch: Optional[Callable] = None) -> bool:
    tgz = out / "python.tar.gz"
    try:
        (fetch or urllib.request.urlretrieve)(py_url, str(tgz))
    except Exception as exc:  # noqa: BLE001
        log(f"[FAILED] download error: {exc}")
        return False
    if tgz.stat().st_size < _MIN_RUNTIME_BYTES:
        log("[FAILED] downloaded file too small — proxy block page or truncated download.")
        log(f"         got: {tgz} ({tgz.stat().st_size} bytes). Check in a browser: {py_url}")
        return False
    log("       extracting ...")
    try:
        with tarfile.open(str(tgz)) as tf:
            tf.extractall(str(out))
    except Exception as exc:  # noqa: BLE001
        log(f"[FAILED] extract error: {exc}")
        return False
    tgz.unlink(missing_ok=True)
    return True


def copy_app_tree(repo_root: Path, out: Path) -> Path:
    """app/ = aoi_capacity/ + main.py + requirements.txt. 순수 파일 복사 — 테스트 대상."""
    app = out / "app"
    app.mkdir(parents=True, exist_ok=True)
    _copytree(repo_root / "aoi_capacity", app / "aoi_capacity")
    shutil.copy2(repo_root / "main.py", app / "main.py")
    shutil.copy2(repo_root / "requirements.txt", app / "requirements.txt")
    return app


def run_build(repo_root: Path, py_url: str, run: Optional[Callable] = None, log: Callable = print,
              out_dirname: str = OUT_DIRNAME, bats: tuple = DEFAULT_BATS,
              install_deps: bool = True, fetch: Optional[Callable] = None) -> int:
    """번들 런타임 준비 → pip 준비(+의존성) → app/ 복사 → VERSION. 0 = 성공."""
    if run is None:
        def run(cmd, cwd=None):
            log(">> " + " ".join(str(c) for c in cmd))
            return subprocess.call([str(c) for c in cmd], cwd=str(cwd) if cwd else None)

    out = repo_root / out_dirname
    out.mkdir(parents=True, exist_ok=True)
    ppy = portable_python(out)

    # 1) 자체 포함 CPython(이미 있으면 재사용 — 다시 받으면 오래 걸린다).
    if ppy.exists():
        log(f"[1/4] reuse existing {ppy}")
    else:
        log(f"[1/4] downloading CPython: {py_url}")
        if not _fetch_runtime(py_url, out, log, fetch):
            return 1
    if not ppy.exists():
        log(f"[FAILED] {ppy} not found after extract")
        return 1

    # 2) pip 준비 — lite 도 사용자 PC 에서 이 pip 로 설치하므로 두 모드 모두 최신으로.
    log("[2/4] preparing pip ...")
    if run(_isolated(ppy, "-m", "pip", "install", "--upgrade", "pip")) != 0:
        log("[FAILED] pip self-upgrade failed (network/proxy).")
        return 1
    if install_deps:
        log("       installing dependencies (PyQt6 + WebEngine — takes a while) ...")
        if run(_isolated(ppy, "-m", "pip", "install", "-r", repo_root / "requirements.txt")) != 0:
            log("[FAILED] dependency install failed (requirements.txt). See the last pip error above.")
            return 1
        missing = missing_packages(out, repo_root / "requirements.txt")
        if missing:
            log("[FAILED] packages not present in the bundle: " + ", ".join(missing))
            log(f"         checked: {site_packages_dir(out)}")
            return 1
        if not write_deps_marker(repo_root, out):
            log("[FAILED] could not write .deps_installed marker.")
            return 1
    else:
        log("       skipping dependencies — lite build (installed on the user's PC at first run)")
        marker = out / ".deps_installed"
        if marker.exists():
            marker.unlink()          # 전체 빌드 잔재 — 남으면 첫 실행이 설치를 건너뛴다

    # 3) 앱 소스 + 실행 스크립트.
    log("[3/4] copying app source ...")
    app = copy_app_tree(repo_root, out)
    for bat in bats:
        src = repo_root / "scripts" / bat
        if src.exists():
            shutil.copy2(src, out / bat)

    # 4) VERSION — git 정보를 못 얻어도 반드시 쓴다(빈 sha = 미상, 업데이터가 최신을 받아 채운다).
    sha, branch = _git_head(repo_root)
    branch = branch or _default_branch_name()
    (app / "VERSION").write_text(version_stamp(sha, branch), encoding="utf-8")
    log(f"       VERSION: {branch or '(default)'} @ {sha or '(unknown)'}")
    log(f"[4/4] done: {out}")
    return 0
