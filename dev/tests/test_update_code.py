"""최신 코드 받기 도구(scripts/update_code.py) 계약.

- 브랜치 이름이 **파일 맨 위**에 있어야 한다(사용자가 직접 고치는 값).
- zip 방식: 바뀐 파일만 덮어쓰고, 원본을 백업하며, 온전하지 않은 내용은 적용하지 않는다.
- git 방식: 커밋하지 않은 변경이 있으면 멈춘다(내 작업을 버리지 않는다).
- 테스트는 네트워크도 git 도 실제로 부르지 않는다.
"""
from __future__ import annotations

import importlib.util
import io
import re
import sys
import zipfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "scripts" / "update_code.py"
_spec = importlib.util.spec_from_file_location("update_code", _SRC)
upd = importlib.util.module_from_spec(_spec)
sys.modules["update_code"] = upd
_spec.loader.exec_module(upd)


def test_branch_is_declared_at_the_top_of_the_file():
    head = _SRC.read_text(encoding="utf-8").split("\n")[:30]
    assert any(re.match(r'^BRANCH = ".+"', l) for l in head), "브랜치는 파일 맨 위에 있어야 한다"
    assert any(re.match(r'^REPO = ".+/.+"', l) for l in head)
    assert upd.BRANCH and upd.REPO.count("/") == 1


def _make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for rel, body in files.items():
            z.writestr(f"AOI-capacity-branch/{rel}", body)
    return buf.getvalue()


def _full(extra=None):
    files = {r: f"# {r}\n" for r in upd.REQUIRED}
    files.update(extra or {})
    return files


@pytest.fixture
def local(tmp_path):
    """이미 풀려 있는 폴더 — 한 파일은 옛 내용, 한 파일은 이 폴더에만 있다."""
    root = tmp_path / "AOI-capacity-branch"
    (root / "aoi_capacity" / "ui" / "assets").mkdir(parents=True)
    (root / "main.py").write_text("# 옛 내용\n", encoding="utf-8")
    (root / "requirements.txt").write_text("# requirements.txt\n", encoding="utf-8")
    (root / "aoi_capacity" / "collect.py").write_text("# aoi_capacity/collect.py\n", encoding="utf-8")
    (root / "aoi_capacity" / "ui" / "assets" / "template.html").write_text("# aoi_capacity/ui/assets/template.html\n",
                                                                           encoding="utf-8")
    (root / "내메모.txt").write_text("지우면 안 됨", encoding="utf-8")
    return root


def _patch_download(monkeypatch, payload: bytes):
    def fake(url, dest, timeout=120.0):
        Path(dest).write_bytes(payload)
    monkeypatch.setattr(upd, "download", fake)


def test_zip_update_overwrites_changed_keeps_backup_and_never_deletes(monkeypatch, local, capsys):
    _patch_download(monkeypatch, _make_zip(_full({"새파일.py": "new\n"})))
    assert upd.zip_update(local, "any", check_only=False) == 0
    assert (local / "main.py").read_text(encoding="utf-8") == "# main.py\n"     # 갱신됨
    assert (local / "새파일.py").is_file()                                       # 추가됨
    assert (local / "내메모.txt").read_text(encoding="utf-8") == "지우면 안 됨"   # ★ 내 파일은 지우지 않는다
    backup = next(p for p in local.iterdir() if p.name.startswith("_backup_"))
    assert (backup / "main.py").read_text(encoding="utf-8") == "# 옛 내용\n"      # 원본이 남는다


def test_zip_update_check_only_changes_nothing(monkeypatch, local):
    _patch_download(monkeypatch, _make_zip(_full({"새파일.py": "new\n"})))
    assert upd.zip_update(local, "any", check_only=True) == 0
    assert (local / "main.py").read_text(encoding="utf-8") == "# 옛 내용\n"
    assert not (local / "새파일.py").exists()
    assert not [p for p in local.iterdir() if p.name.startswith("_backup_")]


def test_zip_update_refuses_incomplete_tree(monkeypatch, local):
    _patch_download(monkeypatch, _make_zip({"main.py": "x\n"}))      # 필수 파일이 빠졌다
    assert upd.zip_update(local, "any", check_only=False) == 2
    assert (local / "main.py").read_text(encoding="utf-8") == "# 옛 내용\n"


def test_zip_update_says_nothing_to_do_when_identical(monkeypatch, local):
    (local / "main.py").write_text("# main.py\n", encoding="utf-8")
    _patch_download(monkeypatch, _make_zip(_full()))
    assert upd.zip_update(local, "any", check_only=False) == 0
    assert not [p for p in local.iterdir() if p.name.startswith("_backup_")]


def test_git_update_stops_when_working_tree_is_dirty(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_git(root, *args):
        calls.append(args)
        if args[:1] == ("--version",):
            return True, "git version 2.0"
        if args[:2] == ("status", "--porcelain"):
            return True, " M aoi_capacity/collect.py"
        return True, ""

    monkeypatch.setattr(upd, "git", fake_git)
    assert upd.git_update(tmp_path, "b", check_only=False) == 1
    assert "커밋하지 않은 변경" in capsys.readouterr().out
    assert not any(a[:1] == ("merge",) for a in calls)      # 아무것도 적용하지 않았다


def test_git_update_reports_already_up_to_date(monkeypatch, tmp_path, capsys):
    def fake_git(root, *args):
        if args[:1] == ("--version",):
            return True, "git version 2.0"
        if args[:2] == ("status", "--porcelain"):
            return True, ""
        if args[:1] == ("fetch",):
            return True, ""
        if args[:1] == ("log",):
            return True, ""
        if args[:2] == ("rev-parse", "--short"):
            return True, "abc1234"
        return True, ""

    monkeypatch.setattr(upd, "git", fake_git)
    assert upd.git_update(tmp_path, "b", check_only=False) == 0
    assert "이미 최신" in capsys.readouterr().out


def test_main_uses_zip_when_folder_is_not_a_git_checkout(monkeypatch, tmp_path):
    used = {}
    monkeypatch.setattr(upd, "repo_root", lambda: tmp_path)
    def fake_zip(root, branch, check):
        used["zip"] = branch
        return 0

    monkeypatch.setattr(upd, "zip_update", fake_zip)
    monkeypatch.setattr(upd, "git_update", lambda *a: pytest.fail("git 폴더가 아닌데 git 을 썼다"))
    assert upd.main([]) == 0
    assert used["zip"] == upd.BRANCH
