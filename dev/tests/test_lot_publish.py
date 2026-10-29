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
from aoi_capacity.nas_guard import NasWriteRefused
from aoi_capacity.utils import config as config_mod
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
    with pytest.raises(NasWriteRefused):
        collect.write_html(cfg, rows[:5], meta["devices"], [], 0.0, lot_only=True, out_dir=str(nas / "AOI-1" / "pub"))
    assert not (nas / "AOI-1" / "pub").exists()


def test_template_keeps_only_the_lot_tab_when_lot_only():
    t = TEMPLATE.read_text(encoding="utf-8")
    assert 'if(meta.lot_only)state.view="lot"' in t
    assert 'lotOnly?[["lot","LOT 추적"]]' in t
    assert "!lotOnly" in t                                       # 사본 저장 · 레시피 묶음 · 날짜 줄 · 설정 단추를 감춘다
    for piece in ('lotOnly?"":`<section class="cards sm lotcards"', '${lotOnly?"":slots}',
                  '${lotOnly?"":\'<span class="r">배치 시간</span><span>구분</span><span></span>\'}'):
        assert piece in t, piece                                 # 카드 · 배치 시간 · 구분 · Slot 지도 없음
    assert "SLOT_WARN" not in t and 'const mx=lotOnly' not in t  # 10/29: Slot 세로 목록 · 경고 없앰, Wafer × 검사는 원본과 같다


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
    assert sorted(p.name for p in share.iterdir()) == ["AOI_LOT.html", "AOI_LOT_shortcut.url", "data", "latest.js"]
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
    with pytest.raises(NasWriteRefused):
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


def test_shortcut_points_at_the_stub_with_an_encoded_file_url(tmp_path, sample):
    cfg, rows, devs = _publish_cfg(tmp_path, sample)
    url = publish.stub_url(config_mod.PUBLISH_DIR_DEFAULT)
    assert url == ("file://k5cifsn2/k5tsvdata$/1.%20Conder%20Scan/0.%20%EC%A0%84%EC%82%B0%20X/%EC%9E%84%ED%98%84%ED%83%9D/"
                   "LOT%EC%B6%94%EC%A0%81/AOI_LOT.html")
    assert publish.stub_url("Z:\\a b\\c\\") == "file:///Z:/a%20b/c/AOI_LOT.html"
    desk = tmp_path / "Desktop"
    path = publish.write_shortcut(str(desk), config_mod.PUBLISH_DIR_DEFAULT, cfg)
    # 바로가기(.url)는 ANSI 로 읽힌다 — 한글을 퍼센트 인코딩하면 셸이 UTF-8 바이트를 ANSI 로 풀어 경로가 깨졌다(10/27 실측). 한글은 그대로 CP949 로
    raw = "file://k5cifsn2/k5tsvdata$/1.%20Conder%20Scan/0.%20전산%20X/임현택/LOT추적/AOI_LOT.html"
    assert publish.raw_stub_url(config_mod.PUBLISH_DIR_DEFAULT) == raw
    data = Path(path).read_bytes()
    if os.name != "nt":
        assert data == ("[InternetShortcut]\r\nURL=" + raw + "\r\n").encode("cp949")
    assert "%EC" not in data.decode("cp949", "replace") and b"\xc0\xfc\xbb\xea" in data     # 전산(CP949) 바이트
    assert publish.raw_stub_url("Z:\\a b\\c\\") == "file:///Z:/a%20b/c/AOI_LOT.html"
    share = tmp_path / "share"
    publish.publish_lot(cfg, str(share), rows=rows[:100], dev_meta=devs, now=dt.datetime(2026, 10, 27, 8, 15))
    assert b"AOI_LOT.html" in (share / "AOI_LOT_shortcut.url").read_bytes()


def test_publish_dir_is_hardcoded_by_default_and_must_be_absolute(tmp_path, sample):
    assert collect.DEFAULT_CONFIG["publish_dir"] == config_mod.PUBLISH_DIR_DEFAULT
    assert config_mod.PUBLISH_DIR_DEFAULT.startswith("\\\\k5cifsn2\\")
    cfg, problems = config_mod.normalize_config(dict(collect.DEFAULT_CONFIG))
    assert cfg["publish_dir"] == config_mod.PUBLISH_DIR_DEFAULT and not [p for p in problems if p.key == "publish_dir"]
    _cfg_, rows, devs = _publish_cfg(tmp_path, sample)
    with pytest.raises(ValueError):
        publish.publish_lot(_cfg_, "relative\\folder", rows=rows[:10], dev_meta=devs)
    assert not Path("relative\\folder").exists()
    if os.name != "nt":                                           # 개발 환경 · CI 에서는 기본 UNC 로 나가지 않는다
        assert publish.publish_after_collect(dict(_cfg_, publish_dir=config_mod.PUBLISH_DIR_DEFAULT), rows[:10], devs, log=None) is None


def test_prune_keeps_the_file_latest_js_points_to(tmp_path):
    from aoi_capacity import publish
    d = tmp_path / "data"
    d.mkdir()
    for n in ("lot_20260101_0900", "lot_20260102_0900", "lot_20260103_0900", "lot_20260104_0900"):
        (d / f"{n}.html").write_text("x")
    publish._prune(str(d), 3, [], protect={"lot_20260101_0900.html"})
    assert sorted(p.name for p in d.iterdir()) == ["lot_20260101_0900.html", "lot_20260102_0900.html", "lot_20260103_0900.html", "lot_20260104_0900.html"][0:1] + ["lot_20260102_0900.html", "lot_20260103_0900.html", "lot_20260104_0900.html"]


def test_lot_only_meta_drops_nas_paths():
    src = open(collect.__file__, encoding="utf-8").read()
    assert 'meta["devices"] = [{k: dm[k] for k in ("name", "key", "status", "read_errors")' in src


def test_publish_same_minute_three_times_keeps_three_distinct_files_and_a_valid_pointer(tmp_path, sample):
    cfg, rows, devs = _publish_cfg(tmp_path, sample)
    share = tmp_path / "share"
    now = dt.datetime(2026, 10, 27, 8, 10, 0)
    got = [publish.publish_lot(cfg, str(share), rows=rows[:300], dev_meta=devs, now=now) for _ in range(3)]
    assert len({g["data"] for g in got}) == 3
    ptr = (share / "latest.js").read_text(encoding="utf-8")
    assert os.path.basename(got[-1]["data"]) in ptr and os.path.isfile(got[-1]["data"])


def test_publish_to_a_missing_share_fails_fast(tmp_path, sample):
    cfg, rows, devs = _publish_cfg(tmp_path, sample)
    with pytest.raises(FileNotFoundError):
        publish.publish_lot(cfg, str(tmp_path / "no" / "share"), rows=rows[:10], dev_meta=devs)
