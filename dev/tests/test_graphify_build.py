"""dev/tools/graphify_build.py 가드 — 임시 JS 는 절대 남지 않고(테스트는 패키지 폴더에 아무것도 만들지 않고), 워크플로는 main 에 커밋하지 않는다.

같은 파일에서 `.github/workflows/*.yml` 전체의 계약도 본다 — yaml 이 없는 환경에서도 도는 글자 검사와, yaml 이 있을 때의 구조 검사.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "dev" / "tools" / "graphify_build.py"
WORKFLOWS = ROOT / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "graphify.yml"
TESTS_WORKFLOW = WORKFLOWS / "tests.yml"
ASSETS = ROOT / "aoi_capacity" / "ui" / "assets"
TEMPLATE = ASSETS / "template.html"


def _load():
    spec = importlib.util.spec_from_file_location("graphify_build", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fingerprint(p: Path):
    """(sha256, mtime_ns) — 같은 내용을 다시 써도 mtime 이 바뀌므로 git status 로는 못 잡는 덮어쓰기까지 검출한다."""
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns


def _assets_snapshot():
    """패키지 assets 폴더의 파일 이름 집합 + template.html 지문 — 임시 JS 가 잠깐이라도 생기면 이름 집합이 달라진다."""
    return sorted(p.name for p in ASSETS.iterdir()), _fingerprint(TEMPLATE)


@pytest.fixture(scope="module", autouse=True)
def _package_assets_untouched():
    """S04 가드: 이 모듈의 어떤 테스트도 aoi_capacity/ui/assets 안에 파일을 만들거나 바꾸지 않는다."""
    before = _assets_snapshot()
    yield
    assert _assets_snapshot() == before, "테스트가 패키지 assets 폴더를 건드렸다(임시 JS 는 tmp_path 로 보내야 한다)"


@pytest.fixture
def tmp_inline_js(tmp_path, monkeypatch):
    """임시 JS 위치를 tmp 로 돌린다 — build() 는 호출 시점의 모듈 상수를 읽으므로 monkeypatch 가 먹는다."""
    mod = _load()
    dst = tmp_path / "_template_inline.js"
    monkeypatch.setattr(mod, "INLINE_JS", dst)
    return mod, dst


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


def test_default_temp_js_sits_next_to_the_template():
    """실제 실행에서는 template 옆이어야 graphify 가 그래프에 넣는다(모듈 문서 참고) — 기본값은 바꾸지 않는다."""
    mod = _load()
    assert mod.INLINE_JS == TEMPLATE.with_name("_template_inline.js")
    assert not mod.INLINE_JS.exists()


def test_write_inline_js_accepts_a_destination(tmp_path):
    mod = _load()
    dst = tmp_path / "x" / "inline.js"
    dst.parent.mkdir()
    assert mod.write_inline_js(dst=dst) == dst
    assert "function buildModel(" in dst.read_text(encoding="utf-8")


def test_temp_js_is_removed_even_when_graphify_fails(tmp_inline_js, monkeypatch):
    mod, dst = tmp_inline_js
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/graphify")
    seen = []

    def fake_run(cmd, cwd=None):
        seen.append(cmd)
        assert dst.exists(), "graphify 가 도는 동안에는 임시 JS 가 있어야 한다"
        return subprocess.CompletedProcess(cmd, 1)

    assert mod.build(run=fake_run) == 1
    assert not dst.exists()
    assert seen and seen[0][:2] == ["graphify", "extract"] and "--code-only" in seen[0]


def test_temp_js_is_removed_on_exception(tmp_inline_js, monkeypatch):
    mod, dst = tmp_inline_js
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/graphify")

    def boom(cmd, cwd=None):
        raise OSError("boom")

    with pytest.raises(OSError):
        mod.build(run=boom)
    assert not dst.exists()


def test_explicit_inline_js_argument_wins_over_the_constant(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/graphify")
    explicit = tmp_path / "explicit.js"
    seen = []

    def fake_run(cmd, cwd=None):
        seen.append(explicit.exists())
        return subprocess.CompletedProcess(cmd, 0)

    assert mod.build(no_viz=True, run=fake_run, inline_js=explicit) == 0
    assert seen == [True, True] and not explicit.exists()


def test_build_paths_leave_the_package_folder_untouched(tmp_inline_js, monkeypatch):
    """S04 수락 기준: 도구의 코드 경로를 전부 태워도(성공·실패·예외) 패키지 폴더의 이름 집합·template 지문이 그대로다."""
    mod, dst = tmp_inline_js
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/graphify")

    def boom(cmd, cwd=None):
        raise RuntimeError("x")

    before = _assets_snapshot()
    assert mod.build(run=lambda cmd, cwd=None: subprocess.CompletedProcess(cmd, 0)) == 0
    assert mod.build(run=lambda cmd, cwd=None: subprocess.CompletedProcess(cmd, 3)) == 3
    with pytest.raises(RuntimeError):
        mod.build(run=boom)
    assert _assets_snapshot() == before
    assert not dst.exists()


def test_output_is_gitignored_but_the_temp_js_is_not():
    """graphify 는 .gitignore 를 따른다 — 임시 JS 를 무시 목록에 넣으면 그래프에서도 빠진다(실측: 함수 0개)."""
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "graphify-out/" in ignore
    assert not any("_template_inline" in l for l in ignore)


# ── 워크플로 계약(글자 검사 — yaml 이 없는 환경에서도 돈다) ─────────────────────────

def _workflow_files() -> list[Path]:
    files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    assert WORKFLOW in files and TESTS_WORKFLOW in files
    return files


def _top_level_permissions(text: str) -> list[str]:
    """열 0 의 `permissions:` 블록 안 줄들(들여쓴 자식만). 없으면 []."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if line.rstrip() == "permissions:":
            for nxt in lines[i + 1:]:
                if nxt.strip() and not nxt.startswith(" "):
                    break
                if nxt.strip():
                    out.append(nxt.strip())
    return out


