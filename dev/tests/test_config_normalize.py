"""C13 · D14 — 설정 값 검사(`utils.config.normalize_config`)를 GUI(prefs)와 CLI(config.json)가 같은 규칙으로 쓴다.

- 문자/NaN/음수/0/null/bool/너무 큰 값 → 성능·기간 값은 경고 + 기본값/클램프(`bool("false")` 없음)
- 잘못된 scope·경로·폴더 이름 → 실행 차단(ConfigError), NAS 접근 0
- prefs_version 이 잘못돼도 장비 목록을 기본 30대로 되돌리지 않는다
- attention_util·attention_err 가 결과 HTML 의 meta.dashboard_settings 로 나간다(D14)
"""
from __future__ import annotations

import builtins
import json
import math
import os
import time
from pathlib import Path

import pytest

from aoi_capacity import collect, devices, scope
from aoi_capacity.utils import config, prefs
from conftest import make_cfg


# ── 낱개 변환 ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    (8, 8), ("8", 8), (" 12 ", 12), (8.0, 8), ("-3", -3), (0, 0), (10 ** 30, 10 ** 30),
    ("abc", None), ("", None), (None, None), (True, None), (False, None), (8.5, None),
    (math.nan, None), (math.inf, None), ([8], None), ({"n": 8}, None),
])
def test_parse_int_rejects_bool_nan_and_text(raw, expected):
    assert config.parse_int(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    (True, True), (False, False), (1, True), (0, False), ("true", True), ("False", False), ("yes", True), ("no", False),
    ("on", True), ("off", False), ("1", True), ("0", False),
    ("abc", None), ("", None), (None, None), (2, None), (1.0, None), ([], None), ("nope", None),
])
def test_parse_bool_never_uses_truthiness(raw, expected):
    assert config.parse_bool(raw) is expected


# ── 규칙 표 ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("key,raw,fixed,code", [
    ("backfill_days", "abc", 30, config.BAD_INT),
    ("backfill_days", None, 30, config.BAD_INT),
    ("backfill_days", True, 30, config.BAD_INT),
    ("backfill_days", math.nan, 30, config.BAD_INT),
    ("backfill_days", 0, 30, config.OUT_OF_RANGE),
    ("backfill_days", -7, 30, config.OUT_OF_RANGE),
    ("backfill_days", 10 ** 9, 3650, config.OUT_OF_RANGE),
    ("backfill_days", "45", 45, None),
    ("retention_days", 0, 90, config.OUT_OF_RANGE),
    ("read_workers", "abc", 8, config.BAD_INT),
    ("read_workers", 0, 8, config.OUT_OF_RANGE),
    ("read_workers", -1, 8, config.OUT_OF_RANGE),
    ("read_workers", 999, 32, config.OUT_OF_RANGE),
    ("read_workers", 32, 32, None),
    ("read_workers", "1", 1, None),
    ("refresh_window_days", -5, 0, config.OUT_OF_RANGE),
    ("refresh_window_days", "x", 0, config.BAD_INT),
    ("attention_util", 140, 100, config.OUT_OF_RANGE),
    ("attention_util", -1, 0, config.OUT_OF_RANGE),
    ("attention_util", "35", 35, None),
    ("attention_err", "many", 3, config.BAD_INT),
    ("write_csv", "false", False, None),
    ("write_csv", "true", True, None),
    ("write_csv", "abc", False, config.BAD_BOOL),
    ("rebuild_all", 1, True, None),
    ("rebuild_all", None, False, config.BAD_BOOL),
    ("report_dir", "", "Report", None),
    ("report_dir", None, "Report", None),
    ("report_dir", 5, "Report", config.BAD_STR),
    ("scan_dir", " ScanResult ", "ScanResult", None),
])
def test_performance_values_warn_and_are_fixed(key, raw, fixed, code):
    out, problems = config.normalize_config({key: raw})
    assert out[key] == fixed and type(out[key]) is type(fixed)
    codes = [p.code for p in problems]
    assert codes == ([code] if code else [])
    assert not config.fatal(problems)
    for p in problems:
        assert p.message() and key in p.message()


