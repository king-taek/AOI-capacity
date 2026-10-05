"""D67: 레시피 묶음 파일 — 수집기가 찾아 결과 HTML 의 meta.recipe_groups 로 담는다(읽기만)."""
import json

from aoi_capacity import collect, recipes

import sample_rows


def _w(p, saved, groups):
    p.write_text(json.dumps({"v": 1, "saved": saved, "groups": groups}, ensure_ascii=False), encoding="utf-8")


def test_normalize_drops_bad_and_duplicate_entries():
    d = recipes.normalize({"saved": "2026-10-05T10:00:00", "groups": [
        {"name": " A ", "jobs": ["j1", "j2", 3]}, {"name": "A", "jobs": ["j3"]}, {"name": "", "jobs": ["j4"]},
        {"name": "B", "jobs": ["j1", "j5"]}, {"name": "C", "jobs": []}, "x"]})
    assert d == {"v": 1, "saved": "2026-10-05T10:00:00", "groups": [{"name": "A", "jobs": ["j1", "j2"]}, {"name": "B", "jobs": ["j5"]}]}
    assert recipes.normalize({"groups": "x"}) is None and recipes.normalize([]) is None


def test_load_picks_the_latest_saved_among_data_folder_and_downloads(tmp_path, monkeypatch):
    data, home = tmp_path / "data", tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    data.mkdir()
    from aoi_capacity.utils import paths
    monkeypatch.setattr(paths, "data_root", lambda: data)
    monkeypatch.setenv("USERPROFILE", str(home))
    _w(data / "recipe_groups.json", "2026-10-01T00:00:00", [{"name": "OLD", "jobs": ["j"]}])
    _w(home / "Downloads" / "recipe_groups (1).json", "2026-10-05T09:00:00", [{"name": "NEW", "jobs": ["j"]}])
    (home / "Downloads" / "recipe_groups (2).json").write_text("{broken", encoding="utf-8")
    d, path = recipes.load({})
    assert d["groups"][0]["name"] == "NEW" and path.endswith("recipe_groups (1).json")
    d2, path2 = recipes.load({"recipe_groups_file": str(data / "recipe_groups.json")})   # 지정하면 그 파일만
    assert d2["groups"][0]["name"] == "OLD"
    assert recipes.load({"recipe_groups_file": str(tmp_path / "none.json")}) == (None, "")


def test_write_html_embeds_recipe_groups(tmp_path, monkeypatch):
    rg = tmp_path / "rg.json"
    _w(rg, "2026-10-05T09:00:00", [{"name": "TB500 RDL3", "jobs": ["TB500_RDL3 - Multi"]}])
    cfg = dict(collect.DEFAULT_CONFIG, output_dir=str(tmp_path / "out"), cache_file=str(tmp_path / "c.json"),
               recipe_groups_file=str(rg), split_mb=0)
    out = collect.write_html(cfg, [], [], [], 0.0)
    meta = sample_rows.unfold(sample_rows.embedded(open(out, encoding="utf-8").read()))[1]
    assert meta["recipe_groups"] == {"v": 1, "saved": "2026-10-05T09:00:00", "groups": [{"name": "TB500 RDL3", "jobs": ["TB500_RDL3 - Multi"]}]}
