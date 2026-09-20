"""graphify 코드 지도를 만든다 — 로컬에서도, GitHub Actions(main 푸시마다)에서도 같은 절차.

    python dev/tools/graphify_build.py [--no-viz] [--out graphify-out]

graphify 는 HTML 안의 인라인 <script> 를 파싱하지 않아 결과 화면(template.html)의 JS 168개 함수가
그래프에 0개로 남는다. 그래서 스크립트만 `aoi_capacity/ui/assets/_template_inline.js` 로 **잠깐** 빼내
추출한 뒤, 성공하든 실패하든 그 임시 파일을 지운다(저장소에는 절대 남기지 않는다).
★ .gitignore 에 넣지 않는다 — graphify 가 .gitignore 를 따르므로 무시하면 그래프에서도 빠진다(실측 함수 0개).

- 표준 라이브러리만 쓴다. NAS·네트워크 없음. 쓰는 것은 임시 JS 한 개와 graphify-out/ 뿐.
- `graphifyy` 패키지(명령 `graphify`)가 깔려 있어야 한다: pip install "graphifyy[sql]"
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "aoi_capacity" / "ui" / "assets" / "template.html"
INLINE_JS = TEMPLATE.with_name("_template_inline.js")

_SCRIPT = re.compile(r"<script[^>]*>(.*?)</script>", re.S)


def inline_scripts(html: str) -> str:
    """template.html 의 <script> 본문만 이어 붙인다(외부 src 는 없다 — 화면은 바깥 요청 0건)."""
    return "\n".join(_SCRIPT.findall(html))


def write_inline_js(template: Path = TEMPLATE, dst: Path = INLINE_JS) -> Path:
    dst.write_text(inline_scripts(template.read_text(encoding="utf-8")), encoding="utf-8")
    return dst


def graphify_cmds(root: Path, no_viz: bool) -> list[list[str]]:
    cluster = ["graphify", "cluster-only", str(root), "--no-label"]
    if no_viz:
        cluster.append("--no-viz")
    cmds = [["graphify", "extract", str(root), "--code-only"], cluster]
    if not no_viz:
        cmds.append(["graphify", "tree", str(root)])
    return cmds


def build(root: Path = ROOT, no_viz: bool = False, run=subprocess.run, inline_js: Path | None = None) -> int:
    """`inline_js` 는 임시 JS 의 위치. 기본(None)은 호출 시점의 모듈 상수 INLINE_JS — 실제 실행에서는 template 옆이어야
    graphify 가 그래프에 넣고, 테스트는 tmp 경로를 넘기거나 상수를 monkeypatch 해 패키지 폴더에 아무것도 만들지 않는다."""
    if shutil.which("graphify") is None:
        print("graphify 명령이 없습니다: pip install \"graphifyy[sql]\"", file=sys.stderr)
        return 2
    tmp_js = Path(inline_js) if inline_js is not None else INLINE_JS
    write_inline_js(dst=tmp_js)
    try:
        for cmd in graphify_cmds(root, no_viz):
            print("+", " ".join(cmd), flush=True)
            rc = run(cmd, cwd=str(root)).returncode
            if rc != 0:
                return rc
    finally:
        tmp_js.unlink(missing_ok=True)   # 성공·실패·예외 어느 경우에도 임시 파일은 남기지 않는다
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-viz", action="store_true", help="graph.html · GRAPH_TREE.html 을 만들지 않는다")
    args = ap.parse_args(argv)
    return build(no_viz=args.no_viz)


if __name__ == "__main__":
    sys.exit(main())
