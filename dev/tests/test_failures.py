"""실패 로그 수집(10/20, `aoi_capacity/failures.py`) — app.log · 캐시 · 장비 확인에서 실패를 모아 로컬 zip 한 장으로.

- 기간 밖 기록은 빼고, `[수집 상세]` 의 오류 줄(KLA 읽기 실패의 유일한 기록)과 `[건너뜀]` 이유를 읽는다.
- 건너뛴 장비(수집 범위 안인데 드라이브가 안 열림)는 장비 확인 결과에서 '접근 못 함' 으로 남는다.
- 실패한 파일은 허용 장비의 장비 폴더 아래 경로만 읽고, 내용을 zip 에 담는다. 범위 밖 · 장비 밖 경로는 읽지 않는다.
- 저장 위치가 NAS 아래면 시작 전에 거부한다.
"""
from __future__ import annotations

import datetime as dt
import zipfile

import pytest

from aoi_capacity import failures, nas_guard
from conftest import make_cfg

NOW = dt.datetime(2026, 10, 20, 13, 0, 0)

LOG = """\
2026-10-10 09:00:00,100 INFO aoi.devices: [건너뜀] K1: KLA 날짜 폴더 없음/접근 불가 (Z:\\)
2026-10-19 15:00:00,100 INFO aoi.devices: [건너뜀] K1: KLA 날짜 폴더 없음/접근 불가 (Z:\\)
2026-10-19 15:00:01,000 INFO aoi.collect: 정상 줄입니다
2026-10-19 15:17:00,000 INFO aoi.collect: [수집 상세] collect · 수집기 abc · 모드 gui
  단계(ms): total_ms=1
  오류 device=K4 · path=N:\\2026-10-19\\LOT\\2026-10-19-10-26_7 · tries=1 · error=PermissionError: [Errno 13] Permission denied: '{kfile}'
2026-10-19 15:18:00,000 WARNING aoi.collect: 경고 줄
"""


def _cfg(tmp_path, csv_path, **over):
    return make_cfg(tmp_path, csv_path, **over)


def test_clamp_days():
    assert failures.clamp_days(0) == 1 and failures.clamp_days(500) == 90 and failures.clamp_days("x") == 3 and failures.clamp_days(7) == 7


def test_log_parsing_window_errors_and_skips(tmp_path):
    base = tmp_path / "app.log"
    base.write_text(LOG.format(kfile="N:\\\\a\\\\b.001"), encoding="utf-8")
    (tmp_path / "app.log.1").write_text("2026-10-01 00:00:00,000 INFO aoi.x: 아주 옛 줄\n", encoding="utf-8")
    recs = failures.read_log_records(base, NOW - dt.timedelta(days=3))
    assert [r["ts"].day for r in recs] == [19, 19, 19, 19]          # 10/10 · 10/1 은 기간 밖
    fails = [r for r in recs if failures.is_failure_record(r)]
    assert len(fails) == 3                                           # 정상 줄은 뺀다(건너뜀 · 수집 상세 · WARNING)
    errs = failures.log_errors(recs)
    assert errs[0]["device"] == "K4" and errs[0]["tries"] == 1 and "Permission denied" in errs[0]["error"]
    assert failures.log_skips(recs) == {"K1": "KLA 날짜 폴더 없음/접근 불가 (Z:\\)"}


def test_file_path_of_unescapes_kla_error():
    it = {"path": "N:\\d\\lot\\w", "error": "PermissionError: [Errno 13] Permission denied: 'N:\\\\d\\\\lot\\\\w\\\\x.001'"}
    assert failures.file_path_of(it) == "N:\\d\\lot\\w\\x.001"
    assert failures.file_path_of({"path": "X:\\a\\r.htm", "error": ""}) == "X:\\a\\r.htm"


