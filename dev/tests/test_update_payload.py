"""업데이트 페이로드 계약 — 스테이징 최상위는 **허용 목록과 정확히 같다**(저장소 루트에 무엇이 있든), 필수 파일이 담기고 개발 전용은 빠진다."""
from __future__ import annotations

from pathlib import Path

from aoi_capacity.utils import updater

_ROOT = Path(__file__).resolve().parents[2]
_ALLOW = {"main.py", "requirements.txt", "aoi_capacity", "scripts", "VERSION"}


def test_allow_list_is_exactly_the_intended_payload():
    assert set(updater.STAGED_TOP_LEVEL) == _ALLOW
    assert not hasattr(updater, "_UPDATE_SKIP_TOP"), "거부 목록으로 되돌아가면 저장소 루트의 잡파일이 다시 배포된다(S01)"


def test_keep_only_names_exist_in_repo():
    for top, names in updater._UPDATE_KEEP_ONLY.items():
        for n in names:
            assert (_ROOT / top / n).exists(), f"{top}/{n} 가 저장소에 없다 — 사용자에게 안 간다"


def test_required_in_staging_exist_in_repo():
    for rel in updater._REQUIRED_IN_STAGING:
        if rel != "VERSION":
            assert (_ROOT / rel).is_file(), rel


def test_staging_real_tree_passes_verification_and_top_level_equals_allow_list(tmp_path):
    staging = tmp_path / "stage"
    updater._stage_tree(_ROOT, staging, lambda *a: None)
    updater._write_version_to(staging, "sha", "branch", "repo")
    assert updater._verify_staged(staging) == ""
    assert {p.name for p in staging.iterdir()} == _ALLOW
    for gone in ("dev", "docs", ".git", "CLAUDE.md", "README.md", "pytest.ini", "scripts/build.py",
                 "scripts/internal", ".claude", "진행상황.md", ".graphifyignore"):
        assert not (staging / gone).exists(), gone
    assert not list(staging.glob("*.png"))
    assert (staging / "scripts" / "run_aoi.bat").is_file() and (staging / "scripts" / "collect_sample.py").is_file()
    assert not list(staging.rglob("__pycache__"))
    assert not list(staging.rglob("*.pyc"))
    assert not list(staging.rglob("*.log")) and not list(staging.rglob("*.bak"))


def _fake_repo(root: Path) -> Path:
    """허용 목록 항목 + 루트 잡파일(스크린샷·문서·숨김 설정·임의 신규 파일·캐시)."""
    for rel, body in {
        "main.py": "x", "requirements.txt": "PyQt6\n",
        "aoi_capacity/__init__.py": "", "aoi_capacity/ui/main_window.py": "x",
        "aoi_capacity/ui/assets/template.html": "__DATA__", "aoi_capacity/ui/style.qss": "",
        "aoi_capacity/utils/updater.py": "x", "aoi_capacity/assets/devices.default.csv": "n\n",
        "aoi_capacity/__pycache__/m.cpython-311.pyc": "junk", "aoi_capacity/stray.log": "junk", "aoi_capacity/old.bak": "junk",
        "scripts/run_aoi.bat": "x", "scripts/collect_sample.py": "x", "scripts/build.py": "dev", "scripts/internal/tool.py": "dev",
        "진행상황.md": "68KB", "v6home.png": "664KB", "v6cmp.png": "x", ".graphifyignore": "x", "CLAUDE.md": "x", "README.md": "x",
        "pytest.ini": "x", ".gitignore": "x", "random_new_root_file.txt": "x", "notes.docx": "x",
        "dev/tests/test_a.py": "x", "docs/design/a.html": "x", ".github/workflows/tests.yml": "x",
        ".claude/settings.json": "x", ".pytest_cache/v/x": "x", "build/out.bin": "x", "dist/a.zip": "x",
    }.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root


def test_staging_top_level_equals_allow_list_even_with_junk_in_source_root(tmp_path):
    src = _fake_repo(tmp_path / "src")
    staging = tmp_path / "stage"
    updater._stage_tree(src, staging, lambda *a: None)
    updater._write_version_to(staging, "sha", "branch", "repo")
    assert {p.name for p in staging.iterdir()} == _ALLOW
    assert sorted(p.name for p in (staging / "scripts").iterdir()) == ["collect_sample.py", "run_aoi.bat"]
    names = {p.relative_to(staging).as_posix() for p in staging.rglob("*") if p.is_file()}
    assert not any(n.endswith((".pyc", ".log", ".bak")) for n in names), names
    assert "aoi_capacity/ui/assets/template.html" in names


def test_verify_rejects_unexpected_top_level_entry(tmp_path):
    src = _fake_repo(tmp_path / "src")
    staging = tmp_path / "stage"
    updater._stage_tree(src, staging, lambda *a: None)
    updater._write_version_to(staging, "sha", "branch", "repo")
    (staging / "aoi_capacity" / "ui" / "style.qss").write_text("QWidget{color:$fg}", encoding="utf-8")
    (staging / "진행상황.md").write_text("x", encoding="utf-8")
    reason = updater._verify_staged(staging)
    assert "진행상황.md" in reason
