"""숨긴 수집 로그(10/5 사용자 요청) — 결과 HTML 의 `meta.collect_log` 에 장비 · 단계 · 개수 · 시간을 남기고 화면에는 그리지 않는다."""
from __future__ import annotations

import sample_rows
from aoi_capacity import collect
from conftest import make_cfg



def test_collect_log_lists_devices_phases_and_slowest_reports(tmp_path, fake_nas):
    _nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    stats: dict = {}
    rows, dev_meta, errors = collect.collect(cfg, stats=stats)
    log = stats["log"]
    assert log["kind"] == "collect" and log["started"] and log["finished"]
    assert set(log["phases_ms"]) >= {"devices_ms", "list_ms", "read_ms", "cache_ms", "total_ms"}
    d = log["devices"][0]
    assert {"name", "listing", "list_dev_ms", "found", "reports", "read_n", "read_sum_ms", "rows", "status"} <= set(d)
    assert log["slowest_reports"] and {"ms", "device", "report"} == set(log["slowest_reports"][0])
    path = collect.write_html(cfg, rows, dev_meta, errors, 0.0, timing=stats, collect_log=log)
    meta = sample_rows.unfold(sample_rows.embedded(open(path, encoding="utf-8").read()))[1]
    assert meta["collect_log"]["devices"][0]["name"] == d["name"]
    assert "log" not in meta["timing"]                                   # 같은 내용을 두 번 싣지 않는다


def test_screen_never_draws_the_collect_log():
    tpl = open(collect.__file__.replace("collect.py", "ui/assets/template.html"), encoding="utf-8").read()
    assert "collect_log" not in tpl                                     # 화면 코드는 이 키를 읽지도 그리지도 않는다(숨김)
