"""LOT 추적 발행 시험(10/27) — LOT 추적 탭만 담은 HTML 한 장을 이 PC 의 시험 폴더에 만든다(NAS 는 읽지 않고, 공유 폴더에는 쓰지 않는다).

- `write_html(lot_only=True)`: `meta.lot_only` · 기간 전부 · 파라미터 · 레시피 묶음 · CSV 없음 · 안 쓰는 열은 값만 비운다(열 이름은 그대로).
- `out_dir` 은 NAS 아래면 거부한다. 화면(template)은 `meta.lot_only` 일 때 탭 줄에 LOT 추적만 둔다."""
from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path

import pytest

from aoi_capacity import collect, publish
import sample_rows

TEMPLATE = Path(__file__).resolve().parents[2] / "aoi_capacity" / "ui" / "assets" / "template.html"


def _cfg(out: Path, **extra) -> dict:
    cfg = dict(collect.DEFAULT_CONFIG)
    cfg.update({"output_dir": str(out), "cache_file": str(out / "c.json"), "html_days": 7, "scope_devices": ["*"], "write_csv": True})
    cfg.update(extra)
    return cfg


@pytest.fixture(scope="module")
def sample():
    rows, meta, _sha = sample_rows.load(sample_rows.sample_path("AOI_capacity_2026-09-18_30일치.html"))
    return rows, meta


def test_lot_only_file_has_all_days_blank_columns_and_no_csv(tmp_path, sample):
    rows, meta = sample
    out = tmp_path / collect.LOT_PUBLISH_DIR
    path = collect.write_html(_cfg(tmp_path / "main"), rows, meta["devices"], [], 0.0, lot_only=True,
                              out_dir=str(out), out_name=collect.LOT_PUBLISH_NAME,
                              params_store={"snaps": {"k": {"job": "j", "t": "2026-09-01 00:00:00"}}, "blobs": {}})
    assert Path(path) == out / collect.LOT_PUBLISH_NAME
    assert sorted(p.name for p in out.iterdir()) == [collect.LOT_PUBLISH_NAME]          # 임시 파일 · CSV 가 남지 않는다
    assert not list((tmp_path / "main").glob("*.csv"))
    emb = sample_rows.embedded(Path(path).read_text(encoding="utf-8"))
    m = emb["meta"]
    assert m["lot_only"] is True
    assert "params" not in m and "recipe_groups" not in m, [k for k in ("params", "recipe_groups") if k in m]
    assert (m["range"]["from"], m["range"]["to"]) == (m["data_from"], m["data_to"])      # html_days=7 이어도 가진 데이터 전부
    back, _ = sample_rows.unfold(emb)
    keep_rows = [r for r in rows if not r.get("kind")]
    assert len(back) == len(keep_rows) < len(rows)                                    # 합성 행(kind)은 담지 않는다
    for c in collect.LOT_ONLY_BLANK_COLS:
        assert c in emb["cols"] and all(r.get(c) == "" for r in back)
    assert set(collect.LOT_ONLY_BLANK_COLS) | set(collect.LOT_ONLY_KEEP_COLS) == set(collect.OUT_COLS)
    for c in ("wafer_id", "lot", "job", "device", "slot_no", "status", "recipe", "faults", "report", "batch_start", "wafer_start_time"):
        assert [r.get(c) or "" for r in back] == [r.get(c) or "" for r in keep_rows], c                   # LOT 추적이 쓰는 열은 그대로


def test_out_dir_under_a_nas_root_is_refused(tmp_path, sample):
    rows, meta = sample
    nas = tmp_path / "nas"
    (nas / "AOI-1").mkdir(parents=True)
    dev_csv = tmp_path / "devices.csv"
    cfg = _cfg(tmp_path / "main", devices_csv=str(dev_csv))
    dev_csv.write_text("name,path\nAOI-1," + str(nas / "AOI-1") + "\n", encoding="utf-8")
    with pytest.raises(Exception):
        collect.write_html(cfg, rows[:5], meta["devices"], [], 0.0, lot_only=True, out_dir=str(nas / "AOI-1" / "pub"))
    assert not (nas / "AOI-1" / "pub").exists()


def test_template_keeps_only_the_lot_tab_when_lot_only():
    t = TEMPLATE.read_text(encoding="utf-8")
    assert 'if(meta.lot_only)state.view="lot"' in t
    assert 'lotOnly?[["lot","LOT 추적"]]' in t
    assert "!lotOnly" in t                                       # 사본 저장 · 레시피 묶음 · 날짜 줄 · 설정 단추를 감춘다
    for piece in ('lotOnly?"":`<section class="cards sm lotcards"', 'sCell(lotOnly?top-i:i+1)', 'lotOnly?"":`<div class="panel" style="padding:12px 16px;overflow-x:auto">',
                  '${lotOnly?"":\'<span class="r">배치 시간</span><span>구분</span><span></span>\'}', 'SLOT_WARN'):
        assert piece in t, piece                                 # 카드 · 배치 시간 · 구분 · Wafer × 검사 없음, Slot 세로 + 경고


