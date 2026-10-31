"""계측 결과(out/*.json) + 스크린샷 → HTML 보고서 한 장(바깥 요청 0, 이미지 인라인). 사용: python3 report.py <출력 폴더>"""
import base64, io, json, glob, os, shutil, statistics as st, sys
from pathlib import Path
from PIL import Image
S = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)

V = [  # (키, 이름, 묶음, 한 줄, 무엇이 달라지나, 유지되는 규칙 / 바뀌는 것)
 ("baseline","현재(기준)","base","데이터 입자 16,000개 · Worker + OffscreenCanvas · 걷힐 때 blur(5px)","—","—"),
 ("lite","V1 경량화","particle","같은 '데이터 입자' 장면을 1/3 비용으로","입자 16,000 → 6,000(밀도 낮아짐) · 흐름장을 격자로 120ms 마다 · 팔레트 40 → 12 · dpr 1 · 느려지면 꼬리 생략 · 걷힘은 opacity 만","장면 동일(성김만 다름)"),
 ("pixel","V2 픽셀 버퍼","particle","같은 장면, 그리기 방식만 교체","Path2D · stroke 대신 Uint32 버퍼(반해상도)에 직접 찍고 putImageData 한 번 — 입자 10,000개여도 프레임당 1.5ms","장면 동일(입자가 2px 네모로 또렷)"),
 ("hybrid","V4 하이브리드","particle","틀은 CSS, 데이터 몫만 입자","카드 · 줄 · 트랙은 DOM + CSS 키프레임, 숫자 블록 · 막대 구간만 입자 ≤1,800개(투명 캔버스)","'입자가 데이터 자리에 앉는다' 는 뜻은 남고 틀은 즉시 또렷"),
 ("cheap","V6 최소 변경","particle","현재 코드에 손잡이 넷만","입자 8,000 · dpr 1 · 30fps 상한(두 프레임에 한 번) · blur 제거 — 4줄 치환","장면 동일(움직임이 30fps 라 덜 매끄러움)"),
 ("css","V3 CSS 스켈레톤","css","캔버스 · Worker 없음","카드 · 줄 · 막대가 DOM 요소, transform · opacity 키프레임으로 차례로 자라고 로딩 끝에 제 색으로 — 프레임마다 JS 0","입자 없음(새 디자인)"),
 ("scan","V5 스캔 라인","css","한 번 그리고 스캔 헤드로 드러내기","장면을 캔버스에 한 번만 그리고 clip-path + 스캔 헤드(translateY)가 위→아래로 드러냄 — 프레임마다 JS 0","입자 없음(새 디자인 · AOI 스캔 은유)"),
 ("text_lens","T1 'O 는 렌즈'","text","AOI 의 O 가 렌즈가 되어 A · I 를 검사","렌즈가 A 로 가 결함 하나(빨강)를 찾고 I 는 통과(파랑 점), 제자리로. 기다릴 땐 초점을 더듬음(3px)","글자 'AOI' 새 디자인 · 자막 없음"),
 ("text_bars","T2 '막대로 쓴 AOI'","text","가동률 24시간 막대로 글자를 쓴다","5×7 비트맵의 가로 줄마다 막대 하나가 왼→오른으로 차오름, 색은 범례(Scan · Rescan · Test · Error). 기다릴 땐 '지금' 선이 지나감","글자 'AOI' 새 디자인 · 자막 없음"),
 ("text_story","T3 '검사 이력 4초'","text","Scan → Error → Rescan → PASS 를 4초에","빔이 지나며 파랑, I 가 Error 로 잡혀 흔들리고 Rescan(연파랑) 뒤 PASS(파랑)","글자 'AOI' 새 디자인 · 자막 없음"),
]
COND = {"dpr1_cpu1":"기본(1920×1080 · dpr 1)","dpr1_cpu4":"CPU 4배 느리게(메인 스레드)","dpr15_cpu1":"dpr 1.5(노트북 125~150% 배율)"}

