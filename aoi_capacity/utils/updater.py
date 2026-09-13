"""GitHub 공개 저장소의 기본 브랜치에서 앱 업데이트를 확인/적용한다.

배포본은 ``app/VERSION`` (JSON ``{"sha","branch","repo"}``) 을 동봉한다. 실행 시 백그라운드로 브랜치 최신 커밋
SHA 를 받아 현재 SHA 와 비교하고, 다르면 UI 가 안내한다. 동의하면 브랜치 zip 을 받아 **앱 구동에 필요한 것을 전부**
담은 새 트리를 만든다(``aoi_capacity/`` · ``main.py`` · ``requirements.txt`` · ``scripts/run_*.bat``). 개발 전용·VCS·캐시는 제외.

**적용은 "완성·검증된 트리만" 한다** — 새 트리를 통째로 만들어 바꾸므로 상류에서 삭제된 파일이 실제로 사라지고,
중간에 실패해도 구버전과 ``VERSION`` 이 그대로 남는다.
- **exe 모드**(런처가 ``AOI_APP_HOME`` 을 넘겨준 경우): ``app.new.part`` 에 만들고 검증 후 ``app.new`` 로 rename. 실제 교체는
  다음 실행 때 런처(``scripts/exe_launcher.py``)가 한다. 새 requirements 는 동봉 파이썬에 먼저 설치하고, 실패하면 적용하지 않는다.
- **비-exe**(개발 클론이 아닌 loose 폴더): 제자리에 항목 단위로 적용(실패 시 롤백).
- git 작업트리(``.git`` 있음)에서는 자동 확인·적용을 하지 않는다.
- 표준 라이브러리(urllib)만 사용. 회사 SSL 검사 프록시 대비 truststore → OS 인증서 → 검증 없이 재시도.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional, Tuple

from .. import i18n
from . import paths

DEFAULT_REPO = "king-taek/AOI-capacity"
# 자동 업데이트 기준은 저장소의 GitHub 기본 브랜치다. 이름은 api 로 동적 조회하고, 실패하면 아래 상수를 폴백으로 쓴다.
DEFAULT_BRANCH = "claude/multiple-device-network-addresses-t0ea7o"
_API_REPO = "https://api.github.com/repos/{repo}"
_API = "https://api.github.com/repos/{repo}/commits/{branch}"
_ATOM = "https://github.com/{repo}/commits/{branch}.atom"      # api.github.com 만 막힌 사내망 폴백
_ZIP = "https://github.com/{repo}/archive/refs/heads/{branch}.zip"
_UA = {"User-Agent": "AOI-Capacity-Updater"}
_APP_HOME_ENV = paths.APP_HOME_ENV

_last_error: str = ""
_OPENER = None
_OPENER_INSECURE = None
_insecure_used: bool = False
_deps_changed: bool = False
_deps_blocked: bool = False
_default_branch_cache: dict = {}


def last_error() -> str:
    return _last_error


def insecure_fallback_used() -> bool:
    return _insecure_used


def deps_changed() -> bool:
    return _deps_changed


def deps_blocked() -> bool:
    """직전 적용이 '새 패키지를 설치하지 못해서' 포기됐는지(exe 모드) — UI 가 새 배포본을 받으라고 안내."""
    return _deps_blocked


# ── 네트워크 ──
def _ssl_context(insecure: bool = False):
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:  # noqa: BLE001
        pass
    try:
        ctx = ssl.create_default_context()
        ctx.load_default_certs()
        return ctx
    except Exception:  # noqa: BLE001
        return None


def _make_opener(insecure: bool):
    handlers = []
    proxies = urllib.request.getproxies()
    if proxies:
        handlers.append(urllib.request.ProxyHandler(proxies))
    ctx = _ssl_context(insecure=insecure)
    if ctx is not None:
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers)


def _opener(insecure: bool = False):
    global _OPENER, _OPENER_INSECURE
    if insecure:
        if _OPENER_INSECURE is None:
            _OPENER_INSECURE = _make_opener(True)
        return _OPENER_INSECURE
    if _OPENER is None:
        _OPENER = _make_opener(False)
    return _OPENER


def _is_ssl_verify_error(exc: Exception) -> bool:
    return isinstance(exc, ssl.SSLError) or isinstance(getattr(exc, "reason", None), ssl.SSLError)


def _urlopen(url: str, headers: dict, timeout: float):
    """HTTPS GET — 인증서 검증 실패 시 검증 없이 자동 재시도. ``AOI_UPDATE_INSECURE=1`` 이면 처음부터 검증 없이."""
    global _insecure_used
    if os.environ.get("AOI_UPDATE_INSECURE") == "1":
        _insecure_used = True
        return _opener(True).open(urllib.request.Request(url, headers=headers), timeout=timeout)
    try:
        return _opener(False).open(urllib.request.Request(url, headers=headers), timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        if _is_ssl_verify_error(exc):
            _insecure_used = True
            return _opener(True).open(urllib.request.Request(url, headers=headers), timeout=timeout)
        raise


def _describe_err(exc: Exception, url: str) -> str:
    host = url.split("/")[2] if "//" in url else url
    if isinstance(exc, urllib.error.HTTPError):
        return i18n.KO.UPDATE_ERR_HTTP_FMT.format(code=exc.code, host=host)
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, ssl.SSLError):
            return i18n.KO.UPDATE_ERR_SSL_FMT.format(host=host, reason=reason)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return i18n.KO.UPDATE_ERR_TIMEOUT_FMT.format(host=host)
        return i18n.KO.UPDATE_ERR_CONNECT_FMT.format(host=host, reason=reason)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return i18n.KO.UPDATE_ERR_TIMEOUT_FMT.format(host=host)
    if isinstance(exc, zipfile.BadZipFile):
        return i18n.KO.UPDATE_ERR_BAD_ZIP
    return i18n.KO.UPDATE_ERR_OTHER_FMT.format(kind=type(exc).__name__, host=host, detail=exc)


def _http_get(url: str, headers: dict, timeout: float) -> bytes:
    with _urlopen(url, headers, timeout) as r:
        return r.read()


# ── 위치·버전 ──
def _app_root() -> Path:
    """앱 소스 루트(배포의 ``app/``, 개발 시 저장소 루트)."""
    return paths._project_root()


def _install_root() -> Optional[Path]:
    v = os.environ.get(_APP_HOME_ENV)
    return Path(v) if v else None


def _pending_dir(root: Path) -> Path:
    return root / "app.new"


def update_pending() -> bool:
    root = _install_root()
    return bool(root and _pending_dir(root).exists())


def _staging_dir(root: Optional[Path], app_root: Path) -> Path:
    """최종 위치와 **같은 볼륨** 이어야 rename 이 원자적이다(%TEMP% 금지)."""
    return (root / "app.new.part") if root else (app_root / ".update.part")


def _version_file() -> Path:
    return _app_root() / "VERSION"


def current_version() -> Optional[dict]:
    f = _version_file()
    try:
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:  # noqa: BLE001
        pass
    return None


def _write_version_to(root: Path, sha: str, branch: str, repo: str) -> None:
    try:
        (Path(root) / "VERSION").write_text(json.dumps({"sha": sha, "branch": branch, "repo": repo}), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _write_version(sha: str, branch: str, repo: str) -> None:
    _write_version_to(_app_root(), sha, branch, repo)


def is_git_checkout() -> bool:
    return (_app_root() / ".git").exists()


def _git_head() -> Optional[dict]:
    root = str(_app_root())
    try:
        sha = subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL,
                                      timeout=5).decode().strip()
        branch = subprocess.check_output(["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"],
                                         stderr=subprocess.DEVNULL, timeout=5).decode().strip()
    except Exception:  # noqa: BLE001
        return None
    if sha and branch and branch != "HEAD":
        return {"sha": sha, "branch": branch, "repo": DEFAULT_REPO}
    return None


def ensure_version_file() -> Optional[dict]:
    """VERSION 이 없으면 초기 파일을 만든다(SHA 미상). git 작업트리에는 만들지 않는다."""
    cur = current_version()
    if cur is not None:
        return cur
    if is_git_checkout():
        return None
    seed = _git_head() or {"sha": "", "branch": DEFAULT_BRANCH, "repo": DEFAULT_REPO}
    _write_version(str(seed.get("sha") or ""), str(seed.get("branch") or DEFAULT_BRANCH), str(seed.get("repo") or DEFAULT_REPO))
    return current_version()


# ── 최신 커밋 ──
def _latest_via_api(repo: str, branch: str, timeout: float) -> Optional[dict]:
    global _last_error
    url = _API.format(repo=repo, branch=branch)
    try:
        data = json.loads(_http_get(url, {**_UA, "Accept": "application/vnd.github+json"}, timeout).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        _last_error = _describe_err(exc, url)
        return None
    sha = data.get("sha")
    if not sha:
        _last_error = i18n.KO.UPDATE_ERR_NO_SHA_API
        return None
    commit = data.get("commit") or {}
    msg = (commit.get("message") or "").splitlines()
    return {"sha": str(sha), "message": msg[0] if msg else "", "date": (commit.get("committer") or {}).get("date", "")}


def _latest_via_atom(repo: str, branch: str, timeout: float) -> Optional[dict]:
    global _last_error
    url = _ATOM.format(repo=repo, branch=branch)
    try:
        text = _http_get(url, _UA, timeout).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        _last_error = _describe_err(exc, url)
        return None
    m = re.search(r"commit/([0-9a-fA-F]{40})", text, re.IGNORECASE)
    if not m:
        _last_error = i18n.KO.UPDATE_ERR_NO_SHA_ATOM
        return None
    return {"sha": m.group(1).lower(), "message": "", "date": ""}


def latest_commit(repo: str, branch: str, timeout: float = 15.0) -> Optional[dict]:
    return _latest_via_api(repo, branch, timeout) or _latest_via_atom(repo, branch, timeout)


def _default_branch(repo: str, timeout: float = 10.0) -> str:
    if repo in _default_branch_cache:
        return _default_branch_cache[repo]
    try:
        raw = _http_get(_API_REPO.format(repo=repo), {**_UA, "Accept": "application/vnd.github+json"}, timeout)
        b = (json.loads(raw.decode("utf-8")).get("default_branch") or "").strip()
        if b:
            _default_branch_cache[repo] = b
            return b
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_BRANCH


def _latest_self_healing(repo: str, branch: str) -> Tuple[Optional[dict], str]:
    """추적 브랜치가 삭제/이름변경(404)돼 실패하면 저장소의 실제 기본 브랜치로 한 번 더."""
    info = latest_commit(repo, branch)
    if info:
        return info, branch
    db = _default_branch(repo)
    if db and db != branch:
        info = latest_commit(repo, db)
        if info:
            return info, db
    return None, branch


def _resolve_branch(branch: Optional[str], repo: str = DEFAULT_REPO) -> str:
    """VERSION 에 박힌 브랜치를 저장소 기본 브랜치로 정규화(비었거나 claude/* · main · master)."""
    b = (branch or "").strip()
    if not b or b.startswith("claude/") or b in ("main", "master"):
        return _default_branch(repo)
    return b


def _identity() -> tuple:
    """(repo, branch, current_sha). VERSION → git HEAD → 내장 기본값."""
    cur = current_version()
    if cur and cur.get("branch"):
        repo = cur.get("repo") or DEFAULT_REPO
        return (repo, _resolve_branch(cur["branch"], repo), str(cur.get("sha") or ""))
    gh = _git_head()
    if gh and gh.get("branch"):
        return (gh.get("repo") or DEFAULT_REPO, gh["branch"], str(gh.get("sha") or ""))
    return (DEFAULT_REPO, _default_branch(DEFAULT_REPO), "")


def check_for_update() -> Optional[dict]:
    """시작 시 자동 확인. git 작업트리·대기 중 업데이트·네트워크 실패는 None(조용히)."""
    if is_git_checkout() or update_pending():
        return None
    ensure_version_file()
    repo, branch, cur_sha = _identity()
    if not branch:
        return None
    latest, branch = _latest_self_healing(repo, branch)
    if not latest or not latest.get("sha"):
        return None
    if cur_sha and str(latest["sha"]) == str(cur_sha):
        return None
    info = {"repo": repo, "branch": branch, "sha": latest["sha"], "message": latest.get("message", ""),
            "date": latest.get("date", ""), "current": bool(cur_sha)}
    if not cur_sha:
        info["current_unknown"] = True
    return info


def manual_check() -> tuple:
    """[업데이트 확인] 버튼: ("update", info) | ("latest", {}) | ("unknown", {"error"})."""
    global _last_error
    _last_error = ""
    repo, branch, cur_sha = _identity()
    latest, branch = _latest_self_healing(repo, branch)
    if not latest or not latest.get("sha"):
        return ("unknown", {"error": _last_error or i18n.KO.UPDATE_ERR_GITHUB})
    if cur_sha and str(latest["sha"]) == str(cur_sha):
        return ("latest", {})
    info = {"repo": repo, "branch": branch, "sha": latest["sha"], "message": latest.get("message", ""), "current": bool(cur_sha)}
    if not cur_sha:
        info["current_unknown"] = True
    return ("update", info)


# ── 스테이징 ──
_UPDATE_SKIP_TOP = {".git", ".github", "__pycache__", ".pytest_cache", ".idea", ".vscode", ".claude", ".coverage",
                    "dev", "docs", "pytest.ini", ".gitignore", "CLAUDE.md", "README.md"}
# 최상위는 남기되 그 안에서 내려보낼 것만(기본값 '안 보냄' — 빌드 도구가 사용자 PC 로 새지 않게).
_UPDATE_KEEP_ONLY = {"scripts": {"run_aoi.bat", "run_aoi_debug.bat", "run_collect.bat"}}
_REQUIRED_IN_STAGING = ("main.py", "requirements.txt", "aoi_capacity/ui/main_window.py",
                        "aoi_capacity/ui/assets/template.html", "aoi_capacity/ui/style.qss",
                        "aoi_capacity/utils/updater.py", "aoi_capacity/assets/devices.default.csv", "VERSION")
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def _stage_tree(src_root: Path, staging: Path, emit) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    items = [p for p in sorted(src_root.iterdir(), key=lambda p: p.name) if p.name not in _UPDATE_SKIP_TOP]
    m = len(items)
    for i, item in enumerate(items, start=1):
        dst = staging / item.name
        keep = _UPDATE_KEEP_ONLY.get(item.name)
        if keep is not None and item.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for name in sorted(keep):
                src = item / name
                if src.is_dir():
                    shutil.copytree(src, dst / name, ignore=_IGNORE)
                elif src.exists():
                    shutil.copy2(src, dst / name)
        elif item.is_dir():
            shutil.copytree(item, dst, ignore=_IGNORE)
        else:
            shutil.copy2(item, dst)
        emit(i, m, i18n.KO.UPDATE_PHASE_PREPARE)


def _verify_staged(staging: Path) -> str:
    """빈 문자열 = 정상. 아니면 사용자에게 보일 사유. '예외가 안 났다' 이상을 보장하는 관문."""
    for rel in _REQUIRED_IN_STAGING:
        p = staging / rel
        if not p.is_file():
            return i18n.KO.UPDATE_ERR_MISSING_FILE_FMT.format(rel=rel)
        try:
            if p.stat().st_size <= 0:
                return i18n.KO.UPDATE_ERR_EMPTY_FILE_FMT.format(rel=rel)
        except OSError as exc:
            return i18n.KO.UPDATE_ERR_STAT_FAIL_FMT.format(rel=rel, error=exc)
    try:
        if "__DATA__" not in (staging / "aoi_capacity/ui/assets/template.html").read_text(encoding="utf-8", errors="replace"):
            return i18n.KO.UPDATE_ERR_TEMPLATE_DATA
    except OSError as exc:
        return i18n.KO.UPDATE_ERR_STAT_FAIL_FMT.format(rel="template.html", error=exc)
    try:
        from string import Template

        from ..ui import theme
        Template((staging / "aoi_capacity/ui/style.qss").read_text(encoding="utf-8")).substitute(theme.colors("dark"))
    except Exception as exc:  # noqa: BLE001
        return i18n.KO.UPDATE_ERR_QSS_FMT.format(error=exc)
    return ""


def _promote_in_place(staging: Path, app_root: Path, emit) -> None:
    """비-exe 제자리 적용 — 항목마다 옆으로 치우고 → 새것 → 지운다. 중간 실패는 전부 롤백."""
    def _discard(p: Path) -> None:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            try:
                p.unlink()
            except OSError:
                pass

    items = sorted(staging.iterdir(), key=lambda p: p.name)
    m = len(items)
    done: list = []
    try:
        for i, item in enumerate(items, start=1):
            dst = app_root / item.name
            aside = app_root / (item.name + ".old-update")
            _discard(aside)
            moved_aside = False
            if dst.exists():
                dst.rename(aside)
                moved_aside = True
            shutil.move(str(item), str(dst))
            done.append((dst, aside if moved_aside else None))
            emit(i, m, i18n.KO.UPDATE_PHASE_APPLY)
    except Exception:
        for dst, aside in reversed(done):
            _discard(dst)
            if aside is not None:
                try:
                    aside.rename(dst)
                except OSError:
                    pass
        raise
    for _dst, aside in done:
        if aside is not None:
            _discard(aside)


def _bundled_python(root: Path) -> str:
    for cand in (root / "python" / "python.exe", root / "python" / "bin" / "python3"):
        if cand.exists():
            return str(cand)
    return sys.executable


def _ensure_deps(root: Path, staging: Path, emit) -> bool:
    """새 requirements 를 동봉 파이썬에 설치. 실패하면 업데이트를 적용하지 않는다(반쪽 업데이트 방지)."""
    global _last_error
    from . import bootstrap

    req = staging / "requirements.txt"
    text = _file_text(req)
    if text is None or bootstrap.deps_installed(root, text):
        return True
    emit(0, 0, i18n.KO.UPDATE_PHASE_DEPS)
    kwargs = {"creationflags": 0x08000000} if os.name == "nt" else {}      # CREATE_NO_WINDOW
    try:
        rc = subprocess.call(bootstrap.pip_install_cmd(_bundled_python(root), req), **kwargs)
    except Exception as exc:  # noqa: BLE001
        _last_error = i18n.KO.UPDATE_ERR_PIP_START_FMT.format(error=exc)
        return False
    if rc != 0:
        _last_error = i18n.KO.UPDATE_ERR_PIP_RC_FMT.format(rc=rc)
        return False
    bootstrap.write_deps_marker(root, text)
    return True


def download_and_apply(repo: str, branch: str, target_sha: str, timeout: float = 60.0,
                       progress: Optional[Callable[[int, int, str], None]] = None) -> bool:
    """브랜치 zip → 새 트리 스테이징 → 검증 → (exe) app.new 로 rename / (비-exe) 제자리 적용. 실패 시 False(사유 last_error)."""
    global _last_error, _deps_changed, _deps_blocked
    _deps_changed = False
    _deps_blocked = False
    staging: Optional[Path] = None

    def _emit(done, total, phase):
        if progress:
            try:
                progress(int(done), int(total), str(phase))
            except Exception:  # noqa: BLE001
                pass

    url = _ZIP.format(repo=repo, branch=branch)
    tmpd = Path(tempfile.mkdtemp(prefix="aoi_update_"))
    try:
        zip_path = tmpd / "src.zip"
        with _urlopen(url, _UA, timeout) as r, open(zip_path, "wb") as f:
            total = int(getattr(r, "headers", {}).get("Content-Length", 0) or 0)
            done = 0
            _emit(0, total, i18n.KO.UPDATE_PHASE_DOWNLOAD)
            while True:
                chunk = r.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                _emit(done, total, i18n.KO.UPDATE_PHASE_DOWNLOAD)
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            n = len(names)
            for i, name in enumerate(names, start=1):
                z.extract(name, tmpd)
                if i % 20 == 0 or i == n:
                    _emit(i, n, i18n.KO.UPDATE_PHASE_EXTRACT)
        roots = [p for p in tmpd.iterdir() if p.is_dir()]
        if not roots or not (roots[0] / "aoi_capacity").exists():
            _last_error = i18n.KO.UPDATE_ERR_NO_TREE
            return False
        src_root = roots[0]
        app_root = _app_root()
        _deps_changed = _requirements_differ(src_root, app_root)

        install_root = _install_root()
        staging = _staging_dir(install_root, app_root)
        shutil.rmtree(staging, ignore_errors=True)
        _stage_tree(src_root, staging, _emit)
        _write_version_to(staging, target_sha, branch, repo)      # VERSION 은 스테이징에만
        reason = _verify_staged(staging)
        if reason:
            _last_error = i18n.KO.UPDATE_ERR_VERIFY_FMT.format(detail=reason)
            return False
        if install_root is not None:
            if not _ensure_deps(install_root, staging, _emit):
                _deps_blocked = True
                return False
            pending = _pending_dir(install_root)
            shutil.rmtree(pending, ignore_errors=True)
            staging.rename(pending)                  # ★ 이 rename 이 '준비 완료' 신호
            staging = None
        else:
            _promote_in_place(staging, app_root, _emit)
            _write_version(target_sha, branch, repo)
        _emit(1, 1, i18n.KO.UPDATE_PHASE_DONE)
        return True
    except Exception as exc:  # noqa: BLE001
        _last_error = _describe_err(exc, url)
        return False
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)


def _file_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return None


def _requirements_differ(src_root: Path, app_root: Path) -> bool:
    new = _file_text(src_root / "requirements.txt")
    old = _file_text(app_root / "requirements.txt")
    if new is None or old is None:
        return False
    return old.strip() != new.strip()
