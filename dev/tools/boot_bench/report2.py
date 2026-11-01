"""한눈에 읽는 판 — 아티팩트용(스켈레톤 없음 · 테마 토큰). python3 report2.py <출력.html>"""
import base64, io, json, glob, os, statistics as st, sys
from pathlib import Path
from PIL import Image
S = Path(__file__).resolve().parent; OUT = Path(sys.argv[1])
V = [  # 키, 이름, 묶음, 한 줄, 디자인 변화, 코드 변경, 설명
 ("baseline","현재","base","데이터 입자 16,000개 · Worker 캔버스 · 걷힐 때 전체 화면 blur","—","—","지금 template 의 boot 스크립트 그대로."),
 ("pixel","V2 픽셀 버퍼","particle","같은 장면, 그리는 방식만 교체","그대로","엔진 교체(스크립트 1개)","Path2D 선 16,000개를 긋는 대신 픽셀 버퍼 한 장에 점을 찍고 한 번에 올린다. 입자 10,000개여도 프레임당 1.5ms."),
 ("lite","V1 경량화","particle","입자를 줄이고 계산을 격자로","살짝 성김","엔진 교체(스크립트 1개)","입자 16,000 → 6,000, 흐름장은 24px 격자로 120ms 마다, 팔레트 40 → 12, dpr 1. 느려지면 꼬리를 생략한다."),
 ("hybrid","V4 하이브리드","particle","틀은 CSS, 데이터 몫만 입자","틀이 즉시 또렷","엔진 교체 + CSS","카드 · 줄 · 트랙은 DOM 요소로 바로 그리고, 숫자 블록 · 막대 구간에만 입자 1,800개가 날아와 앉는다."),
 ("cheap","V6 최소 변경","particle","현재 코드에 손잡이 넷","그대로(30fps)","4줄 치환","입자 8,000 · dpr 1 · 두 프레임에 한 번 그리기 · blur 제거. 가장 쉬운 임시 조치."),
 ("scan","V5 스캔 라인","css","한 번 그리고 스캔 헤드로 드러내기","새 디자인","캔버스 1회 + CSS","장면을 한 번만 그리고 스캔 헤드가 위에서 아래로 지나며 드러낸다(AOI 스캔 은유). 프레임마다 JS 0."),
 ("css","V3 CSS 스켈레톤","css","캔버스 · Worker 없음","새 디자인","CSS 만","카드 · 줄 · 막대가 DOM 요소이고 CSS 키프레임으로 차례로 자란다. 프레임마다 JS 0."),
 ("text_lens","T1 'O 는 렌즈'","text","O 가 A 와 I 를 검사한다","글자 AOI","CSS 만","렌즈(O)가 A 로 가서 결함 하나(빨강)를 찾고 I 는 통과(파랑 점) 뒤 제자리로. 기다릴 땐 초점을 더듬는다."),
 ("text_bars","T2 '막대로 쓴 AOI'","text","가동률 막대로 글자를 쓴다","글자 AOI","CSS 만","5×7 비트맵의 줄마다 막대가 왼쪽에서 차오른다. 색은 범례 그대로(Scan · Rescan · Test · Error). 기다릴 땐 '지금' 선이 지나간다."),
 ("text_story","T3 '검사 이력 4초'","text","Scan → Error → Rescan → PASS","글자 AOI","CSS 만","빔이 지나며 파랑이 되고, I 가 Error 로 잡혀 흔들린 뒤 Rescan(연파랑) 을 거쳐 PASS(파랑)."),
 ("bars_a","T2-A '줄마다 차오름'","t2","막대마다 구간 1~3개, 읽는 순서로","글자 AOI","CSS 만","막대 하나가 하루의 24시간 막대처럼 구간 1~3개(Scan · Rescan · Test · Error)로 나뉘고, 위에서 아래 · 왼쪽에서 오른쪽 순서로 차오른다. 기다릴 땐 '지금' 선이 하루를 가로지른다."),
 ("bars_b","T2-B '장비 목록'","t2","가동률 목록 줄 7개 안에 글자가 숨어 있다","글자 AOI","CSS 만","가동률 화면과 같은 줄(장비 이름 자리 · 숫자 블록 · 24시간 트랙)이 7개 깔리고, 트랙 안의 바쁜 구간이 자라서 AOI 를 쓴다 — 쉬는 시간은 회색 트랙. 기다릴 땐 '지금' 선."),
 ("bars_b_wave","W1 파도","idle","글자 구간이 왼→오른으로 살짝 들렸다 내려온다","—","CSS 만","열마다 위상을 달리해 구간이 4px 들렸다 내려온다(2.6초 주기). 'AOI' 가 파도를 탄다."),
 ("bars_b_drift","W2 흐름","idle","구간이 아주 천천히 오른쪽으로 흘렀다 돌아온다","—","CSS 만","줄마다 4~6px 를 5.2초에 걸쳐 흘렀다 돌아온다. 하루가 흐른다는 뜻, 가장 조용하다."),
 ("bars_b_glow","W3 점등","idle","구간이 읽는 순서로 하나씩 밝아졌다 돌아온다","—","CSS 만","구간 하나가 0.2초쯤 옅어졌다 돌아오며 다음 구간으로 넘어간다(읽는 순서, 한 바퀴 약 5초). 데이터가 차례로 들어오는 중."),
 ("bars_b_count","W4 셈","idle","숫자 블록이 값을 세듯 폭이 줄었다 늘었다","—","CSS 만","줄 왼쪽의 숫자 블록이 왼쪽 기준으로 55~100% 사이를 1.9초에 오간다(줄마다 위상). 트랙은 가만히 — 계산 중."),
 ("bars_c","T2-C '스캔 헤드'","t2","스캔 헤드가 지나가며 글자를 쓴다","글자 AOI","CSS 만","빈 트랙이 먼저 깔리고 스캔 헤드가 왼쪽에서 오른쪽으로 지나가면 닿은 구간부터 차오른다(AOI 검사처럼). 지나간 뒤 기다릴 땐 헤드가 천천히 오간다."),
]
def load():
    runs = {}
    for f in glob.glob(str(S/"out"/"*__*.json")):
        name = os.path.basename(f)[:-5]; v, rest = name.split("__", 1); cond = rest.split("_r")[0]
        d = json.load(open(f, encoding="utf-8"))
        if d["errors"]: continue
        runs.setdefault((v, cond), []).append(d)
    return runs
