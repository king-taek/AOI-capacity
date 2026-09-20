"""보관 샘플(30일치)로 캐시·HTML 쓰기의 **크기와 메모리**를 잰다 — P3-A(C04 · C07) 전후 비교의 근거. 표준 라이브러리만, NAS 없음.

    python dev/tools/measure_cache.py [샘플] --out <임시 폴더> [--json 결과.json]

- 샘플의 원천 행을 `(장비, Report)` 로 묶어 캐시 모양 dict 를 만들고 JSON 크기를 잰다.
- HTML 쓰기: 옛 방식(`json.dumps` → `tpl.replace` 큰 사본 → 한 번에 write)과 지금 `collect.write_html`(앞·데이터·뒤 순차 쓰기)의
  tracemalloc 최고점과 경과 시간을 같은 입력으로 비교한다.
- 캐시 저장: `_save_cache` 한 번의 크기·시간과, 저장을 생략한 no-op(0바이트)을 나란히 적는다.
- `--out` 폴더 안에만 쓴다(저장소 안 파일은 건드리지 않는다). 수치는 그대로 적는다 — 예상치에 맞추는 도구가 아니다.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dev" / "tests"))
import sample_rows  # noqa: E402
from aoi_capacity import collect  # noqa: E402
from aoi_capacity.utils import paths  # noqa: E402

DEFAULT = "AOI_capacity_2026-09-18_30일치.html.gz"


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def cache_from_rows(rows, meta) -> dict:
    """행을 캐시 모양으로 — 새 키 형식(`dev:<장비>|<report 소문자>`)."""
    cache = collect._empty_cache()
    reports = cache["reports"]
    for r in rows:
        dev, rep = str(r.get("device") or ""), str(r.get("report") or "")
        key = collect.report_key(f"dev:{dev}", rep)
        e = reports.get(key)
        if e is None:
            e = reports[key] = {"mtime": 0.0, "device": dev, "device_id": f"x:\\{dev.lower()}", "device_key": f"dev:{dev}",
                                "rel": collect._rel_key(rep), "path": f"X:\\{dev}\\Report\\{rep}", "sha256": "", "revision": 1,
                                "rows": [], "seen": 0.0, "parser_version": collect.PARSER_VERSION}
        e["rows"].append(r)
    for d in {str(r.get("device") or "") for r in rows}:
        cache["devices"][f"dev:{d}"] = {"name": d, "ids": [f"x:\\{d.lower()}"], "aliases": []}
        cache["last_mtime"][f"dev:{d}"] = 0.0
    cache["parser_version"] = collect.PARSER_VERSION
    return cache


def timed(fn):
    tracemalloc.start()
    t0 = time.perf_counter()
    out = fn()
    sec = time.perf_counter() - t0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return out, {"sec": round(sec, 3), "peak_mb": round(peak / 1048576, 1)}


def old_write_html(cfg, rows, dev_meta, target):
    """P3-A 이전 write_html 의 핵심 — 템플릿 · 치환 결과 · 접힌 dict 를 동시에 든다(비교용, 결과 파일은 같은 내용)."""
    from aoi_capacity import nas_guard
    tpl = nas_guard.read_text(paths.template_path())
    emb = collect._embed_rows(rows)
    emb["meta"] = {"devices": dev_meta}
    data = json.dumps(emb, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = tpl.replace("__DATA__", data, 1)
    with open(target, "w", encoding="utf-8") as f:
        f.write(out)
    return len(out)


def measure(sample: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, meta, sha = sample_rows.load(sample)
    dev_meta = list(meta.get("devices") or [])
    res = {"input": sample.name, "input_sha256": sha, "rows": len(rows), "rss_after_load_mb": round(rss_mb(), 1)}

    cache, m = timed(lambda: cache_from_rows(rows, meta))
    res["cache_build"] = {**m, "reports": len(cache["reports"])}
    cfg = dict(collect.DEFAULT_CONFIG, cache_file=str(out_dir / "aoi_cache.json"), output_dir=str(out_dir), output_name="m.html")

    _, m = timed(lambda: collect._save_cache(cfg, cache))
    res["cache_save"] = {**m, "json_bytes": os.path.getsize(cfg["cache_file"])}
    res["cache_noop"] = {"bytes_written": 0, "note": "C04: 저장 이유가 없으면 _save_cache 를 부르지 않는다(파일 mtime·바이트 그대로)"}

    size, m = timed(lambda: old_write_html(cfg, rows, dev_meta, str(out_dir / "old.html")))
    res["html_old_replace"] = {**m, "bytes": size}
    _, m = timed(lambda: collect.write_html(cfg, rows, dev_meta, [], time.time(), mode="measure"))
    res["html_new_stream"] = {**m, "bytes": os.path.getsize(out_dir / "m.html")}
    res["rss_end_mb"] = round(rss_mb(), 1)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description="캐시·HTML 쓰기의 크기와 메모리를 잰다")
    ap.add_argument("sample", nargs="?", default=str(ROOT / "dev" / "samples" / DEFAULT))
    ap.add_argument("--out", required=True, help="결과 파일을 쓸 임시 폴더(저장소 밖)")
    ap.add_argument("--json", default="", help="결과를 이 파일에 쓴다(없으면 표준 출력)")
    a = ap.parse_args()
    res = measure(Path(a.sample), Path(a.out))
    text = json.dumps(res, ensure_ascii=False, indent=1)
    if a.json:
        Path(a.json).write_text(text, encoding="utf-8")
        print(f"저장: {a.json}")
    else:
        print(text)


if __name__ == "__main__":
    main()
