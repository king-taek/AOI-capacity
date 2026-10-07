"""제안서(rdl_2026-10-07.html) 의 각 안을 **실제 전체 화면**에서 보는 미리보기 HTML 을 만든다.

    python docs/proposals/rdl_2026-10-07_preview.py <수집 결과 HTML> <출력 HTML>
    python docs/proposals/rdl_2026-10-07_preview.py --shots <그림 폴더>     # 제안서에 실제 화면 그림(A1A.jpg …)을 넣는다

제품 template.html 을 복사해 각 안(A1~D3 의 B · C 안)을 `PV` 스위치로 넣고, 오른쪽 아래 '제안 미리보기' 판에서 바로 바꿔 본다.
데이터는 주어진 수집 결과 HTML 의 embedded JSON 을 그대로 쓴다. 제품 template 은 건드리지 않는다(이 파일은 출력만 쓴다).
주소 뒤 `#pv=B3:B,C2:C` 로 처음 상태를 줄 수 있다."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "aoi_capacity" / "ui" / "assets" / "template.html"

ITEMS = [  # 판에 보이는 항목 — 제안서와 같은 번호 · 안 이름
    ("A1", "이상치 묶음", ["레시피×방식 3σ", "레시피 통째 3σ", "레시피×방식 MAD"]),
    ("A2", "25 wafer 환산", ["×25÷n", "대기 그대로", "25 wafer 이상만"]),
    ("B1", "멀티 vs 단일 영역", ["타일+비교", "한 줄 덤벨", "문장+표"]),
    ("B2", "레시피 목록", ["비율 막대", "중앙값 숫자", "맨 위 요약표"]),
    ("B3", "장비별 그래프", ["덤벨", "기준선+강조", "히트맵"]),
    ("B4", "아래 두 칸", ["그대로", "ⓘ 도움말", "둘 다 삭제"]),
    ("B5", "'장당' 이름", ["장당", "Wafer당", "Wafer 기준"]),
    ("C1", "팝업 점 단위", ["Lot", "wafer", "점 없음"]),
    ("C2", "Defect 축", ["선형", "로그", "백분위"]),
    ("C3", "팝업 interactive", ["지금", "끌어서 선택", "미리보기 카드"]),
    ("D1", "같이 켜지기", ["팝업만", "장비→위 띠", "목록 미리보기"]),
    ("D2", "버전 표시", ["칩 title", "삭제", "바닥 작게"]),
    ("D3", "제외 레시피", ["목록 아래", "다시 포함", "Job 칩 끝"]),
]

INFRA = r"""
/* ════ 제안 미리보기(docs/proposals/rdl_2026-10-07_preview.py 가 넣음 — 제품 template 에는 없다) ════ */
let PV={};try{const m=(location.hash||"").match(/pv=([^&]*)/);if(m)for(const t of decodeURIComponent(m[1]).split(",")){const [a,b]=t.split(":");if(a&&b&&b!=="A")PV[a]=b;}}catch(e){}
const PV_ITEMS=__ITEMS__;
function pvSet(q,o){PV={...PV};if(o==="A")delete PV[q];else PV[q]=o;_rcp=null;
  if(q==="B3"&&o==="B")state.rcpDevSort="big";if(q==="B3"&&o!=="B"&&state.rcpDevSort==="big")state.rcpDevSort="name";
  state.rcpBin=null;state.pvPeek=null;state.pvHelp=false;
  try{history.replaceState(null,"","#pv="+Object.entries(PV).map(([a,b])=>a+":"+b).join(","));}catch(e){}render();}
function pvPanelHtml(){const open=state.pvOpen!==false;
  return `<div class="pvpanel${open?"":" min"}" data-key="pvpanel"><button type="button" class="pvph" data-h="${h(()=>setState({pvOpen:!open}))}"><b>제안 미리보기</b><span>${Object.keys(PV).length?Object.entries(PV).map(([a,b])=>a+b).join(" "):"모두 A(지금)"}</span><i>${open?"▾":"▴"}</i></button>
    ${open?`<div class="pvpb">${PV_ITEMS.map(([id,t,os])=>`<div class="pvr"><span class="pvid">${id}</span><span class="pvt">${t}</span><span class="pvo">${os.map((o,i)=>{const L="ABC"[i],on=(PV[id]||"A")===L;return `<button type="button" class="${on?"on":""}" title="${L}안 — ${o}" data-h="${h(()=>pvSet(id,L))}">${L}</button>`;}).join("")}</span></div>`).join("")}
    <p class="pvnote">RDL 단일스캔 탭 · 장비 팝업에서 바뀝니다. 제안서의 A·B·C 와 같습니다.</p></div>`:""}</div>`;}
function trimMad(items,get){const n=items.length,none={kept:items,out:[],n,get,m:null,sd:null,lo:null,hi:null};if(n<OUT_MIN_N)return none;
  const v=items.map(get),md=qs(v,.5),mad=qs(v.map(x=>Math.abs(x-md)),.5)*1.4826;if(!(mad>0))return {...none,m:md,sd:mad};
  const lo=md-3*mad,hi=md+3*mad,kept=[],out=[];for(const x of items){const y=get(x);(y<lo||y>hi?out:kept).push(x);}return {kept,out,n,get,m:md,sd:mad,lo,hi};}
