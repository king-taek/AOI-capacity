"""헤드리스 실행(작업 스케줄러용). GUI 와 같은 수집 코어를 쓴다.

    python -m aoi_capacity.cli                    # config.json (이 파일 옆 또는 --config) 로 증분 수집
    python -m aoi_capacity.cli --backfill         # 검색 창을 최근 backfill_days 로 넓힘(캐시된 파일은 건너뜀 — 다시 읽지 않는다)
    python -m aoi_capacity.cli --refresh-window 30   # 최근 30일 안의 Report 는 캐시에 있어도 다시 읽음(창 밖 이력 보존, D60)
    python -m aoi_capacity.cli --rebuild-all      # 보관 기간 전부를 새 후보 캐시에 모아 검증 뒤 교체(실패하면 기존 캐시 유지)
    python -m aoi_capacity.cli --full             # = --rebuild-all (옛 별칭, 이력 삭제 없음)
    python -m aoi_capacity.cli --recover          # INI 를 못 찾았던 Report 만 다시 읽음
    python -m aoi_capacity.cli --update           # (opt-in) 시작 전에 GitHub 최신 커밋으로 자기 갱신 시도

config.json 이 없으면 GUI 와 같은 데이터 폴더(prefs.json / devices.csv)를 쓴다.
config.json 의 `refresh_window_days` · `rebuild_all` 로도 같은 모드를 켤 수 있다(명령줄이 우선).

종료 코드(스케줄러 계약)
    0  성공 — HTML(과 켜 두었다면 CSV)을 썼다
    3  부분 성공 — HTML 은 썼지만 CSV 를 쓰지 못했다(Excel 이 열어 둔 파일 등, C06). 캐시·HTML 은 정상
    1  실패 — 전체 재구축 후보가 검증에 걸려 기존 캐시를 그대로 둔 경우(`RebuildRejected`)와 그 밖의 예외(traceback)
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

EXIT_OK, EXIT_FAILED, EXIT_PARTIAL = 0, 1, 3


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
    ap.add_argument("--refresh-window", type=int, default=None, metavar="N",
                    help="최근 N일 안의 Report 는 캐시에 있어도(수정시각이 같아도) 다시 읽음. 창 밖 이력은 그대로 두고, "
                         "다시 읽다 실패한 Report 는 이전 행을 유지한 채 다음에 재시도")
    ap.add_argument("--rebuild-all", action="store_true",
                    help="보관 기간(retention_days) 전부를 새 후보 캐시에 모아 검증을 통과할 때만 기존 캐시와 바꿈. "
                         "실패하면 기존 캐시를 그대로 둠(이력 삭제 없음)")
    ap.add_argument("--full", action="store_true", help="--rebuild-all 의 옛 별칭(같은 동작)")
    ap.add_argument("--backfill", action="store_true",
                    help="검색 창을 최근 backfill_days 로 넓힘. 이미 캐시된 Report(수정시각 같음)는 건너뜀 — "
                         "다시 읽으려면 --refresh-window")
    ap.add_argument("--recover", action="store_true", help="INI 를 못 찾았던 Report 만 다시 읽음(누락 복구)")
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
                elif status == "held":
                    _print(f"업데이트 보류({info.get('sha', '')[:7]}): {info.get('reason', '')}")
                else:
                    _print(f"업데이트 확인 실패: {info.get('error', '')}")
        except Exception as e:  # noqa: BLE001
            _print(f"업데이트 단계 오류(무시): {e}")

    started = time.time()
    cfg = load_config(args.config)
    paths.ensure_user_files()
    rebuild = bool(args.rebuild_all or args.full) or None            # None 이면 cfg 의 rebuild_all 을 따른다
    refresh = args.refresh_window                                      # None 이면 cfg 의 refresh_window_days 를 따른다
    plan = collect.plan_run(cfg, backfill=args.backfill, recover=args.recover,
                            refresh_window_days=refresh, rebuild_all=rebuild)
    _print(f"모드 {plan.mode} · 캐시 Report {plan.total_reports}개(다시 읽기 {plan.reread_reports} · 그대로 {plan.keep_reports}"
           f" · 누락 복구 {plan.recover_reports}) · 새 Report 는 NAS 를 본 뒤 셈")
    stats: dict = {}
    try:
        rows, dev_meta, errors = collect.collect(cfg, backfill=args.backfill, recover=args.recover,
                                                 refresh_window_days=refresh, rebuild_all=rebuild,
                                                 progress=_progress_printer(), log=_print, stats=stats)
    except collect.RebuildRejected as ex:
        _print(f"전체 재구축 거부 — 기존 캐시·HTML 은 그대로입니다: {ex}")
        return EXIT_FAILED
    warnings: list = []
    collect.write_html(cfg, rows, dev_meta, errors, started, mode="auto", log=_print, timing=stats, warnings=warnings)
    if stats.get("cache_status") == collect.CACHE_CORRUPT:
        _print(f"캐시 파일이 손상되어 처음부터 다시 수집했습니다. 손상 원본 보존: {stats.get('cache_preserved', '')}")
    bad = [d for d in dev_meta if d.get("error")]
    if bad:
        _print("접근 실패 장비: " + ", ".join(f"{d['name']} ({d['error']})" for d in bad))
    partial = [d for d in dev_meta if not d.get("error") and d.get("read_errors")]
    if partial:
        _print("일부 Report 를 읽지 못한 장비: " + ", ".join(f"{d['name']} ({d['read_errors']}개)" for d in partial))
    for w in warnings:
        _print(f"경고({w.get('kind')}): {w.get('path')} — {w.get('error')}")
    code = EXIT_PARTIAL if warnings else EXIT_OK
    _print(f"완료 · {time.time() - started:.1f}초 · 종료 코드 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
