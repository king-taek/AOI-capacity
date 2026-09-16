"""build.py — exe-lite 빌드 스크립트 (Windows + 인터넷 환경에서 실행).

    python scripts\\build.py exe-lite     # 얇은 런처 exe + python 런타임 + app\\ (라이브러리는 첫 실행 때 pip)
    python scripts\\build.py exe          # 위와 같되 라이브러리까지 번들에 포함(인터넷 없는 PC 용)
    python scripts\\build.py verify-lite  # 산출물 검증만
    python scripts\\build.py verify

핵심: **앱 코드를 exe 안에 넣지 않는다.** 런처 exe(``scripts/exe_launcher.py``)만 얼리고 앱은 ``app\\`` 에
loose 로 둔다. 옛 단독 exe 는 앱을 PYZ 에 넣어 자동 업데이트가 '성공했다는데 안 바뀌는' 상태가 됐다.
순수 판단 로직(명령 구성·검증 목록)은 부수효과 없이 분리해 헤드리스 테스트가 가능하다.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

for _stream in (sys.stdout, sys.stderr):     # cp949 콘솔/로그 리다이렉트에서 한글로 죽지 않게
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
INTERNAL = REPO_ROOT / "scripts" / "internal"
EXE_NAME = "AOI_Capacity.exe"
EXE_OUT_DIRNAME = "dist/AOI_Capacity"
EXE_LITE_OUT_DIRNAME = "dist/AOI_Capacity_Lite"
LAUNCHER_MAX_MB = 30
_STALE_ON_REBUILD = ("_internal", "app.new", "app.new.part", "app.old", EXE_NAME)
_REQUIRED_SOURCES = ("main.py", "requirements.txt", "scripts/exe_launcher.py", "scripts/internal/exe_launcher.spec",
                     "scripts/internal/portable_build.py", "aoi_capacity/ui/assets/template.html",
                     "aoi_capacity/ui/style.qss", "aoi_capacity/assets/devices.default.csv")


def _py_standalone_url() -> str:
    """자체 포함 CPython 주소 — 앱의 bootstrap 이 단일 출처."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from aoi_capacity.utils.bootstrap import PY_STANDALONE_URL
    return PY_STANDALONE_URL


# ── 순수 로직 ──
def venv_python(repo_root: Path) -> Path:
    if os.name == "nt":
        return repo_root / ".venv" / "Scripts" / "python.exe"
    return repo_root / ".venv" / "bin" / "python"


def pyinstaller_cmd(python_exe: str, spec: Path, distpath: Optional[Path] = None) -> List[str]:
    cmd = [str(python_exe), "-m", "PyInstaller", "--noconfirm"]
    if distpath is not None:
        cmd += ["--distpath", str(distpath)]
    return cmd + [str(spec)]


def pip_install_cmd(python_exe: str, *args: str) -> List[str]:
    return [str(python_exe), "-m", "pip", "install", *args]


def exe_out_dirname(lite: bool) -> str:
    return EXE_LITE_OUT_DIRNAME if lite else EXE_OUT_DIRNAME


