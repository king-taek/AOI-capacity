"""코드가 바뀐 변경에 `진행상황.md` 가 함께 있는지 — CI(PR) 용 검사(S14, CLAUDE.md '커밋' 규칙의 두 번째 그물).

    python dev/tools/progress_doc_check.py --base <기준 rev> --head <검사할 rev>

`git merge-base <base> <head>` 부터 `<head>` 까지 바뀐 파일을 보고, 코드 경로(`CODE_PREFIXES` · `CODE_FILES`)가 하나라도 있으면
`진행상황.md` 도 바뀌었어야 한다. 문서·샘플·보관물만 바뀐 변경은 통과. HEAD 한 커밋만 보지 않고 **범위**를 보는 이유는
squash·merge 에서 마지막 커밋에 문서가 없을 수 있기 때문이다. 로컬 옵트인 후크(`dev/hooks/pre-commit`)와 같은 규칙, 표준 라이브러리만.
종료 코드: 0 통과 · 1 코드만 바뀜 · 2 git 을 못 돌림.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence, Tuple

DOC = "진행상황.md"
CODE_PREFIXES = ("aoi_capacity/", "scripts/", "dev/tests/", "dev/tools/", "dev/hooks/")
CODE_FILES = ("main.py", "requirements.txt")


def is_code(path: str) -> bool:
    p = path.replace("\\", "/")
    return p in CODE_FILES or p.startswith(CODE_PREFIXES)


def check(changed: Iterable[str]) -> Tuple[bool, str]:
    """(통과 여부, 이유). 순수 함수 — 테스트가 직접 부른다."""
    files = [f for f in changed if f]
    code = sorted(f for f in files if is_code(f))
    if not code:
        return True, "코드 변경 없음 — 문서만 바뀐 변경은 진행상황.md 없이 통과"
    if DOC in files:
        return True, f"코드 {len(code)}개 변경 + {DOC} 동반"
    shown = ", ".join(code[:8]) + (" …" if len(code) > 8 else "")
    return False, (f"코드가 바뀌었는데 {DOC} 가 함께 바뀌지 않았습니다: {shown}\n"
                   f"  '작업 기록' 맨 위에 한 줄, 달라진 항목(지금 상태 · 확정된 결정 · 다음 할 일)을 고쳐 같이 넣어 주세요(CLAUDE.md '커밋').")


def changed_files(repo: Path, base: str, head: str) -> Sequence[str]:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-c", "core.quotepath=false", "-C", str(repo), *args],
                              capture_output=True, text=True, check=True, timeout=60).stdout
    mb = git("merge-base", base, head).strip()
    out = git("diff", "--name-only", mb, head)
    return [l.strip() for l in out.splitlines() if l.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True, help="기준 rev(PR 의 base sha 또는 브랜치)")
    ap.add_argument("--head", default="HEAD", help="검사할 rev(PR 의 head sha)")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    a = ap.parse_args(argv)
    try:
        files = changed_files(Path(a.repo), a.base, a.head)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"git 을 돌리지 못했습니다: {e}", file=sys.stderr)
        return 2
    ok, why = check(files)
    print(("통과: " if ok else "실패: ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
