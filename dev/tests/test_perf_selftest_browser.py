"""속도 시험 LOT 파일의 자가 점검(11/25 LOTD-01)을 진짜 Chromium 으로 연다.

- `meta.selftest` 면 열린 뒤 스스로 LOT 를 고르고 · Wafer 이력을 열고 닫고 · 다른 이름을 펼치고 · 검색해 본 뒤 맨 위 띠에
  '열기 n.n초 · 자동 점검 m가지 · 오류 k개' 를 적는다 — 오류 0. `meta.lot_skip_model` 이면 가동률 모델 대신 가벼운 D 로도 같은 점검이 통과한다.
- 표식이 없는 파일(제품)에는 띠도 점검도 없다. 바깥 요청 0건 · 콘솔 오류 0.
- 11/26 단추 하나: `meta.selftest_token` 이 있으면 점검이 끝난 뒤 결과를 blob 으로 `aoi_perf_<토큰>_<이름>.json` **한 장** 내려받는다
  (수집기가 다운로드 폴더에서 가져간다). 토큰이 없으면(손으로 만든 시험 파일) · 제품 파일이면 다운로드 0.
마커 `browser` — Playwright · Chromium 이 없으면 skip."""
from __future__ import annotations

import json

import pytest

from aoi_capacity import collect
from test_dashboard_browser import TEMPLATE, _meta, _row, page_factory  # noqa: F401 - page_factory 는 fixture

pytestmark = pytest.mark.browser


def _rows():
    ids = [f"K62540{n:02d}B0" for n in range(6)]
    rows = [_row("AOI-1", w, f"08:{i * 5:02d}", f"08:{i * 5 + 4:02d}", lot="KLK-3D", job="TB500_RDL2") for i, w in enumerate(ids)]
    rows += [_row("AOI-2", w, f"10:{i * 5:02d}", f"10:{i * 5 + 4:02d}", lot="KLK-3D-RE", job="TB500_RDL2") for i, w in enumerate(ids[:3])]
    rows += [_row("AOI-10", f"Z77310{n:02d}A1", f"12:{n * 6:02d}", f"12:{n * 6 + 5:02d}", lot="QWE-2D", job="R_KENDALL_A0_FS") for n in range(4)]
    return rows


def _open(page_factory, tmp_path, downloads=None, **flags):  # noqa: F811
    emb = collect._embed_rows(_rows(), collect.LOT_ONLY_COLS)
    emb["meta"] = dict(_meta(), lot_only=True, data_from="2026-09-18", data_to="2026-09-18",
                       range={"from": "2026-09-18", "to": "2026-09-18", "explicit": False}, **flags)   # write_html 이 늘 넣는 기간
    tpl = TEMPLATE.read_text(encoding="utf-8").replace('<html lang="ko" ', '<html lang="ko" data-boot="lot" ', 1)
    out = tmp_path / "lot.html"
    out.write_text(tpl.replace("__DATA__", json.dumps(emb, ensure_ascii=False).replace("</", "<\\/"), 1), encoding="utf-8")
    ctx = page_factory.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    errors, requests = [], []
    if downloads is not None:
        pg.on("download", lambda d: downloads.append(d))
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("file:", "blob:")) else None)
    pg.goto(out.as_uri())
    pg.wait_for_selector('main[data-key="view:lot"]')
    return ctx, pg, errors, requests


@pytest.mark.parametrize("skip", [False, True], ids=["now", "skip_model"])
def test_self_test_band_reports_open_time_and_no_errors(page_factory, tmp_path, skip):  # noqa: F811
    flags = {"selftest": True, **({"lot_skip_model": True} if skip else {})}
    ctx, pg, errors, requests = _open(page_factory, tmp_path, **flags)
    pg.wait_for_selector("#aoi-selftest", timeout=20000)
    st = pg.evaluate("window.__selftest")
    assert st["done"] and st["lite"] is skip and st["open"] > 0
    assert not st["errors"], st["errors"]
    names = [s["name"] for s in st["steps"]]
    assert names[0] == "LOT 목록" and "Wafer 이력 열기 · 닫기" in names and "검색 입력" in names and sum(n.startswith("LOT 고르기") for n in names) >= 2
    assert all(s["ok"] for s in st["steps"]), st["steps"]
    band = pg.inner_text("#aoi-selftest")
    assert "열기" in band and f"자동 점검 {len(names)}가지" in band and "오류 0개" in band
    assert pg.locator(".lotmxp").count() == 1                         # 마지막으로 고른 LOT 의 격자가 남아 있다
    assert not errors and not requests
    ctx.close()


def test_self_test_downloads_one_result_file_with_the_token(page_factory, tmp_path):  # noqa: F811
    downloads = []
    ctx, pg, errors, requests = _open(page_factory, tmp_path, downloads, selftest=True, selftest_token="a1b2c3", selftest_name="skip",
                                      lot_skip_model=True)
    pg.wait_for_selector("#aoi-selftest .st-dl", timeout=20000)
    pg.wait_for_timeout(500)
    assert len(downloads) == 1, [d.suggested_filename for d in downloads]
    d = downloads[0]
    assert d.suggested_filename == "aoi_perf_a1b2c3_skip.json" and d.url.startswith("blob:")
    got = json.loads(open(d.path(), encoding="utf-8").read())
    st = pg.evaluate("window.__selftest")
    assert got["token"] == "a1b2c3" and got["name"] == "skip" and got["lite"] is True and got["open"] == st["open"] > 0
    assert [s["name"] for s in got["steps"]] == [s["name"] for s in st["steps"]] and got["errors"] == [] and got["rows"] > 0
    assert set(got["stages"]) == {"parse", "unfold", "model", "first"} and got["stages"]["parse"] is not None
    assert st["downloaded"] == "aoi_perf_a1b2c3_skip.json"
    assert not errors and not requests
    ctx.close()


def test_without_a_token_the_self_test_downloads_nothing(page_factory, tmp_path):  # noqa: F811
    downloads = []
    ctx, pg, errors, requests = _open(page_factory, tmp_path, downloads, selftest=True)
    pg.wait_for_selector("#aoi-selftest", timeout=20000)
    pg.wait_for_timeout(600)
    assert not downloads and pg.locator("#aoi-selftest .st-dl").count() == 0 and not errors and not requests
    ctx.close()


def test_without_the_flag_there_is_no_band(page_factory, tmp_path):  # noqa: F811
    downloads = []
    ctx, pg, errors, requests = _open(page_factory, tmp_path, downloads, selftest_token="a1b2c3")   # 토큰만 있어도(표식 없음) 아무것도 안 한다
    pg.wait_for_selector("#aoi-boot", state="detached", timeout=15000)
    pg.wait_for_timeout(600)
    assert not downloads
    assert pg.locator("#aoi-selftest").count() == 0 and pg.evaluate("window.__selftest") is None
    assert pg.locator(".lotscroll .lotpick").count() >= 2 and pg.locator(".lotmxp").count() == 0   # 아무것도 저절로 눌리지 않았다
    assert not errors and not requests
    ctx.close()
