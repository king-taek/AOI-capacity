"""바로가기 아이콘 진단(11/4 임시) — 배포 폴더의 `AOI LOT.lnk` 가 빈 파일 모양으로 보이는 원인을 사용자 PC 에서 가른다.

원인 후보와 이 도구가 보는 것
  1 AOI.ico 안 그림이 전부 PNG 압축      → PNG ico · BMP ico 로 만든 시험 바로가기, 크기별(16·32·48·256) 직접 읽기
  2 탐색기가 공유 폴더 아이콘을 안 읽음   → 공유 ico · 내 PC ico 비교, 공유 주소의 보안 영역 · ZoneMap 설정
  3 경로 특수 글자(`$` · `Eng'r` · 한글)  → .lnk 안에 저장된 아이콘 경로를 글자 그대로 해석(`parse_lnk`)
  4 .lnk 에 아이콘 경로가 잘못 들어감     → 같은 해석(플래그 · 대상 · 아이콘)
  5 폴더 정리 뒤 옛 .lnk 가 옛 위치       → 대상 · 아이콘 파일이 실제로 있는지
  6 AOI.ico 가 안 올라갔거나 깨짐         → 크기 · 해시를 앱 아이콘과 비교
  7 아이콘 캐시가 첫 실패 모습을 기억     → 실행마다 처음 보는 이름의 시험 바로가기, 캐시 파일 크기 · 시각

만드는 것: 내 PC `<데이터>\\icon_diag\\시험_<시각>\\` 와 `<배포 폴더>\\_aoi_icon_diag\\` 에 시험 바로가기 8개(눌러도 LOT 추적 안내 파일이 열릴 뿐),
그리고 보고서(report.html · report.json · 읽은 .lnk/.ico 사본)를 zip 한 장으로. 팝업은 없다.

★ 쓰기는 내 PC 데이터 폴더와 배포 폴더 안 `_aoi_icon_diag\\` 뿐 — 쓰기 함수는 첫 줄에서 `nas_guard.assert_local`(규칙 1, 가드 `test_icon_diag.py`).
장비 NAS 는 읽지도 않는다. Windows 가 아니면 파일 해석만 하고 Windows 호출은 건너뛴다.
"""
from __future__ import annotations

import base64
import datetime as dt
import glob
import hashlib
import html
import json
import os
import socket
import struct
import subprocess
import time
import zipfile
import zlib
from typing import Callable, Dict, List, Optional

from . import nas_guard, publish
from .utils import paths

SHARE_SUB = "_aoi_icon_diag"
LOCAL_SUB = "icon_diag"
PS_TIMEOUT_SEC = 60
SIZES = (16, 32, 48, 256)
OUR_EXT = (".lnk", ".url", ".ico")


# ── 순수 해석(어느 OS 에서나) ───────────────────────────────────────────
def ico_frames(data: bytes) -> List[Dict[str, object]]:
    """ICO 안 그림 목록 — 크기 · 방식(PNG/BMP) · 바이트. 깨졌으면 빈 목록."""
    if len(data) < 6:
        return []
    reserved, typ, n = struct.unpack("<HHH", data[:6])
    if reserved != 0 or typ != 1 or n == 0 or len(data) < 6 + 16 * n:
        return []
    out = []
    for i in range(n):
        w, h, _c, _r, _p, bpp, size, off = struct.unpack("<BBBBHHII", data[6 + 16 * i:22 + 16 * i])
        head = data[off:off + 8]
        out.append({"w": w or 256, "h": h or 256, "bpp": bpp, "bytes": size,
                    "fmt": "PNG" if head.startswith(b"\x89PNG") else ("BMP" if head[:4] == b"\x28\x00\x00\x00" else "?")})
    return out


_LNK_FLAGS = [(0x1, "HasLinkTargetIDList"), (0x2, "HasLinkInfo"), (0x4, "HasName"), (0x8, "HasRelativePath"),
              (0x10, "HasWorkingDir"), (0x20, "HasArguments"), (0x40, "HasIconLocation"), (0x80, "IsUnicode"),
              (0x200, "HasExpString"), (0x4000, "HasExpIcon")]


def _cstr(data: bytes, off: int, unicode: bool, ansi: str) -> str:
    if unicode:
        end = off
        while end + 1 < len(data) and data[end:end + 2] != b"\x00\x00":
            end += 2
        return data[off:end].decode("utf-16-le", "replace")
    end = data.find(b"\x00", off)
    return data[off:end if end >= 0 else len(data)].decode(ansi, "replace")


