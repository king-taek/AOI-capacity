"""사용자 문구는 i18n/ko.py 에만 — 위젯·페이지·워커·업데이터·부트스트랩·런처에 한글 리터럴이 없어야 한다.
주석과 docstring 은 허용(문자열 토큰 중 표현식에 쓰인 것만 검사)."""
from __future__ import annotations

import ast
import re
from pathlib import Path

from aoi_capacity.utils import paths

ROOT = paths._project_root()
TARGETS = [
    "aoi_capacity/ui", "aoi_capacity/workers", "aoi_capacity/utils/updater.py",
    "aoi_capacity/utils/bootstrap.py", "aoi_capacity/utils/config.py", "aoi_capacity/cli.py", "main.py",
]
# collect.py · devices.py 의 한글은 로그 문장(예외)과 원문 데이터라 검사하지 않는다 — 행 데이터의 비고는 C12 로 코드(issue_codes)가 됐고
# 문장은 ko.py 의 ISSUE_TEXTS 에서 출력 때 만든다(test_collect_parse 가 rows_for_report 의 data_issue 가 비어 있음을 본다).
# scripts/exe_launcher.py 는 표준 라이브러리만 쓰는 계약이라 i18n 을 import 할 수 없다 — 유일한 예외.
HANGUL = re.compile(r"[가-힣]")


def _files():
    for t in TARGETS:
        p = ROOT / t
        if p.is_file():
            yield p
        elif p.is_dir():
            yield from sorted(p.rglob("*.py"))


def _string_literals(tree: ast.AST):
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                doc_nodes.add(id(node.body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_nodes:
            yield node


def test_no_korean_string_literals_outside_i18n():
    bad = []
    for f in _files():
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in _string_literals(tree):
            if HANGUL.search(node.value):
                bad.append(f"{f.relative_to(ROOT)}:{node.lineno}: {node.value[:40]!r}")
    assert not bad, "\n".join(bad)
