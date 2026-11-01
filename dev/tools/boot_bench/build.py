"""template.html + 보관 샘플(30일치) 의 embedded JSON → 시험용 HTML. boot 스크립트를 variants/<이름>.js 로 바꿔 끼운다."""
import gzip, json, re, sys
from pathlib import Path
S = Path(__file__).resolve().parent; ROOT = S.parents[2]
tpl = (ROOT/"aoi_capacity/ui/assets/template.html").read_text(encoding="utf-8")
def embedded_text(sample):
    t = gzip.decompress((ROOT/"dev/samples"/sample).read_bytes()).decode("utf-8")
    h = t.index('id="embedded">')+len('id="embedded">'); e = t.index("</script>", h)
    return t[h:e]
def build(variant, sample, out, lot=False):
    page = tpl
    if variant != "baseline":
        a = page.index('<script id="boot">'); b = page.index("</script>", a)+len("</script>")
        if (S/"variants"/f"{variant}.patch.json").exists():          # baseline 스크립트에 치환만 적용하는 변형
            js = page[a+len('<script id="boot">'):b-len("</script>")]
            for old, new in json.loads((S/"variants"/f"{variant}.patch.json").read_text(encoding="utf-8")):
                assert js.count(old) == 1, (variant, old)
                js = js.replace(old, new)
        else:
            parts = ["_shell.js", "_layout.js"]
            vj = (S/"variants"/f"{variant}.js").read_text(encoding="utf-8")
            if "workerScene(" in vj: parts.append("_engine.js")
            if "cssFrame(" in vj or "cssScene(" in vj: parts.append("_css.js")
            if "textStage(" in vj: parts.append("_text.js")
            if "barsGeom(" in vj: parts.append("_bars.js")
            js = "(function(){\n\"use strict\";\n" + "\n".join((S/"variants"/f).read_text(encoding="utf-8") for f in parts) + "\n" + vj + "\n})();"
        page = page[:a] + '<script id="boot">\n' + js + "\n</script>" + page[b:]
    if lot: page = page.replace('<html lang="ko" ', '<html lang="ko" data-boot="lot" ', 1)
    data = embedded_text(sample)
    page = page.replace("__DATA__", data, 1)
    Path(out).write_text(page, encoding="utf-8")
if __name__ == "__main__":
    variant, sample, out = sys.argv[1:4]
    build(variant, sample, out, lot="--lot" in sys.argv)
    print(out, Path(out).stat().st_size)