const pvLot=(R,raw)=>{if(R.n>=LOT_STD)return raw;if(PV.A2==="B"&&R.nI){const per=R.sumS/R.nI;return raw-per*R.n+LOT_STD*per;}return raw*LOT_STD/R.n;};
function pvHeroB(a,A,U,NMK){const pr=U.lot?A.pairedL:A.paired;
  const row=(lab,x,y,gx,gy,fm,unit,word)=>{if(x==null&&y==null)return"";const mx=Math.max(x||0,y||0,gx||0,gy||0)*1.18||1,p=v=>(v/mx*100).toFixed(1)+"%";const d=x!=null&&y!=null?y-x:null,k=d==null?"":d<0?"S":"M";
    return `<div class="pvdb"><span class="pvl">${lab}</span><span class="pvtr">${x!=null&&y!=null?`<i class="ln" style="left:${p(Math.min(x,y))};width:${(Math.abs(y-x)/mx*100).toFixed(1)}%"></i>`:""}${gx!=null?`<b class="dt ghost" style="left:${p(gx)};background:${MODE_C.M}" title="같은 장비끼리 ${NMK("M")} ${fm(gx)}${unit}"></b>`:""}${gy!=null?`<b class="dt ghost" style="left:${p(gy)};background:${MODE_C.S}" title="같은 장비끼리 ${NMK("S")} ${fm(gy)}${unit}"></b>`:""}${x!=null?`<b class="dt" style="left:${p(x)};background:${MODE_C.M}" title="${NMK("M")} ${fm(x)}${unit}"></b><em class="vl" style="left:${p(x)};color:${MODE_C.M}">${fm(x)}</em>`:""}${y!=null?`<b class="dt" style="left:${p(y)};background:${MODE_C.S}" title="${NMK("S")} ${fm(y)}${unit}"></b><em class="vl" style="left:${p(y)};color:${MODE_C.S}">${fm(y)}</em>`:""}</span>
      <span class="pvd" style="color:${k?MODE_C[k]:"#8A96A3"}">${d==null?"—":(Math.abs(d)<0.05?"차이 없음":NMK(k)+" "+fm(Math.abs(d))+" "+word)}<small>${d!=null&&x?" ("+(d>0?"+":"−")+Math.round(Math.abs(d)/x*100)+"%)":""}</small></span></div>`;};
  return `<div class="pvhero">${row(U.tl,qs(U.T(a.M),.5),qs(U.T(a.S),.5),pr?pr.m:null,pr?pr.s:null,f1,U.tu,"빠름")}${row("Defect",qs(U.F(a.M),.5),qs(U.F(a.S),.5),null,null,fD,U.fu,"적음")}
    <p class="pvcap"><i class="sw" style="background-color:${MODE_C.M}"></i>${NMK("M")} <i class="sw" style="background-color:${MODE_C.S};margin-left:8px"></i>${NMK("S")} · 옅은 점 = 같은 장비끼리${pr?" ("+pr.n+"대)":""} · ${U.tu} / ${U.fu} · 중앙값</p></div>`;}
const pvJ=w=>{const c=String(w).charCodeAt(String(w).length-1);return c>=0xAC00&&c<=0xD7A3&&(c-0xAC00)%28?"이":"가";};
function pvHeroC(a,A,U,NMK){const x=qs(U.T(a.M),.5),y=qs(U.T(a.S),.5),fx=qs(U.F(a.M),.5),fy=qs(U.F(a.S),.5),pr=U.lot?A.pairedL:A.paired;
  let s1="비교할 값이 없습니다";if(x!=null&&y!=null){const d=y-x,k=d<0?"S":"M";s1=Math.abs(d)<0.05?"두 방식 차이 없음":`<span style="color:${MODE_C[k]}">${NMK(k)}</span>${pvJ(NMK(k))} <span class="num">${f1(Math.abs(d))}${U.tu}</span> 빠름 <span class="muted">(${Math.round(Math.abs(d)/x*100)}%)</span>`;}
  let s2="";if(fx!=null&&fy!=null)s2=`Defect ${fD(fx)} → ${fD(fy)} ${U.fu} <span class="muted">(${NMK("M")} → ${NMK("S")})</span>`;
  let s3="";if(pr&&x!=null&&y!=null){const dd=pr.s-pr.m;if((dd<0)!==(y-x<0))s3=`단, 두 방식을 다 돌린 장비 ${pr.n}대끼리는 ${NMK(dd<0?"S":"M")}${pvJ(NMK(dd<0?"S":"M"))} ${f1(Math.abs(dd))}${U.tu} 빠름`;}
  return `<div class="pvsent"><p class="s1">${s1}</p>${s2?`<p class="s2">${s2}</p>`:""}${s3?`<p class="s3">${s3}</p>`:""}<table class="pvtab"><tr><th></th><th><i class="sw" style="background-color:${MODE_C.M}"></i>${NMK("M")}</th><th><i class="sw" style="background-color:${MODE_C.S}"></i>${NMK("S")}</th></tr>
    <tr><td>${U.tl} · 전체</td><td>${f1(x)}</td><td>${f1(y)}</td></tr><tr><td>${U.tl} · 같은 장비${pr?" "+pr.n+"대":""}</td><td>${pr?f1(pr.m):"—"}</td><td>${pr?f1(pr.s):"—"}</td></tr><tr><td>${U.fl}</td><td>${fD(fx)}</td><td>${fD(fy)}</td></tr></table></div>`;}
let _pvAgg=null;const pvAgg=(F,from,to)=>{const k=F.k+"|"+from+"|"+to+"|"+Object.keys(state.rcpOff||{}).join()+"|"+JSON.stringify(PV);if(!_pvAgg||_pvAgg.D!==D)_pvAgg={D,m:new Map()};
  if(!_pvAgg.m.has(k))_pvAgg.m.set(k,rcpAgg(new Set([...F.gs.keys()].filter(g=>!rcpOffOf(D.pool.job[D.jobGroups[g].l]))),from,to));return _pvAgg.m.get(k);};