@pytest.mark.parametrize("key,raw", [
    ("scope_devices", 5), ("scope_devices", {"a": 1}), ("scope_devices", [1, "AOI-1"]), ("scope_devices", [None]),
    ("devices_csv", 3), ("cache_file", ["x"]), ("output_dir", {"p": 1}), ("output_dir", "C:\\out\x00"),
    ("nas_roots", 7), ("nas_roots", ["X:\\", 2]),
    ("scan_dir", "..\\AOI-2\\Scanresult"), ("scan_dir", "a/b"), ("report_dir", ".."), ("output_name", "..\\x.html"),
])
def test_scope_path_and_folder_name_problems_are_fatal_and_untouched(key, raw):
    out, problems = config.normalize_config({key: raw})
    bad = config.fatal(problems)
    assert len(bad) == 1 and bad[0].key == key and bad[0].message()
    assert out[key] == raw or (isinstance(raw, float) and math.isnan(raw))     # fail closed: 고쳐 넣지 않는다
    with pytest.raises(config.ConfigError) as ei:
        config.check_or_raise({key: raw})
    assert bad[0].message() in str(ei.value)


def test_scope_forms_that_are_fine():
    assert config.normalize_config({"scope_devices": "AOI-1"})[0]["scope_devices"] == ["AOI-1"]
    assert config.normalize_config({"scope_devices": [" AOI-1 ", "", "4F-AOI-01"]})[0]["scope_devices"] == ["AOI-1", "4F-AOI-01"]
    assert config.normalize_config({"scope_devices": []})[0]["scope_devices"] == []          # 빈 목록 = 기본값(scope_list)
    assert config.normalize_config({"scope_devices": ["*"]})[1] == []
    assert config.normalize_config({"nas_roots": "X:\\"})[0]["nas_roots"] == ["X:\\"]
    assert config.normalize_config({"nas_roots": None})[0]["nas_roots"] == []


def test_retention_shorter_than_backfill_is_raised_to_backfill():
    out, problems = config.normalize_config({"backfill_days": 60, "retention_days": 30})
    assert out["retention_days"] == 60 and [p.code for p in problems] == [config.RETENTION_LT_BACKFILL]
    out, problems = config.normalize_config({"backfill_days": 30, "retention_days": 90})
    assert out["retention_days"] == 90 and not problems


def test_partial_cfg_is_left_alone_and_unknown_keys_pass_through():
    out, problems = config.normalize_config({"foo": 1})
    assert out == {"foo": 1} and not problems
    out, _ = config.normalize_config(collect.DEFAULT_CONFIG)
    assert out == collect.DEFAULT_CONFIG                                                     # 기본값은 문제 0


def test_default_config_and_example_json_are_clean():
    assert config.normalize_config(collect.DEFAULT_CONFIG)[1] == []
    assert collect.DEFAULT_CONFIG["attention_util"] == 40 and collect.DEFAULT_CONFIG["attention_err"] == 3
    from aoi_capacity.utils import paths
    ex = json.loads((paths._project_root() / "docs" / "config.example.json").read_text(encoding="utf-8"))
    body = {k: v for k, v in ex.items() if not k.startswith("_")}
    assert {"read_workers", "attention_util", "attention_err"} <= set(body)
    assert config.normalize_config(body)[1] == []


# ── 장비 게이트 · 수집 진입점: 잘못된 범위면 NAS 접근 0 ─────────────────────────
class _Spy:
    def __init__(self):
        self.calls = []


@pytest.fixture
def fs_spy(monkeypatch):
    spy = _Spy()
    real = {"scandir": os.scandir, "stat": os.stat, "isdir": os.path.isdir, "isfile": os.path.isfile, "open": builtins.open}

    def wrap(api, fn):
        def inner(*a, **kw):
            if a:
                spy.calls.append((api, str(a[0])))
            return fn(*a, **kw)
        return inner

    for api, fn in real.items():
        target = os.path if api in ("isdir", "isfile") else builtins if api == "open" else os
        monkeypatch.setattr(target, api, wrap(api, fn))
    return spy


def _nas_calls(spy, nas: Path):
    return [c for c in spy.calls if c[1].startswith(str(nas))]


