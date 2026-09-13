"""★ NAS 읽기 전용 회귀 가드.

세 겹으로 지킨다.
1. 경로 판정(`is_under`) 이 Windows 의미론(드라이브 문자, UNC, 대소문자, 긴 경로 접두)에서 맞는가.
2. 정적: collect.py 에서 쓰기 API 는 허용 함수 3개 안에만 있고, 각 함수가 assert_local/check_cfg 를 부르는가.
3. 동적: 실제 수집·출력을 돌리는 동안 어떤 쓰기 API 도 NAS 루트 아래 경로로 불리지 않고, NAS 파일의 해시·mtime 이 전후 동일한가.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import ntpath
import os
import shutil
import time
from pathlib import Path

import pytest

from aoi_capacity import collect, nas_guard
from conftest import make_cfg

WRITE_FUNCS = {"_save_cache", "write_html", "_write_csv"}


# ── 1. 경로 판정 ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("path,root,expected", [
    (r"X:\AOI-1\Report\a.htm", r"X:\\", True),
    (r"X:\AOI-1\Report\a.htm", "X:", True),
    (r"x:\aoi-1", r"X:\AOI-1", True),                      # 대소문자
    (r"X:\AOI-10", r"X:\AOI-1", False),                    # 접두 문자열이 아니라 경로 단위
    (r"\\10.142.80.90\Camtek\AOI-2\x", r"\\10.142.80.90\Camtek", True),
    (r"\\?\X:\AOI-1\x", r"X:\\", True),                    # 긴 경로 접두
    (r"\\?\UNC\host\share\a", r"\\host\share", True),
    (r"C:\Users\me\AppData\Local\AOI_Capacity", r"X:\\", False),
    (r"X:/AOI-1/Report", r"X:\AOI-1", True),               # 슬래시 혼용
])
def test_is_under_windows_semantics(path, root, expected):
    assert nas_guard.is_under(path, root, pathmod=ntpath) is expected


def test_expand_roots_adds_share_root_for_unc():
    roots = nas_guard.expand_roots([r"\\host\share\AOI-1", "X:\\", ""])
    assert r"\\host\share" in roots and "X:\\" in roots and "" not in roots


def test_assert_local_and_check_cfg(tmp_path):
    nas = tmp_path / "nas"
    nas.mkdir()
    nas_guard.assert_local(tmp_path / "out", [str(nas)])
    with pytest.raises(nas_guard.NasWriteRefused):
        nas_guard.assert_local(nas / "out", [str(nas)])
    with pytest.raises(nas_guard.NasWriteRefused):
        nas_guard.check_cfg({"nas_roots": [str(nas)], "cache_file": str(nas / "c.json"), "output_dir": str(tmp_path)})


def test_roots_for_cfg_reads_every_row_even_disabled(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    roots = nas_guard.roots_for_cfg({"devices_csv": str(csv_path), "nas_roots": []})
    assert str(nas / "X") in roots and str(nas / "none") in roots     # 꺼둔/접근불가 행도 금지 구역


# ── 2. 정적 가드 ─────────────────────────────────────────────────────────
def _enclosing_function(tree, node):
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(fn):
                if sub is node:
                    return fn.name
    return None


def _call_name(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Attribute):
        base = f.value
        if isinstance(base, ast.Name):
            return f"{base.id}.{f.attr}"
        if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
            return f"{base.value.id}.{base.attr}.{f.attr}"
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def test_static_write_calls_only_in_allowed_functions():
    src = Path(collect.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        writes = False
        if name == "open":
            mode = ""
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value)
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = str(kw.value.value)
            writes = any(ch in mode for ch in "wax+")
        elif name in {"os.replace", "os.rename", "os.remove", "os.unlink", "os.makedirs", "os.mkdir",
                      "os.utime", "os.chmod", "os.rmdir"} or name.startswith("shutil."):
            writes = True
        if writes:
            fn = _enclosing_function(tree, node)
            if fn not in WRITE_FUNCS:
                offenders.append(f"{name} in {fn} (line {node.lineno})")
    assert not offenders, "허용 함수 밖의 쓰기 호출: " + ", ".join(offenders)


def test_static_every_write_function_guards_first():
    src = Path(collect.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for name in WRITE_FUNCS:
        fn = fns[name]
        first = fn.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            first = fn.body[1]                                  # docstring 건너뜀
        assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Call), name
        assert _call_name(first.value) in {"nas_guard.check_cfg", "nas_guard.assert_local"}, name


def test_nas_guard_module_has_no_write_helpers():
    src = Path(nas_guard.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) == "open":
            mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r"
            assert not any(ch in str(mode) for ch in "wax+")


# ── 3. 동적 트립와이어 ──────────────────────────────────────────────────
def _snapshot(root: Path):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p)] = (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
    return out


def test_dynamic_no_write_under_nas(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    before = _snapshot(nas)
    touched = []
    real_open = builtins.open

    def spy_open(file, mode="r", *a, **k):
        if any(ch in str(mode) for ch in "wax+"):
            touched.append(("open", str(file)))
        return real_open(file, mode, *a, **k)

    monkeypatch.setattr(builtins, "open", spy_open)
    for mod, names in ((os, ["replace", "rename", "remove", "unlink", "makedirs", "mkdir", "utime", "chmod", "rmdir"]),
                       (shutil, ["copy", "copy2", "copyfile", "move", "rmtree"])):
        for n in names:
            real = getattr(mod, n)

            def spy(*a, _n=n, _real=real, **k):
                touched.append((_n, str(a[0]) if a else ""))
                return _real(*a, **k)

            monkeypatch.setattr(mod, n, spy)

    rows, dev_meta, errors = collect.collect(cfg)
    collect.write_html(cfg, rows, dev_meta, errors, time.time(), mode="gui")

    under_nas = [t for t in touched if nas_guard.is_under(t[1], str(nas))]
    assert not under_nas, f"NAS 아래 쓰기 시도: {under_nas}"
    assert touched, "쓰기 API 가 전혀 기록되지 않았다(트립와이어가 동작하지 않음)"
    assert _snapshot(nas) == before, "NAS 파일이 바뀌었다"
    assert (tmp_path / "out" / "AOI_capacity.html").exists()