runs = load()
def m(v, cond, path, how="mean"):
    vals = []
    for d in runs.get((v, cond), []):
        x = d
        for k in path.split("."): x = x[k]
        vals.append(x)
    if not vals: return None
    return {"mean": st.mean(vals), "min": min(vals), "max": max(vals)}[how]
def fps(v, cond):
    ds = runs.get((v, cond), [])
    if not ds or ds[0]["worker"]["frames"] == 0: return None
    f = st.mean(d["worker"]["fpsEff"] for d in ds); return f/2 if v == "cheap" else f
def f0(x): return "—" if x is None else f"{x:.0f}"
def f1(x): return "—" if x is None else f"{x:.1f}"
def img(path, w=640):
    p = S/"shots"/path
    if not p.exists(): return ""
    im = Image.open(p).convert("RGB"); im.thumbnail((w, 9999)); b = io.BytesIO(); im.save(b, "JPEG", quality=76, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
R = {}
for v in [x[0] for x in V] + ["noblur"]:
    R[v] = {c: {"fps": fps(v, c), "p95": m(v, c, "worker.intP95"), "dur": m(v, c, "worker.durP50"), "drop": m(v, c, "compositor.dropped"), "rev": m(v, c, "main.reveal.intP95")} for c in ["dpr1_cpu1", "dpr15_cpu1", "dpr1_cpu4"]}
names = {x[0]: x[1] for x in V}
def grade(v):
    r = R[v]["dpr1_cpu1"]; r15 = R[v]["dpr15_cpu1"]
    if r["p95"] is None or r["fps"] is None: return ("JS 0", "g3", "프레임마다 도는 JS 가 없다")
    worst = max(r["p95"] or 0, r15["p95"] or 0)
    if worst <= 40: return ("매끄러움", "g2", f"p95 {f0(r['p95'])}ms · dpr 1.5 {f0(r15['p95'])}ms")
    if worst <= 80: return ("가끔 끊김", "g1", f"p95 {f0(r['p95'])}ms · dpr 1.5 {f0(r15['p95'])}ms")
    return ("끊김", "g0", f"p95 {f0(r['p95'])}ms · dpr 1.5 {f0(r15['p95'])}ms")
def mainok(v):
    return ("영향 없음", "g3") if R[v]["dpr1_cpu1"]["fps"] is None else ("CPU 를 나눠 씀", "g1" if v == "baseline" else "g2")
def rec(v):
    return {"pixel": ("추천", "g3"), "cheap": ("임시 조치", "g1"), "baseline": ("", ""), "scan": ("새 디자인이면 추천", "g2"), "text_lens": ("글자면 추천", "g2")}.get(v, ("", ""))
chip = lambda t, c: f'<span class="chip {c}">{t}</span>' if t else ""
b, px, nb = R["baseline"]["dpr1_cpu1"], R["pixel"]["dpr1_cpu1"], R["noblur"]["dpr1_cpu1"]
b15, px15 = R["baseline"]["dpr15_cpu1"], R["pixel"]["dpr15_cpu1"]

def mrow(v):
    k, name, grp, one, design, code, _ = next(x for x in V if x[0] == v); g = grade(v); mo = mainok(v); rc = rec(v); r = R[v]["dpr1_cpu1"]
    cls = " class='base'" if v == "baseline" else ""
    return f"<tr{cls}><th>{name}<br><small>{one}</small></th><td>{chip(*g[:2])}<br><small>{g[2]}</small></td><td>{chip(*mo)}<br><small>합성기 드롭 {f0(r['drop'])}</small></td><td>{design}</td><td>{code}</td><td>{chip(*rc)}</td></tr>"

def bars(items, unit, cap=None):
    mx = cap or max(x[1] for x in items); out = []
    for n, val, c in items:
        w = min(100, val/mx*100); out.append(f'<div class="br"><span class="bl">{n}</span><i class="bb"><b class="{c}" style="width:{w:.1f}%"></b></i><span class="bv">{val:.0f}{unit}</span></div>')
    return "".join(out)
p95_items = [(names[v], R[v]["dpr1_cpu1"]["p95"], "e" if v == "baseline" else "a") for v in ["baseline", "cheap", "hybrid", "lite", "pixel"]]
p95_items.sort(key=lambda x: -x[1])
drop_items = sorted([(names[v], R[v]["dpr1_cpu1"]["drop"], "e" if v == "baseline" else "a") for v, *_ in V if R[v]["dpr1_cpu1"]["drop"] is not None], key=lambda x: -x[1])

def idlecard(v):
    k, name, grp, one, design, code, desc = next(x for x in V if x[0] == v)
    return f"""<article class="vc t2"><div class="vh"><h3>{name}</h3><span class="stat">{one}</span><button class="btn" data-demo="{v}" data-slow="1">데모 보기</button></div><p>{desc}</p></article>"""
def t2card(v):
    k, name, grp, one, design, code, desc = next(x for x in V if x[0] == v)
    shots = "".join(f'<figure><img src="{img(f"{v}_{t}.png", 560)}" alt="{name} {t}ms" loading="lazy"><figcaption>{t/1000:.1f}초</figcaption></figure>' for t in (1200, 2600, 3800) if (S/"shots"/f"{v}_{t}.png").exists())
    return f"""<article class="vc t2"><div class="vh"><h3>{name}</h3><button class="btn" data-demo="{v}">데모 보기</button></div><p>{desc}</p><div class="shots">{shots}</div></article>"""
def vcard(v):
    k, name, grp, one, design, code, desc = next(x for x in V if x[0] == v); r = R[v]["dpr1_cpu1"]; g = grade(v)
    shots = "".join(f'<figure><img src="{img(f"{v}_{t}.png")}" alt="{name} {t}ms" loading="lazy"><figcaption>{t/1000:.1f}초</figcaption></figure>' for t in (1200, 2600, 3800) if (S/"shots"/f"{v}_{t}.png").exists())
    stat = "프레임마다 JS 0" if r["fps"] is None else f"그림 {f0(r['fps'])}fps · 간격 p95 {f0(r['p95'])}ms · 콜백 {f1(r['dur'])}ms"
    return f"""<article class="vc" id="v-{v}"><div class="vh"><h3>{name}</h3>{chip(*g[:2])}<span class="stat">{stat}</span><button class="btn" data-demo="{v}">데모 보기</button></div>
<p>{desc}</p><div class="shots">{shots}</div></article>"""

demo_tabs = "".join(f'<button class="tab" data-demo="{x[0]}"{" data-slow=1" if x[2]=="idle" else ""}>{x[1]}</button>' for x in V)
html = f"""<title>시작 화면 렉 개선안</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* 레이아웃: 결론 → 큰 차이 4장 → 비교표 → 데모 뷰어 → 안 카드 → 자세한 수치(접힘) */
:root{{--bg:#F4F6F8;--ink:#16202B;--ink2:#5A6673;--ink3:#AEB8C4;--line:#D3DAE2;--acc:#2E6BA8;--err:#C5453C;--ok:#2F8F5B;--warn:#C98A1C;--card:#FFFFFF;--card2:#F8FAFC;--baserow:#FFF6F5;--codebg:#EEF2F6;--sep:#EEF1F4;--chip0:#FBE3E1;--chip1:#FBEFD4;--chip2:#DCE7F3;--chip3:#DAF0E3;--sans:"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",sans-serif;--mono:Consolas,"D2Coding",monospace}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#141A21;--ink:#E6ECF2;--ink2:#A3B0BD;--ink3:#6B7886;--line:#2B3540;--acc:#6FA6DC;--err:#E0756C;--ok:#5FB884;--warn:#D9A54A;--card:#1B232C;--card2:#20292F;--baserow:#2C2124;--codebg:#243039;--sep:#242D36;--chip0:#4A2A28;--chip1:#4A3B1E;--chip2:#223548;--chip3:#1F3B2C;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#141A21;--ink:#E6ECF2;--ink2:#A3B0BD;--ink3:#6B7886;--line:#2B3540;--acc:#6FA6DC;--err:#E0756C;--ok:#5FB884;--warn:#D9A54A;--card:#1B232C;--card2:#20292F;--baserow:#2C2124;--codebg:#243039;--sep:#242D36;--chip0:#4A2A28;--chip1:#4A3B1E;--chip2:#223548;--chip3:#1F3B2C;color-scheme:dark}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 var(--sans)}}
.wrap{{max-width:1080px;margin:0 auto;padding-block:28px 80px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
h1{{font-size:24px;margin:0 0 6px;text-wrap:balance}}h2{{font-size:18px;margin:36px 0 10px;text-wrap:balance}}h3{{font-size:15px;margin:0}}
.muted{{color:var(--ink2)}}small{{color:var(--ink2);font-size:12px}}
.lead{{font-size:16px;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:10px;padding:14px 18px;margin:14px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}.grid3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}.grid3>*{{min-width:0;margin:0}}.t2 .shots figure{{flex:1 1 120px;max-width:none}}.grid>*{{min-width:0}}
.diff{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}.diff .t{{font-weight:600;color:var(--ink2);font-size:12.5px}}.diff .n{{font:600 28px/1.2 var(--mono);margin:4px 0;font-variant-numeric:tabular-nums}}.diff .n em{{font-style:normal;color:var(--err)}}.diff .n b{{color:var(--acc)}}.diff .n s{{text-decoration:none;color:var(--ink3);font-weight:500;font-size:18px;margin:0 6px}}.diff p{{margin:4px 0 0}}
.chip{{display:inline-block;padding:1px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}}.g0{{background:var(--chip0);color:var(--err)}}.g1{{background:var(--chip1);color:var(--warn)}}.g2{{background:var(--chip2);color:var(--acc)}}.g3{{background:var(--chip3);color:var(--ok)}}
.tw{{overflow-x:auto;min-width:0}}table{{border-collapse:collapse;width:100%;min-width:820px;font-size:13px;background:var(--card);border:1px solid var(--line);border-radius:10px;font-variant-numeric:tabular-nums}}th,td{{padding:8px 10px;border-bottom:1px solid var(--sep);text-align:left;vertical-align:top}}thead th{{background:var(--card2);color:var(--ink2);font-weight:600;white-space:nowrap}}tbody th{{font-weight:600}}tr.base td,tr.base th{{background:var(--baserow)}}td.r,th.r{{text-align:right}}
.br{{display:grid;grid-template-columns:150px 1fr 56px;gap:10px;align-items:center;margin:5px 0;font-size:12.5px}}.bl{{color:var(--ink2);text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.bb{{display:block;height:14px;background:var(--sep);border-radius:3px;overflow:hidden}}.bb b{{display:block;height:100%;border-radius:3px}}.bb .a{{background:var(--acc)}}.bb .e{{background:var(--err)}}.bv{{font-family:var(--mono);font-weight:600;font-size:12px}}
.box{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin:12px 0;min-width:0}}
.viewer{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:12px 0}}.tabs{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}}.tab{{font:600 12.5px var(--sans);padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card2);color:var(--ink);cursor:pointer}}.tab.on{{background:var(--acc);color:#fff;border-color:var(--acc)}}
.opts{{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin-bottom:10px;font-size:13px}}.opts label{{display:inline-flex;gap:4px;align-items:center;cursor:pointer}}
.frame{{position:relative;aspect-ratio:16/9;max-width:100%;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#F4F6F8}}.frame iframe{{position:absolute;inset:0;width:100%;height:100%;border:0}}
.btn{{font:600 13px var(--sans);padding:6px 12px;border:1px solid var(--acc);border-radius:8px;background:transparent;color:var(--acc);cursor:pointer}}.btn:focus-visible,.tab:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
.vc{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin:12px 0}}.vh{{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}}.vh .stat{{font-family:var(--mono);font-size:12px;color:var(--ink2)}}.vh .btn{{margin-left:auto}}.vc p{{margin:8px 0}}
.shots{{display:flex;gap:10px;flex-wrap:wrap}}figure{{margin:0;flex:1 1 200px;min-width:0;max-width:340px}}figure img{{width:100%;max-width:100%;border:1px solid var(--line);border-radius:6px;display:block}}figcaption{{font-size:12px;color:var(--ink2);text-align:center}}
details{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 18px;margin:12px 0}}summary{{cursor:pointer;font-weight:600;font-size:15px}}
ul{{padding-left:20px;margin:6px 0}}li{{margin:3px 0}}code{{font-family:var(--mono);font-size:12.5px;background:var(--codebg);padding:1px 4px;border-radius:3px}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>
<div class="wrap">
<h1>시작 화면 렉 개선안</h1>
<p class="muted">결과 HTML 을 열 때 나오는 4초 랜딩 애니메이션(D104 '데이터 입자')이 끊기는 원인과 고친 안 9개 + 결정된 T2 의 세 버전. 2026-10-31~11-01 계측, 30일치 19MB 파일 기준.</p>
<div class="lead"><b>결론</b> — 지금 장면은 프레임마다 입자 16,000개를 선으로 긋느라 끊긴다. 그리는 방식만 바꾼 <b>V2 픽셀 버퍼</b>가 같은 장면을 {b['p95']/px['p95']:.0f}배 매끄럽게(프레임 간격 p95 기준) 만들고, 디자인을 바꿀 수 있다면 <b>스캔 라인 · CSS · 글자 안</b>은 프레임마다 JS 가 0 이라 어떤 PC 에서도 끊길 거리가 없다. 어느 안이든 걷힐 때의 전체 화면 blur 는 뺀다.</div>

<h2>결정 — T2 '막대로 쓴 AOI' 세 버전</h2>
<p class="muted"><b>11/1 결정: T2-B '장비 목록' + 대기 동작 W3 점등</b> — template 에 적용(D105). 4초를 넘겨 기다릴 땐 구간이 읽는 순서로 차례로 켜진다(opacity 만, JS 0). 아래 세 버전은 비교용으로 남긴다. 셋 다 프레임마다 JS 0(CSS 키프레임 · transform · opacity 만), 값이 오기 전엔 회청색, 로딩이 끝나면 범례 색(Scan 파랑 · Rescan 연파랑 · Test 보라 · Error 빨강). 차이는 <b>글자를 어떻게 쓰느냐</b>뿐이다.</p>
<div class="grid3">
{"".join(t2card(v) for v in ["bars_a","bars_b","bars_c"])}
</div>
<div class="tw"><table><thead><tr><th>버전</th><th>움직임</th><th>어디서 온 모양</th><th>기다릴 때</th><th>렉</th></tr></thead><tbody>
<tr><th>T2-A 줄마다 차오름</th><td>막대가 읽는 순서로 하나씩 차오름(약 2.4초)</td><td>장비 팝업의 24시간 막대(구간 1~3개)</td><td>'지금' 선이 지나감</td><td>{chip(*grade("bars_a")[:2])}<br><small>{grade("bars_a")[2]} · 드롭 {f0(R["bars_a"]["dpr1_cpu1"]["drop"])}</small></td></tr>
<tr><th>T2-B 장비 목록</th><td>줄 7개가 깔리고 구간이 자람 — 글자가 '나타난다'</td><td>가동률 목록(이름 · 숫자 · 트랙)</td><td>'지금' 선이 지나감</td><td>{chip(*grade("bars_b")[:2])}<br><small>{grade("bars_b")[2]} · 드롭 {f0(R["bars_b"]["dpr1_cpu1"]["drop"])}</small></td></tr>
<tr><th>T2-C 스캔 헤드</th><td>헤드가 지나가면 닿은 구간부터 차오름(2.3초)</td><td>AOI 스캔 · V5 스캔 라인</td><td>헤드가 천천히 오감</td><td>{chip(*grade("bars_c")[:2])}<br><small>{grade("bars_c")[2]} · 드롭 {f0(R["bars_c"]["dpr1_cpu1"]["drop"])}</small></td></tr>
</tbody></table></div>

<h2>대기 동작 대안 — '지금' 선 대신</h2>
<p class="muted">4초를 넘겨도 로딩 중일 때의 움직임. 현택 11/1 "'지금' 선은 구리다" → 넷. 전부 transform · opacity 키프레임(합성 스레드), 글자는 그대로 읽힌다. 뷰어에서 '느린 로딩 7초' 로 보면 4초 뒤부터 보인다.</p>
<div class="grid3">{"".join(idlecard(v) for v in ["bars_b_wave","bars_b_drift","bars_b_glow","bars_b_count"])}</div>

<h2>가장 큰 차이 4가지</h2>
<div class="grid">
<div class="diff"><div class="t">① 프레임 간격 p95 — 입자 장면</div><div class="n"><em>{f0(b['p95'])}</em><s>→</s><b>{f0(px['p95'])}</b> ms</div><p>현재 → V2 픽셀 버퍼. 60fps 는 16.7ms. 프레임당 JS 도 {f1(b['dur'])} → {f1(px['dur'])}ms.</p></div>
<div class="diff"><div class="t">② 노트북 배율(dpr 1.5)에서</div><div class="n"><em>{f0(b15['fps'])}</em><s>→</s><b>{f0(px15['fps'])}</b> fps</div><p>현재 코드는 dpr 2 까지 그려 125~150% 배율에서 더 무겁다. 개선안은 dpr 1 로 고정.</p></div>
<div class="diff"><div class="t">③ 메인 스레드가 막혀도</div><div class="n"><em>{f0(b['drop'])}</em><s>→</s><b>{f0(R['text_lens']['dpr1_cpu1']['drop'])}</b> 드롭</div><p>JSON 해석 4~5초 동안 합성기가 놓친 프레임. CSS · 글자 안은 합성 스레드만 써서 영향이 없다.</p></div>
<div class="diff"><div class="t">④ 걷힘의 blur(5px) 만 빼도</div><div class="n"><em>{f0(b['rev'])}</em><s>→</s><b>{f0(nb['rev'])}</b> ms</div><p>덮개가 걷히는 0.7초의 메인 프레임 간격 p95. 전체 화면 흐림이 첫 화면 그리기와 겹친다.</p></div>
</div>

<h2>한눈에 비교</h2>
<div class="tw"><table><thead><tr><th>안</th><th>렉</th><th>메인 스레드가 막힐 때</th><th>디자인</th><th>코드 변경</th><th>판단</th></tr></thead>
<tbody>{"".join(mrow(x[0]) for x in V)}</tbody></table></div>
<p class="muted">렉 등급: 매끄러움 = 기본 · dpr 1.5 모두 p95 40ms 이하 · 가끔 끊김 = 80ms 이하 · 끊김 = 그 이상. JS 0 = 그림 스레드 자체가 없음(CSS · WAAPI 만). 숫자는 헤드리스 Chromium 상대 비교라 현장 절대값과 다르다.</p>

<h2>직접 보기</h2>
<div class="viewer">
<div class="tabs">{demo_tabs}</div>
<div class="opts"><span class="muted">상황:</span><label><input type="radio" name="sit" id="sit-fast" value="load=2500" checked> 빠른 로딩 2.5초</label><label><input type="radio" name="sit" id="sit-slow" value="load=7000"> 느린 로딩 7초</label><label><input type="radio" name="sit" id="sit-busy" value="load=7000&busy=1"> 메인 스레드 7초 막힘(실제 파일과 비슷)</label><label><input type="checkbox" id="sit-lot"> LOT 배포판 장면</label><button class="btn" id="replay">다시 보기</button><a class="btn" id="openNew" href="demos/bars_a.html" target="_blank" rel="noopener">새 탭으로</a></div>
<div class="frame"><iframe id="demo" title="시작 화면 데모" src="demos/bars_a.html?load=2500"></iframe></div>
<p class="muted" style="margin:8px 0 0">4초 안에는 걷히지 않는 규칙이 그대로라 빠른 로딩도 4초 장면을 다 보여 준다. '메인 스레드 7초 막힘' 은 실제 19MB 파일에서 JSON 을 해석하는 동안과 같은 상황이다 — 현재 안은 이때 가장 많이 끊긴다.</p>
</div>

<h2>안마다 한 장</h2>
{"".join(vcard(x[0]) for x in V if x[2] not in ("t2","idle"))}

<details><summary>자세한 수치</summary>
<div class="box"><b>그림 스레드 프레임 간격 p95(기본 조건, 낮을수록 좋음)</b>{bars(p95_items, "ms")}</div>
<div class="box"><b>합성기가 놓친 프레임(열기~걷힘, 기본 조건)</b>{bars(drop_items, "")}</div>
<div class="tw"><table><thead><tr><th>안</th><th class="r">기본 fps</th><th class="r">기본 p95 ms</th><th class="r">콜백 p50 ms</th><th class="r">dpr 1.5 fps</th><th class="r">dpr 1.5 p95</th><th class="r">CPU 4배 fps</th><th class="r">드롭(기본)</th><th class="r">걷힘 p95 ms</th></tr></thead><tbody>
{"".join(f"<tr{' class=base' if x[0]=='baseline' else ''}><th>{x[1]}</th><td class=r>{'JS 0' if R[x[0]]['dpr1_cpu1']['fps'] is None else f0(R[x[0]]['dpr1_cpu1']['fps'])}</td><td class=r>{f0(R[x[0]]['dpr1_cpu1']['p95'])}</td><td class=r>{f1(R[x[0]]['dpr1_cpu1']['dur'])}</td><td class=r>{'JS 0' if R[x[0]]['dpr15_cpu1']['fps'] is None else f0(R[x[0]]['dpr15_cpu1']['fps'])}</td><td class=r>{f0(R[x[0]]['dpr15_cpu1']['p95'])}</td><td class=r>{'JS 0' if R[x[0]]['dpr1_cpu4']['fps'] is None else f0(R[x[0]]['dpr1_cpu4']['fps'])}</td><td class=r>{f0(R[x[0]]['dpr1_cpu1']['drop'])}</td><td class=r>{f0(R[x[0]]['dpr1_cpu1']['rev'])}</td></tr>" for x in V if x[2]!="idle")}
</tbody></table></div>
<p class="muted">fps · p95 = Worker 가 실제로 그린 프레임 간격(V6 은 30fps 상한). 콜백 = 프레임 하나의 JS + 캔버스 명령. 드롭 = CDP 트레이스 PipelineReporter 의 STATE_DROPPED(메인 스레드 레이어 트리 기준이라 Worker 캔버스 안에서는 메인이 막힌 동안의 드롭이 섞인다). 반복 실행 평균(기준 3회 · 주요 안 2~3회).</p>
</details>

<details><summary>왜 끊기나 — 현재 코드 진단</summary><ul>
<li><b>프레임마다 너무 많이 한다.</b> 입자 16,000개 × curl noise 4번 + Path2D 꼬리 선 16,000개 · 네모 16,000개를 팔레트 40색마다 stroke/fill. 콜백만 p50 {f1(b['dur'])}ms, 그 뒤 래스터(선 16,000개를 alpha 로 긋기)가 따로 든다.</li>
<li><b>dpr 2 까지 그린다.</b> 125~150% 배율이면 픽셀이 1.6~2.3배. dpr 1.5 에서 {f0(b15['fps'])}fps.</li>
<li><b>Worker 라도 CPU 는 나눠 쓴다.</b> 메인이 19MB JSON 을 해석하는 동안 코어 하나를 다 쓰고 래스터 · 합성기 · Worker 가 나머지를 나눈다. 4코어에서 현재 코드는 그 구간에 실행마다 16~45fps 로 흔들렸다.</li>
<li><b>걷힐 때 전체 화면 blur(5px) + scale.</b> 메인이 첫 화면을 그리는 순간과 겹친다. blur 만 빼면 걷힘 구간 p95 {f0(b['rev'])} → {f0(nb['rev'])}ms.</li>
<li><b>OffscreenCanvas 가 없는 브라우저(옛 Edge)는 전부 메인 스레드</b> — JSON 해석 동안 0프레임.</li></ul>
<p class="muted">기준: <code>animation-performance</code>(합성 전용 속성 · 메인 스레드 밖 · 프레임 예산) · <code>improve-animations</code> 성능 항목 · <code>design-motion-principles</code> 생성 체크(blur 상한 · 반복 맥동 금지 · reduced-motion).</p></details>

<details><summary>어떻게 쟀나 · 주의</summary><ul>
<li>30일치 보관 샘플(Report 55,717개)을 현재 template 에 넣은 19.3MB 결과 HTML 에서 boot 스크립트만 교체. Playwright Chromium 153(헤드리스 · 소프트웨어 합성 · 4 vCPU). 조건: 기본(1920×1080 · dpr 1) · CPU 4배 느리게(메인 스레드만) · dpr 1.5.</li>
<li>지표: Worker rAF 간격(실제 화면 갱신)과 콜백 시간 · 합성기 드롭(CDP 트레이스) · 걷힘 구간 메인 rAF 간격 · long-animation-frame.</li>
<li>절대값은 현장 PC(Windows · 내장 GPU) 와 다르다 — 안 사이의 상대 비교로 읽는다. 고른 안은 현장 노트북(125~150% 배율 · 실데이터 · Edge/Chrome)에서 확인한다.</li>
<li>모든 안이 지키는 것: 4초 최소 · 바깥 요청 0 · <code>AOI_BOOT</code> 인터페이스 그대로(template 나머지 무변경) · reduced-motion · 걷힘은 opacity 만.</li></ul></details>

<h2>다음</h2>
<div class="box">안을 고르면 template 의 <code>&lt;script id="boot"&gt;</code> 만 교체하고 가드(<code>test_boot_screen_*</code> · 브라우저 테스트 · 사본 저장)를 맞춘 뒤 현장 Windows 에서 확인한다. 계측 도구 · 변형 스크립트는 <code>dev/tools/boot_bench/</code>.</div>
</div>
<script>
(function(){{const fr=document.getElementById("demo"),tabs=[...document.querySelectorAll(".tab")],open=document.getElementById("openNew");let cur="bars_a";
  const q=()=>{{const s=document.querySelector('input[name="sit"]:checked').value,lot=document.getElementById("sit-lot").checked;return s+(lot?"&lot=1":"");}};
  const go=()=>{{tabs.forEach(t=>t.classList.toggle("on",t.dataset.demo===cur));const u="demos/"+cur+".html?"+q();fr.src=u+"&t="+Date.now();open.href=u;}};
  document.addEventListener("click",e=>{{const b=e.target.closest("[data-demo]");if(b){{cur=b.dataset.demo;if(b.dataset.slow)document.getElementById("sit-slow").checked=true;go();if(b.classList.contains("btn"))document.querySelector(".viewer").scrollIntoView({{behavior:"smooth",block:"start"}});}}
    if(e.target.id==="replay")go();}});
  document.querySelectorAll('input[name="sit"],#sit-lot').forEach(i=>i.addEventListener("change",go));go();}})();
</script>
"""
OUT.write_text(html, encoding="utf-8"); print("wrote", OUT, OUT.stat().st_size)
