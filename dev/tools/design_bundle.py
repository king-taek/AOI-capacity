"""디자인 프로토타입(docs/design/dashboard-redesign) 빌드 — 오프라인 DC 변형과 **더블클릭으로 열리는 단일 HTML** 을 만든다.

    python dev/tools/design_bundle.py            # app/AOI-Dashboard-offline.dc.html 갱신 + 오프라인 단일 HTML 생성
    python dev/tools/design_bundle.py --out 경로  # 단일 HTML 출력 위치 지정

- 입력: app/AOI-Dashboard.dc.html(본체) · app/support.js(DC 런타임, 수정 금지) · app/aoi-data.json(화면 데이터) ·
  offline_shell.html + offline_shell.json(Claude Design 이 만든 번들의 껍데기 — 로더·React·런타임 리소스, 데이터·템플릿은 비움).
- 출력: app/AOI-Dashboard-offline.dc.html(데이터를 aoi-data.js 로 읽는 변형) · `AOI 가동 현황 (오프라인).html`(외부 요청 0, 단일 파일).
- 표준 라이브러리만. 네트워크·NAS 없음. 프로토타입 전용이며 제품(template.html)과는 별개다.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs" / "design" / "dashboard-redesign"
APP = DESIGN / "app"
MAIN = APP / "AOI-Dashboard.dc.html"
OFFLINE_DC = APP / "AOI-Dashboard-offline.dc.html"
DATA = APP / "aoi-data.json"
SHELL = DESIGN / "offline_shell.html"
SHELL_META = DESIGN / "offline_shell.json"
DEFAULT_OUT = DESIGN / "AOI 가동 현황 (오프라인).html"

FETCH_LINE = 'const DATA_P=(window.__aoiFullP ||= fetch("aoi-data.json").then(r=>r.json()));'
OFFLINE_LINE = ('const DATA_P=(window.__aoiFullP ||= new Promise(res=>{const t=()=>window.AOI_DATA?res(window.AOI_DATA)'
                ':setTimeout(t,30);t();}));')
THUMB = ('<template id="__bundler_thumbnail"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
         '<rect width="120" height="120" rx="18" fill="#2E6BA8"/><rect x="26" y="40" width="68" height="9" rx="4.5" fill="#fff" opacity=".95"/>'
         '<rect x="26" y="56" width="46" height="9" rx="4.5" fill="#fff" opacity=".7"/><rect x="26" y="72" width="58" height="9" rx="4.5" fill="#C5453C"/></svg></template>')


def offline_variant(main_html: str) -> str:
    """본체 → 오프라인 DC 변형: fetch 대신 window.AOI_DATA 를 기다리고, helmet 에 aoi-data.js 를 싣는다."""
    if FETCH_LINE not in main_html:
        raise SystemExit("본체에서 DATA_P fetch 줄을 찾지 못했습니다 — 형식이 바뀌었으면 이 도구를 함께 고치세요")
    out = main_html.replace(FETCH_LINE, OFFLINE_LINE)
    marker = "</style>\n</helmet>"
    if marker not in out:
        raise SystemExit("helmet 끝을 찾지 못했습니다")
    return out.replace(marker, '</style>\n<script src="aoi-data.js"></script>\n' + THUMB + "\n</helmet>", 1)


_CAMEL_ATTR_RE = re.compile(r"(\s)([a-z]+[A-Z][A-Za-z0-9]*)(\s*=)")


def encode_camel_attrs(html: str) -> str:
    """support.js 의 `encodeCamelAttrs` 와 같은 규칙 — 번들에서는 템플릿이 문서 자체라 브라우저가 `onClick` 을 `onclick` 으로
    낮춰 버리므로 `sc-camel-on-click` 으로 미리 적어 둔다(원본 번들과 동일)."""
    return _CAMEL_ATTR_RE.sub(lambda m: m.group(1) + "sc-camel-" + re.sub(r"[A-Z]", lambda c: "-" + c.group(0).lower(), m.group(2)) + m.group(3), html)


def bundle_template(offline_dc: str, runtime_uuid: str, data_uuid: str) -> str:
    t = offline_dc.replace('<script src="./support.js"></script>', f'<script src="{runtime_uuid}"></script>', 1)
    t = t.replace('<script src="aoi-data.js"></script>', f'<script src="{data_uuid}"></script>', 1)
    t = t.replace(THUMB + "\n", "", 1)                      # 썸네일 템플릿은 페이지에 넣지 않는다(원본 번들과 동일)
    a, b = t.index("<x-dc>"), t.index("</x-dc>")             # ★ 마크업만 — 스크립트의 `eDay=` 같은 식별자를 건드리면 문법 오류가 난다
    t = t[:a] + encode_camel_attrs(t[a:b]) + t[b:]
    if runtime_uuid not in t or data_uuid not in t:
        raise SystemExit("템플릿에 런타임/데이터 리소스 자리를 만들지 못했습니다")
    return t


def _res(text: str, mime: str) -> dict:
    return {"mime": mime, "compressed": True,
            "data": base64.b64encode(gzip.compress(text.encode("utf-8"), mtime=0)).decode("ascii")}


def build(out: Path = DEFAULT_OUT, offline_dc: Path = OFFLINE_DC) -> Path:
    """단일 HTML 을 `out` 에, 오프라인 DC 변형을 `offline_dc` 에 쓴다.

    기본값은 저장소의 추적 파일(app/AOI-Dashboard-offline.dc.html)이다 — 테스트는 반드시 tmp 경로를 넘긴다.
    같은 내용을 다시 써도 mtime 이 바뀌어 작업 트리가 오염되기 때문이다(test_design_bundle 이 sha256·mtime 으로 지킨다).
    """
    main = MAIN.read_text(encoding="utf-8")
    off = offline_variant(main)
    offline_dc.parent.mkdir(parents=True, exist_ok=True)
    offline_dc.write_text(off, encoding="utf-8")
    meta = json.loads(SHELL_META.read_text(encoding="utf-8"))
    manifest = dict(meta["shell_manifest"])
    data_js = "window.AOI_DATA=" + json.dumps(json.loads(DATA.read_text(encoding="utf-8")), ensure_ascii=False, separators=(",", ":")) + ";"
    manifest[meta["data_uuid"]] = _res(data_js, "application/javascript")
    tpl = bundle_template(off, meta["runtime_uuid"], meta["data_uuid"])
    shell = SHELL.read_text(encoding="utf-8")
    safe = lambda s: s.replace("</", "<\\/")   # noqa: E731 — <script> 안의 JSON 문자열이 태그를 닫지 않게
    html = shell.replace("__MANIFEST__", safe(json.dumps(manifest, ensure_ascii=False)), 1)
    html = html.replace("__TEMPLATE__", safe(json.dumps(tpl, ensure_ascii=False)), 1)
    if "__MANIFEST__" in html or "__TEMPLATE__" in html:
        raise SystemExit("껍데기 자리표시가 남았습니다")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--offline-dc", default=str(OFFLINE_DC), help="오프라인 DC 변형 출력 위치(기본: 저장소의 추적 파일)")
    args = ap.parse_args(argv)
    p = build(Path(args.out), Path(args.offline_dc))
    print(f"오프라인 DC: {args.offline_dc}\n단일 HTML : {p} ({p.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
