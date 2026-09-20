"""`진행상황.md` · `CLAUDE.md` 회귀 가드 — 세션이 바뀌어도 이어서 일할 수 있게 하는 파일이라 형식이 계약이다.

이 파일의 값어치는 '읽으면 맞다' 는 데 있다. 그래서 형식뿐 아니라 **코드와 어긋나는지**까지 본다 —
수집 범위 대수, 결정 번호(D01…)의 연속성, 작업 기록의 최신 커밋이 실제로 있는 커밋인지.

S18(9/20): 문서의 **숫자**는 코드에서 기계적으로 뽑은 값과 대조한다 — 수집 범위 대수 · 행 열 수 · ROW_SCHEMA_VERSION · PARSER_VERSION ·
MODEL_VERSION · 원인 규칙 수 · 표기명 수. 이 가드의 범위는 여기 적힌 숫자뿐이다(산문 전체를 정규식으로 검증하지 않는다).
어긋나면 문서를 코드에 맞춘다(코드를 문서에 맞추지 않는다).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

import template_facts
from aoi_capacity import collect, scope

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "진행상황.md"
TEXT = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
RULES = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
SECTIONS = ["한 줄 요약", "지금 상태", "확정된 결정", "실물로 확인한 사실",
            "다음 할 일", "확인 대기", "작업 기록"]


def test_lives_at_the_repo_root_so_a_new_session_finds_it():
    assert DOC.is_file(), "진행상황.md 가 저장소 맨 앞에 없습니다"
    assert "진행상황.md" in (ROOT / "CLAUDE.md").read_text(encoding="utf-8"), \
        "CLAUDE.md 가 진행상황.md 를 가리키지 않으면 새 세션이 읽지 않는다"


@pytest.mark.parametrize("name", SECTIONS)
def test_required_section_exists(name):
    assert re.search(rf"^##+ .*{re.escape(name)}", TEXT, re.M), f"'{name}' 절이 없습니다"


def test_last_updated_line_is_present():
    assert re.search(r"마지막 갱신:\s*\d{4}-\d{2}-\d{2}", TEXT), "'마지막 갱신: YYYY-MM-DD' 줄이 없습니다"


def test_decision_numbers_are_unique_and_unbroken():
    """확정된 결정은 번호로 이야기한다 — 빠지거나 겹치면 '사용자가 뭘 정했더라' 를 못 찾는다."""
    nums = [int(n) for n in re.findall(r"^\|\s*D(\d{2})\s*\|", TEXT, re.M)]
    assert nums, "확정된 결정 표(D01…)가 없습니다"
    assert nums == sorted(nums) and len(set(nums)) == len(nums), f"결정 번호가 겹치거나 뒤섞였다: {nums}"
    assert nums == list(range(1, len(nums) + 1)), f"결정 번호가 비었다: {nums}"


def test_work_log_entries_follow_the_one_line_format():
    body = TEXT.split("## 작업 기록", 1)[1]
    entries = [l for l in body.splitlines() if l.startswith("- ")]
    assert len(entries) >= 5, "작업 기록이 거의 비었습니다"
    # 커밋 해시 하나 이상(`…`·`·` 로 이은 묶음도 됨), 아직 커밋 전이면 `(작업 중)`
    fmt = re.compile(r"- \d{4}-\d{2}-\d{2} (?:`?\(작업 중\)`? |(?:`[0-9a-f]{7,40}`[ ·…]*)+)— .+")
    for line in entries:
        assert fmt.match(line), f"형식이 다릅니다(- 날짜 `커밋` — 무엇을·왜): {line}"


def test_newest_work_log_entry_points_at_a_real_commit():
    """맨 위 항목은 실제로 있는 커밋이어야 한다 — 손으로 적다 틀리면 이력을 못 따라간다."""
    body = TEXT.split("## 작업 기록", 1)[1]
    first = next(l for l in body.splitlines() if l.startswith("- "))
    m = re.search(r"`([0-9a-f]{7,40})`", first)
    if not m:
        return                                        # `(작업 중)` — 아직 커밋 전이면 볼 것이 없다
    sha = m.group(1)
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-t", sha],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pytest.skip("git 을 쓸 수 없는 환경")
    if out.returncode != 0:
        pytest.skip("얕은 클론이라 옛 커밋이 없을 수 있다")   # 배포본·zip 에서는 확인하지 않는다
    assert out.stdout.strip() == "commit", f"{sha} 는 커밋이 아닙니다"


def test_scope_size_in_the_doc_matches_the_code():
    """★ 문서가 조용히 낡는 걸 막는다 — 수집 범위 대수는 코드가 정답이다."""
    n = len(scope.DEFAULT_SCOPE)
    assert re.search(rf"\b{n}대\b", TEXT), f"수집 범위가 {n}대인데 문서에 '{n}대' 가 없습니다"


def test_rules_are_not_copied_into_the_status_file():
    """규칙은 CLAUDE.md 한 곳에만 — 베껴 두면 따로 낡는다."""
    assert "## 절대 규칙" not in TEXT


def test_pre_commit_hook_is_shipped_and_opt_in():
    hook = ROOT / "dev" / "hooks" / "pre-commit"
    assert hook.is_file(), "dev/hooks/pre-commit 이 없습니다"
    body = hook.read_text(encoding="utf-8")
    assert "진행상황.md" in body and "--no-verify" in body      # 막되, 빠져나갈 길은 알려 준다
    assert "core.hooksPath" in body                            # 켜는 법이 파일 안에 있다


def test_hook_reads_the_korean_file_name_correctly():
    """★ git 은 기본으로 한글 경로를 `\\354\\247…` 로 내놓는다 — 그대로 비교하면 후크가 늘 막는다."""
    body = (ROOT / "dev" / "hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "core.quotepath=false" in body


# ── S18: 문서의 숫자 ↔ 코드 ───────────────────────────────────────────────────
def _numbers(text: str, pattern: str) -> list[int]:
    return [int(x) for x in re.findall(pattern, text)]


FACTS = [
    # (이름, 코드 값, CLAUDE.md 에서 그 숫자를 적는 자리의 정규식 — 그룹 1 이 숫자)
    ("수집 범위 대수", lambda: len(scope.DEFAULT_SCOPE), r"현재 (\d+)대 전부"),
    ("행 열 수(OUT_COLS)", lambda: len(collect.OUT_COLS), r"`collect\.OUT_COLS`, (\d+)열"),
    ("ROW_SCHEMA_VERSION", lambda: collect.ROW_SCHEMA_VERSION, r"`ROW_SCHEMA_VERSION` (\d+)"),
    ("PARSER_VERSION", lambda: collect.PARSER_VERSION, r"`PARSER_VERSION` (\d+)"),
    ("MODEL_VERSION", template_facts.model_version, r"MODEL_VERSION (\d+)"),
    ("원인 규칙 수(_CAUSE_RULES)", lambda: len(collect._CAUSE_RULES), r"`collect\._CAUSE_RULES`\((\d+)개"),
    ("표기명 수(JOB_ALIAS)", lambda: len(template_facts.job_alias()), r"표기명 (\d+)개"),
]


@pytest.mark.parametrize("name,code_value,pattern", FACTS, ids=[f[0] for f in FACTS])
def test_numbers_in_claude_md_match_the_code(name, code_value, pattern):
    """CLAUDE.md 가 적는 숫자는 코드가 정답이다. 그 숫자를 아직 적지 않은 항목(PARSER_VERSION)은 적히는 순간부터 검사된다."""
    found = _numbers(RULES, pattern)
    if not found:
        pytest.skip(f"CLAUDE.md 에 '{name}' 숫자가 없다(적지 않은 것은 어긋난 것이 아니다)")
    v = code_value()
    assert all(n == v for n in found), f"CLAUDE.md 의 {name} {found} ≠ 코드 {v} — 문서를 코드에 맞춘다"


def test_progress_doc_numbers_match_the_code():
    """진행상황.md 가 표기명·열 수를 적는다면 같은 숫자여야 한다(적지 않으면 그냥 통과)."""
    for name, v, pattern in (("표기명 수", len(template_facts.job_alias()), r"표기명 (\d+)개"),
                             ("행 열 수", len(collect.OUT_COLS), r"OUT_COLS[^\n]{0,20}?(\d+)열")):
        found = _numbers(TEXT, pattern)
        assert all(n == v for n in found), f"진행상황.md 의 {name} {found} ≠ 코드 {v}"
