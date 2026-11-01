/* T2-B '장비 목록' — 가동률 화면의 줄 7개(장비 이름 자리 · 숫자 블록 · 24시간 트랙)가 먼저 깔리고, 트랙 안의 바쁜 구간이 자라 AOI 를 쓴다(쉬는 시간은 회색 트랙). 기다릴 땐 '지금' 선 */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){
  const T=textStage(ov,env,BARS_CSS+`
#aoi-boot .tx .nm{position:absolute;border-radius:2px;background:${TXT.INK3};opacity:0;animation:txTk .35s cubic-bezier(.22,1,.36,1) both}
#aoi-boot .tx .num{position:absolute;border-radius:2px;opacity:0;animation:txTk .35s cubic-bezier(.22,1,.36,1) both}
#aoi-boot .tx .num>i{position:absolute;left:0;top:0;width:100%;height:100%;display:block;border-radius:2px}#aoi-boot .tx .num>.g{background:${TXT.WAIT}}#aoi-boot .tx .num>.c{opacity:0;transition:opacity .5s cubic-bezier(.33,1,.68,1)}
#aoi-boot .tx.ld .num>.g{opacity:0;transition:opacity .5s}#aoi-boot .tx.ld .num>.c{opacity:1}
#aoi-boot .tx .sep{position:absolute;height:1px;background:${TXT.LINE};opacity:0;animation:txTk .35s both}`);
  const cell=Math.min(T.fs/7,(env.W*.5)/17),nameW=cell*2.2,numW=cell*1.1,gap=cell*.5,x0=T.cx-(nameW+gap+numW+gap+cell*17.8)/2+nameW+gap+numW+gap;
  const G=barsGeom(T,{cell,x0}),rnd=mulberry(2027),trackW=G.W3+cell*.8;
  for(let r=0;r<7;r++){const y=G.y0+r*cell,d=120+r*95,mid=y+cell/2;
    const nm=document.createElement("i");nm.className="nm";nm.style.cssText=`left:${x0-nameW-gap-numW-gap}px;top:${mid-cell*.1}px;width:${nameW*(.7+(r*3%4)*.08)}px;height:${cell*.2}px;animation-delay:${d}ms`;T.root.appendChild(nm);
    const num=document.createElement("i");num.className="num";num.style.cssText=`left:${x0-numW-gap}px;top:${mid-cell*.13}px;width:${numW*.85}px;height:${cell*.26}px;animation-delay:${d+40}ms`;
    const g=document.createElement("i");g.className="g";const c=document.createElement("i");c.className="c";c.style.background=r%4===1?TXT.ERR:TXT.INK;num.appendChild(g);num.appendChild(c);T.root.appendChild(num);
    /* 줄의 트랙 하나(회색) — 글자 구간들은 그 안의 바쁜 시간 */
    const runs=G.runs.filter(b=>b.r===r),segs=runs.map((b,i)=>({p:(b.x-(x0-cell*.4))/trackW,w:b.w/trackW,c:barsColor(rnd),d:d+180+b.li*160+i*60}));
    barsMake(T.root,{x:x0-cell*.4,y:y,w:trackW,h:G.bh,r},segs,d+60,{tkExtra:`top:${mid-G.bh/2}px`});
    if(r<6){const sp=document.createElement("i");sp.className="sep";sp.style.cssText=`left:${x0-nameW-gap-numW-gap}px;top:${y+cell-1}px;width:${nameW+gap+numW+gap+trackW}px;animation-delay:${d+80}ms`;T.root.appendChild(sp);}}
  const now=document.createElement("i");now.className="now";now.style.cssText=`left:${x0-cell*.4}px;top:${G.y0-cell*.3}px;height:${cell*7.6}px;--span:${trackW}px`;T.root.appendChild(now);
  return barsCtl(T,3000);
}});
