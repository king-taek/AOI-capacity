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
from typing import Dict, List, Optional

from . import collect, i18n
from .utils import config as config_mod
from .utils import paths, prefs

EXIT_OK, EXIT_FAILED, EXIT_PARTIAL = 0, 1, 3


def load_config(path: str, problems: Optional[List[config_mod.Problem]] = None) -> Dict[str, object]:
    """config.json 을 읽어 cfg 를 만든다. 상대 경로 기본값은 config.json 이 있는 폴더 기준.

    GUI 의 prefs 와 **같은 규칙**(`utils.config.normalize_config`)으로 형·범위를 맞춘다(C13). `problems` 리스트를 주면
    경고(고친 값)와 치명(범위·경로 — 실행을 막아야 함)을 담아 준다. 여기서는 막지 않는다 — `main` 이 문구를 찍고 종료 코드를 정한다."""
    cfg = copy.deepcopy(collect.DEFAULT_CONFIG)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            user = json.load(f)
        for k, v in (user.items() if isinstance(user, dict) else ()):
            if not k.startswith("_"):
                cfg[k] = v
        cfg, found = config_mod.normalize_config(cfg)
        if problems is not None:
            problems.extend(found)
        base = os.path.dirname(os.path.abspath(path))
        if not config_mod.fatal(found):
            cfg["devices_csv"] = cfg.get("devices_csv") or os.path.join(base, "devices.csv")
            cfg["cache_file"] = cfg.get("cache_file") or os.path.join(base, "aoi_cache.json")
            cfg["output_dir"] = cfg.get("output_dir") or base
        return cfg
    p = prefs.load()
    return prefs.to_collect_cfg(p)


def _print(msg: str) -> None:
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def rerun_args(argv) -> List[str]:
    """갱신 뒤 다시 실행할 인자 — `--update` 만 뺀다(같은 인자로 한 번만 다시 돌고, 자식은 다시 갱신하지 않는다)."""
    src = list(sys.argv[1:]) if argv is None else list(argv)
    return [a for a in src if a != "--update"]


