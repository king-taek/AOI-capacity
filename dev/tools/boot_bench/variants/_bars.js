/* '막대로 쓴 AOI' 공통 — 5×7 비트맵의 가로 줄(run) 목록과 자리. 세 버전이 같은 글자 · 같은 색 규칙을 쓴다 */
const BAR_G={A:[".###.","#...#","#...#","#####","#...#","#...#","#...#"],O:[".###.","#...#","#...#","#...#","#...#","#...#",".###."],I:["#####","..#..","..#..","..#..","..#..","..#..","#####"]};
function barsGeom(T,opt){
  const cell=(opt&&opt.cell)||T.fs/7,bh=cell*.62,gapL=cell*1.4,W3=cell*5*3+gapL*2,x0=(opt&&opt.x0!=null)?opt.x0:T.cx-W3/2,y0=T.cy-cell*3.5,runs=[];
  ["A","O","I"].forEach((ch,li)=>{BAR_G[ch].forEach((row,r)=>{let c=0;while(c<5){if(row[c]!=="#"){c++;continue;}let e=c;while(e<5&&row[e]==="#")e++;
    runs.push({li,r,x:x0+li*(cell*5+gapL)+c*cell,w:(e-c)*cell-cell*.18,y:y0+r*cell+(cell-bh)/2,h:bh,cells:e-c});c=e;}});});
  return{cell,bh,gapL,W3,x0,y0,runs};}
/* 구간 색: 범례 비율대로(Scan 파랑 대부분 · Rescan 연파랑 · Test 보라 · Error 빨강) */
function barsColor(rnd){const u=rnd();return u<.66?TXT.ACC:u<.82?TXT.ACC2:u<.92?"#7A5BB5":TXT.ERR;}
/* 막대 하나: 트랙(회색) 안에 구간 여러 개. 구간은 .f(scaleX 로 자람) > .g(값 전 회청색) + .c(제 색). 로딩 끝 = .g → .c crossfade */
function barsMake(root,b,segs,delay,opts){
  const tk=document.createElement("div");tk.className="tk";tk.style.cssText=`left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px;animation-delay:${delay}ms,${-(b.r||0)*350}ms;${(opts&&opts.tkExtra)||""}`;   /* 둘째 지연 = 흔들림 위상(.wait 일 때만 쓰인다) */
  segs.forEach((s,i)=>{const f=document.createElement("i");f.className="f";f.style.cssText=`left:${(s.p*100).toFixed(2)}%;width:${(s.w*100).toFixed(2)}%;animation-delay:${s.d}ms`;
    const g=document.createElement("i");g.className="g";const c=document.createElement("i");c.className="c";c.style.background=s.c;f.appendChild(g);f.appendChild(c);tk.appendChild(f);});
  root.appendChild(tk);return tk;}
const BARS_CSS=`
#aoi-boot .tx .tk{position:absolute;border-radius:3px;background:${TXT.LINE};opacity:0;animation:txTk .35s cubic-bezier(.22,1,.36,1) both}
#aoi-boot .tx .tk>.f{position:absolute;top:0;height:100%;display:block;transform:scaleX(0);transform-origin:0 50%;animation:txFill .6s cubic-bezier(.16,1,.3,1) both;will-change:transform;border-radius:3px;overflow:hidden}
#aoi-boot .tx .tk>.f>i{position:absolute;left:0;top:0;width:100%;height:100%;display:block}
#aoi-boot .tx .tk>.f>.g{background:${TXT.WAIT}}#aoi-boot .tx .tk>.f>.c{opacity:0;transition:opacity .5s cubic-bezier(.33,1,.68,1)}
#aoi-boot .tx.ld .tk>.f>.g{opacity:0;transition:opacity .5s cubic-bezier(.33,1,.68,1)}#aoi-boot .tx.ld .tk>.f>.c{opacity:1}
@keyframes txTk{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}
@keyframes txFill{from{transform:scaleX(0)}to{transform:scaleX(1)}}
`;
/* 로딩 신호 처리는 셋이 같다 */
function barsCtl(T,waitAt){const waitT=setTimeout(()=>{if(!T.root.classList.contains("ld"))T.root.classList.add("wait");},waitAt);
  return{post(m){if(m.type==="loaded"){clearTimeout(waitT);T.root.classList.remove("wait");T.root.classList.add("ld");}},kill(){clearTimeout(waitT);},reveal(){}};}

