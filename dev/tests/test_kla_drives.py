"""끊긴 KLA 드라이브 다시 연결(10/22) — 가짜 Windows 로 본다: 비밀번호 파일이 없으면 시도하지 않고 · 있으면 기억된 원격 주소로만 연결하고 ·
범위 밖 KLA 행은 연결도 시도하지 않고 · 비밀번호는 로그에 남지 않는다."""
from __future__ import annotations

import os

import pytest

from aoi_capacity import devices, kla_drives
from conftest import make_cfg


@pytest.fixture
def fake_win(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(kla_drives, "IS_WINDOWS", lambda: True)
    monkeypatch.setattr(kla_drives, "REMOTE_OF", lambda letter: r"\\10.0.0.5\kla" if letter == "Z" else None)

    def connect(letter, remote, user, pw):
        calls.append((letter, remote, user, pw))
        return True, ""
    monkeypatch.setattr(kla_drives, "CONNECT", connect)
    monkeypatch.setattr(kla_drives.paths, "data_root", lambda: tmp_path)
    return calls, tmp_path


def test_no_password_file_means_no_attempt(fake_win):
    calls, _ = fake_win
    assert kla_drives.reconnect("Z:\\", {}) == (False, [])
    assert calls == []


def test_single_line_is_password_for_current_account(fake_win):
    calls, root = fake_win
    (root / kla_drives.FILE_NAME).write_text("s3cret\n", encoding="utf-8")
    ok, msgs = kla_drives.reconnect("Z:\\", {})
    assert ok and calls == [("Z", r"\\10.0.0.5\kla", None, "s3cret")]
    assert all("s3cret" not in m for m in msgs)


def test_two_lines_are_account_then_password_and_output_dir_wins(fake_win, tmp_path_factory):
    calls, root = fake_win
    out = tmp_path_factory.mktemp("out")
    (root / kla_drives.FILE_NAME).write_text("data-pw", encoding="utf-8")
    (out / kla_drives.FILE_NAME).write_text("kla\\user\nout-pw", encoding="utf-8")
    kla_drives.reconnect("Z:\\", {"output_dir": str(out)})
    assert calls == [("Z", r"\\10.0.0.5\kla", "kla\\user", "out-pw")]


def test_unknown_remote_is_not_invented(fake_win):
    calls, root = fake_win
    (root / kla_drives.FILE_NAME).write_text("pw", encoding="utf-8")
    ok, msgs = kla_drives.reconnect("W:\\", {})
    assert not ok and calls == [] and msgs and "pw" not in "".join(msgs)


def test_not_windows_or_not_drive_letter_does_nothing(fake_win, monkeypatch):
    calls, root = fake_win
    (root / kla_drives.FILE_NAME).write_text("pw", encoding="utf-8")
    assert kla_drives.reconnect(r"\\srv\share", {}) == (False, [])
    monkeypatch.setattr(kla_drives, "IS_WINDOWS", lambda: False)
    assert kla_drives.reconnect("Z:\\", {}) == (False, [])
    assert calls == []


def test_out_of_scope_kla_row_never_reconnects(fake_win, tmp_path):
    calls, root = fake_win
    (root / kla_drives.FILE_NAME).write_text("pw", encoding="utf-8")
    cfg = make_cfg(tmp_path, tmp_path / "d.csv", scope_devices=["K2"])
    rows = [{"name": "K1", "root": "Z:\\", "sub": "", "on": True, "memo": "KLA"}]
    devs = devices.devices_from_rows(rows, cfg)
    assert devs == [] and calls == []
