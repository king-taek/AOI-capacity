"""dev/tools/progress_doc_check.py 가드(S14) — 코드+문서 통과 · 코드만 실패 · 문서만 통과, 그리고 실제 git 범위(merge-base → head)로 한 번."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "dev" / "tools" / "progress_doc_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("progress_doc_check", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("changed,ok", [
    (["aoi_capacity/collect.py", "진행상황.md"], True),
    (["aoi_capacity/collect.py"], False),
    (["scripts/build.py", "README.md"], False),
    (["dev/tests/test_x.py"], False),
    (["main.py"], False),
    (["README.md", "docs/config.example.json", "CLAUDE.md"], True),
    (["dev/samples/README.md", "archive/README.md"], True),
    ([], True),
    (["aoi_capacity\\ui\\theme.py", "진행상황.md"], True),      # Windows 구분자도 코드로 본다
])
def test_check_requires_the_doc_only_when_code_changed(changed, ok):
    mod = _load()
    got, why = mod.check(changed)
    assert got is ok, why
    if not ok:
        assert "진행상황.md" in why


def test_code_paths_match_the_opt_in_hook():
    """로컬 후크(dev/hooks/pre-commit)와 CI 검사가 같은 코드 경로를 본다 — 한쪽만 통과하는 변경이 없게."""
    mod = _load()
    hook = (ROOT / "dev" / "hooks" / "pre-commit").read_text(encoding="utf-8")
    for top in ("aoi_capacity", "scripts", "main\\.py", "requirements\\.txt"):
        assert top in hook
    assert all(mod.is_code(p) for p in ("aoi_capacity/x.py", "scripts/x.bat", "main.py", "requirements.txt", "dev/tests/t.py", "dev/tools/t.py"))
    assert not any(mod.is_code(p) for p in ("README.md", "CLAUDE.md", "docs/x.md", "archive/x", "dev/samples/x.gz", ".github/workflows/tests.yml"))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, timeout=30,
                          env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x",
                               "HOME": str(repo), "PATH": "/usr/bin:/bin:/usr/local/bin"}).stdout


def test_main_looks_at_the_merge_base_range_not_only_the_last_commit(tmp_path):
    """두 커밋짜리 브랜치: 첫 커밋이 코드, 둘째 커밋이 문서 — 마지막 커밋만 보면 '코드 없음' 으로 잘못 통과하고, 범위로 보면 동반으로 통과.
    코드만 있는 브랜치는 실패(exit 1)."""
    if not shutil.which("git"):
        pytest.skip("git 없음")
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("a", encoding="utf-8")
    _git(repo, "add", "."), _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "checkout", "-q", "-b", "feat")
    (repo / "aoi_capacity").mkdir()
    (repo / "aoi_capacity" / "x.py").write_text("x", encoding="utf-8")
    _git(repo, "add", "."), _git(repo, "commit", "-q", "-m", "code")
    mod = _load()
    assert mod.main(["--base", "main", "--head", "HEAD", "--repo", str(repo)]) == 1          # 코드만
    (repo / "진행상황.md").write_text("doc", encoding="utf-8")
    _git(repo, "add", "."), _git(repo, "commit", "-q", "-m", "doc")
    assert mod.main(["--base", "main", "--head", "HEAD", "--repo", str(repo)]) == 0          # 범위 안에 동반
    _git(repo, "checkout", "-q", "main"), _git(repo, "checkout", "-q", "-b", "docs-only")
    (repo / "README.md").write_text("b", encoding="utf-8")
    _git(repo, "add", "."), _git(repo, "commit", "-q", "-m", "docs")
    assert mod.main(["--base", "main", "--head", "HEAD", "--repo", str(repo)]) == 0          # 문서만
    assert mod.main(["--base", "no-such-rev", "--head", "HEAD", "--repo", str(repo)]) == 2   # git 실패는 2