def test_fetch_content_respects_scope_and_device_roots(tmp_path):
    root = tmp_path / "nas" / "AOI-9"
    root.mkdir(parents=True)
    f = root / "a.htm"
    f.write_text("<html>본문</html>", encoding="utf-8")
    out_of = tmp_path / "other.htm"
    out_of.write_text("x", encoding="utf-8")
    ok = failures.fetch_content({"device": "AOI-9", "path": str(f), "error": ""}, lambda n: True, {"AOI-9": str(root)})
    assert ok["data"] == "<html>본문</html>".encode() and ok["size"] == f.stat().st_size
    assert failures.fetch_content({"device": "AOI-9", "path": str(f), "error": ""}, lambda n: False, {"AOI-9": str(root)})["data"] is None
    far = failures.fetch_content({"device": "AOI-9", "path": str(out_of), "error": ""}, lambda n: True, {"AOI-9": str(root)})
    assert far["data"] is None and "밖" in far["note"]
    assert failures.fetch_content({"device": "AOI-9", "path": str(f), "error": ""}, lambda n: True, {})["data"] is None   # 장비 폴더를 못 찾았으면 읽지 않는다
    assert failures.fetch_content({"device": "AOI-9", "path": str(f), "error": ""}, lambda n: True, {"AOI-10": str(root)})["data"] is None
    big = root / "big.htm"
    big.write_bytes(b"a" * (failures.MAX_FILE_BYTES + 10))
    cut = failures.fetch_content({"device": "AOI-9", "path": str(big), "error": ""}, lambda n: True, {"AOI-9": str(root)})
    assert len(cut["data"]) == failures.MAX_FILE_BYTES and "앞" in cut["note"]
    missing = failures.fetch_content({"device": "AOI-9", "path": str(root / "no.htm"), "error": ""}, lambda n: True, {"AOI-9": str(root)})
    assert missing["data"] is None and "못 읽음" in missing["note"]


