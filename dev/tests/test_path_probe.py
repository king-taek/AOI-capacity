"""배포 경로 자동 시험(10/30 임시) — 가짜 공유 폴더(임시 폴더)에서 끝까지 돌고 zip 한 장이 나오는지, 장비 NAS 아래면 아무것도 쓰지 않는지.
시험 경로 글자는 실제와 같은 종류(공백 · 한글 · 따옴표)로 둔다."""
from __future__ import annotations

import copy
import zipfile
from pathlib import Path

from aoi_capacity import collect, i18n, path_probe

K = i18n.KO


def _cfg(tmp_path, **over):
    cfg = copy.deepcopy(collect.DEFAULT_CONFIG)
    cfg.update({"scope_devices": ["*"], "output_dir": str(tmp_path / "out"), "nas_roots": []})
    cfg.update(over)
    return cfg


def _tree(root: Path):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_full_run_makes_one_zip_and_cleans_up_the_share(tmp_path):
    share = tmp_path / "전산 X" / "임현택 ENG'R"
    share.mkdir(parents=True)
    out = tmp_path / "res"
    res = path_probe.run(_cfg(tmp_path), str(out), root=str(share))
    assert res["ok"], [r for r in res["rows"] if r["ok"] is False]
    zips = list(out.glob("*.zip"))
    assert zips == [Path(res["path"])]
    with zipfile.ZipFile(zips[0]) as z:
        names = z.namelist()
        assert {"요약.txt", "결과.json", "검사표.tsv", "환경.txt", "app_log_최근.txt"} <= set(names)
        assert any(n.startswith("바로가기_샘플/") and n.endswith("AOI_ALL_shortcut.url") for n in names)
        assert any(n.startswith("바로가기_샘플/") and n.endswith("AOI_LOT_shortcut.url") for n in names)
        assert "모두 통과" in z.read("요약.txt").decode("utf-8")
    # 두 배포 폴더만 남고 시험 폴더·파일은 모두 지워졌다
    assert _tree(share) == [K.TEST_PATH_LOT_DIR, K.TEST_PATH_FULL_DIR]
    names = {r["name"] for r in res["rows"]}
    assert any("latest.js" in n for n in names) and any("AOI.ico" in n for n in names) and any("바로가기" in n for n in names)
    assert any("한글" in n for n in names)


def test_unreachable_share_still_gives_a_zip_with_the_failure(tmp_path):
    res = path_probe.run(_cfg(tmp_path), str(tmp_path / "res"), root=str(tmp_path / "없는 공유"))
    assert not res["ok"] and res["failed"] >= 1
    with zipfile.ZipFile(res["path"]) as z:
        assert "실패" in z.read("요약.txt").decode("utf-8")
    assert not (tmp_path / "없는 공유").exists()                 # 닿지 못한 곳은 만들지 않는다


def test_equipment_nas_is_refused_without_writing(tmp_path):
    nas = tmp_path / "nas"
    (nas / "AOI-1").mkdir(parents=True)
    before = _tree(nas)
    res = path_probe.run(_cfg(tmp_path, nas_roots=[str(nas)]), str(tmp_path / "res"), root=str(nas / "AOI-1"))
    assert not res["ok"] and _tree(nas) == before
    assert any("장비 NAS" in r["detail"] for r in res["rows"])


def test_result_folder_under_the_nas_is_refused(tmp_path):
    import pytest
    from aoi_capacity.nas_guard import NasWriteRefused
    nas = tmp_path / "nas"
    nas.mkdir()
    with pytest.raises(NasWriteRefused):
        path_probe.run(_cfg(tmp_path, nas_roots=[str(nas)]), str(nas / "res"), root=str(tmp_path))
    assert not (nas / "res").exists()


def test_stop_request_ends_early_but_still_writes_the_zip(tmp_path):
    share = tmp_path / "s"
    share.mkdir()
    res = path_probe.run(_cfg(tmp_path), str(tmp_path / "res"), root=str(share), should_stop=lambda: True)
    assert res["stopped"] and Path(res["path"]).is_file()
