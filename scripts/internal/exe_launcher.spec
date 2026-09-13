# -*- mode: python ; coding: utf-8 -*-
"""'exe + app 폴더' 배포용 **얇은 런처** PyInstaller 스펙.

빌드(Windows, 저장소 루트에서):  python scripts\\build.py exe-lite
산출물: dist\\AOI_Capacity_Lite\\AOI_Capacity.exe (단일 파일, 수 MB).

★ 이 exe 에는 **앱 코드가 한 줄도 들어가면 안 된다.** (FrozenImporter 가 디스크의 새 코드를 가린다)
  · hiddenimports 비움            — 앱 모듈을 끌어들일 통로를 없앤다
  · excludes 에 aoi_capacity 명시  — 혹시 참조돼도 빠지게
  · pathex 에 저장소 루트를 넣지 않는다 — Analysis 가 앱 패키지를 찾지 못하게
빌드 후 ``build.py`` 의 verify 가 `_internal/` 부재와 exe 용량으로 재확인한다.
"""

block_cipher = None

import os
_ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
_LAUNCHER = os.path.join(_ROOT, "scripts", "exe_launcher.py")
_ICON = os.path.join(_ROOT, "aoi_capacity", "ui", "assets", "logo.ico")

hiddenimports = []          # ★ 비어 있어야 한다 — 런처는 표준 라이브러리만 쓴다.
excludes = ["aoi_capacity", "PyQt6", "PySide6", "tkinter", "pytest", "IPython", "numpy", "PIL"]

a = Analysis(
    [_LAUNCHER],
    pathex=[],              # ★ 저장소 루트를 넣지 않는다(앱을 못 찾게)
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="AOI_Capacity",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    runtime_tmpdir=None, console=False,
    icon=_ICON if os.path.isfile(_ICON) else None,
)