def test_no_workflow_pushes_to_main_textually():
    """yaml 없이도 도는 계약: 어떤 워크플로도 main 에 push 하지 않는다 — 업데이터가 main SHA 로 배포하므로 봇 커밋은 헛 업데이트가 된다."""
    for wf in _workflow_files():
        text = wf.read_text(encoding="utf-8")
        assert "HEAD:main" not in text and "push origin main" not in text, wf.name
        for line in text.splitlines():
            if "git push" in line:
                assert wf == WORKFLOW, f"{wf.name}: 푸시하는 워크플로는 graphify 뿐이어야 한다"
                assert "graphify-out:graphify-out" in line and not re.search(r":main\b", line), line
    graph = WORKFLOW.read_text(encoding="utf-8")
    assert "dev/tools/graphify_build.py" in graph
    assert "graphify-out:graphify-out" in graph, "결과는 별도 브랜치로만 간다"


def test_graphify_write_permission_is_confined_to_the_publish_job_textually():
    """S16: 워크플로 수준 권한은 없고, contents: write 는 게시 잡 한 곳뿐이며 분석 잡은 read 다."""
    raw = WORKFLOW.read_text(encoding="utf-8")
    text = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))   # 주석은 계약이 아니다
    assert _top_level_permissions(text) == [], "워크플로 수준 permissions 를 두지 않는다(잡별로 최소 권한)"
    assert text.count("contents: write") == 1
    assert text.count("contents: read") >= 1
    # write 는 publish 잡 아래에서만 — 그 줄 앞의 마지막 잡 이름이 publish 다
    job_names = []
    in_jobs = False
    for line in text.splitlines():
        if line.rstrip() == "jobs:":
            in_jobs = True
            continue
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if in_jobs and m:
            job_names.append(m.group(1))
        if "contents: write" in line:
            assert job_names and job_names[-1] == "publish", job_names
    assert job_names == ["graph", "publish"]


def test_tests_workflow_contract_textually():
    """S02: 업데이터가 나중에 이 이름의 성공 실행을 요구한다 — 이름은 정확히 `tests`, 읽기 권한만, main 푸시·PR 에서 전체 스위트."""
    text = TESTS_WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"^name: tests\s*$", text, re.M), "워크플로 이름은 정확히 tests"
    assert _top_level_permissions(text) == ["contents: read"]
    assert "contents: write" not in text
    assert "pull_request:" in text and re.search(r"branches:\s*\[main\]", text)
    assert "cancel-in-progress: true" in text
    assert "-r requirements.txt -r dev/requirements-dev.txt" in text
    assert "import yaml, PyQt6" in text and "node --version" in text, "사전 점검: 필수 의존성이 없으면 실패"
    assert "python -m pytest -q --durations=15" in text, "전체 스위트(slow 포함) — pytest.ini 의 -q 그대로"
    assert 'QT_QPA_PLATFORM: offscreen' in text
    assert "playwright install --with-deps chromium" in text and "-m browser" in text
    assert re.search(r'-eq 5', text), "browser 테스트가 아직 없으면 exit 5 를 통과로 처리"
    assert "-m \"not slow\"" not in text and "-m 'not slow'" not in text and "not slow" not in text
    # S14: PR 에서 코드 변경에 진행상황.md 동반 검사 — merge-base 를 구하려면 전체 이력, 규칙은 도구 한 곳
    assert "dev/tools/progress_doc_check.py" in text and "fetch-depth: 0" in text
    assert "github.event.pull_request.base.sha" in text and "github.event.pull_request.head.sha" in text