function pvListNums(F,from,to,U){const a=pvAgg(F,from,to).all,x=qs(U.T(a.M),.5),y=qs(U.T(a.S),.5),d=x!=null&&y!=null&&x?Math.round((y-x)/x*100):null;
  return `<span class="pvln"><b style="color:${MODE_C.M}">${f1(x)}</b><b style="color:${MODE_C.S}">${f1(y)}</b><i style="color:${d==null?"#8A96A3":d<0?"#1F7A4D":"#B4402F"}">${d==null?"—":(d>0?"+":"")+d+"%"}</i></span>`;}
function pvHeatC(r){if(r<=1){const l=96-(1-r)*110;return [`oklch(${Math.max(52,l).toFixed(0)}% ${(0.02+(1-r)*0.3).toFixed(3)} 250)`,l<66];}const l=95-(r-1)*70;return [`oklch(${Math.max(48,l).toFixed(0)}% ${Math.min(0.17,0.03+(r-1)*0.25).toFixed(3)} 27)`,l<64];}
function pvHeat(from,to,U,MET){const f=famIndex(),fams=new Map();D.jobGroups.forEach((G,gi)=>{if(!f.canon[gi]||rcpOffOf(D.pool.job[G.l]))return;const k=f.key[gi];if(!fams.has(k))fams.set(k,new Set());fams.get(k).add(gi);});
  const ks=RCP_ORDER.filter(k=>fams.has(k)),agg=ks.map(k=>[k,rcpAgg(fams.get(k),from,to),/PI/.test(k)]),sel=o=>MET==="defect"?U.F(o):U.T(o),devs=new Set();
  for(const [,A] of agg)for(const d of Object.keys(A.devs))devs.add(d);const dl=[...devs].sort(cmpDev),fm=MET==="defect"?fD:f1,unit=MET==="defect"?U.fu:U.tu;
  const cell=(k,A,pi,dev,m)=>{const d=A.devs[dev],v=d?qs(sel(d[m]),.5):null,ref=qs(sel(A.all[m]),.5);if(v==null)return `<span class="hc nil"></span>`;const r=ref?v/ref:1,[bg,dark]=pvHeatC(r);
    return `<button type="button" class="hc" style="background:${bg};color:${dark?"#fff":"#16202A"}" title="${esc(dev+" · "+k+" · "+nmK(m,pi)+"\n"+fm(v)+unit+" (그 레시피 전체 "+fm(ref)+" 대비 "+(r>=1?"+":"")+Math.round((r-1)*100)+"%)\n"+(m==="M"?d.M.n:d.S.n)+" wafer · 누르면 상세")}" data-h="${h(()=>rcpDevOpen(dev,k))}">${fm(v)}</button>`;};
  const cols=`86px repeat(${ks.length*2},minmax(0,1fr))`;
  return `<div class="panel" data-key="rcp:mdev" style="margin-top:14px"><div class="ph"><h2>장비 × 레시피 ${MET==="defect"?U.fl:U.tl}</h2><span class="muted" style="font-size:12px">중앙 · ${unit} · 색 = 그 레시피 전체 중앙 대비(파랑 빠름/적음 · 빨강 느림/많음)</span><div class="spacer"></div>${segHtml([{label:"시간",on:MET==="time",pick:()=>setState({rcpMetric:"time"})},{label:"Defect",on:MET==="defect",pick:()=>setState({rcpMetric:"defect"})}],'aria-label="지표"')}</div>
    <div class="pvhm" style="grid-template-columns:${cols}"><span></span>${agg.map(([k])=>`<span class="hh" style="grid-column:span 2">${k.replace("TB500 ","")}</span>`).join("")}<span></span>${agg.map(([,,pi])=>`<span class="hs">${nmK("M",pi)}</span><span class="hs">${nmK("S",pi)}</span>`).join("")}
    ${dl.map(dev=>`<span class="hd">${esc(dev)}</span>`+agg.map(([k,A,pi])=>cell(k,A,pi,dev,"M")+cell(k,A,pi,dev,"S")).join("")).join("")}</div></div>`;}
function pvExChip(key,from,to){const X=rcpIndex(),m=new Map();for(const e of X.excl){if(e.day<from||e.day>to)continue;const c=(rcpCanon(e.raw)||"").replace(" Swelling","");if(c!==key)continue;m.set(e.raw,(m.get(e.raw)||0)+1);}
  if(!m.size)return"";const op=!!state.pvExOpen;return `<span class="pvex"><button type="button" class="jchip pvexb" data-h="${h(()=>setState({pvExOpen:!op}))}">제외 ${m.size} ${op?"▴":"▾"}</button>${op?`<span class="pvexl">${[...m].map(([r,n])=>`<span><span class="mono">${esc(r)}</span><em>${RCP_EXCL_NM[rcpExclWhy(r)]||"제외"}</em><b class="num">${n}</b></span>`).join("")}</span>`:""}</span>`;}
