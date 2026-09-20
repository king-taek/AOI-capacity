"""archive/ 보관물 가드(D62) — 지우지 않고 옮긴 파일들이 **원본 그대로**인지.

- `archive/SHA256SUMS` 의 모든 항목을 다시 계산해 대조한다(`.gz` 는 압축을 푼 내용의 sha256).
- archive/ 안의 파일은 README·SHA256SUMS 를 빼고 전부 목록에 있어야 한다(적지 않고 넣은 보관물 없음).
- 옛 위치에 파일이 남아 있지 않다(옮긴 것이지 복사한 것이 아니다).
네트워크·쓰기 없음. 표준 라이브러리만.
"""
from __future__ import annotations

import gzip
import hashlib
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "archive"
SUMS = ARCHIVE / "SHA256SUMS"
OLD_LOCATIONS = [
    "v6cmp.png", "v6home.png", "v6set.png", "v6trend.png",
    "docs/screenshots", "docs/aoi_collector_demo.html",
    "docs/design/dashboard-redesign/PROMPT.md", "docs/design/dashboard-redesign/PROMPT_extract-script.md",
    "docs/design/dashboard-redesign/patch", "docs/design/dashboard-redesign/app/Err-Popup-A.dc.html",
    "docs/design/dashboard-redesign/app/AOI-4 해결 제안.dc.html", "docs/design/dashboard-redesign/app/aoi-recovery.json",
    "dev/samples/AOI_capacity_2026-09-16_3일치.html", "dev/samples/AOI_capacity_2026-09-17_30대.html",
]


def entries() -> list[tuple[str, str]]:
    out = []
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        sha, rel = line.split("  ", 1)
        out.append((sha, rel))
    return out


def content_sha(p: Path) -> str:
    raw = p.read_bytes()
    if p.suffix == ".gz":
        raw = gzip.decompress(raw)
    return hashlib.sha256(raw).hexdigest()


def test_manifest_has_entries_and_no_duplicates():
    e = entries()
    assert len(e) >= 16
    assert len({rel for _, rel in e}) == len(e)


@pytest.mark.parametrize("sha,rel", entries(), ids=[rel for _, rel in entries()])
def test_every_archived_file_matches_its_original_fingerprint(sha, rel):
    p = ROOT / rel
    assert p.is_file(), f"{rel} 이 없다 — 보관물은 지우지 않는다"
    assert content_sha(p) == sha, f"{rel} 의 내용이 원본과 다르다"


def test_everything_under_archive_is_listed():
    listed = {rel for _, rel in entries()}
    files = {p.relative_to(ROOT).as_posix() for p in ARCHIVE.rglob("*") if p.is_file()}
    files -= {"archive/README.md", "archive/SHA256SUMS"}
    assert files <= listed, f"SHA256SUMS 에 없는 보관물: {sorted(files - listed)}"


def test_old_locations_are_empty():
    for rel in OLD_LOCATIONS:
        assert not (ROOT / rel).exists(), f"{rel} 이 옛 자리에 아직 있다(옮긴 것이지 복사한 것이 아니다)"


def test_archive_is_not_in_the_update_payload():
    from aoi_capacity.utils import updater

    assert "archive" not in set(updater.STAGED_TOP_LEVEL)


def test_no_compiled_python_is_tracked():
    """S09: 옛 모듈의 .pyc 가 추적되고 있었다(`__pycache__/aoi_collect.cpython-311.pyc`). .gitignore 는 이미 막고 있었지만 추적 파일은 무시 규칙보다 세다."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", "*.pyc", "__pycache__"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pytest.skip("git 을 쓸 수 없는 환경")
    if out.returncode != 0:
        pytest.skip("git 저장소가 아닌 체크아웃(zip)")
    assert out.stdout.strip() == "", out.stdout