def test_browser_marker_is_registered():
    ini = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert re.search(r"^\s+browser:", ini, re.M)


def test_dev_requirements_declare_yaml_and_playwright_but_runtime_does_not():
    """S10: 워크플로 가드가 조용히 skip 되지 않게 dev 의존성에 선언 — 운영 requirements 에는 섞지 않는다."""
    dev = (ROOT / "dev" / "requirements-dev.txt").read_text(encoding="utf-8").lower()
    run = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert re.search(r"^pyyaml", dev, re.M) and re.search(r"^playwright", dev, re.M)
    assert "yaml" not in run and "playwright" not in run


# ── 워크플로 계약(구조 검사 — yaml 이 있을 때; CI 는 사전 점검으로 yaml 을 보장한다) ─────

def _yaml_doc(path: Path) -> dict:
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _on(doc: dict) -> dict:
    return doc.get("on") or doc.get(True)          # PyYAML 은 'on' 을 True 로 읽는다


def test_workflow_runs_on_main_push_and_never_commits_to_main():
    doc = _yaml_doc(WORKFLOW)
    assert _on(doc)["push"]["branches"] == ["main"]
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "dev/tools/graphify_build.py" in text
    assert "graphify-out:graphify-out" in text, "결과는 별도 브랜치로만 간다"
    assert "HEAD:main" not in text and "push origin main" not in text


def test_graphify_jobs_have_least_privilege():
    doc = _yaml_doc(WORKFLOW)
    assert "permissions" not in doc
    jobs = doc["jobs"]
    assert set(jobs) == {"graph", "publish"}
    assert jobs["graph"]["permissions"] == {"contents": "read"}
    assert jobs["publish"]["permissions"] == {"contents": "write"}
    assert jobs["publish"]["needs"] == "graph"
    graph_steps = " ".join(str(s.get("run", "")) for s in jobs["graph"]["steps"])
    assert "git push" not in graph_steps, "분석 잡은 어디에도 푸시하지 않는다"


def test_tests_workflow_structure():
    doc = _yaml_doc(TESTS_WORKFLOW)
    assert doc["name"] == "tests"
    on = _on(doc)
    assert on["push"]["branches"] == ["main"] and "pull_request" in on
    assert doc["permissions"] == {"contents": "read"}
    assert doc["concurrency"]["cancel-in-progress"] is True
    jobs = doc["jobs"]
    assert set(jobs) == {"core", "browser", "progress-doc"}
    pd = jobs["progress-doc"]
    assert pd["if"] == "github.event_name == 'pull_request'" and "permissions" not in pd
    assert any(s.get("with", {}).get("fetch-depth") == 0 for s in pd["steps"] if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert any("progress_doc_check.py" in str(s.get("run", "")) for s in pd["steps"])
    for name in ("core", "browser"):
        assert jobs[name]["runs-on"] == "ubuntu-latest"
        uses = [s.get("uses", "") for s in jobs[name]["steps"]]
        assert any(u.startswith("actions/checkout@") for u in uses)
        assert any(u.startswith("actions/setup-python@") for u in uses)
    core_uses = [s.get("uses", "") for s in jobs["core"]["steps"]]
    assert any(u.startswith("actions/setup-node@") for u in core_uses)
    py = [s for s in jobs["core"]["steps"] if str(s.get("uses", "")).startswith("actions/setup-python@")][0]
    assert str(py["with"]["python-version"]) == "3.11"
    node = [s for s in jobs["core"]["steps"] if str(s.get("uses", "")).startswith("actions/setup-node@")][0]
    assert str(node["with"]["node-version"]) == "22"