def test_gather_and_write_report(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = _cfg(tmp_path, csv_path, scope_devices=["AOI-9", "K1"])
    bad = nas / "X" / "AOI-9" / "Report" / "bad.htm"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("<html>깨진 Report</html>", encoding="utf-8")
    base = tmp_path / "app.log"
    base.write_text(LOG.format(kfile="N:\\\\a\\\\b.001"), encoding="utf-8")
    mt = (NOW - dt.timedelta(hours=5)).timestamp()
    cache = {"reports": {"dev:AOI-9|ok.htm": {"device": "AOI-9", "rel": "ok.htm", "rows": [
        {"kind": "", "ini_match": "READ_ERROR", "issue_codes": "INI_READ_ERROR=PermissionError", "batch_start": "20-Oct-26 09:00:00 AM",
         "batch_end": "20-Oct-26 10:00:00 AM", "report": "ok.htm", "wafer_id": "W1"}]}},
             "failed": {"dev:AOI-9|bad.htm": {"mtime": mt, "tries": 2, "device_key": "dev:AOI-9", "path": str(bad), "error": "UnicodeError"}},
             "devices": {"dev:AOI-9": {"name": "AOI-9"}}, "last_mtime": {},
             "kla": {"k": {"name": "K1", "lots": {"L": {"w": {"t": "2026-10-05T10:00"}}}}}}
    monkeypatch.setattr(failures.collect, "_load_cache", lambda *a, **k: cache)
    dev = {"name": "AOI-9", "path": str(nas / "X" / "AOI-9"), "key": "dev:AOI-9"}

    def resolver(cfg_, log=None, should_stop=None):
        log("[건너뜀] K1: KLA 날짜 폴더 없음/접근 불가 (Z:\\)")
        return [dev]
    g = failures.gather(cfg, 3, log=lambda m: None, now=NOW, log_base=base, resolver=resolver)
    cats = {(i["category"], i["device"]) for i in g["items"]}
    assert (failures.CAT_DEVICE, "K1") in cats and (failures.CAT_REPORT, "AOI-9") in cats and (failures.CAT_INI, "AOI-9") in cats
    k1 = next(i for i in g["items"] if i["device"] == "K1")
    assert "Z:" in k1["error"] and "2026-10-05" in k1["note"]                # 이유 · 마지막 데이터가 함께
    assert not any(i["device"] == "K4" for i in g["items"])                   # 범위 밖 장비(K4)의 로그 오류는 목록에도 넣지 않는다
    out_dir = tmp_path / "result"
    path = failures.write_report(cfg, g, str(out_dir))
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        assert {"요약.txt", "실패목록.tsv", "장비상태.tsv", "app_log_발췌.txt"} <= set(names)
        member = next(n for n in names if n.startswith("files/AOI-9/"))
        assert "깨진 Report" in z.read(member).decode()
        tsv = z.read("실패목록.tsv").decode()
        assert "장비 접근 못 함" in tsv and "UnicodeError" in tsv and "bad.htm" in tsv
        assert "K1" in z.read("요약.txt").decode()


def test_out_of_scope_log_error_is_dropped_and_never_read(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = _cfg(tmp_path, csv_path, scope_devices=["AOI-9"])
    secret = nas / "X" / "AOI-10" / "r.htm"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text("비밀", encoding="utf-8")
    base = tmp_path / "app.log"
    base.write_text("2026-10-19 15:17:00,000 INFO aoi.collect: [수집 상세] c\n  오류 device=AOI-10 · path=%s · tries=1 · error=E\n" % secret, encoding="utf-8")
    monkeypatch.setattr(failures.collect, "_load_cache", lambda *a, **k: {"reports": {}, "failed": {}, "devices": {}, "last_mtime": {}})
    g = failures.gather(cfg, 3, log=lambda m: None, now=NOW, log_base=base,
                        resolver=lambda c, log=None, should_stop=None: [{"name": "AOI-9", "path": str(nas / "X" / "AOI-9")}])
    assert not any(i["device"] == "AOI-10" for i in g["items"])
    assert not any("content" in i and i["content"]["data"] == "비밀".encode() for i in g["items"])


def test_refuses_nas_output_dir(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = _cfg(tmp_path, csv_path)
    with pytest.raises(nas_guard.NasWriteRefused):
        failures.run(cfg, 3, str(nas / "X" / "fail"), log=lambda m: None)


# ── 수집 창 카드 ────────────────────────────────────────────────────────────
def _pump(app, secs=0.05):
    import time
    end = time.time() + secs
    while time.time() < end:
        app.processEvents()
        time.sleep(0.005)


def test_card_remembers_days_runs_and_blocks_collect(styled_qapp, fake_nas, tmp_path):
    import time

    pytest.importorskip("PyQt6.QtWidgets")
    from aoi_capacity import devices, i18n
    from aoi_capacity.ui import main_window as mw
    from aoi_capacity.ui.main_window import MainWindow
    from aoi_capacity.utils import paths, prefs

    _nas, csv_path = fake_nas
    devices.write_devices_csv(paths.devices_csv_path(), devices.read_devices_csv(csv_path))
    prefs.patch(scope_devices=["*"])
    w = MainWindow()
    w.show()
    _pump(styled_qapp)
    page = w.collect_page
    page.wait_for_plan()
    _pump(styled_qapp, 0.2)
    assert page._fl_days.value() == 3 and page._b_fl_run.text() == i18n.KO.FAIL_LOGS_RUN
    page._fl_days.setValue(7)
    assert prefs.load().fail_log_days == 7                       # 적은 일수를 기억한다
    page._fl_out.setText(str(tmp_path / "fl"))
    page._b_fl_run.click()
    assert page.wafer_logs_running() and not page._b_fl_run.isEnabled() and not page._b_run.isEnabled()
    warned = []
    mw.sheets.warn, orig = (lambda *a: warned.append(a)), mw.sheets.warn
    try:
        w._start_collect(False, False)                           # 실패 로그를 모으는 동안에는 수집이 시작되지 않는다
    finally:
        mw.sheets.warn = orig
    assert not w.is_collecting() and warned
    t0 = time.time()
    while page._fl_worker is not None and time.time() - t0 < 30:
        _pump(styled_qapp)
    _pump(styled_qapp, 0.1)
    assert page._b_fl_run.isEnabled() and page._b_run.isEnabled() and not page.wafer_logs_running()
    assert list((tmp_path / "fl").glob("AOI_fail_logs_*.zip")), page._fl_status.text()
    w.close()
    _pump(styled_qapp)