def test_template_reads_only_the_columns_the_publish_file_keeps():
    """LOT 추적 화면(lotIndex · lotFamily · lotHtml · lotCauseHtml)이 읽는 열은 전부 남기는 열이다."""
    t = TEMPLATE.read_text(encoding="utf-8")
    start = t.index("function lotParse(")
    end = t.index("/* ---------- RDL 단일스캔 탭")
    src = t[start:end]
    used = {c for c in collect.OUT_COLS if re.search(r"\br\.%s\b|\.r\.%s\b" % (c, c), src)}
    shown_only_in_full = {"batch_end", "ini_match", "wafer_end_time"}      # 배치 시간 · Wafer 시간 계산에만 쓰인다 — 배포판은 그 표시를 감춘다(비어 있어도 값이 null 일 뿐)
    assert used - shown_only_in_full <= set(collect.LOT_ONLY_KEEP_COLS), sorted(used - shown_only_in_full - set(collect.LOT_ONLY_KEEP_COLS))


# ── 배포(publish.py) ──
def _publish_cfg(tmp_path, sample):
    rows, meta = sample
    cfg = _cfg(tmp_path / "main")
    return cfg, rows, meta["devices"]


def test_publish_writes_stub_pointer_and_unique_data_files_and_prunes(tmp_path, sample):
    cfg, rows, devs = _publish_cfg(tmp_path, sample)
    share = tmp_path / "share"
    now = dt.datetime(2026, 10, 27, 8, 15)
    got = [publish.publish_lot(cfg, str(share), rows=rows[:3000], dev_meta=devs, now=now + dt.timedelta(minutes=i)) for i in range(5)]
    assert all(g["pointer_ok"] for g in got)
    assert sorted(p.name for p in share.iterdir()) == ["AOI_LOT.html", "data", "latest.js"]
    data = sorted(p.name for p in (share / "data").iterdir())
    assert data == ["lot_20261027_0817.html", "lot_20261027_0818.html", "lot_20261027_0819.html"]       # 최근 3개만
    assert (share / "latest.js").read_text(encoding="utf-8") == 'window.AOI_LOT_LATEST="data/lot_20261027_0819.html";\n'
    stub = (share / "AOI_LOT.html").read_text(encoding="utf-8")
    assert "latest.js" in stub and "location.replace" in stub and "http" not in stub
    emb = sample_rows.embedded((share / "data" / data[-1]).read_text(encoding="utf-8"))
    assert emb["meta"]["lot_only"] is True


def test_publish_survives_a_locked_pointer_and_never_overwrites_a_data_file(tmp_path, sample, monkeypatch):
    cfg, rows, devs = _publish_cfg(tmp_path, sample)
    share = tmp_path / "share"
    publish.publish_lot(cfg, str(share), rows=rows[:500], dev_meta=devs, now=dt.datetime(2026, 10, 27, 8, 15))
    first = (share / "data" / "lot_20261027_0815.html").read_bytes()
    real = os.replace

    def locked(src, dst):
        if str(dst).endswith("latest.js"):
            raise PermissionError(13, "열려 있음")
        return real(src, dst)
    monkeypatch.setattr(publish.os, "replace", locked)
    monkeypatch.setattr(publish, "REPLACE_WAIT_SEC", 0)
    got = publish.publish_lot(cfg, str(share), rows=rows[:500], dev_meta=devs, now=dt.datetime(2026, 10, 27, 8, 16))
    assert got["pointer_ok"] is False
    assert (share / "data" / "lot_20261027_0815.html").read_bytes() == first      # 옛 데이터 파일은 그대로
    assert (share / "data" / "lot_20261027_0816.html").is_file()
    assert not [p for p in share.iterdir() if p.name.endswith(".tmp")]            # 임시 파일이 남지 않는다


def test_publish_refuses_a_folder_under_an_equipment_nas(tmp_path, sample):
    cfg, rows, devs = _publish_cfg(tmp_path, sample)
    nas = tmp_path / "nas"
    (nas / "AOI-1").mkdir(parents=True)
    dev_csv = tmp_path / "devices.csv"
    dev_csv.write_text("name,path\nAOI-1," + str(nas / "AOI-1") + "\n", encoding="utf-8")
    cfg["devices_csv"] = str(dev_csv)
    with pytest.raises(Exception):
        publish.publish_lot(cfg, str(nas / "AOI-1" / "pub"), rows=rows[:10], dev_meta=devs)
    assert not (nas / "AOI-1" / "pub").exists()
    with pytest.raises(ValueError):
        publish.publish_lot(cfg, "  ", rows=rows[:10], dev_meta=devs)


def test_publish_after_collect_is_silent_and_never_raises(tmp_path, sample):
    cfg, rows, devs = _publish_cfg(tmp_path, sample)
    lines: list = []
    assert publish.publish_after_collect(cfg, rows[:10], devs, log=lines.append) is None and not lines    # 폴더가 비면 아무것도 안 한다
    cfg["publish_dir"] = str(tmp_path / "x" / "NUL:bad")
    cfg["publish_dir"] = ""   # 경로가 잘못돼도 예외 대신 로그 한 줄 — 아래에서 실제 실패를 만든다
    blocker = tmp_path / "file_not_dir"
    blocker.write_text("x")
    cfg["publish_dir"] = str(blocker / "sub")                                          # 폴더를 만들 수 없는 경로
    assert publish.publish_after_collect(cfg, rows[:10], devs, log=lines.append) is None
    assert len(lines) == 1 and lines[0].startswith("LOT 추적 배포 실패(수집은 정상)")
