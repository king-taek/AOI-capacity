"""dev/tools/design_bundle.py 가드 — 디자인 프로토타입 번들은 표준 라이브러리만 쓰고, 마크업만 camelCase 를 인코딩하며, 결과가 한 파일로 닫힌다."""
from __future__ import annotations

import ast
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "dev" / "tools" / "design_bundle.py"


def _load():
    spec = importlib.util.spec_from_file_location("design_bundle", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tool_imports_only_the_standard_library():
    tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    assert names <= set(sys.stdlib_module_names), names - set(sys.stdlib_module_names)


def test_camel_attrs_are_encoded_only_in_markup_not_in_the_script():
    """실측 회귀: 스크립트의 `eDay=` 까지 `sc-camel-e-day=` 로 바꾸면 'Missing initializer in const declaration' 으로 화면이 죽는다."""
    mod = _load()
    dc = ('<script src="./support.js"></script>\n<x-dc>\n<helmet>\n<style></style>\n<script src="aoi-data.js"></script>\n</helmet>\n'
          '<button onClick="{{ go }}" title="x">a</button>\n</x-dc>\n'
          '<script type="text/x-dc" data-dc-script>const eDay=1, mDev=2; const onClick=3;</script>')
    out = mod.bundle_template(dc, "RT", "DATA")
    assert 'sc-camel-on-click="{{ go }}"' in out and '<script src="DATA"></script>' in out and '<script src="RT"></script>' in out
    assert "const eDay=1, mDev=2; const onClick=3;" in out


def test_offline_variant_waits_for_window_data_instead_of_fetching():
    mod = _load()
    main = "<x-dc>\n<helmet>\n<style>x</style>\n</helmet>\n</x-dc>\n<script>" + mod.FETCH_LINE + "</script>"
    off = mod.offline_variant(main)
    assert "fetch(" not in off and "window.AOI_DATA" in off and '<script src="aoi-data.js"></script>' in off


def test_build_produces_one_closed_file_whose_logic_parses(tmp_path):
    mod = _load()
    if not (mod.MAIN.is_file() and mod.DATA.is_file() and mod.SHELL.is_file()):
        pytest.skip("디자인 프로토타입 파일이 없는 트리")
    out = mod.build(tmp_path / "offline.html")
    html = out.read_text(encoding="utf-8")
    assert "__MANIFEST__" not in html and "__TEMPLATE__" not in html
    # 바깥으로 나가는 <script src=http…>·<link href=http…> 는 없다(ext_resources 의 unpkg 는 이름표일 뿐 번들 안에 리소스가 있다)
    assert not re.search(r'<script[^>]+src="https?://', html) and not re.search(r'<link[^>]+href="https?://', html)
    node = shutil.which("node")
    if not node:
        pytest.skip("node 없음")
    main = mod.MAIN.read_text(encoding="utf-8")
    js = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', main, re.S).group(1)
    f = tmp_path / "logic.js"
    f.write_text("class DCLogic{constructor(p){this.props=p}}\n" + js, encoding="utf-8")
    r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