/* 끌어서 범위 고르기(C3-B) · Lot 미리보기 카드(C3-C) · 장비 행 → 위 띠(D1-B) · 목록 미리보기(D1-C) */
(function(){let br=null;
  document.addEventListener("pointerdown",e=>{if(PV.C3!=="B")return;const w=e.target.closest&&e.target.closest(".bsw[data-brush]");if(!w||e.target.closest("button.bd")||e.button!==0)return;const r=w.getBoundingClientRect();
    br={w,r,x0:e.clientX,el:document.createElement("i")};br.el.className="pvbr";w.appendChild(br.el);e.preventDefault();});
  document.addEventListener("pointermove",e=>{if(!br)return;const a=Math.max(0,Math.min(br.x0,e.clientX)-br.r.left),b=Math.min(br.r.width,Math.max(br.x0,e.clientX)-br.r.left);br.el.style.left=a+"px";br.el.style.width=Math.max(0,b-a)+"px";br.a=a/br.r.width*100;br.b=b/br.r.width*100;});
  document.addEventListener("pointerup",()=>{if(!br)return;const B=br;br=null;if(!(B.b-B.a>1)){B.el.remove();return;}const rks=[],vs=[];
    for(const d of B.w.querySelectorAll("button.bd[data-rkx]")){const p=parseFloat(d.style.left);if(p>=B.a&&p<=B.b){const rk=decodeURIComponent(d.dataset.rkx);if(!rks.includes(rk))rks.push(rk);vs.push(+d.dataset.v);}}
    const [m,k]=B.w.dataset.brush.split("|");setState({rcpBin:rks.length?{rks,med:qs(vs,.5),br:{m,k,a:B.a,b:B.b}}:null,rcpPopOpen:{...(state.rcpPopOpen||{}),lots:true}});});
  let card=null;const hideCard=()=>{if(card)card.hidden=true;};
  document.addEventListener("mouseover",e=>{
    if(PV.C3==="C"){const d=e.target.closest&&e.target.closest(".dlg [data-rkx]");if(!d){hideCard();}else{const rk=decodeURIComponent(d.dataset.rkx),dev=state.rcpPop&&state.rcpPop.dev,X=rcpIndex(),qq=X.recs.filter(q=>q.rk===rk&&q.dev===dev).sort((x,y)=>x.t-y.t);
      if(qq.length){if(!card){card=document.createElement("div");card.className="pvcard";document.body.appendChild(card);}const ss=qq.map(q=>q.s).filter(v=>v!=null),md=qs(ss,.5)||1,mx=Math.max(...ss,1),fs=qq.map(q=>q.f).filter(v=>v!=null),fmx=Math.max(1,...fs);
        card.innerHTML=`<b>${esc(qq[0].lot||"(Lot)")}</b><span>${md2(qq[0].day)} ${hhmm(qq[0].t)} · ${qq.length} wafer · 스캔 중앙 ${f1(qs(ss,.5))}분</span><div class="pvbars">${qq.map(q=>`<i style="height:${q.s==null?4:Math.max(4,q.s/mx*100)}%;background:${q.s==null?"#D5DCE3":q.s>md*1.4?"#C5453C":"#5A6673"}"></i>`).join("")}</div><span class="muted">wafer 별 스캔 시간(붉은 = 그 Lot 중앙의 1.4배 넘음)</span><div class="pvbars f">${qq.map(q=>`<i style="height:${q.f==null?4:Math.max(4,q.f/fmx*100)}%"></i>`).join("")}</div><span class="muted">wafer 별 Defect</span>`;
        card.hidden=false;const W=innerWidth;let x=e.clientX+16,y=e.clientY+16;if(x+300>W)x=e.clientX-316;if(y+200>innerHeight)y=e.clientY-210;card.style.left=x+"px";card.style.top=y+"px";}}}
    if(PV.D1==="B"){const r=e.target.closest&&e.target.closest('[data-key="rcp:mdev"] button.dbrow[data-pvm]');for(const x of document.querySelectorAll(".pvmk"))x.remove();
      if(r){const S0=document.querySelector(".scanhero .srows[data-mx]");if(S0){const mx=+S0.dataset.mx,rows=S0.querySelectorAll(".srow:not(.axis)"),nm=r.dataset.row.slice(4);
        [["M",r.dataset.pvm],["S",r.dataset.pvs]].forEach(([k,v],i)=>{const tr=rows[i]&&rows[i].querySelector(".srng");if(!tr||v==="")return;const el=document.createElement("i");el.className="pvmk";el.style.left=Math.min(100,+v/mx*100)+"%";el.innerHTML=`<em>${esc(nm)} ${f1(+v)}</em>`;tr.appendChild(el);});}}}
    if(PV.D1==="C"){const r=e.target.closest&&e.target.closest(".rcplist .rcprow[data-row]");const k=r?r.dataset.row.slice(4):null;if(k!==(state.pvPeek||null)&&(r||!(e.target.closest&&e.target.closest(".rcplist"))))setState({pvPeek:k});}
  });})();
