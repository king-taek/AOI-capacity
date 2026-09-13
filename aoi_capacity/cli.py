"""헤드리스 실행(작업 스케줄러용). GUI 와 같은 수집 코어를 쓴다.

    python -m aoi_capacity.cli                    # config.json (이 파일 옆 또는 --config) 로 증분 수집
    python -m aoi_capacity.cli --backfill         # 최근 backfill_days 를 전부 다시 읽음
    python -m aoi_capacity.cli --full             # 캐시를 버리고 처음부터
    python -m aoi_capacity.cli --update           # (opt-in) 시작 전에 GitHub 최신 커밋으로 자기 갱신 시도

config.json 이 없으면 GUI 와 같은 데이터 폴더(prefs.json / devices.csv)를 쓴다.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from typing import Dict

from . import collect
from .utils import paths, prefs


def load_config(path: str) -> Dict[str, object]:
    """config.json 을 읽어 cfg 를 만든다. 상대 경로 기본값은 config.json 이 있는 폴더 기준."""
    cfg = copy.deepcopy(collect.DEFAULT_CONFIG)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            if not k.startswith("_"):
                cfg[k] = v
        base = os.path.dirname(os.path.abspath(path))
        cfg["devices_csv"] = cfg.get("devices_csv") or os.path.join(base, "devices.csv")
        cfg["cache_file"] = cfg.get("cache_file") or os.path.join(base, "aoi_cache.json")
        cfg["output_dir"] = cfg.get("output_dir") or base
        return cfg
    p = prefs.load()
    return prefs.to_collect_cfg(p)


def _print(msg: str) -> None:
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def _progress_printer():
    last = {"pct": -1}

    def cb(done: int, total: int, phase: str) -> None:
        if total > 0:
            pct = int(done * 100 / total)
            if pct != last["pct"] and pct % 10 == 0:
                last["pct"] = pct
                _print(f"{pct:3d}%  {phase}")
        elif phase:
            _print(phase)
    return cb


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows cp949 콘솔에서 한글 로그가 깨지지 않게
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="AOI Capacity 수집기(헤드리스)")
    ap.add_argument("--config", default=os.path.join(os.getcwd(), "config.json"))
    ap.add_argument("--full", action="store_true", help="캐시를 무시하고 처음부터 다시 읽음")
    ap.add_argument("--backfill", action="store_true", help="최근 backfill_days 안의 Report 를 전부 다시 읽음")
    ap.add_argument("--update", action="store_true", help="시작 전에 GitHub 최신 커밋으로 자기 갱신(선택)")
    args = ap.parse_args(argv)

    if args.update:
        try:
            from .utils import updater

            if updater.is_git_checkout():
                _print("git 작업 폴더 — 자동 업데이트 생략(git pull 사용)")
            else:
                status, info = updater.manual_check()
                if status == "update":
                    _print(f"새 버전 {info.get('sha', '')[:7]} 다운로드")
                    if updater.download_and_apply(info["repo"], info["branch"], info["sha"]) and not updater.update_pending():
                        _print("갱신 완료 — 다시 실행합니다")
                        os.execv(sys.executable, [sys.executable, "-m", "aoi_capacity.cli"] +
                                 [a for a in (argv or sys.argv[1:]) if a != "--update"])
                elif status == "latest":
                    _print("최신 버전입니다")
                else:
                    _print(f"업데이트 확인 실패: {info.get('error', '')}")
        except Exception as e:  # noqa: BLE001
            _print(f"업데이트 단계 오류(무시): {e}")

    started = time.time()
    cfg = load_config(args.config)
    paths.ensure_user_files()
    rows, dev_meta, errors = collect.collect(cfg, full=args.full, backfill=args.backfill,
                                             progress=_progress_printer(), log=_print)
    collect.write_html(cfg, rows, dev_meta, errors, started, mode="auto", log=_print)
    bad = [d for d in dev_meta if d.get("error")]
    if bad:
        _print("접근 실패 장비: " + ", ".join(f"{d['name']} ({d['error']})" for d in bad))
    _print(f"완료 · {time.time() - started:.1f}초")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