@pytest.mark.parametrize("bad", [{"scope_devices": 5}, {"scope_devices": [1]}, {"scan_dir": "..\\AOI-2\\Scanresult"}])
def test_device_gates_refuse_bad_config_before_touching_anything(tmp_path, fake_nas, fs_spy, bad):
    nas, csv_path = fake_nas
    rows = devices.read_devices_csv(csv_path)
    cfg = make_cfg(tmp_path, csv_path, **bad)
    fs_spy.calls.clear()
    for fn in (lambda: devices.devices_from_rows(rows, cfg), lambda: devices.check_rows(rows, cfg),
               lambda: devices.discover_devices({**cfg, "nas_roots": [str(nas / "X")]}), lambda: devices.resolve_devices(cfg)):
        with pytest.raises(config.ConfigError):
            fn()
    assert _nas_calls(fs_spy, nas) == []


def test_collect_with_bad_scope_raises_before_any_nas_call_and_writes_nothing(tmp_path, fake_nas, fs_spy):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, scope_devices={"not": "a list"})
    fs_spy.calls.clear()
    with pytest.raises(config.ConfigError) as ei:
        collect.collect(cfg)
    assert "scope_devices" in str(ei.value)
    assert _nas_calls(fs_spy, nas) == []
    assert not Path(cfg["cache_file"]).exists()


