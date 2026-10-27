"""LOT 추적 발행 시험(10/27) — LOT 추적 탭만 담은 HTML 한 장을 이 PC 의 시험 폴더에 만든다(NAS 는 읽지 않고, 공유 폴더에는 쓰지 않는다).

- `write_html(lot_only=True)`: `meta.lot_only` · 기간 전부 · 파라미터 · 레시피 묶음 · CSV 없음 · 안 쓰는 열은 값만 비운다(열 이름은 그대로).
- `out_dir` 은 NAS 아래면 거부한다. 화면(template)은 `meta.lot_only` 일 때 탭 줄에 LOT 추적만 둔다."""
from __future__ import annotations

from pathlib import Path

import pytest

from aoi_capacity import collect
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
    assert len(back) == len(rows)
    for c in collect.LOT_ONLY_BLANK_COLS:
        assert c in emb["cols"] and all(r.get(c) == "" for r in back)
    assert [r["wafer_id"] for r in back] == [r["wafer_id"] for r in rows]            # LOT 추적이 쓰는 열은 그대로


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
