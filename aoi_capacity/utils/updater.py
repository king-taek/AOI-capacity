"""GitHub 공개 저장소의 기본 브랜치에서 앱 업데이트를 확인/적용한다.

배포본은 ``app/VERSION`` (JSON ``{"sha","branch","repo"}``) 을 동봉한다. 실행 시 백그라운드로 브랜치 최신 커밋
SHA 를 받아 현재 SHA 와 비교하고, 다르면 UI 가 안내한다. 동의하면 **그 SHA 의 archive zip** 을 받아 **앱 구동에 필요한 것만**
담은 새 트리를 만든다(허용 목록: ``aoi_capacity/`` · ``main.py`` · ``requirements.txt`` · ``scripts/`` 선별 · 생성한 ``VERSION``).

**적용은 "완성·검증된 트리만" 한다** — 새 트리를 통째로 만들어 바꾸므로 상류에서 삭제된 파일이 실제로 사라지고,
중간에 실패해도 구버전과 ``VERSION`` 이 그대로 남는다.
- **exe 모드**(런처가 ``AOI_APP_HOME`` 을 넘겨준 경우): ``app.new.part`` 에 만들고 검증 후 ``app.new`` 로 rename. 실제 교체는
  다음 실행 때 런처(``scripts/exe_launcher.py``)가 한다. 새 requirements 는 동봉 파이썬에 먼저 설치하고, 실패하면 적용하지 않는다.
- **비-exe**(개발 클론이 아닌 loose 폴더): 제자리에 항목 단위로 적용 — 항목마다 저널(prepared → old_moved → new_moved)을
  남기고, 어느 단계에서 실패하든 그 항목과 앞선 항목을 전부 되돌린다. 되돌리기도 실패하면 백업(``*.old-update``)을 지우지 않고
  어느 파일을 손으로 복구해야 하는지 알려 준다.
- git 작업트리(``.git`` 있음)에서는 자동 확인·적용을 하지 않는다.
- 표준 라이브러리(urllib)만 사용. TLS 는 **검증된 연결만** — truststore(OS 신뢰 저장소) → 기본 인증서. 검증에 실패하면
  확인도 적용도 멈추고 사유를 남긴다(검증 없이 다시 시도하는 길은 없다).

받는 커밋의 조건(D61): 대상 SHA 는 40자리 전체 SHA 이고, 그 SHA 로 **필수 CI(워크플로 ``tests.yml``)가 성공 완료**한 것만 받는다.
조회 불가·진행 중·실패·기록 없음이면 현재 버전을 유지하고 이유를 남긴다. zip 은 ``archive/<full sha>.zip`` 으로 고정해
확인한 SHA 와 받은 코드가 같게 하고, 압축 안은 풀기 전에 검사한다(루트 폴더 하나 · 절대 경로/``..``/드라이브/UNC/심볼릭 링크 거부 ·
파일 수·전체 크기 상한 · 대소문자만 다른 경로 거부 · 루트 폴더 이름이 대상 SHA 와 맞는지).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .. import i18n
from . import paths

DEFAULT_REPO = "king-taek/AOI-capacity"
# 자동 업데이트 기준은 저장소의 GitHub 기본 브랜치다. 이름은 api 로 동적 조회하고, 실패하면 아래 상수를 폴백으로 쓴다.
DEFAULT_BRANCH = "main"
# 필수 CI — 이 워크플로 파일이 대상 SHA 에서 성공 완료해야만 받는다(D61).
REQUIRED_WORKFLOW_FILE = "tests.yml"
REQUIRED_WORKFLOW_NAME = "tests"
# 신뢰하는 실행 원인 — 기본 브랜치 push(와 관리자의 수동 실행)만. fork 의 pull_request 등은 세지 않는다.
_TRUSTED_EVENTS = {"push", "workflow_dispatch"}
_API_REPO = "https://api.github.com/repos/{repo}"
_API = "https://api.github.com/repos/{repo}/commits/{branch}"
_API_RUNS = "https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs?head_sha={sha}&per_page=30"
_ATOM = "https://github.com/{repo}/commits/{branch}.atom"      # api.github.com 만 막힌 사내망 폴백(SHA 조회만)
_ZIP = "https://github.com/{repo}/archive/{sha}.zip"           # 브랜치 HEAD 가 아니라 **확인한 SHA** 의 archive
_UA = {"User-Agent": "AOI-Capacity-Updater"}
_APP_HOME_ENV = paths.APP_HOME_ENV
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# 압축 파일 방어 상한 — 저장소 전체(문서·샘플 포함)가 수백 파일·수십 MB 라 넉넉하되 폭탄은 막는다.
ZIP_MAX_FILES = 5000
ZIP_MAX_BYTES = 300 * 1024 * 1024
# pip 설치 상한(초). 사내 프록시에서 pip 가 멈추면 이 시간 뒤 자식 프로세스를 죽이고 적용을 포기한다(C10).
PIP_TIMEOUT_SEC = 600.0

_last_error: str = ""
_OPENER = None
_deps_changed: bool = False
_deps_blocked: bool = False
_default_branch_cache: dict = {}


class UpdateError(Exception):
    """사용자에게 그대로 보일 사유를 담은 업데이트 실패."""


class RollbackError(UpdateError):
    """제자리 적용을 되돌리다 실패했다 — 백업은 남겨 두었고 메시지에 복구할 경로가 있다."""


class TlsVerifyError(UpdateError):
    """인증서 검증 실패 — 확인도 적용도 여기서 멈춘다(다른 주소·검증 없는 연결로 돌아가지 않는다)."""


def last_error() -> str:
    return _last_error


def deps_changed() -> bool:
    return _deps_changed


def deps_blocked() -> bool:
    """직전 적용이 '새 패키지를 설치하지 못해서' 포기됐는지(exe 모드) — UI 가 새 배포본을 받으라고 안내."""
    return _deps_blocked


# ── 네트워크 ──
def _ssl_context():
    """검증하는 컨텍스트만 만든다. truststore(OS 신뢰 저장소 — 사내 CA 포함) → 파이썬 기본. 검증 없는 컨텍스트는 없다."""
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


def _make_opener():
    handlers = []
    proxies = urllib.request.getproxies()
    if proxies:
        handlers.append(urllib.request.ProxyHandler(proxies))
    ctx = _ssl_context()
    if ctx is not None:
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers)


def _opener():
    global _OPENER
    if _OPENER is None:
        _OPENER = _make_opener()
    return _OPENER


def _is_ssl_verify_error(exc: Exception) -> bool:
    return isinstance(exc, ssl.SSLError) or isinstance(getattr(exc, "reason", None), ssl.SSLError)


def _urlopen(url: str, headers: dict, timeout: float):
    """HTTPS GET — 검증된 TLS 로만. 인증서 검증 실패는 ``TlsVerifyError`` 로 올린다(재시도·우회 없음)."""
    try:
        return _opener().open(urllib.request.Request(url, headers=headers), timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        if _is_ssl_verify_error(exc):
            host = url.split("/")[2] if "//" in url else url
            raise TlsVerifyError(i18n.KO.UPDATE_ERR_TLS_VERIFY_FMT.format(
                host=host, reason=getattr(exc, "reason", exc))) from exc
        raise


def _describe_err(exc: Exception, url: str) -> str:
    host = url.split("/")[2] if "//" in url else url
    if isinstance(exc, UpdateError):
        return str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        return i18n.KO.UPDATE_ERR_HTTP_FMT.format(code=exc.code, host=host)
    if _is_ssl_verify_error(exc):
        return i18n.KO.UPDATE_ERR_TLS_VERIFY_FMT.format(host=host, reason=getattr(exc, "reason", exc))
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", exc)
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
    except TlsVerifyError:
        raise
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
    """API → (api 만 막힌 사내망) atom 피드. 인증서 검증 실패는 폴백 없이 여기서 끝난다."""
    global _last_error
    try:
        return _latest_via_api(repo, branch, timeout) or _latest_via_atom(repo, branch, timeout)
    except TlsVerifyError as exc:
        _last_error = str(exc)
        return None


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


# ── 필수 CI 게이트(D61) ──
def _is_full_sha(sha: str) -> bool:
    return bool(_SHA_RE.match(str(sha or "").lower()))


def _ci_gate(repo: str, sha: str, timeout: float = 15.0) -> Tuple[bool, str]:
    """(통과, 사유). 대상 SHA 로 필수 워크플로가 **성공 완료**한 실행이 하나라도 있어야 통과.
    이전 커밋의 성공·진행 중·건너뜀·취소는 성공이 아니다. 조회 자체가 안 되면 통과가 아니다."""
    sha = str(sha or "").lower()
    if not _is_full_sha(sha):
        return False, i18n.KO.UPDATE_ERR_BAD_SHA_FMT.format(sha=sha[:12])
    url = _API_RUNS.format(repo=repo, workflow=REQUIRED_WORKFLOW_FILE, sha=sha)
    try:
        data = json.loads(_http_get(url, {**_UA, "Accept": "application/vnd.github+json"}, timeout).decode("utf-8"))
        runs = data.get("workflow_runs")
        if not isinstance(runs, list):
            raise ValueError("workflow_runs")
    except Exception as exc:  # noqa: BLE001
        return False, i18n.KO.UPDATE_CI_QUERY_FAILED_FMT.format(detail=_describe_err(exc, url))
    pending = False
    failed = False
    for run in runs:
        if not isinstance(run, dict) or str(run.get("head_sha") or "").lower() != sha:
            continue
        path = str(run.get("path") or "")
        if path and not path.endswith("/" + REQUIRED_WORKFLOW_FILE) and path != REQUIRED_WORKFLOW_FILE:
            continue
        if run.get("name") and str(run.get("name")) != REQUIRED_WORKFLOW_NAME:
            continue
        if str(run.get("event") or "") not in _TRUSTED_EVENTS:
            continue
        if str(run.get("status") or "") != "completed":
            pending = True
            continue
        if str(run.get("conclusion") or "") == "success":
            return True, ""
        failed = True
    if pending:
        return False, i18n.KO.UPDATE_CI_PENDING
    if failed:
        return False, i18n.KO.UPDATE_CI_FAILED
    return False, i18n.KO.UPDATE_CI_NO_RUN


def _gate_info(repo: str, branch: str, latest: dict, cur_sha: str) -> Tuple[str, dict]:
    """공통 판정: ("update", info) | ("held", {"sha","reason","error"})."""
    sha = str(latest["sha"])
    ok, reason = _ci_gate(repo, sha)
    if not ok:
        return "held", {"sha": sha, "reason": reason, "error": reason, "repo": repo, "branch": branch}
    info = {"repo": repo, "branch": branch, "sha": sha, "message": latest.get("message", ""),
            "date": latest.get("date", ""), "current": bool(cur_sha)}
    if not cur_sha:
        info["current_unknown"] = True
    return "update", info


def check_for_update() -> Optional[dict]:
    """시작 시 자동 확인. git 작업트리·대기 중 업데이트·네트워크 실패·CI 미통과는 None(조용히, 사유는 last_error)."""
    global _last_error
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
    status, info = _gate_info(repo, branch, latest, cur_sha)
    if status != "update":
        _last_error = str(info.get("reason") or "")
        return None
    return info


def manual_check() -> tuple:
    """[업데이트 확인] 버튼: ("update", info) | ("latest", {}) | ("held", {"sha","reason"}) | ("unknown", {"error"})."""
    global _last_error
    _last_error = ""
    repo, branch, cur_sha = _identity()
    latest, branch = _latest_self_healing(repo, branch)
    if not latest or not latest.get("sha"):
        return ("unknown", {"error": _last_error or i18n.KO.UPDATE_ERR_GITHUB})
    if cur_sha and str(latest["sha"]) == str(cur_sha):
        return ("latest", {})
    status, info = _gate_info(repo, branch, latest, cur_sha)
    if status != "update":
        _last_error = str(info.get("reason") or "")
    return (status, info)


# ── 압축 검사·해제 ──
def _zip_entry_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _check_zip_entries(z: zipfile.ZipFile, target_sha: str) -> str:
    """검사만 한다(파일을 하나도 쓰지 않는다). 통과하면 루트 폴더 이름, 아니면 UpdateError."""
    infos = z.infolist()
    files = [i for i in infos if not i.is_dir()]
    total = sum(int(i.file_size or 0) for i in files)
    if len(files) > ZIP_MAX_FILES or total > ZIP_MAX_BYTES:
        raise UpdateError(i18n.KO.UPDATE_ERR_ZIP_TOO_BIG_FMT.format(
            files=len(files), mb=total // (1024 * 1024), max_files=ZIP_MAX_FILES, max_mb=ZIP_MAX_BYTES // (1024 * 1024)))
    roots = set()
    seen_ci = set()
    for info in infos:
        name = info.filename
        if not name or name.startswith(("/", "\\")) or "\\" in name or ":" in name:
            raise UpdateError(i18n.KO.UPDATE_ERR_ZIP_ENTRY_FMT.format(name=name[:80]))
        parts = name.split("/")
        if any(p in ("..", "") for p in parts[:-1]) or parts[-1] == "..":
            raise UpdateError(i18n.KO.UPDATE_ERR_ZIP_ENTRY_FMT.format(name=name[:80]))
        if _zip_entry_is_symlink(info):
            raise UpdateError(i18n.KO.UPDATE_ERR_ZIP_ENTRY_FMT.format(name=name[:80]))
        key = name.rstrip("/").lower()
        if key in seen_ci:
            raise UpdateError(i18n.KO.UPDATE_ERR_ZIP_CASE_FMT.format(name=name[:80]))
        seen_ci.add(key)
        roots.add(parts[0])
    if len(roots) != 1:
        raise UpdateError(i18n.KO.UPDATE_ERR_ZIP_ROOTS_FMT.format(roots=", ".join(sorted(roots))[:120] or "-"))
    root = next(iter(roots))
    suffix = root.rsplit("-", 1)[-1].lower()
    if len(suffix) < 7 or not str(target_sha).lower().startswith(suffix):
        raise UpdateError(i18n.KO.UPDATE_ERR_ZIP_ROOT_SHA_FMT.format(root=root[:80], sha=str(target_sha)[:12]))
    return root


def _safe_extract(zip_path: Path, dest: Path, target_sha: str, emit) -> Path:
    """검사를 통과한 항목만 dest 아래에 직접 쓴다(z.extract 대신 경로를 우리가 만든다). 반환 = 풀린 루트 폴더."""
    dest = Path(dest).resolve()
    with zipfile.ZipFile(zip_path) as z:
        root = _check_zip_entries(z, target_sha)
        infos = z.infolist()
        n = len(infos)
        for i, info in enumerate(infos, start=1):
            target = (dest / info.filename).resolve()
            if dest not in target.parents:
                raise UpdateError(i18n.KO.UPDATE_ERR_ZIP_ENTRY_FMT.format(name=info.filename[:80]))
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out, 256 * 1024)
            if i % 20 == 0 or i == n:
                emit(i, n, i18n.KO.UPDATE_PHASE_EXTRACT)
    return dest / root


# ── 스테이징 ──
# 사용자 PC 로 내려보내는 최상위 항목의 **허용 목록**(기본값 '안 보냄'). 여기 없는 것은 저장소 루트에 무엇이 있어도 가지 않는다.
_UPDATE_TOP_ALLOW = ("main.py", "requirements.txt", "aoi_capacity", "scripts")
# 최상위는 남기되 그 안에서 내려보낼 것만(기본값 '안 보냄' — 빌드 도구가 사용자 PC 로 새지 않게).
_UPDATE_KEEP_ONLY = {"scripts": {"run_aoi.bat", "run_aoi_debug.bat", "run_collect.bat",
                                "make_sample.bat", "collect_sample.py"}}
# 스테이징 최상위에 있어야 하는 이름 전부(VERSION 은 스테이징 때 생성).
STAGED_TOP_LEVEL = frozenset(_UPDATE_TOP_ALLOW) | {"VERSION"}
_REQUIRED_IN_STAGING = ("main.py", "requirements.txt", "aoi_capacity/ui/main_window.py",
                        "aoi_capacity/ui/assets/template.html", "aoi_capacity/ui/style.qss",
                        "aoi_capacity/utils/updater.py", "aoi_capacity/assets/devices.default.csv", "VERSION")
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "*.log", "*.bak", ".DS_Store")


def _stage_tree(src_root: Path, staging: Path, emit) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    items = [src_root / name for name in _UPDATE_TOP_ALLOW if (src_root / name).exists()]
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
    extra = sorted(p.name for p in staging.iterdir() if p.name not in STAGED_TOP_LEVEL)
    if extra:
        return i18n.KO.UPDATE_ERR_UNEXPECTED_TOP_FMT.format(names=", ".join(extra)[:120])
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


# ── 제자리 적용(비-exe) ──
def _move(src: Path, dst: Path) -> None:
    """항목 하나를 옮긴다(같은 볼륨이면 rename). 테스트가 실패를 주입하는 유일한 지점."""
    shutil.move(str(src), str(dst))


def _remove(p: Path) -> None:
    """지운다 — 실패는 그대로 올린다(롤백에서 '지웠다고 믿고' 넘어가지 않게)."""
    if p.is_symlink() or p.is_file():
        p.unlink()
    elif p.is_dir():
        shutil.rmtree(p)


def _discard(p: Path) -> None:
    try:
        _remove(p)
    except OSError:
        pass


def _rollback(journal: List[dict]) -> List[str]:
    """저널을 거꾸로 되짚어 원본을 되돌린다. 반환 = 되돌리지 못한 항목 설명(비어 있으면 전부 복구)."""
    failures: List[str] = []
    for e in reversed(journal):
        dst, aside, state = e["dst"], e["aside"], e["state"]
        try:
            if state == "new_moved" or (state == "old_moved" and dst.exists()):
                _remove(dst)                                 # 새 것(또는 반쯤 옮겨진 것)을 치운다
            if e["had_old"] and aside.exists() and not dst.exists():
                _move(aside, dst)                            # 옆에 치워 둔 원본을 제자리로
            if e["had_old"] and not dst.exists():
                raise OSError(i18n.KO.UPDATE_ERR_ROLLBACK_ITEM_MISSING)
            e["state"] = "restored"
        except Exception as exc:  # noqa: BLE001
            failures.append(i18n.KO.UPDATE_ERR_ROLLBACK_ITEM_FMT.format(dst=dst.name, aside=aside.name, error=exc))
    return failures


def _promote_in_place(staging: Path, app_root: Path, emit) -> None:
    """비-exe 제자리 적용 — 항목마다 prepared → old_moved → new_moved 로 저널을 남기며 옆으로 치우고 → 새것 → 지운다.
    어느 단계에서 실패하든 그 항목과 앞선 항목을 전부 되돌린다. 되돌리기에 실패하면 백업(``*.old-update``)을 남기고
    ``RollbackError`` 로 어느 파일을 손으로 복구해야 하는지 알린다."""
    items = sorted(staging.iterdir(), key=lambda p: p.name)
    m = len(items)
    journal: List[dict] = []
    try:
        for i, item in enumerate(items, start=1):
            dst = app_root / item.name
            aside = app_root / (item.name + ".old-update")
            if aside.exists():
                if dst.exists():
                    _remove(aside)                           # 지난 적용의 잔재(원본은 제자리에 있다)
                else:
                    _move(aside, dst)                        # 지난 롤백이 끝나지 못했다 — 먼저 원본을 되살린다
            entry = {"dst": dst, "aside": aside, "had_old": dst.exists(), "state": "prepared"}
            journal.append(entry)
            if entry["had_old"]:
                _move(dst, aside)
                entry["state"] = "old_moved"
            _move(item, dst)
            entry["state"] = "new_moved"
            emit(i, m, i18n.KO.UPDATE_PHASE_APPLY)
    except Exception as exc:  # noqa: BLE001
        failures = _rollback(journal)
        if failures:
            raise RollbackError(i18n.KO.UPDATE_ERR_ROLLBACK_FMT.format(
                folder=str(app_root), items="\n".join(failures), error=exc)) from exc
        raise UpdateError(i18n.KO.UPDATE_ERR_APPLY_ROLLED_BACK_FMT.format(error=exc)) from exc
    for e in journal:                                        # 전부 새것으로 바뀐 뒤에만 백업을 치운다
        if e["had_old"]:
            _discard(e["aside"])


# ── 의존성 설치(exe 모드) ──
def _bundled_python(root: Path) -> str:
    for cand in (root / "python" / "python.exe", root / "python" / "bin" / "python3"):
        if cand.exists():
            return str(cand)
    return sys.executable


class _PipStopped(Exception):
    pass


def _run_pip(cmd: list, timeout: float, cancel: Optional[Callable[[], bool]]) -> int:
    """pip 를 자식 프로세스로 돌리고 종료 코드를 돌려준다. 시간 초과·취소면 자식을 죽이고 기다린 뒤 UpdateError.
    자식을 죽이지 못하면 그것도 사유로 남긴다(조용히 성공으로 넘어가지 않는다)."""
    kwargs = {"creationflags": 0x08000000} if os.name == "nt" else {}      # CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except Exception as exc:  # noqa: BLE001
        raise UpdateError(i18n.KO.UPDATE_ERR_PIP_START_FMT.format(error=exc)) from exc
    deadline = time.monotonic() + float(timeout)
    stop_reason = ""
    while True:
        try:
            return int(proc.wait(timeout=0.5))
        except subprocess.TimeoutExpired:
            pass
        if cancel is not None and cancel():
            stop_reason = i18n.KO.UPDATE_ERR_PIP_CANCELLED
            break
        if time.monotonic() >= deadline:
            stop_reason = i18n.KO.UPDATE_ERR_PIP_TIMEOUT_FMT.format(sec=int(timeout))
            break
    try:
        proc.kill()
        proc.wait(timeout=15)
    except Exception as exc:  # noqa: BLE001
        raise UpdateError(stop_reason + " " + i18n.KO.UPDATE_ERR_PIP_KILL_FMT.format(error=exc)) from exc
    raise UpdateError(stop_reason)


def _ensure_deps(root: Path, staging: Path, emit, timeout: float = PIP_TIMEOUT_SEC,
                 cancel: Optional[Callable[[], bool]] = None) -> bool:
    """새 requirements 를 동봉 파이썬에 설치. 실패·시간 초과·취소면 표식을 쓰지 않고 업데이트를 적용하지 않는다(반쪽 업데이트 방지)."""
    global _last_error
    from . import bootstrap

    req = staging / "requirements.txt"
    text = _file_text(req)
    if text is None or bootstrap.deps_installed(root, text):
        return True
    emit(0, 0, i18n.KO.UPDATE_PHASE_DEPS)
    try:
        rc = _run_pip(bootstrap.pip_install_cmd(_bundled_python(root), req), timeout, cancel)
    except UpdateError as exc:
        _last_error = str(exc)
        return False
    if rc != 0:
        _last_error = i18n.KO.UPDATE_ERR_PIP_RC_FMT.format(rc=rc)
        return False
    bootstrap.write_deps_marker(root, text)
    return True


# ── 적용 ──
def download_and_apply(repo: str, branch: str, target_sha: str, timeout: float = 60.0,
                       progress: Optional[Callable[[int, int, str], None]] = None,
                       pip_timeout: float = PIP_TIMEOUT_SEC, cancel: Optional[Callable[[], bool]] = None) -> bool:
    """CI 게이트 → 그 SHA 의 archive zip → 검사·해제 → 허용 목록만 스테이징 → 검증 → (exe) app.new 로 rename / (비-exe) 제자리 적용.
    실패 시 False(사유 last_error). 확인한 SHA · 받은 zip · 기록하는 VERSION 이 전부 같은 SHA 다."""
    global _last_error, _deps_changed, _deps_blocked
    _deps_changed = False
    _deps_blocked = False
    staging: Optional[Path] = None
    target_sha = str(target_sha or "").lower()

    def _emit(done, total, phase):
        if progress:
            try:
                progress(int(done), int(total), str(phase))
            except Exception:  # noqa: BLE001
                pass

    if not _is_full_sha(target_sha):
        _last_error = i18n.KO.UPDATE_ERR_BAD_SHA_FMT.format(sha=target_sha[:12])
        return False
    ok, reason = _ci_gate(repo, target_sha)
    if not ok:
        _last_error = reason
        return False

    url = _ZIP.format(repo=repo, sha=target_sha)
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
        src_root = _safe_extract(zip_path, tmpd / "x", target_sha, _emit)
        if not (src_root / "aoi_capacity").is_dir():
            _last_error = i18n.KO.UPDATE_ERR_NO_TREE
            return False
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
            if not _ensure_deps(install_root, staging, _emit, timeout=pip_timeout, cancel=cancel):
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
