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
  const tk=document.createElement("div");tk.className="tk";tk.style.cssText=`left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px;animation-delay:${delay}ms;${(opts&&opts.tkExtra)||""}`;
  segs.forEach((s,i)=>{const f=document.createElement("i");f.className="f";f.style.cssText=`left:${(s.p*100).toFixed(2)}%;width:${(s.w*100).toFixed(2)}%;animation-delay:${s.d}ms`;
    const g=document.createElement("i");g.className="g";const c=document.createElement("i");c.className="c";c.style.background=s.c;f.appendChild(g);f.appendChild(c);tk.appendChild(f);});
  root.appendChild(tk);return tk;}
const BARS_CSS=`
#aoi-boot .tx .tk{position:absolute;border-radius:3px;background:${TXT.LINE};opacity:0;animation:txTk .35s cubic-bezier(.22,1,.36,1) both}
#aoi-boot .tx .tk>.f{position:absolute;top:0;height:100%;display:block;transform:scaleX(0);transform-origin:0 50%;animation:txFill .6s cubic-bezier(.16,1,.3,1) both;will-change:transform;border-radius:3px;overflow:hidden}
#aoi-boot .tx .tk>.f>i{position:absolute;left:0;top:0;width:100%;height:100%;display:block}
#aoi-boot .tx .tk>.f>.g{background:${TXT.WAIT}}#aoi-boot .tx .tk>.f>.c{opacity:0;transition:opacity .5s cubic-bezier(.33,1,.68,1)}
#aoi-boot .tx.ld .tk>.f>.g{opacity:0;transition:opacity .5s cubic-bezier(.33,1,.68,1)}#aoi-boot .tx.ld .tk>.f>.c{opacity:1}
#aoi-boot .tx .now{position:absolute;width:2px;background:${TXT.INK2};opacity:0;will-change:transform;transition:opacity .4s}
#aoi-boot .tx.wait .now{opacity:.55;animation:txNow 4.2s cubic-bezier(.45,.05,.55,.95) infinite}
#aoi-boot .tx.ld .now{opacity:0;animation:none}
@keyframes txTk{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}
@keyframes txFill{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes txNow{from{transform:translateX(0)}to{transform:translateX(var(--span))}}`;
/* 로딩 신호 처리는 셋이 같다 */
function barsCtl(T,waitAt){const waitT=setTimeout(()=>{if(!T.root.classList.contains("ld"))T.root.classList.add("wait");},waitAt);
  return{post(m){if(m.type==="loaded"){clearTimeout(waitT);T.root.classList.remove("wait");T.root.classList.add("ld");}},kill(){clearTimeout(waitT);},reveal(){}};}
