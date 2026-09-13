"""exe_launcher.py — 'exe + app 폴더' 배포의 얇은 런처.  **앱 코드 0줄.**

이 파일에 앱 코드를 절대 넣지 마라. PyInstaller 의 ``FrozenImporter`` 는 exe 안의 PYZ 사본으로
디스크의 최신 사본을 **가린다** — 앱이 exe 안에 들어가는 순간 자동 업데이트가 조용히 무력화된다.
그래서 여기서는 **표준 라이브러리만** import 한다(``aoi_capacity`` 는 절대 import 하지 않는다).

이 exe 는 **업데이트되지 않는다**(사용자 손에 있는 그 파일 그대로다). 따라서 여기 있는 로직은
전부 '나중에 못 고쳐도 되는가?' 를 통과해야 한다.
  통과함  : 경로 계산 · 교체 상태기계(중단 복구 포함) · 자식 실행 · 오류 표시
  통과 못함: 네트워크 · zip · pip  → 전부 ``updater``/``bootstrap``(업데이트되는 코드) 쪽에 둔다

교체를 런처가 맡는 이유: 실행 중인 앱은 자기가 돌아가는 폴더를 안전하게 바꿀 수 없다.
런처는 파이썬이 ``app/`` 에서 아무것도 import 하기 전에 돌기 때문에 할 수 있다.

**불변식: 이 파일의 모든 실패 경로는 '구버전을 그대로 실행' 으로 끝난다.**
(사용자 문구가 하나 있다 — i18n 을 import 할 수 없는 유일한 파일이라 예외다.)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple

# 앱에게 "교체해 줄 런처가 있다" 고 알리는 유일한 신호. updater 는 이 값이 있을 때만 app.new 스테이징으로 간다.
APP_HOME_ENV = "AOI_APP_HOME"
APP_TITLE = "AOI Capacity"
EXE_NAME = "AOI_Capacity.exe"


class Layout(NamedTuple):
    root: Path          # 설치 루트(exe 가 있는 폴더)
    app: Path           # 실행 중인 앱 소스
    new: Path           # 적용 대기 중인 새 앱(존재 자체가 '준비 완료' 신호)
    old: Path           # 교체 중 백업
    pythonw: Path       # 번들 파이썬(콘솔 없음)
    python: Path        # 번들 파이썬(콘솔 있음 — 첫 실행 설치 진행을 보여준다)
    marker: Path        # 의존성 설치 표식. 없으면 '아직 설치 안 됨'
    main_py: Path


def app_paths(exe: Path) -> Layout:
    """모든 경로는 **exe 위치 기준**. 얼린 exe 안에서 ``__file__`` 은 임시 폴더라 무의미 — ``sys.executable`` 을 쓴다."""
    root = Path(exe).resolve().parent
    return Layout(root=root, app=root / "app", new=root / "app.new", old=root / "app.old",
                  pythonw=root / "python" / "pythonw.exe", python=root / "python" / "python.exe",
                  marker=root / ".deps_installed", main_py=root / "app" / "main.py")


def swap_pending(lay: Layout) -> None:
    """``app.new`` 를 ``app`` 으로 교체한다. Windows 는 디렉터리를 원자적으로 못 바꿔 rename 2번으로 하고,
    그 사이 중단(app 없음)은 여기서 복구한다. **어떤 실패든 구버전이 살아남는다.**"""
    app, new, old = lay.app, lay.new, lay.old

    if not app.exists():                        # 지난번 교체가 중간에 끊겼다
        if new.exists():
            new.rename(app)                     # ① 직후 중단 → 전진 복구
        elif old.exists():
            old.rename(app)                     # ② 실패 후 중단 → 후진 복구
        shutil.rmtree(old, ignore_errors=True)
        return

    if not new.exists():                        # 대기 중인 업데이트 없음
        shutil.rmtree(old, ignore_errors=True)  # 지난 교체의 잔재만 정리
        return

    shutil.rmtree(old, ignore_errors=True)
    if old.exists():
        return          # 옛 백업을 못 치웠다(AV/핸들) → 이번 교체는 보류, 다음 실행에 재시도

    try:
        app.rename(old)                         # ① 실패해도 상태는 그대로다
    except OSError:
        return                                  # 앱이 아직 떠 있거나 잠김
    try:
        new.rename(app)                         # ②
    except OSError:
        old.rename(app)                         # 롤백 — 구버전 복귀
        return
    shutil.rmtree(old, ignore_errors=True)


def launch_cmd(lay: Layout) -> List[str]:
    """표식(``.deps_installed``)이 없으면 **콘솔이 보이는 python.exe** 로 띄운다(lite 첫 실행의 pip 진행이 보이게).
    설치 자체는 앱 코드(``bootstrap.ensure_deps``)가 한다 — 여기서는 어느 실행 파일로 띄울지만 고른다."""
    first_run = not lay.marker.exists() and lay.python.exists()
    exe = lay.python if first_run else lay.pythonw
    return [str(exe), str(lay.main_py)]


def _error(msg: str) -> None:
    """``console=False`` 라 stderr 가 보이지 않는다 — 메시지 상자로 알린다(의존성 0)."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, msg, APP_TITLE, 0x10)
    except Exception:  # noqa: BLE001
        print(msg, file=sys.stderr)


def main() -> int:
    lay = app_paths(Path(sys.executable))
    try:
        swap_pending(lay)
    except OSError:
        pass                    # 교체 실패는 치명적이지 않다 — 구버전으로 계속 간다

    if not lay.pythonw.exists() or not lay.main_py.exists():
        _error("설치가 손상되었습니다. 받은 zip 을 다시 압축 해제해 주세요.\n" f"위치: {lay.root}")
        return 2

    # cwd 는 설치 루트 — app\ 안에 CWD 핸들을 만들면 다음 교체의 rename 이 막힌다.
    # PYTHONNOUSERSITE — 번들은 자체 완결. 같은 버전 파이썬이 PC 에 있어도 개인 패키지가 섞이지 않게.
    subprocess.Popen(launch_cmd(lay), cwd=str(lay.root),
                     env=dict(os.environ, **{APP_HOME_ENV: str(lay.root), "PYTHONNOUSERSITE": "1"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