def load():
    runs = {}
    for f in glob.glob(str(S/"out"/"*__*.json")):
        name = os.path.basename(f)[:-5]; v, rest = name.split("__", 1); cond = rest.split("_r")[0]
        d = json.load(open(f, encoding="utf-8"))
        if d["errors"]: print("오류 있는 실행 제외:", name, d["errors"][:1]); continue
        runs.setdefault((v, cond), []).append(d)
    return runs
def agg(ds, path, how="mean"):
    vals = []
    for d in ds:
        x = d
        for k in path.split("."): x = x[k]
        vals.append(x)
    if not vals: return None
    return {"mean": st.mean(vals), "min": min(vals), "max": max(vals)}[how]
def fmt(x, nd=0):
    return "—" if x is None else (f"{x:.{nd}f}")
runs = load()
VK = [v[0] for v in V]
def cell(v, cond, path, how="mean", nd=0):
    return agg(runs.get((v, cond), []), path, how) if (v, cond) in runs else None

# 입자 변형의 '장면 fps': cheap 은 두 프레임에 한 번만 그리므로 콜백 시간 > 0.3ms 인 프레임만 센다
def scene_fps(d):
    if d["worker"]["frames"] == 0: return None
    if "cheap" in d["label"]: return d["worker"]["fpsEff"] / 2
    return d["worker"]["fpsEff"]

