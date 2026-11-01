"""더블클릭용 데모 페이지: 변형 boot 스크립트 + 가짜 로딩(?load=ms · ?busy=1 메인 스레드 막힘 · ?lot=1 웨이퍼 장면)."""
import json, sys
from pathlib import Path
S = Path(__file__).resolve().parent; ROOT = S.parents[2]
tpl = (ROOT/"aoi_capacity/ui/assets/template.html").read_text(encoding="utf-8")
def boot_js(variant):
    if variant == "current":   # 지금 template 의 boot(11/1 부터 T2-B)
        a = tpl.index('<script id="boot">')+len('<script id="boot">'); b = tpl.index("</script>", a); return tpl[a:b]
    js = (S/"variants"/"_baseline_d104.js").read_text(encoding="utf-8")   # 옛 D104 입자 장면
    if variant == "baseline": return js
    pj = S/"variants"/f"{variant}.patch.json"
    if pj.exists():
        for old, new in json.loads(pj.read_text(encoding="utf-8")):
            assert js.count(old) == 1; js = js.replace(old, new)
        return js
    parts = ["_shell.js", "_layout.js"]; vj = (S/"variants"/f"{variant}.js").read_text(encoding="utf-8")
    if "workerScene(" in vj: parts.append("_engine.js")
    if "cssFrame(" in vj: parts.append("_css.js")
    if "textStage(" in vj or "barsGeom(" in vj or "barsListScene(" in vj: parts.append("_text.js")
    if "barsGeom(" in vj or "barsListScene(" in vj: parts.append("_bars.js")
    return "(function(){\n\"use strict\";\n" + "\n".join((S/"variants"/f).read_text(encoding="utf-8") for f in parts) + "\n" + vj + "\n})();"
PAGE = """<!doctype html>
<html lang="ko" data-theme="light"><head><meta charset="utf-8"><title>시작 화면 데모 — {title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{{--bg:#F4F6F8;--sans:"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",sans-serif}}html,body{{margin:0;background:var(--bg);font-family:var(--sans);color:#16202B}}
.wrap{{max-width:1200px;margin:0 auto;padding:28px 24px}}h1{{font-size:20px;margin:0 0 6px}}.muted{{color:#5A6673;font-size:13px}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:22px 0}}.card{{background:#fff;border:1px solid #D3DAE2;border-radius:12px;padding:18px}}.card b{{display:block;font-size:30px;margin:6px 0}}
.panel{{background:#fff;border:1px solid #D3DAE2;border-radius:12px;padding:14px 18px}}.row{{display:grid;grid-template-columns:120px 60px 1fr 60px;gap:14px;align-items:center;padding:9px 0;border-bottom:1px solid #EEF1F4;font-size:13px}}
.bar{{height:14px;background:#DFE5EC;border-radius:3px;position:relative;overflow:hidden}}.bar i{{position:absolute;top:0;height:100%;background:#2E6BA8}}
.ctl{{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #D3DAE2;padding:10px 24px;font-size:13px;display:flex;gap:14px;flex-wrap:wrap;align-items:center}}.ctl a{{color:#2E6BA8}}.ctl a.back{{display:inline-block;padding:5px 11px;border:1px solid #2E6BA8;border-radius:8px;font-weight:600;text-decoration:none;margin-right:6px}}
</style>
<script>if(/[?&]lot=1/.test(location.search))document.documentElement.setAttribute("data-boot","lot");</script>
</head><body>
<script id="boot">
{boot}
</script>
<div class="wrap"><h1>AOI 가동 현황 — 데모 화면({title})</h1><p class="muted">이 페이지는 시작 화면 동작만 보는 자리표시 화면입니다. 숫자는 가짜입니다.</p>
<div class="cards"><div class="card"><span class="muted">평균 가동률</span><b>62.4%</b><span class="muted">장비 30대</span></div><div class="card"><span class="muted">Error</span><b style="color:#C5453C">17건</b><span class="muted">Lot 단위</span></div><div class="card"><span class="muted">살펴볼 장비</span><b>5대</b><span class="muted">40% 미만 · Error 3건 이상</span></div></div>
<div class="panel">{rows}</div></div>
<div class="ctl"><a class="back" href="../index.html" onclick="if(history.length>1){{history.back();return false;}}">← 보고서로</a><span>다시 보기:</span><a href="?load=2500">빠른 로딩(2.5초)</a><a href="?load=7000">느린 로딩(7초)</a><a href="?load=7000&busy=1">메인 스레드 7초 막힘(JSON 해석 흉내)</a><a href="?lot=1&load=2500">LOT 배포판 장면</a><a href="?lot=1&load=7000&busy=1">LOT + 막힘</a><span class="muted" id="st"></span></div>
<script>
(function(){{const q=new URLSearchParams(location.search),load=Math.max(300,Number(q.get("load")||2500)),busy=q.get("busy")==="1",B=window.AOI_BOOT;
  const st=document.getElementById("st");const t0=performance.now();
  const ph=[.08,.42,.54,.9].map(f=>f*load);
  if(busy){{ // 메인 스레드를 load ms 동안 통째로 막는다 — 실제 파일에서 JSON 해석 · 모델 계산이 하는 일
    setTimeout(()=>{{const until=performance.now()+load-60;let k=0,i=0;while(performance.now()<until){{k=(k*31+1)%1e9;const el=performance.now()-t0;if(i<4&&el>=ph[i]){{try{{B&&B.phase(i+1);}}catch(e){{}}i++;}}}}
      try{{B&&B.done();}}catch(e){{}}st.textContent="로딩 흉내 "+Math.round(load)+"ms(막힘) 끝";}},60);}}
  else{{ph.forEach((t,i)=>setTimeout(()=>{{try{{B&&B.phase(i+1);}}catch(e){{}}}},t));setTimeout(()=>{{try{{B&&B.done();}}catch(e){{}}st.textContent="로딩 흉내 "+Math.round(load)+"ms 끝";}},load);}}
}})();
</script></body></html>"""
def rows():
    import random; r = random.Random(7); out = []
    for k in range(14):
        segs = ""; p = r.random()*.15
        while p < .9:
            w = .03+r.random()*.1; segs += f'<i style="left:{p*100:.1f}%;width:{w*100:.1f}%;background:{r.choice(["#2E6BA8","#2E6BA8","#2E6BA8","#8FB8E0","#C5453C","#7A5BB5"])}"></i>'; p += w+.02+r.random()*.1
        out.append(f'<div class="row"><span>AOI-{k+1}</span><b>{r.randint(20,95)}%</b><div class="bar">{segs}</div><span class="muted">{r.randint(0,4)}건</span></div>')
    return "\n".join(out)
if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    names = {"baseline":"현재(기준)","lite":"V1 경량화","pixel":"V2 픽셀 버퍼","css":"V3 CSS 스켈레톤","hybrid":"V4 하이브리드","scan":"V5 스캔 라인","cheap":"V6 최소 변경(30fps)","text_lens":"T1 O 는 렌즈","text_bars":"T2 막대로 쓴 AOI","text_story":"T3 검사 이력 4초","bars_a":"T2-A 줄마다 차오름","bars_b":"T2-B 장비 목록","bars_c":"T2-C 스캔 헤드","bars_b_wave":"W1 파도","bars_b_drift":"W2 흐름","bars_b_glow":"W3 점등","bars_b_count":"W4 셈"}
    for v, t in names.items():
        (out/f"{v}.html").write_text(PAGE.format(title=t, boot=boot_js(v), rows=rows()), encoding="utf-8")
        print(v, (out/f"{v}.html").stat().st_size)