def parse_lnk(data: bytes, ansi: str = "cp949") -> Dict[str, object]:
    """.lnk(MS-SHLLINK) 해석 — 대상 경로 · 아이콘 위치 · 플래그 · 확장 블록. 실패하면 `error` 만."""
    try:
        if len(data) < 76 or struct.unpack("<I", data[:4])[0] != 0x4C:
            return {"error": "lnk 머리가 아님"}
        flags, attrs = struct.unpack("<II", data[20:28])
        icon_index = struct.unpack("<i", data[56:60])[0]
        out: Dict[str, object] = {"flags": [n for b, n in _LNK_FLAGS if flags & b], "icon_index": icon_index, "file_attrs": attrs}
        pos = 76
        if flags & 0x1:
            pos += 2 + struct.unpack("<H", data[pos:pos + 2])[0]
        if flags & 0x2:
            li = data[pos:]
            size, hsize, lflags, _vol, lbp, cnrl, cps = struct.unpack("<IIIIIII", li[:28])
            lbp_u = struct.unpack("<I", li[28:32])[0] if hsize >= 0x24 else 0
            cps_u = struct.unpack("<I", li[32:36])[0] if hsize >= 0x24 else 0
            if lflags & 1:
                out["local_base_path"] = _cstr(li, lbp_u, True, ansi) if lbp_u else _cstr(li, lbp, False, ansi)
            if lflags & 2 and cnrl:
                c = li[cnrl:]
                net_off = struct.unpack("<I", c[8:12])[0]
                net_u = struct.unpack("<I", c[20:24])[0] if net_off > 0x14 else 0
                out["net_name"] = _cstr(c, net_u, True, ansi) if net_u else _cstr(c, net_off, False, ansi)
            suffix = _cstr(li, cps_u, True, ansi) if cps_u else (_cstr(li, cps, False, ansi) if cps else "")
            out["path_suffix"] = suffix
            base = out.get("local_base_path") or out.get("net_name") or ""
            out["target"] = (str(base).rstrip("\\") + "\\" + suffix) if suffix else str(base)
            pos += size
        uni = bool(flags & 0x80)
        for bit, key in ((0x4, "name"), (0x8, "relative_path"), (0x10, "working_dir"), (0x20, "arguments"), (0x40, "icon_location")):
            if flags & bit:
                n = struct.unpack("<H", data[pos:pos + 2])[0]
                pos += 2
                raw = data[pos:pos + n * (2 if uni else 1)]
                pos += len(raw)
                out[key] = raw.decode("utf-16-le" if uni else ansi, "replace")
        blocks = []
        while pos + 8 <= len(data):
            bsize = struct.unpack("<I", data[pos:pos + 4])[0]
            if bsize < 8:
                break
            sig = struct.unpack("<I", data[pos + 4:pos + 8])[0]
            blk = data[pos:pos + bsize]
            ent = {"sig": f"0x{sig:08X}", "size": bsize}
            if sig in (0xA0000007, 0xA0000001) and bsize >= 788:
                ent["unicode"] = _cstr(blk, 268, True, ansi)
                ent["ansi"] = _cstr(blk, 8, False, ansi)
                out["icon_env" if sig == 0xA0000007 else "target_env"] = ent["unicode"] or ent["ansi"]
            blocks.append(ent)
            pos += bsize
        out["extra_blocks"] = blocks
        return out
    except (struct.error, IndexError, ValueError) as ex:
        return {"error": f"{type(ex).__name__}: {ex}"}


