"""보관 샘플 하나를 결과 화면 모델(template.html 의 buildModel)로 **실제로 집계**해 요약 수치를 낸다 — 전후 비교표의 근거.

    python dev/tools/measure.py [샘플 경로] [--design-rules] [--json 출력.json]

- 입력 지문(sha256)·코드 SHA(git HEAD)·MODEL_VERSION·규칙(RULES)을 결과에 함께 적는다.
- `--design-rules` 는 D48 제품 유지 두 규칙을 끄고 디자인 스크립트(make_aoi_data.js)와 같은 규칙으로 잰다.
- 네트워크·NAS·쓰기 없음(--json 을 주면 그 파일만 쓴다). Node 가 필요하다(dev/tests/js_harness.js).
- 예상치를 맞추는 도구가 아니다: 지금 코드가 내는 값을 그대로 적는다.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev" / "tests"))
import sample_rows  # noqa: E402

DEFAULT = "AOI_capacity_2026-09-18_30일치.html.gz"


def git_sha() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def model_version() -> int:
    m = re.search(r"const MODEL_VERSION=(\d+);", (ROOT / "aoi_capacity" / "ui" / "assets" / "template.html").read_text(encoding="utf-8"))
    return int(m.group(1)) if m else -1


def measure(path: Path, design_rules: bool = False) -> dict:
    node = shutil.which("node")
    if not node:
        raise SystemExit("node 가 필요합니다")
    html = sample_rows.read_bytes(path).decode("utf-8")
    emb = sample_rows.embedded(html)
    rules = {"waitToObsEnd": False, "denomToday": False} if design_rules else None
    payload = json.dumps({"embedded": emb, **({"rules": rules} if rules else {})}, ensure_ascii=False)
    out = subprocess.run([node, "--max-old-space-size=4096", str(ROOT / "dev" / "tests" / "js_harness.js")], input=payload,
                         capture_output=True, text=True, timeout=900, cwd=str(ROOT))
    if out.returncode != 0:
        raise SystemExit(out.stderr[-2000:])
    D = json.loads(out.stdout)
    days, devs = D["days"], D["devices"]
    tot = {k: 0 for k in ("r", "x", "t", "d", "s", "e", "w")}
    est = 0
    per_day = {}
    for dy in days:
        us = []
        for dv in devs:
            t = D["detail"].get(dy, {}).get(dv)
            if not t:
                continue
            for k in tot:
                tot[k] += t.get(k, 0)
            den = t.get("den", 1440)
            measured = (t["r"] + t["x"] + t["t"] + t["d"]) > 0
            is_est = (t.get("cv") is not None) and (t["cv"] < 50 or not measured) and t.get("be", 0) > 0
            if is_est:
                est += 1
            if den > 0:
                if is_est:
                    us.append(min(100, t["be"] / den * 100))
                elif measured:
                    us.append(min(100, (t["r"] + t["d"]) / den * 100))
        per_day[dy] = {"util": round(sum(us) / len(us), 2) if us else None, "n": len(us)}
    return {"input": path.name, "input_sha256": sample_rows.sha256(path), "input_rows": len(emb["rows"]),
            "generated_iso": (emb.get("meta") or {}).get("generated_iso", ""), "code_sha": git_sha(), "model_version": model_version(),
            "rules": D.get("rules"), "today": D.get("today"), "day": D.get("day"), "days": [days[0], days[-1], len(days)], "devices": len(devs),
            "device_days": sum(len(v) for v in D["detail"].values()), "estimated_device_days": est,
            "totals_minutes_and_counts": tot, "fleet_util_by_day": per_day,
            "fleet_util_avg": round(sum(v["util"] for v in per_day.values() if v["util"] is not None) / max(1, len([v for v in per_day.values() if v["util"] is not None])), 2),
            "jobs": {"names": len(D["pool"]["job"]), "groups": len(D["jobGroups"])}}


def main() -> None:
    ap = argparse.ArgumentParser(description="보관 샘플을 화면 모델로 집계해 요약 수치를 낸다")
    ap.add_argument("sample", nargs="?", default=str(ROOT / "dev" / "samples" / DEFAULT))
    ap.add_argument("--design-rules", action="store_true", help="D48 제품 유지 두 규칙을 끄고 디자인 스크립트와 같은 규칙으로")
    ap.add_argument("--json", default="", help="결과를 이 파일에 쓴다(없으면 표준 출력)")
    a = ap.parse_args()
    res = measure(Path(a.sample), a.design_rules)
    text = json.dumps(res, ensure_ascii=False, indent=1)
    if a.json:
        Path(a.json).write_text(text, encoding="utf-8")
        print(f"저장: {a.json}")
    else:
        print(text)


if __name__ == "__main__":
    main()
