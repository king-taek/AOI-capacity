"""dev/tools/design_bundle.py 가드 — 디자인 프로토타입 번들은 표준 라이브러리만 쓰고, 마크업만 camelCase 를 인코딩하며, 결과가 한 파일로 닫힌다."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "dev" / "tools" / "design_bundle.py"
# 이 테스트 모듈이 절대 건드리면 안 되는 저장소 파일 — 추적 중인 오프라인 DC 변형과, 도구의 기본 단일 HTML 출력 위치
TRACKED_OFFLINE_DC = ROOT / "docs" / "design" / "dashboard-redesign" / "app" / "AOI-Dashboard-offline.dc.html"
DEFAULT_SINGLE_HTML = ROOT / "docs" / "design" / "dashboard-redesign" / "AOI 가동 현황 (오프라인).html"


def _load():
    spec = importlib.util.spec_from_file_location("design_bundle", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fingerprint(p: Path):
    """(sha256, mtime_ns) — 내용이 같아도 다시 쓰면 mtime 이 바뀌므로 git status 로는 못 잡는 '같은 내용 덮어쓰기' 까지 검출한다."""
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns


@pytest.fixture(scope="module", autouse=True)
def _tracked_design_files_untouched():
    """S04 가드: 이 모듈의 어떤 테스트도 저장소의 디자인 파일을 다시 쓰지 않는다(sha256·mtime 전후 동일)."""
    before = {p: _fingerprint(p) for p in (TRACKED_OFFLINE_DC, DEFAULT_SINGLE_HTML)}
    yield
    after = {p: _fingerprint(p) for p in before}
    assert after == before, "테스트가 저장소의 디자인 파일을 다시 썼다(tmp_path 로 출력해야 한다)"


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


def test_build_writes_only_where_it_is_told(tmp_path):
    """S04: build 는 두 출력(단일 HTML · 오프라인 DC)을 넘겨준 경로에만 쓰고 저장소의 추적 파일은 sha256·mtime 까지 그대로다."""
    mod = _load()
    if not (mod.MAIN.is_file() and mod.DATA.is_file() and mod.SHELL.is_file()):
        pytest.skip("디자인 프로토타입 파일이 없는 트리")
    assert mod.OFFLINE_DC == TRACKED_OFFLINE_DC and mod.DEFAULT_OUT == DEFAULT_SINGLE_HTML   # 기본값은 그대로(도구 사용법 불변)
    before = (_fingerprint(TRACKED_OFFLINE_DC), _fingerprint(DEFAULT_SINGLE_HTML))
    out = mod.build(tmp_path / "single.html", tmp_path / "sub" / "offline.dc.html")
    assert out == tmp_path / "single.html" and out.is_file()
    assert (tmp_path / "sub" / "offline.dc.html").is_file()
    assert (_fingerprint(TRACKED_OFFLINE_DC), _fingerprint(DEFAULT_SINGLE_HTML)) == before
    # 오프라인 DC 변형의 내용은 원래 규칙 그대로
    off = (tmp_path / "sub" / "offline.dc.html").read_text(encoding="utf-8")
    assert "window.AOI_DATA" in off and 'fetch("aoi-data.json")' not in off


def test_build_produces_one_closed_file_whose_logic_parses(tmp_path):
    mod = _load()
    if not (mod.MAIN.is_file() and mod.DATA.is_file() and mod.SHELL.is_file()):
        pytest.skip("디자인 프로토타입 파일이 없는 트리")
    out = mod.build(tmp_path / "offline.html", tmp_path / "AOI-Dashboard-offline.dc.html")
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
