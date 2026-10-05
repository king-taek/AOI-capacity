"""수집 상세 로그(10/5 사용자 요청) — 장비 · 단계 · 개수 · 시간을 **app.log** 에 남긴다. 결과 HTML 에는 넣지 않는다
(처음엔 HTML 의 meta.collect_log 에 숨겨 넣었으나 사용자 요청으로 옮김)."""
from __future__ import annotations

import logging

import sample_rows
from aoi_capacity import collect
from aoi_capacity.utils import logs, paths
from conftest import make_cfg


def test_collect_writes_a_detailed_log_to_app_log_and_not_into_the_html(tmp_path, fake_nas, caplog):
    _nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    stats: dict = {}
    with caplog.at_level(logging.INFO, logger="aoi.collect"):
        rows, dev_meta, errors = collect.collect(cfg, stats=stats)
    log = stats["log"]
    assert set(log["phases_ms"]) >= {"devices_ms", "list_ms", "read_ms", "cache_ms", "total_ms"}
    d = log["devices"][0]
    assert {"name", "listing", "list_dev_ms", "found", "reports", "read_n", "read_sum_ms", "rows", "status"} <= set(d)
    detail = next(r.getMessage() for r in caplog.records if r.getMessage().startswith("[수집 상세]"))
    assert "단계(ms):" in detail and f"name={d['name']}" in detail and "느린 Report" in detail
    path = collect.write_html(cfg, rows, dev_meta, errors, 0.0, timing=stats)
    meta = sample_rows.unfold(sample_rows.embedded(open(path, encoding="utf-8").read()))[1]
    assert "collect_log" not in meta and "log" not in meta["timing"]          # HTML 에는 싣지 않는다


def test_cli_and_gui_share_the_app_log_file():
    """로거 `aoi` 는 프로세스에 하나 — 앞 테스트가 다른 임시 홈으로 설정해 두었을 수 있어 이 테스트 동안만 새로 설정한다."""
    logger = logging.getLogger("aoi")
    saved = (logger.handlers[:], getattr(logger, "_aoi_configured", False))
    logger.handlers, logger._aoi_configured = [], False
    try:
        logs.setup_logging(console=False)
        assert not any(type(h) is logging.StreamHandler for h in logger.handlers)    # CLI 는 터미널로 두 번 찍지 않는다
        logging.getLogger("aoi.collect").info("detail-line-for-test")
        for h in logger.handlers:
            h.flush()
        assert "detail-line-for-test" in paths.log_file().read_text(encoding="utf-8")
    finally:
        for h in logger.handlers:
            h.close()
        logger.handlers, logger._aoi_configured = saved


def test_screen_never_reads_a_collect_log():
    tpl = open(collect.__file__.replace("collect.py", "ui/assets/template.html"), encoding="utf-8").read()
    assert "collect_log" not in tpl
