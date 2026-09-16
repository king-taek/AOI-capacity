"""최신 코드 받기 — 이 폴더를 지정한 브랜치의 최신 내용으로 맞춘다.

두 가지 경우를 모두 처리한다.
  * **git 으로 받은 폴더**  → `git fetch` + `git merge --ff-only` (가장 깔끔하다)
  * **GitHub zip 을 푼 폴더**(`AOI-capacity-claude-...` 처럼 `.git` 이 없는 폴더)
    → 브랜치 zip 을 내려받아 바뀐 파일만 덮어쓴다. 덮어쓰기 전 원본을 `_backup_날짜시각\\` 에 남긴다.

★ 내 작업 내용을 함부로 버리지 않는다: git 폴더에 커밋 안 된 변경이 있으면 멈추고 알려 준다.
★ 표준 라이브러리만 쓴다. NAS 는 건드리지 않는다.

    python scripts\\update_code.py              # 최신 코드로 맞추기
    python scripts\\update_code.py --check      # 무엇이 새로 왔는지 보기만(변경 없음)
    python scripts\\update_code.py --branch 다른브랜치
"""
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════════
#  받을 브랜치 — 바꾸려면 이 줄만 고치면 됩니다.
BRANCH = "main"
#  저장소 (owner/repo)
REPO = "king-taek/AOI-capacity"
# ══════════════════════════════════════════════════════════════════════════════

import argparse
import filecmp
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

#: 받은 트리가 멀쩡한지 확인할 파일들 — 하나라도 없으면 덮어쓰지 않는다.
REQUIRED = ("main.py", "requirements.txt", "aoi_capacity/collect.py", "aoi_capacity/ui/assets/template.html")
SKIP_TOP = {".git", ".github", "__pycache__", ".pytest_cache"}
UA = {"User-Agent": "AOI-Capacity-Update"}


def say(msg: str = "") -> None:
    print(msg, flush=True)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ── git 방식 ─────────────────────────────────────────────────────────────────
def git(root: Path, *args: str):
    """git 한 번 실행 → (성공여부, 출력). git 이 없으면 (False, 안내)."""
    try:
        p = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return False, "git 이 설치되어 있지 않습니다"
    return p.returncode == 0, (p.stdout + p.stderr).strip()


def is_git_repo(root: Path) -> bool:
    return (root / ".git").exists()


def git_update(root: Path, branch: str, check_only: bool) -> int:
    ok, _ = git(root, "--version")
    if not ok:
        say("git 을 실행할 수 없어 zip 방식으로 받습니다.")
        return zip_update(root, branch, check_only)

    ok, dirty = git(root, "status", "--porcelain")
    if ok and dirty.strip() and not check_only:
        say("[멈춤] 커밋하지 않은 변경이 있습니다 — 덮어쓰지 않았습니다:")
        for line in dirty.splitlines()[:20]:
            say("   " + line)
        say("\n   먼저 변경 내용을 정리(커밋하거나 되돌리기)한 뒤 다시 실행하세요.")
        return 1

    say(f"1/3 가져오는 중… origin/{branch}")
    ok, out = git(root, "fetch", "origin", branch)
    if not ok:
        say("[오류] 가져오지 못했습니다:\n" + out)
        return 2
    before = git(root, "rev-parse", "--short", "HEAD")[1]

    ok, log = git(root, "log", "--oneline", f"HEAD..FETCH_HEAD")
    if not log.strip():
        say(f"\n이미 최신입니다 (HEAD {before}).")
        return 0
    say("\n새로 온 커밋:")
    for line in log.splitlines()[:20]:
        say("   " + line)
    if check_only:
        say("\n--check 라 받기만 하고 적용하지 않았습니다.")
        return 0

    say(f"\n2/3 브랜치 확인…")
    cur = git(root, "rev-parse", "--abbrev-ref", "HEAD")[1]
    if cur != branch:
        ok, out = git(root, "checkout", branch)
        if not ok:
            ok, out = git(root, "checkout", "-b", branch, f"origin/{branch}")
        if not ok:
            say("[오류] 브랜치를 바꾸지 못했습니다:\n" + out)
            return 2
    say("3/3 적용 중…")
    ok, out = git(root, "merge", "--ff-only", "FETCH_HEAD")
    if not ok:
        say("[오류] 빨리감기 병합을 하지 못했습니다(이 폴더에만 있는 커밋이 있을 수 있습니다):\n" + out)
        return 2
    after = git(root, "rev-parse", "--short", "HEAD")[1]
    say(f"\n완료했습니다. {before} → {after}")
    return 0