def _png(w: int, h: int, rgba: bytes) -> bytes:
    raw = b"".join(b"\x00" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def similarity(a: Optional[tuple], b: Optional[tuple]) -> Optional[float]:
    """두 그림(w, h, rgba)의 같음 정도 0~1 — 크기가 다르면 None."""
    if not a or not b or a[0] != b[0] or a[1] != b[1]:
        return None
    pa, pb = a[2], b[2]
    if not pa:
        return None
    diff = sum(abs(x - y) for x, y in zip(pa, pb))
    return round(1 - diff / (255 * len(pa)), 4)


def opaque_ratio(img: Optional[tuple]) -> float:
    if not img or not img[2]:
        return 0.0
    al = img[2][3::4]
    return round(sum(1 for v in al if v > 16) / max(1, len(al)), 3)


# ── Windows 호출(ctypes) ───────────────────────────────────────────────
class _Win:
    """SHGetFileInfoW(탐색기가 보여 주는 아이콘) · PrivateExtractIconsW(파일에서 직접 읽기) → RGBA."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes as W
        self.c, self.W = ctypes, W
        self.shell32, self.user32, self.gdi32, self.ole32 = (ctypes.WinDLL(n) for n in ("shell32", "user32", "gdi32", "ole32"))

        class SHFILEINFOW(ctypes.Structure):
            _fields_ = [("hIcon", W.HANDLE), ("iIcon", ctypes.c_int), ("dwAttributes", W.DWORD),
                        ("szDisplayName", W.WCHAR * 260), ("szTypeName", W.WCHAR * 80)]

        class ICONINFO(ctypes.Structure):
            _fields_ = [("fIcon", W.BOOL), ("xHotspot", W.DWORD), ("yHotspot", W.DWORD), ("hbmMask", W.HANDLE), ("hbmColor", W.HANDLE)]

        class BITMAP(ctypes.Structure):
            _fields_ = [("bmType", W.LONG), ("bmWidth", W.LONG), ("bmHeight", W.LONG), ("bmWidthBytes", W.LONG),
                        ("bmPlanes", W.WORD), ("bmBitsPixel", W.WORD), ("bmBits", W.LPVOID)]

        class BIH(ctypes.Structure):
            _fields_ = [("biSize", W.DWORD), ("biWidth", W.LONG), ("biHeight", W.LONG), ("biPlanes", W.WORD), ("biBitCount", W.WORD),
                        ("biCompression", W.DWORD), ("biSizeImage", W.DWORD), ("biXPelsPerMeter", W.LONG), ("biYPelsPerMeter", W.LONG),
                        ("biClrUsed", W.DWORD), ("biClrImportant", W.DWORD)]

        self.SHFILEINFOW, self.ICONINFO, self.BITMAP, self.BIH = SHFILEINFOW, ICONINFO, BITMAP, BIH
        self.shell32.SHGetFileInfoW.argtypes = [W.LPCWSTR, W.DWORD, ctypes.POINTER(SHFILEINFOW), W.UINT, W.UINT]
        self.shell32.SHGetFileInfoW.restype = ctypes.c_size_t
        self.user32.PrivateExtractIconsW.argtypes = [W.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                                     ctypes.POINTER(W.HANDLE), ctypes.POINTER(W.UINT), W.UINT, W.UINT]
        self.user32.PrivateExtractIconsW.restype = W.UINT
        self.user32.GetIconInfo.argtypes = [W.HANDLE, ctypes.POINTER(ICONINFO)]
        self.user32.DestroyIcon.argtypes = [W.HANDLE]
        self.user32.GetDC.argtypes = [W.HWND]
        self.user32.GetDC.restype = W.HANDLE
        self.user32.ReleaseDC.argtypes = [W.HWND, W.HANDLE]
        self.gdi32.GetObjectW.argtypes = [W.HANDLE, ctypes.c_int, W.LPVOID]
        self.gdi32.GetDIBits.argtypes = [W.HANDLE, W.HANDLE, W.UINT, W.UINT, W.LPVOID, W.LPVOID, W.UINT]
        self.gdi32.DeleteObject.argtypes = [W.HANDLE]
        self.ole32.CoInitializeEx.argtypes = [W.LPVOID, W.DWORD]

    def co_init(self) -> None:
        self.ole32.CoInitializeEx(None, 2)

    def _bits(self, hdc, hbm, w: int, h: int) -> bytes:
        c = self.c
        bih = self.BIH(c.sizeof(self.BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = (c.c_ubyte * (w * h * 4))()
        info = (c.c_ubyte * (c.sizeof(self.BIH) + 1024))()
        c.memmove(info, c.byref(bih), c.sizeof(self.BIH))
        if not self.gdi32.GetDIBits(hdc, hbm, 0, h, buf, info, 0):
            return b""
        return bytes(buf)

    def icon_rgba(self, hicon) -> Optional[tuple]:
        c = self.c
        ii = self.ICONINFO()
        if not self.user32.GetIconInfo(hicon, c.byref(ii)):
            return None
        try:
            bm = self.BITMAP()
            src = ii.hbmColor or ii.hbmMask
            self.gdi32.GetObjectW(src, c.sizeof(bm), c.byref(bm))
            w, h = bm.bmWidth, bm.bmHeight if ii.hbmColor else bm.bmHeight // 2
            hdc = self.user32.GetDC(None)
            try:
                if not ii.hbmColor:
                    return (w, h, b"")
                color = bytearray(self._bits(hdc, ii.hbmColor, w, h))
                if color and not any(color[3::4]):          # 알파가 없는 옛 아이콘 — 마스크(흰 = 투명)로 채운다
                    mask = self._bits(hdc, ii.hbmMask, w, h)
                    for i in range(0, len(color), 4):
                        color[i + 3] = 0 if (mask and mask[i] > 127) else 255
                for i in range(0, len(color), 4):           # BGRA → RGBA
                    color[i], color[i + 2] = color[i + 2], color[i]
                return (w, h, bytes(color))
            finally:
                self.user32.ReleaseDC(None, hdc)
        finally:
            for hb in (ii.hbmColor, ii.hbmMask):
                if hb:
                    self.gdi32.DeleteObject(hb)

    def shell_icon(self, path: str, small: bool = False, use_attrs: bool = False) -> Optional[tuple]:
        """탐색기 경로(아이콘 캐시 포함)로 받은 아이콘 — 바로가기면 그 IconLocation 의 그림."""
        c = self.c
        sfi = self.SHFILEINFOW()
        fl = 0x100 | (0x1 if small else 0) | (0x10 if use_attrs else 0)
        r = self.shell32.SHGetFileInfoW(path, 0x80 if use_attrs else 0, c.byref(sfi), c.sizeof(sfi), fl)
        if not r or not sfi.hIcon:
            return None
        try:
            return self.icon_rgba(sfi.hIcon)
        finally:
            self.user32.DestroyIcon(sfi.hIcon)

    def file_icon(self, path: str, size: int) -> Optional[tuple]:
        """아이콘 파일에서 직접 그 크기 그림을 읽기 — 못 읽으면 None."""
        c = self.c
        h = self.W.HANDLE()
        iid = self.W.UINT()
        n = self.user32.PrivateExtractIconsW(path, 0, size, size, c.byref(h), c.byref(iid), 1, 0)
        if n in (0, 0xFFFFFFFF) or not h.value:
            return None
        try:
            return self.icon_rgba(h)
        finally:
            self.user32.DestroyIcon(h)


# ── 쓰기(규칙 1 — 첫 줄 assert_local) ───────────────────────────────────
def _write_local(path: str, data: bytes, roots: List[str]) -> None:
    nas_guard.assert_local(path, roots)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _clear_ours(folder: str, roots: List[str]) -> int:
    """이 도구가 전에 만든 시험 파일(.lnk · .url · .ico)만 지운다 — 다른 것은 건드리지 않는다. 지운 개수."""
    nas_guard.assert_local(folder, roots)
    gone = 0
    try:
        names = os.listdir(folder)
    except OSError:
        return 0
    for n in names:
        if n.lower().endswith(OUR_EXT):
            try:
                os.remove(os.path.join(folder, n))
                gone += 1
            except OSError:
                pass
    return gone


def _zip(path: str, files: Dict[str, bytes], roots: List[str]) -> None:
    nas_guard.assert_local(path, roots)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


# ── 진단 ────────────────────────────────────────────────────────────────
def _read(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def _sha(b: Optional[bytes]) -> str:
    return hashlib.sha256(b).hexdigest()[:12] if b else ""


def _file_url(p: str) -> str:
    p = str(p).replace("\\", "/")
    return "file:" + p if p.startswith("//") else "file:///" + p


_PS_ENV = r"""
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$o=[ordered]@{}
$o.ps=$PSVersionTable.PSVersion.ToString()
$o.language_mode=$ExecutionContext.SessionState.LanguageMode.ToString()
$o.os=[Environment]::OSVersion.VersionString
$z=[ordered]@{}
foreach($u in ($env:AOI_ZONES -split '\|')){ if($u){ try{ $z[$u]=[System.Security.Policy.Zone]::CreateFromUrl($u).SecurityZone.ToString() }catch{ $z[$u]='ERR '+$_.Exception.Message } } }
$o.zones=$z
try{ $null=New-Object -ComObject WScript.Shell; $o.wscript='OK' }catch{ $o.wscript='ERR '+$_.Exception.Message }
$o | ConvertTo-Json -Compress -Depth 4
"""

_PS_MAKE = r"""
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$j=Get-Content -LiteralPath $env:AOI_JOBS -Raw -Encoding UTF8 | ConvertFrom-Json
$sh=New-Object -ComObject WScript.Shell
foreach($x in $j){ try{ $s=$sh.CreateShortcut($x.path); $s.TargetPath=$x.target; if($x.icon){ $s.IconLocation=$x.icon }; $s.Save(); Write-Output ("OK`t"+$x.path) }catch{ Write-Output ("ERR`t"+$x.path+"`t"+$_.Exception.Message) } }
"""


def _ps(script: str, env_extra: Dict[str, str]) -> Dict[str, object]:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                           env=dict(os.environ, **env_extra), timeout=PS_TIMEOUT_SEC, capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"rc": r.returncode, "out": r.stdout.decode("utf-8", "replace"), "err": r.stderr.decode("utf-8", "replace")[-2000:]}
    except (OSError, subprocess.SubprocessError) as ex:
        return {"rc": -1, "out": "", "err": f"{type(ex).__name__}: {ex}"}


def _registry() -> Dict[str, object]:
    """보안 영역 · 탐색기 정책에 관계된 레지스트리 값(읽기만)."""
    try:
        import winreg
    except ImportError:
        return {}
    out: Dict[str, object] = {}
    keys = [("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap"),
            ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap"),
            ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMapKey"),
            ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Policies\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMapKey"),
            ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"),
            ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"),
            ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced")]
    for hive, h, sub in keys:
        vals = {}
        try:
            with winreg.OpenKey(h, sub) as k:
                i = 0
                while i < 300:
                    try:
                        n, v, _t = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    vals[n] = v if isinstance(v, (int, str)) else repr(v)[:200]
                    i += 1
        except OSError:
            vals = None
        out[f"{hive}\\{sub}"] = vals
    return out


def _icon_cache() -> List[Dict[str, object]]:
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Explorer")
    out = []
    for p in sorted(glob.glob(os.path.join(base, "iconcache*.db"))):
        try:
            st = os.stat(p)
            out.append({"file": os.path.basename(p), "kb": st.st_size >> 10,
                        "modified": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")})
        except OSError:
            pass
    return out


def _check_shortcut(path: str, ansi: str) -> Dict[str, object]:
    """배포 폴더에 지금 있는 바로가기 하나 — 해석 + 대상 · 아이콘 파일이 있는지(원인 3 · 4 · 5)."""
    data = _read(path)
    if data is None:
        return {"path": path, "exists": False}
    info: Dict[str, object] = {"path": path, "exists": True, "bytes": len(data), "sha": _sha(data)}
    if path.lower().endswith(".lnk"):
        p = parse_lnk(data, ansi)
        info["lnk"] = p
        icon = str(p.get("icon_env") or p.get("icon_location") or "")
        info["icon_path"] = icon
        info["icon_exists"] = bool(icon) and os.path.isfile(os.path.expandvars(icon))
        tgt = str(p.get("target") or "")
        info["target_exists"] = bool(tgt) and os.path.isfile(tgt)
    else:
        text = data.decode(ansi, "replace")
        info["text"] = text[:600]
        icon = next((ln.split("=", 1)[1].strip() for ln in text.splitlines() if ln.lower().startswith("iconfile=")), "")
        info["icon_path"] = icon
        info["icon_exists"] = bool(icon) and os.path.isfile(icon)
    return info


def _verdict(img: Optional[tuple], blank: Optional[tuple], logo: Optional[tuple]) -> str:
    if img is None:
        return "못 읽음"
    if blank and similarity(img, blank) is not None and similarity(img, blank) >= 0.985:
        return "빈 파일 모양"
    s = similarity(img, logo)
    if s is not None and s >= 0.93:
        return "로고"
    if opaque_ratio(img) < 0.02:
        return "투명(빈 그림)"
    return "다른 그림"


def run(cfg: dict, out_root: Optional[str] = None, log: Optional[Callable[[str], None]] = None) -> Dict[str, object]:
    """진단 한 번 — 결과 dict(zip · report · local_dir · share_dir · summary). 실패해도 보고서는 남긴다."""
    say = log or (lambda _m: None)
    roots = nas_guard.roots_for_cfg(cfg)
    ansi = "mbcs" if os.name == "nt" else "cp949"
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = out_root or str(paths.data_root() / LOCAL_SUB)
    local_dir = os.path.join(base, f"시험_{stamp}")
    nas_guard.assert_local(local_dir, roots)
    files: Dict[str, bytes] = {}
    rep: Dict[str, object] = {"time": stamp, "os": os.name, "host": socket.gethostname()}
    share_lot = str(cfg.get("publish_dir") or "").strip().rstrip("\\/")
    share_full = str(cfg.get("publish_full_dir") or "").strip().rstrip("\\/")
    share = share_lot or share_full
    rep["publish_dir"], rep["publish_full_dir"] = share_lot, share_full

    # 1. 앱 아이콘 · 배포 폴더의 AOI.ico(원인 1 · 6)
    app_ico = publish.app_icon(publish.LOT) or ""
    app_data = _read(app_ico) or b""
    bmp_src = str(paths.logo_path("logo_bmp.ico"))
    bmp_data = _read(bmp_src) or b""
    rep["app_icon"] = {"path": app_ico, "bytes": len(app_data), "sha": _sha(app_data), "frames": ico_frames(app_data)}
    rep["bmp_icon"] = {"path": bmp_src, "bytes": len(bmp_data), "frames": ico_frames(bmp_data)}
    shares = []
    seen = set()
    for d in (share_lot, share_full, os.path.dirname(share_lot) if share_lot else ""):
        if not d or d.lower() in seen:
            continue
        seen.add(d.lower())
        ent: Dict[str, object] = {"dir": d, "reachable": os.path.isdir(d)}
        ico = os.path.join(d, publish.ICON_NAME)
        idata = _read(ico)
        ent["ico"] = {"path": ico, "exists": idata is not None, "bytes": len(idata or b""), "sha": _sha(idata),
                      "same_as_app": bool(idata) and idata == app_data, "frames": ico_frames(idata or b"")}
        if idata:
            files[f"share_files/{len(shares)}_AOI.ico"] = idata
        ent["shortcuts"] = []
        for kind in (publish.LOT, publish.FULL):
            for name in (kind.lnk, kind.shortcut):
                fp = os.path.join(d, name)
                if os.path.isfile(fp):
                    info = _check_shortcut(fp, ansi)
                    ent["shortcuts"].append(info)
                    data = _read(fp)
                    if data:
                        files[f"share_files/{len(shares)}_{name}"] = data
        shares.append(ent)
        say(f"[아이콘 진단] 폴더 {d} — 닿음 {ent['reachable']} · AOI.ico {'있음' if idata else '없음'} · 바로가기 {len(ent['shortcuts'])}개")
    rep["shares"] = shares

    win = None
    if os.name == "nt":
        try:
            win = _Win()
            win.co_init()
        except Exception as ex:  # noqa: BLE001
            rep["win_error"] = f"{type(ex).__name__}: {ex}"
            win = None

    # 2. 환경 · 보안 영역 · 정책 · 아이콘 캐시(원인 2 · 7)
    if os.name == "nt":
        zones = [share, _file_url(share)] if share else []
        if share:
            zones += [os.path.join(share, publish.ICON_NAME), _file_url(os.path.join(share, publish.ICON_NAME))]
        r = _ps(_PS_ENV, {"AOI_ZONES": "|".join(zones)})
        try:
            rep["env"] = json.loads(r["out"].strip().splitlines()[-1]) if r["out"].strip() else {"ps_error": r}
        except (ValueError, IndexError):
            rep["env"] = {"ps_error": r}
        rep["registry"] = _registry()
        rep["icon_cache"] = _icon_cache()

    # 3. 시험 바로가기 8개 — 내 PC · 배포 폴더(원인 1 · 2 · 7)
    sdir = os.path.join(share, SHARE_SUB) if share else ""
    tag = stamp[-6:]
    local_png, local_bmp = os.path.join(local_dir, f"png_{tag}.ico"), os.path.join(local_dir, f"bmp_{tag}.ico")
    _write_local(local_png, app_data, roots)
    if bmp_data:
        _write_local(local_bmp, bmp_data, roots)
    share_ok = False
    if sdir and os.path.isdir(share):
        try:
            nas_guard.assert_local(sdir, roots)
            if not os.path.isdir(sdir):
                _make_dir(sdir, roots)
            _clear_ours(sdir, roots)
            share_ok = publish._write_text(os.path.join(sdir, f"png_{tag}.ico"), app_data, roots, tries=2)
            if bmp_data:
                share_ok = publish._write_text(os.path.join(sdir, f"bmp_{tag}.ico"), bmp_data, roots, tries=2) and share_ok
        except (OSError, nas_guard.NasWriteRefused) as ex:
            rep["share_write_error"] = f"{type(ex).__name__}: {ex}"
            share_ok = False
    rep["share_test_dir"], rep["share_test_ok"] = sdir, share_ok
    target = publish.lnk_target(share, publish.LOT) if share else os.path.join(local_dir, "없음.html")
    s_png = os.path.join(sdir, f"png_{tag}.ico") if share_ok else ""
    s_bmp = os.path.join(sdir, f"bmp_{tag}.ico") if share_ok else ""
    real_ico = os.path.join(share, publish.ICON_NAME) if share else ""
    sys_icon = r"%SystemRoot%\System32\imageres.dll,1"
    variants = [
        ("1 지금 방식", "공유 AOI.ico(PNG)", f"{real_ico},0" if real_ico else ""),
        ("2 공유 PNG 새이름", "공유 시험 ico(PNG)", f"{s_png},0" if s_png else ""),
        ("3 공유 BMP", "공유 시험 ico(BMP)", f"{s_bmp},0" if s_bmp else ""),
        ("4 내PC PNG", "로컬 ico(PNG)", f"{local_png},0"),
        ("5 내PC BMP", "로컬 ico(BMP)", f"{local_bmp},0" if bmp_data else ""),
        ("6 시스템 아이콘", "대조군 imageres.dll", sys_icon),
        ("7 아이콘 없음", "대조군 브라우저 아이콘", None),
    ]
    jobs = [{"path": os.path.join(local_dir, f"{n} {tag}.lnk"), "target": target, "icon": ic or ""}
            for n, _d, ic in variants if ic is None or ic]
    made: Dict[str, str] = {}
    if os.name == "nt":
        jf = os.path.join(local_dir, "jobs.json")
        _write_local(jf, json.dumps(jobs, ensure_ascii=True).encode("ascii"), roots)
        r = _ps(_PS_MAKE, {"AOI_JOBS": jf})
        for line in r["out"].splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                made[parts[1].strip()] = "OK" if parts[0] == "OK" else ("ERR " + (parts[2] if len(parts) > 2 else ""))
        if r["rc"] != 0 or r["err"].strip():
            rep["make_lnk_ps"] = r
    url_name = f"8 url BMP {tag}.url"
    url_icon = s_bmp or local_bmp
    _write_local(os.path.join(local_dir, url_name), publish.shortcut_bytes(share or local_dir, publish.LOT, url_icon if bmp_data else None), roots)
    tests = []
    for n, desc, ic in variants + [("8 url BMP", ".url + BMP ico", url_icon)]:
        fn = url_name if n.startswith("8") else f"{n} {tag}.lnk"
        lp = os.path.join(local_dir, fn)
        t = {"name": n, "desc": desc, "icon": ic or "", "file": fn, "local": lp, "made": made.get(lp, "OK" if os.path.isfile(lp) else "없음")}
        if ic == "" and not n.startswith("7"):
            t["made"] = "건너뜀(아이콘 파일 없음)"
        data = _read(lp)
        if data:
            files[f"tests/{fn}"] = data
            if fn.endswith(".lnk"):
                t["lnk"] = parse_lnk(data, ansi)
            if share_ok:
                sp = os.path.join(sdir, fn)
                t["share"] = sp if publish._write_text(sp, data, roots, tries=2) else ""
        tests.append(t)
    rep["tests"] = tests
    say(f"[아이콘 진단] 시험 바로가기 {sum(1 for t in tests if os.path.isfile(t['local']))}개 · 공유 폴더 복사 {'함' if share_ok else '못 함'}")

    # 4. Windows 가 실제로 읽은 그림(원인 1 · 2 · 7)
    imgs: Dict[str, str] = {}
    if win:
        def keep(key: str, img: Optional[tuple]) -> None:
            if img and img[2]:
                imgs[key] = base64.b64encode(_png(img[0], img[1], img[2])).decode("ascii")

        blank = win.shell_icon("aoi_diag_unknown.zzq", use_attrs=True)
        logo = win.file_icon(local_bmp, 32) if bmp_data else win.file_icon(local_png, 32)
        keep("ref_blank", blank)
        keep("ref_logo", logo)
        reads = []
        refs = {sz: win.file_icon(local_bmp if bmp_data else local_png, sz) for sz in SIZES}
        ico_paths = [("공유 AOI.ico", real_ico), ("공유 시험 PNG", s_png), ("공유 시험 BMP", s_bmp), ("내PC PNG", local_png), ("내PC BMP", local_bmp if bmp_data else "")]
        for label, p in ico_paths:
            if not p:
                continue
            row = {"label": label, "path": p, "sizes": {}}
            for sz in SIZES:
                ref = refs[sz]
                img = win.file_icon(p, sz)
                row["sizes"][str(sz)] = {"ok": bool(img and img[2]), "opaque": opaque_ratio(img), "same_as_logo": similarity(img, ref)}
                keep(f"ico|{label}|{sz}", img)
            reads.append(row)
        rep["ico_reads"] = reads
        for t in tests:
            for where in ("local", "share"):
                p = t.get(where)
                if not p or not os.path.isfile(p):
                    continue
                img = win.shell_icon(p)
                t[f"{where}_shell"] = _verdict(img, blank, logo)
                t[f"{where}_sim"] = similarity(img, logo)
                keep(f"test|{t['name']}|{where}", img)
        for ent in shares:
            for sc in ent.get("shortcuts", []):
                img = win.shell_icon(sc["path"])
                sc["shell"] = _verdict(img, blank, logo)
                keep(f"real|{sc['path']}", img)
    rep["images"] = sorted(imgs)

    # 5. 요약 · 보고서
    rep["summary"] = summarize(rep)
    report_html = render_html(rep, imgs).encode("utf-8")
    files["report.html"] = report_html
    files["report.json"] = json.dumps(rep, ensure_ascii=False, indent=1, default=str).encode("utf-8")
    report_path = os.path.join(local_dir, "report.html")
    _write_local(report_path, report_html, roots)
    zpath = os.path.join(base, f"AOI_icon_diag_{stamp}.zip")
    _zip(zpath, files, roots)
    say(f"[아이콘 진단] 끝 — 보고서 {zpath}")
    for s in rep["summary"]:
        say(f"[아이콘 진단] {s}")
    return {"zip": zpath, "report": report_path, "local_dir": local_dir, "share_dir": sdir if share_ok else "", "summary": rep["summary"]}


def _make_dir(path: str, roots: List[str]) -> None:
    nas_guard.assert_local(path, roots)
    os.makedirs(path, exist_ok=True)


def summarize(rep: Dict[str, object]) -> List[str]:
    """자동으로 읽은 사실을 짧은 문장으로 — 판단은 사람이 그림을 보고 한다."""
    out = []
    fr = rep.get("app_icon", {}).get("frames") or []
    if fr and all(f["fmt"] == "PNG" for f in fr):
        out.append(f"앱 아이콘 ico 그림 {len(fr)}장이 모두 PNG 압축(원인 1 후보)")
    for ent in rep.get("shares", []):
        ico = ent.get("ico", {})
        if not ent.get("reachable"):
            out.append(f"폴더에 닿지 못함: {ent['dir']}")
            continue
        if not ico.get("exists"):
            out.append(f"AOI.ico 없음: {ent['dir']}(원인 6)")
        elif not ico.get("same_as_app"):
            out.append(f"AOI.ico 가 앱 아이콘과 다름: {ent['dir']}(원인 6)")
        for sc in ent.get("shortcuts", []):
            name = os.path.basename(sc["path"])
            if sc.get("icon_path") and not sc.get("icon_exists"):
                out.append(f"{name} 의 아이콘 파일이 없음: {sc['icon_path']}(원인 5)")
            if sc.get("lnk") and "target_exists" in sc and not sc["target_exists"]:
                out.append(f"{name} 의 대상 파일이 없음: {sc['lnk'].get('target')}(원인 5)")
            if sc.get("lnk") and not sc.get("icon_path"):
                out.append(f"{name} 안에 아이콘 경로가 없음(원인 4)")
            if sc.get("shell"):
                out.append(f"{name} 을 Windows 가 읽은 모양: {sc['shell']}")
    for z, v in ((rep.get("env") or {}).get("zones") or {}).items():
        if str(v) not in ("Intranet", "MyComputer"):
            out.append(f"보안 영역 {v}: {z}(원인 2 후보)")
            break
    for row in rep.get("ico_reads", []):
        bad = [s for s, v in row["sizes"].items() if not v["ok"] or (v["same_as_logo"] is not None and v["same_as_logo"] < 0.9)]
        if bad:
            out.append(f"{row['label']} 직접 읽기 실패/다름: {', '.join(bad)}px")
    for t in rep.get("tests", []):
        if "local_shell" in t or "share_shell" in t:
            out.append(f"시험 {t['name']}: 내PC {t.get('local_shell', '-')} · 공유 {t.get('share_shell', '-')}")
    return out


def render_html(rep: Dict[str, object], imgs: Dict[str, str]) -> str:
    """사람이 볼 보고서 한 장(바깥 요청 없음 — 그림은 data: 로)."""
    e = lambda s: html.escape(str(s if s is not None else ""))
    img = lambda k: f'<img src="data:image/png;base64,{imgs[k]}" width="32" height="32" alt="">' if k in imgs else "—"
    rows = []
    for t in rep.get("tests", []):
        rows.append(f"<tr><td>{e(t['name'])}</td><td>{e(t['desc'])}</td><td>{e(t['made'])}</td>"
                    f"<td>{img('test|' + t['name'] + '|local')} {e(t.get('local_shell', ''))}</td>"
                    f"<td>{img('test|' + t['name'] + '|share')} {e(t.get('share_shell', ''))}</td></tr>")
    ico_rows = []
    for r in rep.get("ico_reads", []):
        cells = "".join(f"<td>{img('ico|' + r['label'] + '|' + str(s))}<br><small>{e(v['same_as_logo'])}</small></td>" for s, v in r["sizes"].items())
        ico_rows.append(f"<tr><td>{e(r['label'])}</td>{cells}</tr>")
    real = []
    for ent in rep.get("shares", []):
        for sc in ent.get("shortcuts", []):
            l = sc.get("lnk") or {}
            real.append(f"<tr><td>{e(sc['path'])}</td><td>{img('real|' + sc['path'])} {e(sc.get('shell', ''))}</td>"
                        f"<td>{e(sc.get('icon_path'))}<br><small>있음 {e(sc.get('icon_exists'))}</small></td>"
                        f"<td>{e(l.get('target', ''))}<br><small>있음 {e(sc.get('target_exists', ''))}</small></td>"
                        f"<td><small>{e(', '.join(l.get('flags', [])))}</small></td></tr>")
    summ = "".join(f"<li>{e(s)}</li>" for s in rep.get("summary", []))
    head = "<tr><th>번호</th><th>아이콘</th><th>만듦</th><th>내 PC 폴더</th><th>공유 폴더</th></tr>"
    sizes = "".join(f"<th>{s}px</th>" for s in SIZES)
    return f"""<!doctype html><html lang="ko"><meta charset="utf-8"><title>아이콘 진단 {e(rep.get('time'))}</title>
<style>body{{font-family:'Malgun Gothic',sans-serif;margin:20px;color:#1d2430;background:#fff}}table{{border-collapse:collapse;margin:8px 0 20px}}
td,th{{border:1px solid #dde1e8;padding:5px 8px;font-size:13px;text-align:left;vertical-align:middle}}th{{background:#f3f5f8}}img{{vertical-align:middle;background:#eef0f4}}
small{{color:#667085}}h2{{font-size:16px;margin-top:24px}}</style>
<h1 style="font-size:20px">바로가기 아이콘 진단 · {e(rep.get('host'))} · {e(rep.get('time'))}</h1>
<p>기준 그림: 빈 파일 {img('ref_blank')} · 로고 {img('ref_logo')}</p>
<h2>요약</h2><ul>{summ}</ul>
<h2>시험 바로가기 — Windows 가 읽은 모양</h2><table>{head}{''.join(rows)}</table>
<h2>배포 폴더에 지금 있는 바로가기</h2><table><tr><th>파일</th><th>모양</th><th>아이콘 경로</th><th>대상</th><th>플래그</th></tr>{''.join(real)}</table>
<h2>아이콘 파일을 크기별로 직접 읽기(숫자 = 로고와 같은 정도)</h2><table><tr><th>파일</th>{sizes}</tr>{''.join(ico_rows)}</table>
<h2>환경</h2><pre style="white-space:pre-wrap;font-size:12px">{e(json.dumps({k: rep.get(k) for k in ('env', 'icon_cache', 'share_test_dir', 'share_test_ok', 'share_write_error', 'win_error', 'make_lnk_ps')}, ensure_ascii=False, indent=1, default=str))}</pre>
</html>"""
