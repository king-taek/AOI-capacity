"""업데이트 페이로드 계약 — 실제 저장소 트리를 스테이징해 필수 파일이 담기고 개발 전용은 빠지는지."""
from __future__ import annotations

from pathlib import Path

from aoi_capacity.utils import updater

_ROOT = Path(__file__).resolve().parents[2]


def test_keep_only_names_exist_in_repo():
    for top, names in updater._UPDATE_KEEP_ONLY.items():
        for n in names:
            assert (_ROOT / top / n).exists(), f"{top}/{n} 가 저장소에 없다 — 사용자에게 안 간다"


def test_required_in_staging_exist_in_repo():
    for rel in updater._REQUIRED_IN_STAGING:
        if rel != "VERSION":
            assert (_ROOT / rel).is_file(), rel


def test_staging_real_tree_passes_verification(tmp_path):
    staging = tmp_path / "stage"
    updater._stage_tree(_ROOT, staging, lambda *a: None)
    updater._write_version_to(staging, "sha", "branch", "repo")
    assert updater._verify_staged(staging) == ""
    for gone in ("dev", "docs", ".git", "CLAUDE.md", "README.md", "pytest.ini", "scripts/build.py",
                 "scripts/internal", ".claude"):
        assert not (staging / gone).exists(), gone
    assert (staging / "scripts" / "run_aoi.bat").is_file()
    assert not list(staging.rglob("__pycache__"))
    assert not list(staging.rglob("*.pyc"))