# ── zip 방식(.git 이 없는 폴더) ───────────────────────────────────────────────
def _opener(insecure: bool):
    handlers = []
    proxies = urllib.request.getproxies()
    if proxies:
        handlers.append(urllib.request.ProxyHandler(proxies))
    ctx = None
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        try:
            import truststore            # 회사 SSL 검사 프록시에서도 되도록 OS 신뢰 저장소 사용
            ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except Exception:                # noqa: BLE001
            try:
                ctx = ssl.create_default_context()
                ctx.load_default_certs()
            except Exception:            # noqa: BLE001
                ctx = None
    if ctx is not None:
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers)


def download(url: str, dest: Path, timeout: float = 120.0) -> None:
    """브랜치 zip 내려받기. 인증서 검증이 막히면 한 번만 검증 없이 재시도한다."""
    req = urllib.request.Request(url, headers=UA)
    try:
        r = _opener(False).open(req, timeout=timeout)
    except Exception as exc:             # noqa: BLE001
        if isinstance(exc, ssl.SSLError) or isinstance(getattr(exc, "reason", None), ssl.SSLError):
            say("   (인증서 검증이 막혀 검증 없이 다시 시도합니다 — 사내 프록시 환경)")
            r = _opener(True).open(req, timeout=timeout)
        else:
            raise
    with r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def zip_update(root: Path, branch: str, check_only: bool) -> int:
    url = f"https://codeload.github.com/{REPO}/zip/refs/heads/{branch}"
    say(f"1/4 내려받는 중… {branch}")
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        archive = tmpd / "branch.zip"
        try:
            download(url, archive)
        except urllib.error.HTTPError as ex:
            say(f"[오류] 받지 못했습니다(HTTP {ex.code}). 브랜치 이름이 맞는지 확인하세요: {branch}")
            return 2
        except Exception as ex:          # noqa: BLE001
            say(f"[오류] 받지 못했습니다: {type(ex).__name__}: {ex}")
            return 2

        say("2/4 푸는 중…")
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmpd / "x")
        tops = [p for p in (tmpd / "x").iterdir() if p.is_dir()]
        if len(tops) != 1:
            say("[오류] 받은 zip 의 구조가 예상과 다릅니다.")
            return 2
        src = tops[0]
        missing = [r for r in REQUIRED if not (src / r).is_file()]
        if missing:
            say("[오류] 받은 내용이 온전하지 않아 적용하지 않았습니다: " + ", ".join(missing))
            return 2

        say("3/4 견주는 중…")
        new, changed = [], []
        for p in sorted(src.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(src)
            if rel.parts[0] in SKIP_TOP:
                continue
            dst = root / rel
            if not dst.exists():
                new.append(rel)
            elif not filecmp.cmp(p, dst, shallow=False):
                changed.append(rel)
        if not new and not changed:
            say("\n이미 최신입니다(바뀐 파일 없음).")
            return 0
        say(f"   새 파일 {len(new)}개 · 바뀐 파일 {len(changed)}개")
        for rel in (new + changed)[:25]:
            say(f"     {rel}")
        if len(new) + len(changed) > 25:
            say(f"     … 외 {len(new) + len(changed) - 25}개")
        if check_only:
            say("\n--check 라 적용하지 않았습니다.")
            return 0

        backup = root / ("_backup_" + time.strftime("%Y%m%d_%H%M"))
        say(f"4/4 적용 중… (바뀌는 원본은 {backup.name}\\ 에 남깁니다)")
        for rel in changed:
            b = backup / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, b)
        for rel in new + changed:
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, dst)
    say(f"\n완료했습니다. 새 {len(new)}개 · 갱신 {len(changed)}개")
    say("   되돌리려면 _backup_… 폴더의 파일을 제자리에 다시 복사하면 됩니다.")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="최신 코드 받기")
    ap.add_argument("--branch", default=BRANCH, help=f"받을 브랜치 (기본 {BRANCH})")
    ap.add_argument("--check", action="store_true", help="무엇이 새로 왔는지 보기만 한다")
    ap.add_argument("--zip", action="store_true", help="git 폴더여도 zip 방식으로 받는다")
    args = ap.parse_args(argv)

    root = repo_root()
    say(f"폴더: {root}")
    say(f"브랜치: {args.branch}  ({REPO})")
    say("")
    if args.zip or not is_git_repo(root):
        if not args.zip:
            say("(.git 이 없는 폴더라 zip 방식으로 받습니다)")
        return zip_update(root, args.branch, args.check)
    return git_update(root, args.branch, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
