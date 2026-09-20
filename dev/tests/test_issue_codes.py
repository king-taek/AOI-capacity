"""C12 — 행 비고(data_issue)의 구조화 코드 `issue_codes`.

캐시에는 코드만 남고 사람 문장은 출력 때 ko.py 에서 만든다(문구를 바꿔도 NAS 재수집이 필요 없다).
옛 캐시 행(자유 문장)은 손실 파싱하지 않고 그대로 두며, 옛·새 행이 한 출력에 섞여도 된다.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import pytest

from aoi_capacity import collect, i18n
from conftest import make_cfg


@pytest.mark.parametrize("items", [
    [("INI_NOT_FOUND_BACKUPS", 2)],
    [("FOUND_IN_BACKUP", "Scanresult_Back up_260918"), "LOT_MISMATCH"],
    [("INI_READ_ERROR", "PermissionError: [Errno 13] a;b=c,d%e — 한글 경로 \\\\10.1.2.3\\공유\\AOI-1")],
    [("BATCH_NO_WAFER", 24, 3), ("MULTI_LOT", 2)],
    [],
])
def test_issue_field_round_trips_params_with_separators_paths_and_hangul(items):
    field = collect.issue_field(items)
    back = collect.parse_issue_codes(field)
    want = [((it, []) if isinstance(it, str) else (it[0], [str(x) for x in it[1:]])) for it in items]
    assert back == want
    assert ";" not in "".join(p for _, ps in back for p in ps) or field.count(";") == len(items) - 1   # 인자 안의 ; 는 이스케이프됐다


def test_issue_text_renders_known_codes_and_keeps_unknown_ones_raw():
    assert collect.issue_text("INI_NOT_FOUND") == i18n.KO.ISSUE_TEXTS["INI_NOT_FOUND"]
    assert collect.issue_text("INI_NOT_FOUND_BACKUPS=2") == "예상 경로와 백업 폴더 2개 어디에도 WaferInfo.ini 없음"
    assert collect.issue_text("BATCH_NO_WAFER=24,3") == "검사된 Wafer 없음 — 배치 시각으로만 표시 (행 24개 중 오류 3개)"
    assert collect.issue_text("FOUND_IN_BACKUP=Scanresult_Back up_260918;LOT_MISMATCH") == \
        "백업 폴더에서 찾음: Scanresult_Back up_260918; Lot 불일치"
    assert collect.issue_text("SOME_FUTURE_CODE=7;LOT_MISMATCH") == "SOME_FUTURE_CODE=7; Lot 불일치"     # 모르는 코드는 버리지 않는다
    assert collect.issue_text("") == "" and collect.issue_text(None) == ""
    assert collect.issue_text("INI_NOT_FOUND_BACKUPS") == i18n.KO.ISSUE_TEXTS["INI_NOT_FOUND_BACKUPS"].replace("{0}", "?")   # 인자 없는 옛 캐시


def test_every_issue_code_has_a_sentence_with_matching_placeholders():
    assert set(collect.ISSUE_CODES) == set(i18n.KO.ISSUE_TEXTS)
    arity = {"INI_NOT_FOUND_BACKUPS": 1, "INI_READ_ERROR": 1, "FOUND_IN_BACKUP": 1, "JOB_FOLDER_DIFFERS": 1,
             "BATCH_NO_WAFER": 2, "SLOT_ERROR": 1, "MULTI_LOT": 1, "MULTI_JOB": 1}
    for code, text in i18n.KO.ISSUE_TEXTS.items():
        n = arity.get(code, 0)
        assert all(("{%d}" % i) in text for i in range(n)) and ("{%d}" % n) not in text, code


def test_render_issue_rows_fills_new_rows_only_and_never_mutates_or_touches_old_rows():
    new = {"device": "AOI-1", "data_issue": "", "issue_codes": "INI_NOT_FOUND"}
    old = {"device": "AOI-1", "data_issue": "예상 경로에 WaferInfo.ini 없음(옛 문장 그대로)"}
    old_with_both = {"device": "AOI-1", "data_issue": "옛 문장", "issue_codes": "INI_NOT_FOUND"}
    clean = {"device": "AOI-1", "data_issue": "", "issue_codes": ""}
    out = collect.render_issue_rows([new, old, old_with_both, clean])
    assert out[0]["data_issue"] == i18n.KO.ISSUE_TEXTS["INI_NOT_FOUND"] and out[0] is not new and new["data_issue"] == ""
    assert out[1] is old and out[2] is old_with_both and out[3] is clean


def _cache_rows(cfg):
    cache = json.loads(Path(cfg["cache_file"]).read_text(encoding="utf-8"))
    return [r for e in cache["reports"].values() for r in e["rows"]]


def test_cache_keeps_codes_only_and_outputs_carry_the_sentence(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    rows, dev_meta, errors = collect.collect(cfg)
    cached = _cache_rows(cfg)
    flagged = [r for r in cached if r.get("issue_codes")]
    assert flagged and all(r["data_issue"] == "" for r in cached)                       # 캐시: 코드만, 문장 없음
    codes = {c for r in flagged for c, _ in collect.parse_issue_codes(r["issue_codes"])}
    assert {"NO_WAFER_ID_ROW", "INI_NOT_FOUND"} <= codes
    by = {(r["report"], r["wafer_id"], r["kind"]): r for r in rows}
    ph = next(r for r in rows if r["ini_match"] == "NO_WAFER_ID")
    assert ph["data_issue"] == i18n.KO.ISSUE_TEXTS["NO_WAFER_ID_ROW"] and ph["issue_codes"] == "NO_WAFER_ID_ROW"
    assert next(r for r in rows if r["ini_match"] == "EXACT")["data_issue"] == ""
    target = collect.write_html(cfg, rows, dev_meta, errors, time.time())
    text = Path(target).read_text(encoding="utf-8")
    emb = json.loads(text.split('id="embedded">')[1].split("</script>")[0])
    assert "issue_codes" in emb["cols"] and "data_issue" in emb["cols"] and "issue_codes" in emb["pooled"]
    assert i18n.KO.ISSUE_TEXTS["NO_WAFER_ID_ROW"] in emb["pool"]
    with open(Path(target).with_suffix(".csv"), encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    assert csv_rows[0].keys() == set(collect.OUT_COLS) or list(csv_rows[0].keys()) == collect.OUT_COLS
    assert any(r["data_issue"] == i18n.KO.ISSUE_TEXTS["NO_WAFER_ID_ROW"] and r["issue_codes"] == "NO_WAFER_ID_ROW" for r in csv_rows)


def test_old_free_text_rows_and_new_coded_rows_coexist_and_wording_changes_need_no_recollection(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)
    cache_path = Path(cfg["cache_file"])
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    # 옛 캐시 흉내: 첫 Report 의 행에서 issue_codes 를 지우고 옛 자유 문장을 남긴다(옛 스키마)
    first = next(iter(cache["reports"].values()))
    for r in first["rows"]:
        r.pop("issue_codes", None)
        r["data_issue"] = "옛 캐시의 자유 문장 — 그대로 남아야 한다"
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    # 문구를 바꾼다 — 재수집 없이 다음 출력에 반영돼야 한다
    monkeypatch.setitem(i18n.KO.ISSUE_TEXTS, "NO_WAFER_ID_ROW", "자리표시 행(새 문구)")
    from aoi_capacity import nas_guard
    reads = {"htm": 0}
    orig = nas_guard.read_text

    def spy(path, *a, **k):
        if str(path).lower().endswith((".htm", ".html")) and nas_guard.is_under(str(path), str(nas)):
            reads["htm"] += 1
        return orig(path, *a, **k)

    monkeypatch.setattr(collect.nas_guard, "read_text", spy)
    rows, _, _ = collect.collect(cfg)                                                    # 증분 — Report 를 다시 읽지 않는다
    assert reads["htm"] == 0
    old_rows = [r for r in rows if r["data_issue"] == "옛 캐시의 자유 문장 — 그대로 남아야 한다"]
    assert len(old_rows) == len(first["rows"]) and all(not r.get("issue_codes") for r in old_rows)
    new_ph = [r for r in rows if r.get("issue_codes") == "NO_WAFER_ID_ROW"]
    assert new_ph and all(r["data_issue"] == "자리표시 행(새 문구)" for r in new_ph)
    assert all(r["data_issue"] == "" for r in _cache_rows(cfg) if r.get("issue_codes"))    # 캐시에는 여전히 코드만


def test_synthetic_rows_carry_codes(tmp_path):
    """batch · slot 합성 행도 코드로 — 인자(행 수·오류 수·Slot 수)는 숫자 그대로."""
    rows = [{"device": "AOI-1", "kind": "", "job": "J", "setup": "S", "report": "R", "lot": "LOT-A", "wafer_id": f"W{i}",
             "status": "Wafer lost. Batch Aborted. Skipped.", "recipe": "", "faults": "", "scanned_dice": "", "yield": "",
             "wafer_start_time": "", "wafer_end_time": "", "batch_start": "15-Sep-26 01:00:00 PM", "batch_end": "15-Sep-26 01:10:00 PM",
             "ini_match": "NOT_FOUND", "time_basis": "MISSING", "slots": "", "data_issue": "", "issue_codes": "INI_NOT_FOUND"} for i in range(3)]
    out = collect.synthesize_rows(rows)
    batch = next(r for r in out if r["kind"] == "batch")
    assert batch["issue_codes"] == "BATCH_NO_WAFER=3,3" and batch["data_issue"] == ""
    assert collect.issue_text(batch["issue_codes"]) == "검사된 Wafer 없음 — 배치 시각으로만 표시 (행 3개 중 오류 3개)"