/* 대기 동작(4초를 넘겨도 로딩 중일 때, .tx.wait) — 전부 transform · opacity 키프레임. 현택 11/1 "'지금' 선은 구리다" → 대안 넷 */
const BARS_IDLE={
  sway:`#aoi-boot .tx.wait .tk,#aoi-boot .tx.wait .num,#aoi-boot .tx.wait .nm{animation:txTk .35s cubic-bezier(.22,1,.36,1) both,txSway 2.8s cubic-bezier(.45,.05,.55,.95) infinite alternate}
@keyframes txSway{from{transform:translateY(-1.5px)}to{transform:translateY(1.5px)}}
#aoi-boot .tx .now{position:absolute;width:2px;background:${TXT.INK2};opacity:0;will-change:transform;transition:opacity .4s}
#aoi-boot .tx.wait .now{opacity:.55;animation:txNow 4.2s cubic-bezier(.45,.05,.55,.95) infinite}#aoi-boot .tx.ld .now{opacity:0;animation:none}
@keyframes txNow{from{transform:translateX(0)}to{transform:translateX(var(--span))}}`,
  /* 파도: 글자 구간이 왼쪽에서 오른쪽으로 한 번씩 살짝 들렸다 내려온다(열마다 위상) — 'AOI' 가 파도를 탄다 */
  wave:`#aoi-boot .tx.wait .tk>.f{animation:txFill .6s cubic-bezier(.16,1,.3,1) both,txWave 2.6s cubic-bezier(.45,.05,.55,.95) infinite}
@keyframes txWave{0%,38%,100%{transform:translateY(0) scaleX(1)}19%{transform:translateY(-4px) scaleX(1)}}`,
  /* 흐름: 줄 전체(구간 · 숫자 · 이름)가 아주 천천히 오른쪽으로 6px 흘렀다 돌아온다 — 하루가 흐른다 */
  drift:`#aoi-boot .tx.wait .tk>.f{animation:txFill .6s cubic-bezier(.16,1,.3,1) both,txDrift 5.2s cubic-bezier(.45,.05,.55,.95) infinite alternate}
@keyframes txDrift{from{transform:translateX(0) scaleX(1)}to{transform:translateX(var(--dx,6px)) scaleX(1)}}`,
  /* 점등(D105 대기 동작, 현택 11/1): 구간이 읽는 순서로 차례로 밝아졌다 돌아온다 — 한 번에 4~5칸이 꼬리처럼 이어져 잘 보인다.
     회청색 겹(.g)의 opacity 만 움직인다(합성 스레드, 요소당 레이어 하나, JS 0) — 밑의 밝은 트랙 색이 비쳐 '불이 켜진' 것처럼 보인다 */
  glow:`#aoi-boot .tx.wait .tk>.f>.g{animation:txGlow var(--gp,5.4s) cubic-bezier(.45,.05,.55,.95) infinite}
@keyframes txGlow{0%,14%,100%{opacity:1}5%{opacity:.08}}`,
  /* 셈: 숫자 블록이 값을 세듯 폭이 줄었다 늘었다(scaleX, 왼쪽 기준) + 트랙은 가만히 — 계산 중 */
  count:`#aoi-boot .tx.wait .num{transform-origin:0 50%;animation:txTk .35s cubic-bezier(.22,1,.36,1) both,txCount 1.9s cubic-bezier(.45,.05,.55,.95) infinite alternate}
@keyframes txCount{from{transform:scaleX(.55)}to{transform:scaleX(1)}}`};
function barsListScene(ov,env,idle){
  const T=textStage(ov,env,BARS_CSS+(BARS_IDLE[idle]||BARS_IDLE.sway)+`
#aoi-boot .tx .nm{position:absolute;border-radius:2px;background:${TXT.INK3};opacity:0;animation:txTk .35s cubic-bezier(.22,1,.36,1) both}
#aoi-boot .tx .num{position:absolute;border-radius:2px;opacity:0;animation:txTk .35s cubic-bezier(.22,1,.36,1) both}
#aoi-boot .tx .num>i{position:absolute;left:0;top:0;width:100%;height:100%;display:block;border-radius:2px}#aoi-boot .tx .num>.g{background:${TXT.WAIT}}#aoi-boot .tx .num>.c{opacity:0;transition:opacity .5s cubic-bezier(.33,1,.68,1)}
#aoi-boot .tx.ld .num>.g{opacity:0;transition:opacity .5s}#aoi-boot .tx.ld .num>.c{opacity:1}
#aoi-boot .tx .sep{position:absolute;height:1px;background:${TXT.LINE};opacity:0;animation:txTk .35s both}`);
  const cell=Math.min(T.fs/7,(env.W*.5)/17),nameW=cell*2.2,numW=cell*1.1,gap=cell*.5,x0=T.cx-(nameW+gap+numW+gap+cell*17.8)/2+nameW+gap+numW+gap;
  const G=barsGeom(T,{cell,x0}),rnd=mulberry(2027),trackW=G.W3+cell*.8;
  const nSeg=G.runs.length,idxOf=(r,i)=>G.runs.findIndex(b=>b.r===r)+i;   /* 점등 순서 = 읽는 순서 */
  for(let r=0;r<7;r++){const y=G.y0+r*cell,d=120+r*95,mid=y+cell/2;
    const nm=document.createElement("i");nm.className="nm";nm.style.cssText=`left:${x0-nameW-gap-numW-gap}px;top:${mid-cell*.1}px;width:${nameW*(.7+(r*3%4)*.08)}px;height:${cell*.2}px;animation-delay:${d}ms,${-r*350}ms`;T.root.appendChild(nm);
    const num=document.createElement("i");num.className="num";num.style.cssText=`left:${x0-numW-gap}px;top:${mid-cell*.13}px;width:${numW*.85}px;height:${cell*.26}px;animation-delay:${d+40}ms,${-r*350}ms`;
    const g=document.createElement("i");g.className="g";const c=document.createElement("i");c.className="c";c.style.background=r%4===1?TXT.ERR:TXT.INK;num.appendChild(g);num.appendChild(c);T.root.appendChild(num);
    /* 줄의 트랙 하나(회색) — 글자 구간들은 그 안의 바쁜 시간 */
    const runs=G.runs.filter(b=>b.r===r),segs=runs.map((b,i)=>({p:(b.x-(x0-cell*.4))/trackW,w:b.w/trackW,c:barsColor(rnd),d:d+180+b.li*160+i*60}));
    const tk=barsMake(T.root,{x:x0-cell*.4,y:y,w:trackW,h:G.bh,r},segs,d+60,{tkExtra:`top:${mid-G.bh/2}px`});
    tk.querySelectorAll(".f").forEach((f,i)=>{const s=segs[i],ph=Math.round(-(s.p*1400));   /* 파도 · 흐름: 왼쪽 구간이 먼저(위상 = 가로 위치) */
      f.style.animationDelay=`${s.d}ms,${ph}ms`;f.style.setProperty("--dx",(4+r%3)+"px");const g=f.firstChild;const gi=idxOf(r,i);g.style.animationDelay=`${-gi*120}ms`;g.style.setProperty("--gp",(nSeg*120)+"ms");});
    if(r<6){const sp=document.createElement("i");sp.className="sep";sp.style.cssText=`left:${x0-nameW-gap-numW-gap}px;top:${y+cell-1}px;width:${nameW+gap+numW+gap+trackW}px;animation-delay:${d+80}ms`;T.root.appendChild(sp);}}
  if(idle==="sway"){const now=document.createElement("i");now.className="now";now.style.cssText=`left:${x0-cell*.4}px;top:${G.y0-cell*.3}px;height:${cell*7.6}px;--span:${trackW}px`;T.root.appendChild(now);}
  return barsCtl(T,3000);
}