const md2=d=>d.slice(5,7)+"/"+d.slice(8,10);
"""

CSS = r"""
.pvpanel{position:fixed;right:16px;bottom:16px;z-index:90;width:330px;background:#fff;border:1px solid #CBD5DF;border-radius:12px;box-shadow:0 10px 30px rgba(15,21,28,.22);font-size:12px}
.pvpanel.min{width:auto}.pvph{display:flex;align-items:center;gap:8px;width:100%;border:0;background:#16202A;color:#fff;border-radius:11px 11px 0 0;padding:8px 12px;cursor:pointer;font:inherit}.pvpanel.min .pvph{border-radius:11px}
.pvph span{color:#B9C6D3;font-family:var(--mono);font-size:11px;flex:1;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.pvph i{font-style:normal}
.pvpb{padding:6px 10px 8px;max-height:60vh;overflow:auto}.pvr{display:grid;grid-template-columns:26px 1fr auto;gap:6px;align-items:center;padding:3px 0;border-bottom:1px solid #F0F3F6}
.pvid{font:700 11px var(--mono);color:var(--nav-on)}.pvt{color:var(--ink-2)}.pvo{display:flex;gap:3px}.pvo button{width:24px;height:22px;border:1px solid #D5DCE3;background:#fff;border-radius:5px;cursor:pointer;font:700 11px var(--sans);color:var(--ink-3)}
.pvo button.on{background:var(--nav-on);border-color:var(--nav-on);color:#fff}.pvnote{margin:6px 0 0;color:var(--ink-3);font-size:11px}
.pvhero{margin:8px 0 6px;padding:14px 16px 10px;border:1px solid var(--line);border-radius:12px;background:#FBFCFD}
.pvdb{display:grid;grid-template-columns:120px minmax(0,1fr) 220px;gap:14px;align-items:center;height:58px}.pvl{font-weight:700;font-size:13px}
.pvtr{position:relative;height:30px;border-radius:6px;background:linear-gradient(#E9EDF2,#E9EDF2) center/100% 2px no-repeat}.pvtr .ln{position:absolute;top:13px;height:4px;background:#C9D2DC;border-radius:2px}
.pvtr .dt{position:absolute;top:50%;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;box-shadow:0 0 0 2px #fff}.pvtr .dt.ghost{width:10px;height:10px;margin:-5px 0 0 -5px;opacity:.35;box-shadow:none}
.pvtr .vl{position:absolute;top:-16px;transform:translateX(-50%);font-style:normal;font-weight:800;font-size:13px}
.pvd{font-size:18px;font-weight:800;text-align:right;white-space:nowrap}.pvd small{font-size:12px;font-weight:600;margin-left:3px}.pvcap{margin:4px 0 0;font-size:11.5px;color:var(--ink-3)}
.pvsent{margin:8px 0 6px;padding:14px 18px;border:1px solid var(--line);border-radius:12px;background:#FBFCFD}.pvsent .s1{margin:0;font-size:24px;font-weight:800;letter-spacing:-.01em}.pvsent .s2{margin:4px 0 0;font-size:15px;font-weight:700}.pvsent .s3{margin:4px 0 0;font-size:12.5px;color:#8A5A12}
.pvtab{margin-top:10px;border-collapse:collapse;font-size:12.5px}.pvtab th,.pvtab td{padding:4px 14px;border-bottom:1px solid #EDF1F5;text-align:right;font-variant-numeric:tabular-nums}.pvtab th:first-child,.pvtab td:first-child{text-align:left;padding-left:0;color:var(--ink-2)}
.pvln{display:inline-flex;gap:7px;align-items:baseline}.pvln b{font-weight:700}.pvln i{font-style:normal;font-weight:700;font-size:11px;min-width:34px;text-align:right}
.pvsum{margin-bottom:14px}.pvsum table{width:100%;border-collapse:collapse;font-size:13px}.pvsum th{font-size:11.5px;color:var(--ink-3);font-weight:600;text-align:right;padding:8px 14px;border-bottom:1px solid var(--line)}.pvsum th:first-child,.pvsum td:first-child{text-align:left}
.pvsum td{padding:8px 14px;border-bottom:1px solid #EDF1F5;text-align:right;font-variant-numeric:tabular-nums}.pvsum tr.r{cursor:pointer}.pvsum tr.r:hover td{background:#F7F9FB}.pvsum tr.on td{background:var(--accent-soft);font-weight:700}
.pvfl{position:absolute;top:2px;bottom:2px;width:0;border-left:2px dashed;opacity:.55;pointer-events:none}
.pvhm{display:grid;gap:3px;padding:6px 18px 16px;font-size:11.5px}.pvhm .hh{text-align:center;font-weight:700;color:var(--ink-2);border-bottom:2px solid #E3E8EE;padding-bottom:2px}.pvhm .hs{text-align:center;font-size:10.5px;color:var(--ink-3)}
.pvhm .hd{font-weight:700;display:flex;align-items:center}.pvhm .hc{height:28px;border:0;border-radius:4px;font:700 11.5px var(--sans);cursor:pointer;font-variant-numeric:tabular-nums}.pvhm .hc:hover{outline:2px solid #16202A;outline-offset:-1px}.pvhm .hc.nil{background:#F7F9FB;cursor:default}
.pvi{margin-left:8px;width:20px;height:20px;border-radius:50%;border:1.5px solid var(--nav-on);color:var(--nav-on);background:#fff;font:800 11px var(--sans);cursor:pointer}
.pvhelp{position:fixed;top:110px;right:40px;width:min(860px,80vw);max-height:72vh;overflow:auto;z-index:45;box-shadow:0 14px 40px rgba(15,21,28,.25);border-radius:14px}.pvhelp .how{margin-top:0!important}
button.bd.sm{width:4px;height:4px;margin:-2px 0 0 -2px;opacity:.6}
.pvbr{position:absolute;top:0;bottom:0;background:rgba(46,107,168,.13);border-left:2px solid var(--nav-on);border-right:2px solid var(--nav-on);pointer-events:none;z-index:0}.bsw[data-brush]{cursor:crosshair}
.pvcard{position:fixed;z-index:400;width:300px;background:#fff;border:1px solid #CBD5DF;border-radius:10px;box-shadow:0 10px 28px rgba(15,21,28,.25);padding:10px 12px;font-size:11.5px;display:flex;flex-direction:column;gap:3px;pointer-events:none}.pvcard[hidden]{display:none}
.pvbars{display:flex;align-items:flex-end;gap:2px;height:60px;border-bottom:1px solid #E3E8EE}.pvbars i{flex:1;border-radius:2px 2px 0 0}.pvbars.f{height:34px}.pvbars.f i{background:#8FB8DE}
.pvmk{position:absolute;top:-5px;bottom:-5px;width:0;border-left:3px solid #C5453C;z-index:3}.pvmk em{position:absolute;top:-17px;left:4px;font-style:normal;font-size:11px;font-weight:800;color:#C5453C;white-space:nowrap;background:#fff;padding:0 3px}
.pvpk{margin-left:10px;font-size:11px;font-weight:700;color:#8A5A12;background:#FFF4E0;border-radius:9px;padding:1px 8px}
.pvver{margin-top:10px;font-size:10px;color:#B0BAC5;text-align:center}
.pvinc{border:1px solid var(--nav-on);color:var(--nav-on);background:#fff;border-radius:9px;font:700 10.5px var(--sans);padding:0 7px;cursor:pointer;white-space:nowrap}.pvinc.out{border-color:#B0BAC5;color:#7B8794}
.rexb.pvb p{grid-template-columns:minmax(0,1fr) auto 38px auto}
.pvex{position:relative;display:inline-flex}.pvexb{border-style:dashed!important;color:var(--ink-3)!important;cursor:pointer}.pvexl{position:absolute;top:100%;right:0;z-index:20;margin-top:4px;background:#fff;border:1px solid #CBD5DF;border-radius:8px;box-shadow:0 8px 20px rgba(15,21,28,.15);padding:6px 10px;display:flex;flex-direction:column;gap:3px;min-width:380px;font-size:11.5px}
.pvexl>span{display:grid;grid-template-columns:1fr auto 40px;gap:8px;align-items:center}.pvexl em{font-style:normal;font-size:10.5px;background:#FFF4E0;color:#8A5A12;border-radius:9px;padding:0 6px}.pvexl b{text-align:right;font-weight:500;color:var(--ink-3)}
"""


def patch(s: str) -> str:
    def R(old, new, cnt=1):
        nonlocal s
        n = s.count(old)
        if n != cnt:
            raise SystemExit(f"패치 자리 {n}곳(기대 {cnt}): {old[:90]}")
        s = s.replace(old, new)

    import json
    infra = INFRA.replace("__ITEMS__", json.dumps(ITEMS, ensure_ascii=False))
    R('const RUN="#2E6BA8"', infra + '\nconst RUN="#2E6BA8"')
    R("</style>", CSS + "</style>")
    # A1 이상치 묶음
    R('const L=[all.M,all.S,all.U].map(k=>({s:trimOut(k.sq,q=>q.s),b:trimOut(k.bq,p=>p.v)}));',
      'let L;if(PV.A1==="B"){const sq=[].concat(all.M.sq,all.S.sq,all.U.sq),bq=[].concat(all.M.bq,all.S.bq,all.U.bq),one={s:trimOut(sq,q=>q.s),b:trimOut(bq,p=>p.v)};L=[one,one,one];}'
      'else{const TR=PV.A1==="C"?trimMad:trimOut;L=[all.M,all.S,all.U].map(k=>({s:TR(k.sq,q=>q.s),b:TR(k.bq,p=>p.v)}));}')
    # A2 25 wafer 환산
    R("R.sumS+=mm;", "R.sumS+=mm;R.nI=(R.nI||0)+1;")
    R('per.set(rk,{rk,v:R.n<LOT_STD?raw*LOT_STD/R.n:raw', 'per.set(rk,{rk,v:pvLot(R,raw)')
    R('R.n<LOT_MIN?"few"', 'R.n<(PV.A2==="C"?LOT_STD:LOT_MIN)?"few"')
    # B1 멀티 vs 단일 영역
    R('<div class="mtiles">${tile("M",a.M)+tile("S",a.S)+verdict}</div>',
      '${PV.B1==="B"?pvHeroB(a,A,U,NMK):PV.B1==="C"?pvHeroC(a,A,U,NMK):`<div class="mtiles">${tile("M",a.M)+tile("S",a.S)+verdict}</div>`}')
    # B2 레시피 목록
    R('<span class="rp num">${t?', '<span class="rp num">${PV.B2==="B"?pvListNums(F,from,to,U):t?')
    R('  return `<div class="bar-h"><h1>RDL 단일스캔</h1>',
      '''  if(PV.B2==="C"){const rows=list.map(F=>{const a=pvAgg(F,from,to).all,x=qs(U.T(a.M),.5),y=qs(U.T(a.S),.5),fx=qs(U.F(a.M),.5),fy=qs(U.F(a.S),.5),d=x!=null&&y!=null&&x?Math.round((y-x)/x*100):null,on=SF&&F.k===SF.k;
      return `<tr class="r${on?" on":""}" data-h="${h(pickF(F))}"><td>${esc(rcpFamName(titleG(F)))}</td><td>${f0(F.w)}</td><td style="color:${MODE_C.M}">${f1(x)}</td><td style="color:${MODE_C.S}">${f1(y)}</td><td style="color:${d==null?"#8A96A3":d<0?"#1F7A4D":"#B4402F"};font-weight:700">${d==null?"—":(d>0?"+":"")+d+"%"}</td><td>${fD(fx)} / ${fD(fy)}</td><td>${F.pi?"Enhanced "+Math.round(F.c.S/Math.max(1,F.c.M+F.c.S)*100)+"%":"멀티 "+Math.round(F.c.M/Math.max(1,F.c.M+F.c.S)*100)+"%"}</td></tr>`;}).join("");
    return `<div class="bar-h"><h1>RDL 단일스캔</h1><span class="scope-badge" data-key="scope">${scopeBadge("recipe")}</span></div>
    <div class="panel pvsum" data-key="pv:sum"><table><tr><th>레시피</th><th>Wafer</th><th>멀티·기존 (${U.tu})</th><th>단일·Enhanced</th><th>차이</th><th>${U.fl} M / S</th><th>비율</th></tr>${rows}</table>${exclH}</div>
    <div style="min-width:0" data-key="rcp:detail">${detail}</div>`;}
  return `<div class="bar-h"><h1>RDL 단일스캔</h1>''')
    # B3 장비별 그래프
    R('const hasT=d=>', 'const pvF={M:qs(sel(a.M),.5),S:qs(sel(a.S),.5)},pvHot=(x,y)=>PV.B3==="B"&&((x!=null&&pvF.M&&x>pvF.M*1.2)||(y!=null&&pvF.S&&y>pvF.S*1.2)),pvFl=PV.B3==="B"?["M","S"].filter(k=>rcpShow(k)&&pvF[k]!=null).map(k=>`<i class="pvfl" style="left:${(pvF[k]/dmx*100).toFixed(2)}%;border-color:${MODE_C[k]}" title="전체 ${NMK(k)} 중앙 ${mfm(pvF[k])}"></i>`).join(""):"";\n    const hasT=d=>')
    R('<span class="dn">${esc(n)}</span><span class="dtrack">${line}',
      '<span class="dn"${pvHot(x,y)?\' style="color:#C5453C;font-weight:800"\':""}>${esc(n)}${pvHot(x,y)?" ▲":""}</span><span class="dtrack">${pvFl}${line}')
    R('<div class="dblegend">${kbtn("M",W1)}${kbtn("S",W2)}</div>',
      '<div class="dblegend">${kbtn("M",W1)}${kbtn("S",W2)}${PV.B3==="B"?`<span class="muted">점선 = 전체 중앙 · <b style="color:#C5453C">▲</b> = 전체보다 20% 넘게 ${MET==="defect"?"많음":"느림"}</span>`:""}</div>')
    R('const devT=!famGs.size?"":', 'const devT=!famGs.size?"":PV.B3==="C"?pvHeat(from,to,U,MET):')
    # B4 아래 두 칸
    R('detail=hero+devT+how+moreBtn+more;',
      'detail=PV.B4==="B"?hero+devT+(state.pvHelp?`<div class="pvhelp" data-key="pv:help">${how}</div>`:""):PV.B4==="C"?hero+devT:hero+devT+how+moreBtn+more;')
    R('<h2 class="tfade" data-nr data-key="rcp:t:${esc(SF.k)}" style="${al?"":"font-family:"+MONO}">${esc(FN)}</h2>',
      '<h2 class="tfade" data-nr data-key="rcp:t:${esc(SF.k)}" style="${al?"":"font-family:"+MONO}">${esc(FN)}</h2>${PV.B4==="B"?`<button type="button" class="pvi" title="계산 규칙" data-h="${h(()=>setState({pvHelp:!state.pvHelp,rcpHowAll:true}))}">i</button>`:""}${PV.D1==="C"&&state.pvPeek?\'<span class="pvpk">미리보기 — 누르면 고정</span>\':""}')
    # C1 · C2 · C3 팝업
    R('if(!U.lot){const by', 'if(!U.lot&&PV.C1!=="B"){const by')
    R('<div class="bsw">${band}${box}${dots}', '<div class="bsw"${PV.C3==="B"?` data-brush="${m}|${k}"`:""}>${band}${box}${PV.C1==="C"?"":dots}${BIN&&BIN.br&&BIN.br.m===m&&BIN.br.k===k?`<i class="pvbr" style="left:${BIN.br.a}%;width:${BIN.br.b-BIN.br.a}%"></i>`:""}')
    R('class="bd${t.o', 'data-rkx="${encodeURIComponent(t.rk)}" data-v="${t.v}" class="bd${!U.lot&&PV.C1==="B"?" sm":""}${t.o')
    R('BIN&&BIN.rk===t.rk', 'BIN&&(BIN.rks?BIN.rks.includes(t.rk):BIN.rk===t.rk)')
    R('const BIN=state.rcpBin&&state.rcpBin.rk?state.rcpBin:null;', 'const BIN=state.rcpBin&&(state.rcpBin.rk||state.rcpBin.rks)?state.rcpBin:null;')
    R('lots=BIN?lotsAll.filter(G=>G.rk===BIN.rk):lotsAll', 'lots=BIN?lotsAll.filter(G=>BIN.rks?BIN.rks.includes(G.rk):G.rk===BIN.rk):lotsAll')
    R('const binChip=BIN?(()=>{const G=groups.get(BIN.rk);return', 'const binChip=BIN?(()=>{if(BIN.rks)return `<div class="binchip"><span><b>선택</b> ${BIN.rks.length} Lot · 그 값의 중앙 ${BIN.med==null?"—":(BIN.br.m==="t"?f1(BIN.med)+"분":fD(BIN.med)+"개")}</span><button type="button" class="btn sm" data-h="${h(()=>setState({rcpBin:null}))}">선택 해제</button></div>`;const G=groups.get(BIN.rk);return')
    R('data-lk="${lk(G.rk)}"', 'data-lk="${lk(G.rk)}" data-rkx="${encodeURIComponent(G.rk)}"')
    R('<section class="psec"><h3>이 장비 vs 전체', '<section class="psec"><h3>${PV.C3==="B"?\'<span class="pvpk" style="margin:0 8px 0 0">그래프 위를 끌어서 범위 선택</span>\':""}${PV.C3==="C"?\'<span class="pvpk" style="margin:0 8px 0 0">점에 올리면 Lot 미리보기</span>\':""}이 장비 vs 전체')
    # C2 Defect 축: 로그 · 백분위
    R('    const px=v=>Math.min(100,v/mx*100).toFixed(2);',
      '''    const allV=[].concat(...per.map(([k,v])=>v.kept.concat(v.out).map(x=>x.v)),...per.map(([k])=>fleetVals(k,m))),fsort=[].concat(...per.map(([k])=>fleetVals(k,m))).sort((x,y)=>x-y);
    const LG=Math.max(1,Math.ceil(Math.log10(Math.max(10,...allV))));
    const TX=m==="d"&&PV.C2==="B"?(v=>Math.min(100,Math.log10(Math.max(1,v))/LG*100)):m==="d"&&PV.C2==="C"?(v=>{let lo=0,hi=fsort.length;while(lo<hi){const md=(lo+hi)>>1;if(fsort[md]<=v)lo=md+1;else hi=md;}return fsort.length?lo/fsort.length*100:0;}):null;
    const px=v=>TX?(+TX(v)).toFixed(2):Math.min(100,v/mx*100).toFixed(2);''')
    R('p:Math.min(100,it.v/mx*100)', 'p:TXs?+TXs(it.v):Math.min(100,it.v/mx*100)')
    R('const swarm=(its,mx)=>{', 'const swarm=(its,mx,TXs)=>{')
    R('clip:it.v>mx})', 'clip:!TXs&&it.v>mx})')
    R(',mx);\n      const tipOf', ',mx,TX);\n      const tipOf')
    R('<div class="bax num"><span>0</span><span>${ax(mx/2)}${unit}</span><span>${ax(mx)}${unit}</span></div>',
      '${TX&&PV.C2==="B"?`<div class="bax num">${Array.from({length:LG+1},(_,i)=>`<span>${f0(Math.pow(10,i))}${i===LG?unit:""}</span>`).join("")}</div>`:TX?`<div class="bax num"><span>0%</span><span>25%</span><span>전체 중앙</span><span>75%</span><span>100%</span></div>`:`<div class="bax num"><span>0</span><span>${ax(mx/2)}${unit}</span><span>${ax(mx)}${unit}</span></div>`}')
    # D1 장비 행 → 위 띠 · 목록 미리보기
    R('<div class="srows">', '<div class="srows" data-mx="${mx}">')
    R('data-row="dev:${esc(n)}" aria-pressed', 'data-row="dev:${esc(n)}" data-pvm="${x??""}" data-pvs="${y??""}" aria-pressed')
    R('let SF=noMatch', 'let SF0=noMatch')
    R('if(!SF&&list.length)SF=list[0];', 'if(!SF0&&list.length)SF0=list[0];let SF=SF0;if(PV.D1==="C"&&state.pvPeek&&fam.get(state.pvPeek))SF=fam.get(state.pvPeek);')
    # D2 버전
    R('+(meta.version?" · 수집기 v"+esc(meta.version):"")', '+(meta.version&&PV.D2!=="B"?" · 수집기 v"+esc(meta.version):"")')
    # D3 제외 레시피
    R('RCP_USER_EXCL.some(re=>re.test(raw))', '(RCP_USER_EXCL.some(re=>re.test(raw))&&!(PV.D3==="B"&&state.pvInc&&state.pvInc[raw]))')
    R('<em class="why ${E.why}">${RCP_EXCL_NM[E.why]}</em><span class="num">${f0(E.n)}</span></p>`).join("")}</div></div>`:"";',
      '''<em class="why ${E.why}">${RCP_EXCL_NM[E.why]}</em><span class="num">${f0(E.n)}</span>${PV.D3==="B"?(E.why==="user"?`<button type="button" class="pvinc" data-h="${h(()=>{state.pvInc={...(state.pvInc||{}),[E.raw]:1};_rcp=null;render();})}">+ 다시 포함</button>`:"<span></span>"):""}</p>`).join("")}${PV.D3==="B"?Object.keys(state.pvInc||{}).filter(r=>state.pvInc[r]).map(r=>`<p><span class="mono">${esc(r)}</span><em class="why">포함됨</em><span></span><button type="button" class="pvinc out" data-h="${h(()=>{state.pvInc={...state.pvInc,[r]:0};_rcp=null;render();})}">다시 빼기</button></p>`).join(""):""}</div></div>`:"";''')
    R('<div class="rexb">', '<div class="rexb${PV.D3==="B"?" pvb":""}">')
    R('${exclH}', '${PV.D3==="C"?"":exclH}', 2)
    R('모두 포함</button>`:""}</div>`;', '모두 포함</button>`:""}${PV.D3==="C"?pvExChip(SF.k,from,to):""}</div>`;')
    # B5 이름 · 판 · 바닥
    R('\n/* ---------- boot ---------- */', r'''
{const _r=rcpHtml,_p=rcpDevPopupHtml,_f=footHtml;
  const tx=s=>!PV.B5?s:PV.B5==="B"?s.replace(/장당/g,"Wafer당"):s.replace(/>장당</g,">Wafer 기준<").replace(/>LOT당</g,">LOT 기준<").replace(/장당 스캔/g,"스캔 시간").replace(/장당 Defect/g,"Defect").replace(/장당/g,"Wafer당");
  rcpHtml=function(){return tx(_r.apply(this,arguments));};rcpDevPopupHtml=function(){return tx(_p.apply(this,arguments));};
  footHtml=function(){let s=_f();if(PV.D2==="C"&&meta.version)s=s.replace(/<\/div>$/,`<div class="pvver">v${esc(meta.version)}</div></div>`);return s+pvPanelHtml();};}
/* ---------- boot ---------- */''')
    R("<title>", "<title>[제안 미리보기] ")
    return s


def embed_shots(folder):
    """그림 폴더의 `<항목><안>.jpg`(예: B3C.jpg) 를 제안서의 shots 블록에 data URI 로 넣는다 — 다시 돌려도 같은 블록만 바뀐다."""
    import base64, json, re
    prop = Path(__file__).with_name("rdl_2026-10-07.html")
    shots = {f.stem: "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()
             for f in sorted(Path(folder).glob("*.jpg")) if re.fullmatch(r"[A-D][0-9][ABC]", f.stem)}
    html = prop.read_text(encoding="utf-8")
    new, n = re.subn(r'(<script type="application/json" id="shots">).*?(</script>)',
                     lambda m: m.group(1) + json.dumps(shots, separators=(",", ":")) + m.group(2), html, flags=re.S)
    if n != 1:
        raise SystemExit("제안서에 shots 블록이 하나여야 합니다")
    prop.write_text(new, encoding="utf-8")
    print(prop, len(shots), "장")


def main():
    if sys.argv[1] == "--shots":
        return embed_shots(sys.argv[2])
    src, out = sys.argv[1], sys.argv[2]
    h = Path(src).read_text(encoding="utf-8")
    tag = '<script type="application/json" id="embedded">'
    a = h.index(tag) + len(tag)
    data = h[a:h.index("</script>", a)]
    t = patch(TEMPLATE.read_text(encoding="utf-8"))
    i = t.index("__DATA__")
    Path(out).write_text(t[:i] + data + t[i + 8:], encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
