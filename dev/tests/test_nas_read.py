"""NAS 읽기 경로(9/30) — ① `nas_guard.read_bytes/read_text` 를 os.open + 한 번 읽기로 ② 전체 나열을 대량 조회(`FULL_LISTER`)로.

둘 다 **결과는 예전과 같아야** 한다: 바이트·문자열이 `open().read()` 와 같고, 고르는 Report 가 scandir 로 나열했을 때와 같다.
9/29 현장 실측(Wi-Fi+VPN): INI 읽기 167 → 118ms, 전체 나열 scandir 대비 p50 3.7배."""
from __future__ import annotations

import ast
import fnmatch
import json
import os
from pathlib import Path

import pytest

from aoi_capacity import collect, nas_guard
from conftest import make_cfg


# ── ① 읽기 ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("data", [b"", b"x", b"[A]\r\nk=v\r\n", b"a" * 65535, b"a" * 65536, b"a" * 65537,
                                  bytes(range(256)) * 12000, "﻿한글\r\n줄\r끝".encode("utf-8")])
def test_read_bytes_matches_builtin_open(tmp_path, data):
    p = tmp_path / "f.bin"
    p.write_bytes(data)
    assert nas_guard.read_bytes(p) == open(p, "rb").read()


@pytest.mark.parametrize("data", [b"[A]\r\nk=v\r\n", b"a\rb\r\nc\nd", "﻿BOM\r\n".encode("utf-8"), b"bad \xff\xfe utf8\r\n",
                                  ("가" * 40000 + "\r\n").encode("utf-8"), b""])
@pytest.mark.parametrize("encoding,errors", [("utf-8", "replace"), ("utf-8", "strict"), ("cp949", "replace")])
def test_read_text_matches_builtin_open(tmp_path, data, encoding, errors):
    p = tmp_path / "f.txt"
    p.write_bytes(data)
    try:
        want = open(p, "r", encoding=encoding, errors=errors).read()
    except UnicodeDecodeError:
        with pytest.raises(UnicodeDecodeError):
            nas_guard.read_text(p, encoding, errors)
        return
    assert nas_guard.read_text(p, encoding, errors) == want


def test_small_file_is_read_with_one_read_call(tmp_path, monkeypatch):
    """요점: EOF 확인용 두 번째 읽기가 없다(SMB 왕복 하나)."""
    p = tmp_path / "WaferInfo.ini"
    p.write_bytes(b"[AutoCycleInfo]\r\nWaferEndTime=13-Sep-26 05:32:02 PM\r\n" * 20)
    calls = []
    real = os.read

    def spy(fd, n):
        calls.append(n)
        return real(fd, n)

    monkeypatch.setattr(os, "read", spy)
    assert nas_guard.read_bytes(p) == p.read_bytes()
    assert len(calls) == 1


def test_file_growing_while_read_is_not_truncated(tmp_path, monkeypatch):
    p = tmp_path / "grow.txt"
    p.write_bytes(b"a" * 10)
    real = os.read
    grown = []

    def spy(fd, n):
        if not grown:
            grown.append(1)
            with open(p, "ab") as f:                      # 테스트 파일(로컬)에만 덧붙인다
                f.write(b"b" * 100000)
        return real(fd, n)

    monkeypatch.setattr(os, "read", spy)
    assert nas_guard.read_bytes(p) == b"a" * 10 + b"b" * 100000


def test_missing_and_directory_raise_the_same_kinds_as_before(tmp_path):
    with pytest.raises(FileNotFoundError):
        nas_guard.read_bytes(tmp_path / "없음.ini")
    with pytest.raises(FileNotFoundError):
        nas_guard.read_text(tmp_path / "a" / "b" / "WaferInfo.ini")
    with pytest.raises((IsADirectoryError, PermissionError)):
        nas_guard.read_bytes(tmp_path)


def test_ini_memo_classifies_missing_the_same(tmp_path):
    memo = collect._IniMemo()
    assert memo.get(str(tmp_path / "x" / "WaferInfo.ini"))[0] == "missing"
    (tmp_path / "d").mkdir()
    assert memo.get(str(tmp_path / "d"))[0] in ("missing", "error")      # 폴더: 예전 open() 과 같은 분류


def test_os_open_in_nas_guard_is_read_only():
    """정적 가드: nas_guard 의 os.open 은 읽기 전용 플래그 상수만 쓴다."""
    src = Path(nas_guard.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    opens = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "open" and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"]
    assert opens, "os.open 을 찾지 못했다"
    for n in opens:
        assert len(n.args) == 2 and isinstance(n.args[1], ast.Name) and n.args[1].id == "_READ_FLAGS"
    bad = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    assert nas_guard._READ_FLAGS & bad == 0


# ── ② 전체 나열(대량 조회) ─────────────────────────────────────────────────
def _cache(cfg):
    return json.loads(open(cfg["cache_file"], encoding="utf-8").read())


def _picked(cfg):
    return sorted((k, round(v["mtime"])) for k, v in _cache(cfg)["reports"].items())


def test_full_listing_uses_the_bulk_lister_and_picks_the_same_reports(tmp_path, fake_nas, monkeypatch):
    _nas, csv_path = fake_nas
    calls = []

    def bulk(folder, pattern):
        calls.append((folder, pattern))
        return [e for e in os.scandir(folder) if fnmatch.fnmatch(e.name, pattern)]

    monkeypatch.setattr(collect, "FULL_LISTER", bulk)
    cfg = make_cfg(tmp_path / "bulk", csv_path)
    rows_b, _m, _e = collect.collect(cfg)
    assert calls and all(p == "*" for _f, p in calls)
    monkeypatch.setattr(collect, "FULL_LISTER", None)
    ref = make_cfg(tmp_path / "scan", csv_path)
    rows_s, _m, _e = collect.collect(ref)
    assert _picked(cfg) == _picked(ref)
    assert [json.dumps(r, sort_keys=True) for r in rows_b] == [json.dumps(r, sort_keys=True) for r in rows_s]


def test_bulk_listing_failure_falls_back_to_scandir(tmp_path, fake_nas, monkeypatch):
    _nas, csv_path = fake_nas

    def broken(folder, pattern):
        raise OSError("대량 조회 거부")

    monkeypatch.setattr(collect, "FULL_LISTER", broken)
    cfg = make_cfg(tmp_path / "b", csv_path)
    rows, dev_meta, errors = collect.collect(cfg)
    monkeypatch.setattr(collect, "FULL_LISTER", None)
    ref = make_cfg(tmp_path / "r", csv_path)
    rows_r, _m, _e = collect.collect(ref)
    assert _picked(cfg) == _picked(ref) and len(rows) == len(rows_r) and not errors
    assert not [d for d in dev_meta if d.get("error")]