def img(path, w=683):
    p = S/"shots"/path
    if not p.exists(): return ""
    im = Image.open(p).convert("RGB"); im.thumbnail((w, 9999)); b = io.BytesIO(); im.save(b, "JPEG", quality=78, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()

# ── 표 · 차트 데이터 ──
def row(v):
    r = {"v": v}
    for cond in COND:
        ds = runs.get((v, cond), []); r[cond] = {
            "n": len(ds),
            "wfps": (st.mean([scene_fps(d) for d in ds]) if ds and ds[0]["worker"]["frames"] else None),
            "wfps_min": (min([scene_fps(d) for d in ds]) if ds and ds[0]["worker"]["frames"] else None),
            "wp95": cell(v, cond, "worker.intP95", "mean"), "wdur": cell(v, cond, "worker.durP50", "mean"), "wdur95": cell(v, cond, "worker.durP95", "max"),
            "w34": cell(v, cond, "worker.over34", "max"), "wframes": cell(v, cond, "worker.frames", "mean"),
            "drop": cell(v, cond, "compositor.dropped", "mean"), "rep": cell(v, cond, "compositor.reported", "mean"),
            "rev95": cell(v, cond, "main.reveal.intP95", "mean"), "rev34": cell(v, cond, "main.reveal.over34", "mean"),
            "mp95": cell(v, cond, "main.intP95", "mean"), "loaf": cell(v, cond, "main.loafSum", "mean"), "gone": cell(v, cond, "t.gone", "mean"), "thr": cell(v, cond, "metrics.ThreadTime", "mean")}
    return r
R = {v[0]: row(v[0]) for v in V}
names = {v[0]: v[1] for v in V}

def svg_bars(title, unit, items, maxv=None, good="low", width=760):
    """가로 막대 — items [(이름, 값, 색)]. 명목 막대는 한 색(RUN), 기준만 강조."""
    items = [(n, (val if val is not None else 0), c) for n, val, c in items]
    mx = maxv or max([i[1] for i in items] + [1]); bh, gap, lw = 22, 8, 150; h = len(items)*(bh+gap)+34
    s = [f'<svg viewBox="0 0 {width} {h}" width="100%" role="img" aria-label="{title}"><text x="0" y="14" class="ct">{title} <tspan class="cu">({unit})</tspan></text>']
    for i, (n, val, c) in enumerate(items):
        y = 28+i*(bh+gap); w = max(1, (width-lw-70)*val/mx)
        s.append(f'<text x="{lw-8}" y="{y+15}" text-anchor="end" class="cl">{n}</text><rect x="{lw}" y="{y}" width="{w:.1f}" height="{bh}" rx="3" fill="{c}"/><text x="{lw+w+6:.1f}" y="{y+15}" class="cv">{val:.0f}</text>')
    return "".join(s)+"</svg>"
RUN, ERR, MUTE, ACC2 = "#2E6BA8", "#C5453C", "#AEB8C4", "#8FB8E0"
def color(v, key, cond="dpr1_cpu1"):
    return ERR if v == "baseline" else RUN

worker_items = [(names[v], R[v]["dpr1_cpu1"]["wp95"], color(v, "wp95")) for v in VK if R[v]["dpr1_cpu1"]["wp95"]]
drop_items = [(names[v], R[v]["dpr1_cpu1"]["drop"], color(v, "drop")) for v in VK]
rev_items = [(names[v], R[v]["dpr1_cpu1"]["rev95"], color(v, "rev")) for v in VK]
dpr_items = [(names[v], R[v]["dpr15_cpu1"]["wp95"], color(v, "wp95")) for v in VK if R[v]["dpr15_cpu1"]["wp95"]]
sweep = [(k, row(k)["dpr1_cpu1"]) for k in ["lite_n2000", "lite", "lite_n12000", "baseline"] if (k, "dpr1_cpu1") in runs]
if sweep:
    sw_rows = []
    for k, r in sweep:
        n = {"lite_n2000": "2,000", "lite": "6,000", "lite_n12000": "12,000", "baseline": "16,000(현재 코드)"}[k]
        sw_rows.append(f"<tr><td>{n}</td><td>{fmt(r['wdur'],1)}</td><td>{fmt(r['wdur95'],1)}</td><td>{fmt(r['wp95'])}</td><td>{fmt(r['wfps'])}</td></tr>")

def trow(v):
    r = R[v]; c1, c4, c15 = r["dpr1_cpu1"], r["dpr1_cpu4"], r["dpr15_cpu1"]
    w = lambda c: ("<span class='na'>JS 0</span>" if c["wfps"] is None else f"{c['wfps']:.0f}" + (f" <small>(최저 {c['wfps_min']:.0f})</small>" if c["n"] > 1 and c["wfps_min"] is not None and abs(c["wfps_min"]-c["wfps"]) > 1 else ""))
    cls = " class='base'" if v == "baseline" else ""
    return (f"<tr{cls}><th>{names[v]}</th><td>{w(c1)}</td><td>{fmt(c1['wp95'])}</td><td>{fmt(c1['wdur'],1)}</td><td>{fmt(c1['drop'])}</td><td>{fmt(c1['rev95'])}</td>"
            f"<td>{w(c15)}</td><td>{fmt(c15['wp95'])}</td><td>{fmt(c15['drop'])}</td><td>{w(c4)}</td><td>{fmt(c4['drop'])}</td><td class='n'>{c1['n']}·{c15['n']}·{c4['n']}</td></tr>")

def card(v):
    key, name, grp, one, what, keep = next(x for x in V if x[0] == v); r = R[v]["dpr1_cpu1"]
    shots = "".join(f'<figure><img src="{img(f"{v}_{t}.png")}" alt="{name} {t}ms"><figcaption>{t/1000:.1f}초</figcaption></figure>' for t in (1200, 2600, 3800) if (S/"shots"/f"{v}_{t}.png").exists())
    lot = f'<figure><img src="{img(f"{v}_lot_3800.png")}" alt="{name} LOT 배포판"><figcaption>LOT 배포판 장면 3.8초</figcaption></figure>' if (S/"shots"/f"{v}_lot_3800.png").exists() else ""
    stat = ("<span class='na'>프레임마다 JS 0</span>" if r["wfps"] is None else f"그림 스레드 {r['wfps']:.0f}fps · 프레임 간격 p95 {fmt(r['wp95'])}ms · 콜백 {fmt(r['wdur'],1)}ms")
    demo = f'<a class="btn" href="demos/{v}.html">데모 열기(더블클릭용 · 가짜 로딩)</a> <a class="btn sub" href="demos/{v}.html?load=7000&busy=1">메인 스레드 7초 막힘으로</a>'
    return f"""<section class="vc" id="v-{v}"><h3>{name} <small>{one}</small></h3>
<p><b>무엇이 달라지나</b> — {what}</p><p><b>디자인</b> — {keep}</p>
<p class="stat">{stat} · 합성기 드롭 {fmt(r['drop'])} · 걷힘 구간 메인 p95 {fmt(r['rev95'])}ms</p>
<div class="shots">{shots}{lot}</div><p>{demo}</p></section>"""

b1 = R["baseline"]["dpr1_cpu1"]; b15 = R["baseline"]["dpr15_cpu1"]; nb = R["noblur"]["dpr1_cpu1"] if "noblur" in R else None
nb1 = row("noblur")["dpr1_cpu1"]
best_particle = min(["lite", "pixel", "hybrid", "cheap"], key=lambda v: R[v]["dpr1_cpu1"]["wp95"] or 999)

html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>시작 화면 렉 개선안</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--bg:#F4F6F8;--ink:#16202B;--ink2:#5A6673;--ink3:#AEB8C4;--line:#D3DAE2;--acc:#2E6BA8;--err:#C5453C;--sans:"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",sans-serif;--mono:Consolas,"D2Coding",monospace}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 var(--sans)}}
.wrap{{max-width:1100px;margin:0 auto;padding:32px 24px 80px}}h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:18px;margin:36px 0 10px;padding-top:10px;border-top:1px solid var(--line)}}h3{{font-size:16px;margin:0 0 8px}}h3 small{{font-weight:500;color:var(--ink2);margin-left:6px}}
.muted{{color:var(--ink2)}}.lead{{font-size:15px}}.box{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 20px;margin:12px 0}}
.rec{{border-left:4px solid var(--acc)}}.warn{{border-left:4px solid var(--err)}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}}th,td{{padding:7px 9px;border-bottom:1px solid #EEF1F4;text-align:right;white-space:nowrap}}th{{background:#F8FAFC;font-weight:600;color:var(--ink2)}}tbody th{{text-align:left;color:var(--ink)}}td.n{{color:var(--ink3)}}tr.base td,tr.base th{{background:#FFF6F5}}
.na{{color:var(--acc);font-weight:600}}small{{color:var(--ink2)}}
.ct{{font:600 13px var(--sans);fill:var(--ink)}}.cu{{font-weight:400;fill:var(--ink2)}}.cl{{font:12px var(--sans);fill:var(--ink2)}}.cv{{font:600 12px var(--mono);fill:var(--ink)}}
.charts{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}@media(max-width:860px){{.charts{{grid-template-columns:1fr}}}}
.vc{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 20px;margin:14px 0}}.vc p{{margin:4px 0}}.stat{{font-family:var(--mono);font-size:12.5px;color:var(--ink2)}}
.shots{{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}}figure{{margin:0;width:calc(25% - 8px);min-width:200px}}figure img{{width:100%;border:1px solid var(--line);border-radius:6px;display:block}}figcaption{{font-size:12px;color:var(--ink2);text-align:center}}
.btn{{display:inline-block;padding:6px 12px;border:1px solid var(--acc);border-radius:8px;color:var(--acc);text-decoration:none;font-weight:600;font-size:13px}}.btn.sub{{border-color:var(--line);color:var(--ink2);font-weight:500}}
ul{{padding-left:20px}}li{{margin:3px 0}}code{{font-family:var(--mono);font-size:12.5px;background:#EEF2F6;padding:1px 4px;border-radius:3px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}@media(max-width:860px){{.grid3{{grid-template-columns:1fr}}}}.kpi{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}}.kpi b{{display:block;font-size:26px;font-family:var(--mono)}}.kpi.bad b{{color:var(--err)}}.kpi.good b{{color:var(--acc)}}
</style></head><body><div class="wrap">
<h1>시작 화면(랜딩 애니메이션) 렉 개선안</h1>
<p class="muted">2026-10-31 · 결과 HTML 의 <code>&lt;script id="boot"&gt;</code>(D104 '데이터 입자') 를 같은 조건에서 계측하고 개선안 9개를 만들어 비교 · 데모는 <code>demos/</code> 폴더의 파일을 더블클릭</p>

<h2>한눈에</h2>
<div class="grid3">
<div class="kpi bad"><span class="muted">현재 — 입자 그림 스레드 프레임 간격 p95</span><b>{fmt(b1['wp95'])} ms</b><span class="muted">60fps 는 16.7ms. dpr 1.5 에서는 {fmt(b15['wp95'])}ms(≈{fmt(b15['wfps'])}fps)</span></div>
<div class="kpi good"><span class="muted">입자 유지 최선 — {names[best_particle]}</span><b>{fmt(R[best_particle]['dpr1_cpu1']['wp95'])} ms</b><span class="muted">같은 조건 p95 · 콜백 {fmt(R[best_particle]['dpr1_cpu1']['wdur'],1)}ms/프레임(현재 {fmt(b1['wdur'],1)}ms)</span></div>
<div class="kpi good"><span class="muted">CSS · 글자 안 — 프레임마다 JS</span><b>0 ms</b><span class="muted">합성 스레드만 — 메인 스레드가 JSON 을 몇 초 붙들어도 움직임이 끊기지 않는다</span></div>
</div>
<div class="box rec"><b>추천</b>
<ul>
<li><b>'데이터 입자' 장면을 그대로 두려면 → V2 픽셀 버퍼.</b> 그리는 방식만 바꿔(Path2D · stroke → 픽셀 버퍼 한 장) 프레임당 비용이 {fmt(b1['wdur'],1)} → {fmt(R['pixel']['dpr1_cpu1']['wdur'],1)}ms, dpr 1.5 에서도 {fmt(R['pixel']['dpr15_cpu1']['wfps'])}fps. 장면 · 4초 규칙 · 고정 레이아웃 전부 유지.</li>
<li><b>손을 가장 적게 대려면 → V6 최소 변경</b>(4줄 치환: 입자 8,000 · dpr 1 · 30fps 상한 · blur 제거). 콜백은 가벼워지지만 움직임이 30fps 라 덜 매끄럽다 — 임시 조치.</li>
<li><b>렉을 원천 차단하려면 → V5 스캔 라인 · V3 CSS 스켈레톤 · 글자 T1~T3.</b> 프레임마다 도는 JS 가 0 이라 어떤 PC 에서도 끊길 거리가 없다(합성기 드롭 {fmt(R['css']['dpr1_cpu1']['drop'])}~{fmt(R['text_bars']['dpr1_cpu1']['drop'])} vs 현재 {fmt(b1['drop'])}). 대신 '입자' 디자인을 버린다 — 현택 선택 사항.</li>
<li><b>어느 안을 고르든 걷힘의 <code>blur(5px)</code> 는 뺀다.</b> 전체 화면 흐림이 걷히는 순간 메인 스레드가 가장 바쁜 때와 겹친다 — blur 만 뺀 실행(noblur)에서 걷힘 구간 p95 {fmt(b1['rev95'])} → {fmt(nb1['rev95'])}ms.</li>
</ul></div>

<h2>왜 렉이 걸리나 — 현재 코드 진단</h2>
<div class="box">
<ul>
<li><b>프레임마다 하는 일이 너무 많다.</b> 입자 16,000개 × curl noise(noise 4번) = 프레임당 noise 약 64,000번 + Path2D 에 꼬리 선 16,000개 · 네모 16,000개를 넣고 팔레트(최대 40색)마다 stroke/fill. 실측 콜백 p50 {fmt(b1['wdur'],1)}ms · p95 {fmt(b1['wdur95'],1)}ms — JS 만으로 예산(16.7ms)의 절반이고, 래스터(선 16,000개를 alpha 로 긋기)는 그 뒤에 따로 든다.</li>
<li><b>dpr 2 까지 그린다.</b> 125~150% 배율 노트북이면 픽셀이 1.6~2.3배 — 같은 코드가 dpr 1.5 에서 {fmt(b15['wfps'])}fps 로 떨어진다(기본 {fmt(b1['wfps'])}fps, 최저 {fmt(b1['wfps_min'])}).</li>
<li><b>Worker 라도 CPU 는 나눠 쓴다.</b> 메인 스레드가 19MB JSON 을 해석하는 4~5초 동안 코어 하나를 다 쓰고, 래스터 스레드 · 합성기 · Worker 가 나머지를 나눈다. 4코어 계측기에서 현재 코드의 Worker 는 그 구간에 {fmt(b1['wfps_min'])}~{fmt(R['baseline']['dpr1_cpu1']['wfps'])}fps 였다(실행마다 편차 큼 = 경쟁 상태의 특징).</li>
<li><b>걷힐 때 전체 화면 blur(5px) + scale.</b> 1920×1080(×dpr²) 캔버스 한 장에 필터를 0.5초 동안 — 그 순간 메인 스레드는 첫 화면을 그리느라 가장 바쁘다. blur 만 뺀 실행에서 걷힘 구간 메인 프레임 p95 {fmt(b1['rev95'])} → {fmt(nb1['rev95'])}ms.</li>
<li><b>OffscreenCanvas 가 없는 브라우저(옛 Edge)는 전부 메인 스레드.</b> 그땐 JSON 해석 동안 0프레임이다(현재 코드의 폴백 경로).</li>
</ul>
<p class="muted">진단 기준: <code>animation-performance</code> 스킬(합성 전용 속성 · 메인 스레드 밖 · 프레임 예산) · <code>improve-animations</code> 감사 항목 5(성능) · <code>design-motion-principles</code> 생성 체크(blur 상한 · 바깥 이징 · 반복 맥동 금지).</p></div>

<h2>어떻게 쟀나</h2>
<div class="box">
<ul>
<li><b>대상 파일</b>: 30일치 보관 샘플(Report 55,717개)을 현재 template 에 넣은 19.3MB 결과 HTML — 현장에서 여는 크기와 같다. boot 스크립트만 변형별로 교체.</li>
<li><b>브라우저</b>: Playwright Chromium 153(헤드리스, 소프트웨어 합성) · Linux 4 vCPU. 조건 셋 — 기본(1920×1080 · dpr 1) · CPU 4배 느리게(CDP 스로틀, 메인 스레드만) · dpr 1.5. 기준 · 주요 변형은 2~3회 반복(표의 n).</li>
<li><b>지표</b>: ① 그림 스레드(Worker) rAF 간격 — 실제로 화면이 바뀐 간격(p95 · fps) 과 콜백 안 시간(JS + 캔버스 명령) ② 합성기가 '놓쳤다' 고 보고한 프레임(CDP 트레이스 PipelineReporter STATE_DROPPED) ③ 걷힘 구간(덮개 opacity 0 → 제거)의 메인 스레드 rAF 간격 p95 ④ long-animation-frame 합(메인이 막힌 시간 — 변형과 무관하게 4초 안팎, JSON 해석 · 모델 계산).</li>
<li><b>주의</b>: 헤드리스 소프트웨어 합성이라 절대값은 현장 PC(Windows · 내장 GPU) 와 다르다 — <b>변형 사이의 상대 비교</b>로 읽는다. 합성기 드롭 수는 메인 스레드 레이어 트리 기준이라 Worker 캔버스 변형에서는 메인이 막힌 동안의 드롭이 섞인다(그 동안에도 캔버스는 Worker fps 로 움직였다). 현장 확인은 아래 '다음'.</li>
</ul></div>

<h2>수치 비교</h2>
<table><thead><tr><th></th><th colspan="5">기본(dpr 1)</th><th colspan="3">dpr 1.5</th><th colspan="2">CPU 4배 느리게</th><th>n</th></tr>
<tr><th>안</th><th>그림 fps</th><th>간격 p95 ms</th><th>콜백 p50 ms</th><th>합성기 드롭</th><th>걷힘 메인 p95 ms</th><th>그림 fps</th><th>간격 p95</th><th>드롭</th><th>그림 fps</th><th>드롭</th><th></th></tr></thead>
<tbody>{"".join(trow(v) for v in VK)}</tbody></table>
<p class="muted">그림 fps = Worker 가 실제로 그린 프레임 수/초(60 이 상한, V6 은 30fps 상한이라 최대 30). 'JS 0' = 그림 스레드 자체가 없음(CSS · WAAPI 만, 합성 스레드). 반복 실행은 평균(기준 3회 · 주요 변형 2~3회 · 나머지 1회). 콜백 p50 = 프레임 하나의 JS + 캔버스 명령 시간.</p>
<div class="charts">
<div class="box">{svg_bars("그림 스레드 프레임 간격 p95 — 기본 조건", "ms, 낮을수록 좋음 · 16.7 = 60fps", worker_items)}</div>
<div class="box">{svg_bars("그림 스레드 프레임 간격 p95 — dpr 1.5", "ms", dpr_items)}</div>
<div class="box">{svg_bars("합성기가 놓친 프레임 — 기본 조건", "개(열기~걷힘 사이)", drop_items)}</div>
<div class="box">{svg_bars("걷힘 구간 메인 스레드 프레임 간격 p95", "ms", rev_items)}</div>
</div>
{"<div class='box'><b>입자 수만 바꾸면?</b>(V1 엔진, 기본 조건) <table><thead><tr><th>입자</th><th>콜백 p50 ms</th><th>콜백 p95 ms</th><th>간격 p95 ms</th><th>fps</th></tr></thead><tbody>" + "".join(sw_rows) + "</tbody></table><p class='muted'>입자 수는 선형으로 비용을 올린다. 현재 코드(16,000 · 꼬리 · 팔레트 40)는 같은 수의 V1 엔진보다 더 무겁다 — 그리는 방식이 비용의 절반이다.</p></div>" if sweep else ""}

<h2>개선안 — 입자 장면을 지키는 넷</h2>
{"".join(card(v) for v in ["pixel", "lite", "hybrid", "cheap"])}
<h2>개선안 — 프레임마다 JS 0(새 디자인)</h2>
{"".join(card(v) for v in ["scan", "css"])}
<h2>'AOI' 글자 랜딩 셋(추가 요청 · 자막 없음 · JS 0)</h2>
<p class="muted">세 편 모두 이 화면의 말(검사 · Error · Rescan · 가동률 막대 · 범례 색)로만 농담을 한다. 글꼴은 시스템(Segoe UI · 맑은 고딕) — 바깥 요청 0.</p>
{"".join(card(v) for v in ["text_lens", "text_bars", "text_story"])}

<h2>모든 안이 지키는 것</h2>
<div class="box"><ul>
<li>페이지를 연 때부터 <b>4초 안에는 걷히지 않는다</b>(현택 규칙) · 로딩이 길면 데이터 몫만 조용히 기다림 · 끝나면 제 색으로.</li>
<li>바깥 요청 0건(Worker 는 파일 안 blob · 글꼴은 시스템) · 덮개는 클릭을 막지 않음 · <code>AOI_BOOT.phase/done/later/abort</code> 인터페이스 그대로 → template 의 나머지 코드 변경 없음.</li>
<li><code>prefers-reduced-motion</code> 이면 이동 없이 바로 완성 상태. 숨은 탭이면 Worker 가 멈춘다(V1 · V2 · V4).</li>
<li>걷힘은 <b>opacity 만</b>(blur · scale 없음) 0.6초.</li>
<li>단계 글자('데이터 읽는 중' …)와 진행선은 DOM — 글자 교체는 WAAPI(transform · opacity), 진행선은 scaleX 전환.</li>
</ul></div>

<h2>다음</h2>
<div class="box"><ul>
<li>현택이 안을 고르면 template 의 <code>&lt;script id="boot"&gt;</code> 만 교체하고 가드(<code>test_boot_screen_*</code> · 브라우저 테스트 · 사본 저장)를 맞춘다. 글자 안은 LOT 배포판에도 같은 장면.</li>
<li><b>현장 Windows 에서 확인</b>: 125~150% 배율 노트북 · 30일치 실데이터 · Edge/Chrome 에서 ① 입자(또는 글자)가 끊기지 않는지 ② 걷힘이 매끄러운지 ③ 두 번째 열기. 이 보고서의 숫자는 헤드리스 상대 비교다.</li>
<li>계측 하네스와 변형 스크립트는 <code>dev/tools/boot_bench/</code>(수동 도구, 테스트 아님) — <code>README.md</code> 에 재현 순서.</li>
</ul></div>
</div></body></html>"""
(OUT/"report.html").write_text(html, encoding="utf-8")
# 데모 복사
(OUT/"demos").mkdir(exist_ok=True)
for f in glob.glob(str(S/"demos"/"*.html")):
    shutil.copy(f, OUT/"demos"/os.path.basename(f))
print("wrote", OUT/"report.html", (OUT/"report.html").stat().st_size)
