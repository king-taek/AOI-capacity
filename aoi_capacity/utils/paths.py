"""경로 해석 — 한 질문에 한 함수.

- `_project_root()`   앱 소스 루트(개발: 저장소 루트 / 배포: `app/`).
- `resource_path()`   동봉 리소스(템플릿, 아이콘, 기본 CSV).
- `install_root()`    exe 배포의 설치 루트(런처가 `AOI_APP_HOME` 로 알려줌). 없으면 None.
- `data_root()`       이 PC 사용자의 데이터 폴더. ★ 절대 `app/` 안이 아니다(업데이트가 `app/` 를 통째로 교체)
                      그리고 절대 NAS 가 아니다.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from .. import APP_ID

_MADE_DIRS: set = set()
APP_HOME_ENV = "AOI_APP_HOME"
DATA_HOME_ENV = "AOI_DATA_HOME"
EXE_NAME = "AOI_Capacity.exe"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_dir(p: Path) -> Path:
    key = str(p)
    if key not in _MADE_DIRS:
        p.mkdir(parents=True, exist_ok=True)
        _MADE_DIRS.add(key)
    return p


def resource_path(rel: str) -> Path:
    """동봉 리소스. PyInstaller onefile(sys._MEIPASS) → 소스 루트 순."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        cand = Path(base) / rel
        if cand.exists():
            return cand
    return _project_root() / rel


def template_path() -> Path:
    return resource_path("aoi_capacity/ui/assets/template.html")


def default_devices_csv() -> Path:
    return resource_path("aoi_capacity/assets/devices.default.csv")


def logo_path(name: str = "logo.png") -> Path:
    return resource_path(f"aoi_capacity/ui/assets/{name}")


def install_root() -> Optional[Path]:
    """exe 배포의 설치 루트. 런처가 준 환경변수가 1순위, 없으면(백신이 exe 를 막아 bat 로 띄운 경우)
    `app/` 의 부모에 exe 와 python/ 이 있으면 그 폴더."""
    home = os.environ.get(APP_HOME_ENV)
    if home:
        return Path(home)
    root = _project_root().parent
    if (root / EXE_NAME).is_file() and (root / "python").is_dir():
        return root
    return None


def data_root() -> Path:
    home = os.environ.get(DATA_HOME_ENV)
    if home:
        return _ensure_dir(Path(home))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return _ensure_dir(Path(local) / APP_ID)
    return _ensure_dir(Path.home() / ".aoi_capacity")


def prefs_file() -> Path:
    return data_root() / "prefs.json"


def devices_csv_path() -> Path:
    return data_root() / "devices.csv"


def cache_file() -> Path:
    return data_root() / "aoi_cache.json"


def log_file() -> Path:
    return data_root() / "app.log"


def output_dir(configured: str = "") -> Path:
    return Path(configured) if configured else data_root()


def output_html(configured: str = "") -> Path:
    return output_dir(configured) / "AOI_capacity.html"


#: 결과 HTML 이 한도(`split_mb`)를 넘어 기간별로 나뉠 때 옛 구간 파일의 이름 — `AOI_capacity_2026-06-25~2026-08-10.html`.
#: 가장 최근 구간은 원래 이름(`output_name`) 그대로라 더블클릭하던 파일이 바뀌지 않는다.
def part_name(output_name: str, day_from: str, day_to: str) -> str:
    stem, ext = os.path.splitext(output_name)
    return f"{stem}_{day_from}~{day_to}{ext}"


def part_re(output_name: str):
    """`part_name` 이 만든 이름만 맞는 정규식 — 옛 분할 파일을 찾아 정리할 때 이 모양 밖의 파일은 절대 건드리지 않는다."""
    import re

    stem, ext = os.path.splitext(output_name)
    return re.compile(rf"^{re.escape(stem)}_(\d{{4}}-\d\d-\d\d)~(\d{{4}}-\d\d-\d\d){re.escape(ext)}$", re.I)


def output_parts(configured: str = "", output_name: str = "AOI_capacity.html") -> list:
    """옛 구간 파일들(새 것부터). 나뉘지 않았으면 빈 목록."""
    folder = output_dir(configured)
    rx = part_re(output_name)
    try:
        names = [n for n in os.listdir(folder) if rx.match(n)]
    except OSError:
        return []
    return [folder / n for n in sorted(names, key=lambda n: rx.match(n).group(1), reverse=True)]


def ensure_user_files() -> bool:
    """첫 실행: 데이터 폴더에 devices.csv 가 없으면 동봉 예시를 복사한다. 복사했으면 True."""
    dst = devices_csv_path()
    if dst.exists():
        return False
    src = default_devices_csv()
    if src.is_file():
        shutil.copyfile(src, dst)
        return True
    return False
