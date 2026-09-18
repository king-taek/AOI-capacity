"""보관 샘플 하나를 결과 화면 모델(template.html 의 JS)로 **실제로 집계**해 요약 수치를 낸다 — 전후 비교표의 근거.

    python dev/tools/measure.py [샘플 경로] [--viewer-now ISO] [--tz Asia/Seoul] [--json 출력.json]

- 입력 지문(sha256)·코드 SHA(git HEAD)·규칙 번호(CLASS_VERSION)·기준시계·시간대를 결과에 함께 적는다.
- 열람 시계(`--viewer-now`)는 기본으로 그 파일의 수집 시각(meta.generated_iso)에 고정한다 → 언제 돌려도 같은 수치.
- 네트워크·NAS·쓰기 없음(--json 을 주면 그 파일만 쓴다). Node 가 필요하다(dev/tests/js_harness.js).
- 예상치를 맞추는 도구가 아니다: 지금 코드가 내는 값을 그대로 적는다.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev" / "tests"))
import sample_rows  # noqa: E402

DEFAULT = "AOI_capacity_2026-09-18_30일치.html"


def git_sha() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def measure(path: Path, viewer_now: str | None, tz: str) -> dict:
    node = shutil.which("node")
    if not node:
        raise SystemExit("node 가 없습니다 — 화면 모델을 실행할 수 없습니다")
    rows, meta, sha = sample_rows.load(path)
    ref = viewer_now or meta.get("generated_iso") or ""
    env = dict(os.environ, TZ=tz)
    payload = json.dumps({"rows": rows, "meta": meta, "viewer_now": ref or None, "summary": True}, ensure_ascii=False)
    out = subprocess.run([node, str(ROOT / "dev" / "tests" / "js_harness.js")], input=payload, capture_output=True,
                         text=True, timeout=1800, cwd=str(ROOT), env=env)
    if out.returncode != 0:
        raise SystemExit(out.stderr)
    res = json.loads(out.stdout)
    src = {"": 0, "batch": 0, "slot": 0}
    for r in rows:
        src[r.get("kind", "")] = src.get(r.get("kind", ""), 0) + 1
    return {"input": str(path.name), "input_sha256": sha, "input_rows": len(rows), "rows_by_kind": src,
            "generated_iso": meta.get("generated_iso"), "embedded_sha": meta.get("sha"), "code_sha": git_sha(),
            "class_version": res.get("class_version"), "viewer_now": ref, "timezone": tz, "today": res.get("today"),
            "days": [res["days"][0], res["days"][-1], len(res["days"])] if res["days"] else [],
            "totals_seconds_and_counts": res["totals"], "identity_violations": res["identity_violations"],
            "model": res["model"], "fleet": res["fleet"], "quality": res.get("quality"), "occurrences": res.get("occurrences"),
            "loss_pp_plus_util": [round(x["ppSum"] + (x["util"] or 0), 3) for x in res["loss"]]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample", nargs="?", default=DEFAULT)
    ap.add_argument("--viewer-now", default=None)
    ap.add_argument("--tz", default="Asia/Seoul")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    p = Path(a.sample)
    if not p.exists():
        p = sample_rows.sample_path(a.sample)
    res = measure(p, a.viewer_now, a.tz)
    text = json.dumps(res, ensure_ascii=False, indent=1)
    if a.json:
        Path(a.json).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
