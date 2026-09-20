"""dev/tools/graphify_build.py 가드 — 임시 JS 는 절대 남지 않고, 워크플로는 main 에 커밋하지 않는다."""
from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "dev" / "tools" / "graphify_build.py"
WORKFLOW = ROOT / ".github" / "workflows" / "graphify.yml"


def _load():
    spec = importlib.util.spec_from_file_location("graphify_build", TOOL)
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


def test_inline_scripts_take_every_script_body_in_order():
    mod = _load()
    html = "<html><script>const a=1;</script><p>x</p><script type='text/javascript'>function b(){}</script></html>"
    assert mod.inline_scripts(html) == "const a=1;\nfunction b(){}"


def test_real_template_yields_the_dashboard_functions():
    mod = _load()
    js = mod.inline_scripts(mod.TEMPLATE.read_text(encoding="utf-8"))
    for fn in ("function buildModel(", "function dayStats(", "jobKey", "lotName", "function homeHtml("):
        assert fn in js


def test_temp_js_is_removed_even_when_graphify_fails(monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/graphify")
    seen = []

    def fake_run(cmd, cwd=None):
        seen.append(cmd)
        assert mod.INLINE_JS.exists(), "graphify 가 도는 동안에는 임시 JS 가 있어야 한다"
        return subprocess.CompletedProcess(cmd, 1)

    assert mod.build(run=fake_run) == 1
    assert not mod.INLINE_JS.exists()
    assert seen and seen[0][:2] == ["graphify", "extract"] and "--code-only" in seen[0]


def test_temp_js_is_removed_on_exception(monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/graphify")

    def boom(cmd, cwd=None):
        raise OSError("boom")

    with pytest.raises(OSError):
        mod.build(run=boom)
    assert not mod.INLINE_JS.exists()


def test_output_is_gitignored_but_the_temp_js_is_not():
    """graphify 는 .gitignore 를 따른다 — 임시 JS 를 무시 목록에 넣으면 그래프에서도 빠진다(실측: 함수 0개)."""
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "graphify-out/" in ignore
    assert not any("_template_inline" in l for l in ignore)


def test_workflow_runs_on_main_push_and_never_commits_to_main():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on = doc.get("on") or doc.get(True)          # PyYAML 은 'on' 을 True 로 읽는다
    assert on["push"]["branches"] == ["main"]
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "dev/tools/graphify_build.py" in text
    assert "graphify-out:graphify-out" in text, "결과는 별도 브랜치로만 간다"
    assert "HEAD:main" not in text and "push origin main" not in text