def output_path(kind: str, repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / exe_out_dirname(kind == "exe-lite")


def stale_paths(out: Path) -> List[Path]:
    """다시 빌드하기 전에 지울 것(존재하는 것만). python\\ 은 남긴다 — 다시 받으면 오래 걸린다."""
    return [out / name for name in _STALE_ON_REBUILD if (out / name).exists()]


def preflight_problems(repo_root: Path) -> List[str]:
    """무거운 단계 전에 잡을 수 있는 문제 목록. 비어 있으면 정상."""
    problems = [f"missing: {rel}" for rel in _REQUIRED_SOURCES if not (repo_root / rel).exists()]
    launcher = repo_root / "scripts" / "exe_launcher.py"
    if launcher.is_file():
        body = "\n".join(ln for ln in launcher.read_text(encoding="utf-8").splitlines()
                         if not ln.strip().startswith("#"))
        if "import aoi_capacity" in body or "from aoi_capacity" in body:
            problems.append("scripts/exe_launcher.py imports app code (must stay zero-app-code)")
    return problems


def _dir_size_mb(d: Path) -> float:
    if not d.is_dir():
        return 0.0
    return sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / (1024 * 1024)


def _load_portable_impl():
    spec = importlib.util.spec_from_file_location("portable_build", str(INTERNAL / "portable_build.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_checks(out: Path, lite: bool = False) -> List[Tuple[bool, str]]:
    """산출물 검사 목록 [(통과, 라벨)]. lite 는 기대가 뒤집힌다: site-packages 작음, .deps_installed **없음**."""
    exe = out / EXE_NAME
    app = out / "app"
    pkg = app / "aoi_capacity"
    checks: List[Tuple[bool, str]] = []
    checks.append((exe.is_file(), f"{EXE_NAME} exists ({exe})"))
    checks.append((not (out / "_internal").exists(), "_internal/ absent (app was not frozen into the exe)"))
    exe_mb = (exe.stat().st_size / (1024 * 1024)) if exe.is_file() else 0.0
    checks.append((0 < exe_mb < LAUNCHER_MAX_MB, f"launcher exe {exe_mb:.1f} MB (< {LAUNCHER_MAX_MB} MB)"))
    checks.append(((out / "python" / "python.exe").is_file(), "python/python.exe (bundled runtime)"))
    checks.append(((out / "python" / "pythonw.exe").is_file(), "python/pythonw.exe (launched by the exe)"))
    for rel in ("main.py", "requirements.txt"):
        checks.append(((app / rel).is_file(), f"app/{rel}"))
    for rel in ("ui/main_window.py", "ui/assets/template.html", "ui/style.qss", "assets/devices.default.csv",
                "utils/bootstrap.py", "utils/updater.py"):
        checks.append(((pkg / rel).is_file(), f"app/aoi_capacity/{rel}"))
    py_count = len(list(pkg.rglob("*.py"))) if pkg.is_dir() else 0
    checks.append((py_count >= 20, f"app/aoi_capacity python modules: {py_count} (>= 20)"))
    tpl = pkg / "ui" / "assets" / "template.html"
    checks.append((tpl.is_file() and "__DATA__" in tpl.read_text(encoding="utf-8", errors="replace"),
                   "template.html keeps the __DATA__ placeholder"))
    ver_ok = False
    vf = app / "VERSION"
    if vf.is_file():
        try:
            data = json.loads(vf.read_text(encoding="utf-8"))
            ver_ok = isinstance(data, dict) and "sha" in data and "branch" in data
        except Exception:  # noqa: BLE001
            ver_ok = False
    checks.append((ver_ok, "app/VERSION (JSON with sha and branch)"))
    checks.append((not (app / ".git").exists(), "app/.git absent"))
    checks.append((not (out / "app.new").exists() and not (out / "app.new.part").exists(), "no app.new leftovers"))
    checks.append((not any((app / d).exists() for d in ("dev", "docs", ".pytest_cache")), "no dev/docs inside app/"))
    checks.append((not list(pkg.rglob("__pycache__")) if pkg.is_dir() else True, "no __pycache__ inside app/"))
    marker = (out / ".deps_installed").is_file()
    impl = _load_portable_impl()
    sp_mb = _dir_size_mb(impl.site_packages_dir(out))
    if lite:
        checks.append((not marker, ".deps_installed absent (lite — tells the first run to install)"))
        checks.append((sp_mb < 100, f"site-packages {sp_mb:.0f} MB (lite — < 100 MB)"))
    else:
        checks.append((marker, ".deps_installed present (dependency fingerprint)"))
        missing = impl.missing_packages(out, app / "requirements.txt")
        checks.append((not missing, "all required packages in bundle site-packages"
                       + (f" (missing: {', '.join(missing[:5])})" if missing else "")))
        checks.append((sp_mb > 60, f"site-packages {sp_mb:.0f} MB (> 60 MB expected with PyQt6)"))
    for bat in ("run_aoi.bat", "run_aoi_debug.bat"):
        checks.append(((out / bat).is_file(), bat))
    return checks


def import_probe_cmd(out: Path) -> List[str]:
    app = out / "app"
    src = ("import sys; sys.path.insert(0, r'%s');"
           "import PyQt6.QtWidgets;"
           "from aoi_capacity.utils import updater, paths, bootstrap;"
           "assert updater.DEFAULT_BRANCH" % str(app))
    return [str(out / "python" / "python.exe"), "-s", "-c", src]


# ── 부수효과 ──
def _default_run(cmd: List[str], cwd: Optional[Path] = None) -> int:
    print(">> " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.call([str(c) for c in cmd], cwd=str(cwd) if cwd else None)


def clean_stale_output(out: Path, log: Callable = print) -> int:
    for p in stale_paths(out):
        log(f"[clean] removing {p}")
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        except OSError as exc:
            log(f"[FAILED] cannot remove {p}: {exc}")
            return 1
    return 0


def preflight(repo_root: Path, log: Callable = print) -> int:
    problems = preflight_problems(repo_root)
    for p in problems:
        log(f"[preflight] {p}")
    if os.name != "nt":
        log("[preflight] NOTE: exe builds only make sense on Windows (PyInstaller cannot cross-compile).")
    return 1 if problems else 0


def _ensure_venv(run: Callable, log: Callable) -> str:
    vpy = venv_python(REPO_ROOT)
    if not vpy.exists():
        log("[build] creating .venv for PyInstaller ...")
        if run([sys.executable, "-m", "venv", str(REPO_ROOT / ".venv")]) != 0:
            raise SystemExit("venv creation failed")
    return str(vpy)


def build_exe(run: Callable = _default_run, log: Callable = print, lite: bool = False) -> int:
    out = REPO_ROOT / exe_out_dirname(lite)
    if preflight(REPO_ROOT, log) != 0 or clean_stale_output(out, log) != 0:
        return 1
    vpy = _ensure_venv(run, log)
    if run(pip_install_cmd(vpy, "pyinstaller>=6")) != 0:
        raise SystemExit("pyinstaller install failed")
    log("[build] thin launcher exe (no app code inside) ...")
    if run(pyinstaller_cmd(vpy, INTERNAL / "exe_launcher.spec", out), REPO_ROOT) != 0:
        raise SystemExit("launcher build failed")
    exe = out / EXE_NAME
    if not exe.is_file():
        raise SystemExit(f"launcher exe not produced: {exe}")
    exe_mb = exe.stat().st_size / (1024 ** 2)
    if (out / "_internal").exists() or exe_mb >= LAUNCHER_MAX_MB:
        raise SystemExit(f"launcher looks wrong (exe {exe_mb:.1f} MB, _internal "
                         f"{'present' if (out / '_internal').exists() else 'absent'}) — check exe_launcher.spec")
    log(f"       launcher OK ({exe_mb:.1f} MB)")
    impl = _load_portable_impl()
    rc = impl.run_build(REPO_ROOT, _py_standalone_url(), run=run, log=log, out_dirname=exe_out_dirname(lite),
                        install_deps=not lite)
    if rc != 0:
        return rc
    log("[done] " + str(out))
    if lite:
        log("       NOTE: libraries are NOT bundled — installed on the user's PC at first run (internet needed).")
    vrc = verify_exe(REPO_ROOT, log, run=run, lite=lite)
    if vrc == 0:
        log("[next] python scripts\\make_release_zip.py" + (" --lite" if lite else ""))
    return vrc


def verify_exe(repo_root: Path = REPO_ROOT, log: Callable = print, run: Optional[Callable] = None,
               lite: bool = False) -> int:
    out = repo_root / exe_out_dirname(lite)
    log(f"[verify] {out}{' (lite)' if lite else ''}")
    checks = verify_checks(out, lite)
    if not lite and run is not None and (out / "python" / "python.exe").is_file():
        checks.append((run(import_probe_cmd(out)) == 0, "bundled python imports the app"))
    passed = 0
    for good, label in checks:
        log(("  [OK] " if good else "  [!!] ") + label)
        passed += 1 if good else 0
    ok = passed == len(checks)
    log(f"[verify] {passed}/{len(checks)} passed" + ("" if ok else " — fix the [!!] items above"))
    return 0 if ok else 1


_ACTIONS = {
    "exe": lambda run=_default_run, log=print: build_exe(run, log, lite=False),
    "exe-lite": lambda run=_default_run, log=print: build_exe(run, log, lite=True),
    "verify": lambda run=_default_run, log=print: verify_exe(REPO_ROOT, log, run=run),
    "verify-lite": lambda run=_default_run, log=print: verify_exe(REPO_ROOT, log, run=run, lite=True),
}


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    os.chdir(REPO_ROOT)
    if not argv or argv[0] not in _ACTIONS:
        print(__doc__)
        return 2
    return int(_ACTIONS[argv[0]]())


if __name__ == "__main__":
    raise SystemExit(main())
