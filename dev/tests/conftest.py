"""테스트 공통 픽스처.

- 모든 테스트는 임시 HOME/LOCALAPPDATA 아래에서 돈다 → 개발자의 실제 설정·캐시를 건드리지 않는다.
  (`ntpath.expanduser` 는 HOME 이 아니라 USERPROFILE 을 보므로 둘 다 바꾼다.)
- 환경변수 AOI_DATA_HOME / AOI_APP_HOME 은 지운다(테스트가 명시적으로 넣을 때만).
- Qt 가 필요한 테스트는 `qapp` 픽스처를 쓰며 conftest 가 `ui` 마커를 자동으로 붙인다.
  PyQt6 가 없는 환경에서는 그 테스트만 skip 된다.
- MainWindow 의 시작 부수효과(업데이트 확인 스레드)는 클래스 수준에서 막는다 — 테스트가
  네트워크를 타거나 시트 팝업의 중첩 이벤트 루프에 갇히는 사고 방지.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("AOI_NO_WEBENGINE", "1")

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def set_home(monkeypatch, path: Path) -> None:
    monkeypatch.setenv("HOME", str(path))
    monkeypatch.setenv("USERPROFILE", str(path))
    monkeypatch.setenv("LOCALAPPDATA", str(path / "AppData" / "Local"))


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """모든 테스트를 임시 홈에서 돌린다. 반환값은 그 홈 경로."""
    home = tmp_path / "home"
    home.mkdir()
    set_home(monkeypatch, home)
    monkeypatch.delenv("AOI_DATA_HOME", raising=False)
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    try:
        from aoi_capacity.utils import paths, prefs
        paths._MADE_DIRS.clear()
        prefs._cached = None
    except Exception:  # noqa: BLE001 - 아직 모듈이 없을 수 있다(M0 단계)
        pass
    return home


@pytest.fixture(autouse=True)
def _no_startup_side_effects(monkeypatch):
    try:
        from aoi_capacity.ui import main_window as mw
    except Exception:  # noqa: BLE001
        return

    def _suppressed(self, *_a, **_k):
        calls = getattr(self, "_suppressed_startup_calls", [])
        calls.append("_check_for_update_async")
        self._suppressed_startup_calls = calls

    monkeypatch.setattr(mw.MainWindow, "_check_for_update_async", _suppressed)


@pytest.fixture(scope="session")
def _qt_app():
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def qapp(_qt_app):
    return _qt_app


@pytest.fixture
def styled_qapp(_qt_app):
    from aoi_capacity.ui import theme
    theme.apply_to_app(_qt_app)
    return _qt_app


def pytest_collection_modifyitems(config, items):
    for item in items:
        if {"qapp", "styled_qapp"} & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.ui)


# ── 가짜 NAS 트리 ───────────────────────────────────────────────────────
REPORT_NAME = "2D@R2-GA285AAB_0859840PD-0A_6321_KLK-3D_26-Sep-13_(05.32.23)_BatchReport.htm"
REPORT_HTML = """<html><body>
<table><tr><td>Batch Start:</td><td>13-Sep-26 05:25:14 PM</td></tr><tr><td>Batch End:</td><td>13-Sep-26 05:32:21 PM</td></tr>
<tr><td>Batch Time:</td><td>00:07:07</td></tr><tr><td>Recipe:</td><td>Default</td></tr></table>
<table><tr><th>Lot</th><th>Wafer ID</th><th>Faults</th><th>Scanned Dice</th><th>Bad Dice</th><th>Good Dice</th><th>Yield</th><th>Pass/Fail</th></tr>
<tr><td>KLK-3D</td><td>K625407-01B0</td><td>0</td><td>45</td><td>0</td><td>45</td><td>100%</td><td>Pass</td></tr>
<tr><td>KLK-3D</td><td>K625407-99Z9</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0%</td><td>Failed to read wafer id. Reading error = . Aborted.</td></tr>
<tr><td>LoadPort A</td><td>Slot 3</td><td></td><td></td><td></td><td></td><td></td><td>Skipped.</td></tr></table></body></html>"""
WAFER_INI = """[Robot]
Rotation=0
[Recipe]
Name=Default
[AutoCycleInfo]
Machine=EAGLETP_106783
Operator=MAINT
WaferStartTime=13-Sep-26 05:31:04 PM
BatchStartTime=09/13/2026 17:25:14
OCRID=
FillID=K625407-01B0
CarrierID=125342033
UseLot=KLK-3D
UseWaferID=K625407-01B0
WaferEndTime=13-Sep-26 05:32:02 PM
[BatchInfo]
GlobalLotId=KLK-3D
"""


def make_device(root: Path, name: str, report_name: str = REPORT_NAME, mtime: float | None = None) -> Path:
    """root/name 아래에 Report/<report> 와 정확 경로의 WaferInfo.ini 를 만든다."""
    dev = root / name
    (dev / "Report").mkdir(parents=True, exist_ok=True)
    rep = dev / "Report" / report_name
    rep.write_text(REPORT_HTML, encoding="utf-8")
    if mtime is not None:
        os.utime(rep, (mtime, mtime))
    ini_dir = dev / "Scanresult" / "2D@R2-GA285AAB_0859840PD-0A" / "6321" / "KLK-3D" / "K625407-01B0"
    ini_dir.mkdir(parents=True, exist_ok=True)
    (ini_dir / "WaferInfo.ini").write_text(WAFER_INI, encoding="utf-8")
    return dev


@pytest.fixture
def fake_nas(tmp_path):
    """tmp/nas/X 아래 AOI-9, AOI-10 과 tmp/nas/M-AOI-8(루트가 장비)을 만든다. 반환: (nas_root, devices.csv 경로)."""
    nas = tmp_path / "nas"
    make_device(nas / "X", "AOI-9")
    make_device(nas / "X", "AOI-10")
    make_device(nas, "M-AOI-8")
    csv_path = tmp_path / "devices.csv"
    csv_path.write_text(
        "장비명,NAS경로,폴더,사용,메모\n"
        f"9호기,{nas / 'X'},AOI-9,Y,\n"
        f"엑스전체,{nas / 'X'},*,Y,\n"
        f"8호기,{nas / 'M-AOI-8'},,Y,루트가 장비\n"
        f"꺼둠,{nas / 'X'},AOI-10,N,\n"
        f"없음,{nas / 'none'},AOI-1,Y,접근불가\n",
        encoding="utf-8-sig")
    return nas, csv_path


def make_cfg(tmp_path, csv_path, **over):
    from aoi_capacity import collect
    import copy
    cfg = copy.deepcopy(collect.DEFAULT_CONFIG)
    out = tmp_path / "out"
    # 엔진 자체를 보는 테스트는 "수집 범위 제한 없음"을 명시한다.
    # 기본값(AOI-25 만)은 dev/tests/test_scope_isolation.py 가 따로 검증한다.
    cfg.update({"devices_csv": str(csv_path), "cache_file": str(out / "aoi_cache.json"),
                "output_dir": str(out), "backfill_days": 3650, "retention_days": 3650,
                "scope_devices": ["*"]})
    cfg.update(over)
    return cfg