def rerun_without_update(argv, run=None) -> int:
    """갱신 뒤 **자식 프로세스**로 수집을 다시 실행하고 끝날 때까지 기다린 뒤 그 종료 코드를 돌려준다(C14).

    Windows 의 `os.execv` 는 부모를 즉시 끝내 작업 스케줄러가 자식이 돌기도 전에 '완료' 로 기록했다 — 그래서 exec 가 아니라
    subprocess 다. 자식이 실패하면 그 코드가 그대로 부모의 종료 코드다. `run` 은 테스트 주입용(실제 프로세스를 띄우지 않는다)."""
    import subprocess

    cmd = [sys.executable, "-m", "aoi_capacity.cli", *rerun_args(argv)]
    runner = run or (lambda c: subprocess.run(c, check=False).returncode)
    code = int(runner(cmd))
    _print(i18n.KO.CLI_UPDATE_RERUN_DONE_FMT.format(code=code))
    return code


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
    K = i18n.KO
    ap = argparse.ArgumentParser(description=K.CLI_DESC)
    ap.add_argument("--config", default=os.path.join(os.getcwd(), "config.json"))
    ap.add_argument("--refresh-window", type=int, default=None, metavar="N", help=K.CLI_HELP_REFRESH_WINDOW)
    ap.add_argument("--rebuild-all", action="store_true", help=K.CLI_HELP_REBUILD_ALL)
    ap.add_argument("--full", action="store_true", help=K.CLI_HELP_FULL)
    ap.add_argument("--backfill", action="store_true", help=K.CLI_HELP_BACKFILL)
    ap.add_argument("--recover", action="store_true", help=K.CLI_HELP_RECOVER)
    ap.add_argument("--update", action="store_true", help=K.CLI_HELP_UPDATE)
    args = ap.parse_args(argv)

    if args.update:
        try:
            from .utils import updater

            if updater.is_git_checkout():
                _print(K.CLI_UPDATE_GIT_SKIP)
            else:
                status, info = updater.manual_check()
                if status == "update":
                    _print(K.CLI_UPDATE_DOWNLOADING_FMT.format(sha=str(info.get("sha", ""))[:7]))
                    if updater.download_and_apply(info["repo"], info["branch"], info["sha"]) and not updater.update_pending():
                        _print(K.CLI_UPDATE_DONE_RERUN)
                        return rerun_without_update(argv)
                elif status == "latest":
                    _print(K.CLI_UPDATE_LATEST)
                elif status == "held":
                    _print(K.CLI_UPDATE_HELD_FMT.format(sha=str(info.get("sha", ""))[:7], reason=info.get("reason", "")))
                else:
                    _print(K.CLI_UPDATE_CHECK_FAILED_FMT.format(error=info.get("error", "")))
        except Exception as e:  # noqa: BLE001
            _print(K.CLI_UPDATE_STEP_ERROR_FMT.format(error=e))

    started = time.time()
    problems: List[config_mod.Problem] = []
    cfg = load_config(args.config, problems)
    for pr in problems:
        if not pr.fatal:
            _print(i18n.KO.CLI_CFG_WARNING_FMT.format(message=pr.message()))
    if config_mod.fatal(problems):                        # 범위·경로 설정 오류 — NAS 를 만지기 전에 멈춘다(C13)
        for pr in config_mod.fatal(problems):
            _print(i18n.KO.CLI_CFG_FATAL_FMT.format(message=pr.message()))
        return EXIT_FAILED
    paths.ensure_user_files()
    rebuild = bool(args.rebuild_all or args.full) or None            # None 이면 cfg 의 rebuild_all 을 따른다
    refresh = args.refresh_window                                      # None 이면 cfg 의 refresh_window_days 를 따른다
    plan = collect.plan_run(cfg, backfill=args.backfill, recover=args.recover,
                            refresh_window_days=refresh, rebuild_all=rebuild)
    _print(K.CLI_PLAN_FMT.format(mode=plan.mode, total=plan.total_reports, reread=plan.reread_reports,
                                 keep=plan.keep_reports, recover=plan.recover_reports))
    stats: dict = {}
    try:
        rows, dev_meta, errors = collect.collect(cfg, backfill=args.backfill, recover=args.recover,
                                                 refresh_window_days=refresh, rebuild_all=rebuild,
                                                 progress=_progress_printer(), log=_print, stats=stats)
    except collect.RebuildRejected as ex:
        _print(K.CLI_REBUILD_REJECTED_FMT.format(error=ex))
        return EXIT_FAILED
    warnings: list = []
    collect.write_html(cfg, rows, dev_meta, errors, started, mode="auto", log=_print, timing=stats, warnings=warnings)
    if stats.get("cache_status") == collect.CACHE_CORRUPT:
        _print(K.CLI_CACHE_CORRUPT_FMT.format(path=stats.get("cache_preserved", "")))
    bad = [d for d in dev_meta if d.get("error")]
    if bad:
        _print(K.CLI_UNREACHABLE_FMT.format(items=", ".join(K.CLI_UNREACHABLE_ITEM_FMT.format(name=d["name"], error=d["error"]) for d in bad)))
    partial = [d for d in dev_meta if not d.get("error") and d.get("read_errors")]
    if partial:
        _print(K.CLI_PARTIAL_FMT.format(items=", ".join(K.CLI_PARTIAL_ITEM_FMT.format(name=d["name"], n=d["read_errors"]) for d in partial)))
    for w in warnings:
        _print(K.CLI_WARNING_FMT.format(kind=w.get("kind"), path=w.get("path"), error=w.get("error")))
    code = EXIT_PARTIAL if warnings else EXIT_OK
    _print(K.CLI_DONE_FMT.format(sec=time.time() - started, code=code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