def test_collect_fixes_performance_values_instead_of_failing(tmp_path, fake_nas):
    """예전: int("abc") 가 워커 안에서 터졌고, backfill_days 0 은 Report 0개를 조용히 읽었다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, backfill_days="abc", read_workers="0", retention_days=0, write_csv="false")
    rows, dev_meta, errors = collect.collect(cfg)
    assert rows and not errors
    assert cfg["backfill_days"] == "abc"                     # 원본 dict 는 고치지 않는다


def test_cli_prints_warnings_and_stops_on_fatal_config(tmp_path, fake_nas, capsys):
    from aoi_capacity import cli, i18n
    nas, csv_path = fake_nas
    conf = tmp_path / "config.json"
    out = tmp_path / "out"
    base = {"devices_csv": str(csv_path), "cache_file": str(out / "c.json"), "output_dir": str(out), "scope_devices": ["*"]}
    conf.write_text(json.dumps({**base, "read_workers": "many", "backfill_days": 3650}), encoding="utf-8")
    assert cli.main(["--config", str(conf)]) == cli.EXIT_OK
    text = capsys.readouterr().out
    assert i18n.KO.CLI_CFG_WARNING_FMT.split("{")[0] in text and "read_workers" in text
    conf.write_text(json.dumps({**base, "scope_devices": 5}), encoding="utf-8")
    assert cli.main(["--config", str(conf)]) == cli.EXIT_FAILED
    text = capsys.readouterr().out
    assert i18n.KO.CLI_CFG_FATAL_FMT.split("{")[0] in text and "scope_devices" in text


# ── GUI 와 CLI 가 같은 정규화 결과 ──────────────────────────────────────────
RAW = {"backfill_days": "abc", "read_workers": 999, "retention_days": "0", "refresh_window_days": -3,
       "write_csv": "yes", "report_dir": "", "scan_dir": " ScanResult ", "threshold_util": 140, "attention_util": 140,
       "threshold_err": "x", "attention_err": "x"}


def test_gui_prefs_and_cli_config_normalize_the_same_way(tmp_path):
    from aoi_capacity import cli
    gui = prefs.to_collect_cfg(prefs.Prefs.from_dict(dict(RAW)))
    conf = tmp_path / "config.json"
    conf.write_text(json.dumps({k: v for k, v in RAW.items() if not k.startswith("threshold_")}), encoding="utf-8")
    cli_cfg = cli.load_config(str(conf))
    keys = ("backfill_days", "read_workers", "retention_days", "refresh_window_days", "write_csv", "report_dir", "scan_dir",
            "attention_util", "attention_err", "rebuild_all", "output_name")
    assert {k: gui[k] for k in keys} == {k: cli_cfg[k] for k in keys}
    assert gui["backfill_days"] == 30 and gui["read_workers"] == 32 and gui["retention_days"] == 90
    assert gui["refresh_window_days"] == 0 and gui["write_csv"] is True and gui["scan_dir"] == "ScanResult"
    assert gui["attention_util"] == 100 and gui["attention_err"] == 3
    assert set(collect.DEFAULT_CONFIG) <= set(gui)


def test_prefs_from_dict_keeps_good_fields_and_never_resets_scope_for_a_bad_version(tmp_path):
    from aoi_capacity.utils import paths
    mine = ["AOI-7", "AOI-8"]
    paths.prefs_file().write_text(json.dumps({"prefs_version": "abc", "scope_devices": mine, "backfill_days": "abc",
                                              "retention_days": 120, "write_csv": "false", "color_mode": 3}), encoding="utf-8")
    p = prefs.load()
    assert p.scope_devices == mine                                  # ★ 장비 목록은 기본 30대로 돌아가지 않는다
    assert p.retention_days == 120 and p.backfill_days == 30 and p.write_csv is False and p.color_mode == "light"   # 잘못된 값 → 기본값(9/23 부터 light)
    assert p.prefs_version == prefs.PREFS_VERSION
    # 옛 기본값 그대로인 목록 + 잘못된 버전: 사용자가 고른 것인지 알 수 없으니 **넓히지 않는다**(fail closed)
    paths.prefs_file().write_text(json.dumps({"prefs_version": None, "scope_devices": ["AOI-25"]}), encoding="utf-8")
    prefs._cached = None
    assert prefs.load().scope_devices == ["AOI-25"]
    # 버전이 옛 정수면 예전처럼 옮긴다
    paths.prefs_file().write_text(json.dumps({"prefs_version": 1, "scope_devices": ["AOI-25"]}), encoding="utf-8")
    prefs._cached = None
    assert prefs.load().scope_devices == list(scope.DEFAULT_SCOPE)


def test_prefs_bad_scope_type_reaches_collect_as_a_fatal_problem_not_a_widened_scope(tmp_path):
    p = prefs.Prefs.from_dict({"scope_devices": 5})
    cfg = prefs.to_collect_cfg(p)
    assert cfg["scope_devices"] == 5                                # 그대로 두고
    with pytest.raises(config.ConfigError):
        config.check_or_raise(cfg)                                  # 실행 시점에 막는다
    assert prefs.to_collect_cfg(prefs.Prefs.from_dict({"scope_devices": None}))["scope_devices"] == list(scope.DEFAULT_SCOPE)
    assert prefs.to_collect_cfg(prefs.Prefs.from_dict({"scope_devices": "AOI-3"}))["scope_devices"] == ["AOI-3"]


# ── D14: 문턱이 결과 HTML 로 나간다 ─────────────────────────────────────────
def _meta(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text.split('id="embedded">')[1].split("</script>")[0])["meta"]


def test_write_html_emits_dashboard_settings_from_cfg(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, attention_util=35, attention_err=5)
    target = collect.write_html(cfg, [], [], [], time.time())
    assert _meta(Path(target))["dashboard_settings"] == {"attentionUtil": 35, "attentionErr": 5}
    cfg = make_cfg(tmp_path, csv_path, attention_util="bad", attention_err=-9)
    target = collect.write_html(cfg, [], [], [], time.time())
    assert _meta(Path(target))["dashboard_settings"] == {"attentionUtil": 40, "attentionErr": 0}
    cfg = make_cfg(tmp_path, csv_path)
    cfg.pop("attention_util"); cfg.pop("attention_err")
    target = collect.write_html(cfg, [], [], [], time.time())
    assert _meta(Path(target))["dashboard_settings"] == {"attentionUtil": 40, "attentionErr": 3}


def test_gui_thresholds_flow_into_dashboard_settings():
    cfg = prefs.to_collect_cfg(prefs.Prefs(threshold_util=55, threshold_err=2))
    assert config.dashboard_settings(cfg) == {"attentionUtil": 55, "attentionErr": 2}
    assert prefs.Prefs().threshold_util == 40 and prefs.Prefs().threshold_err == 3
