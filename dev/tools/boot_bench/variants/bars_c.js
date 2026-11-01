/* T2-C '스캔 헤드' — 트랙이 먼저 깔리고, 스캔 헤드가 왼→오른으로 지나가며 닿는 구간부터 차오른다(AOI 검사처럼). 지나간 뒤 기다릴 땐 헤드가 천천히 오간다 */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){
  const T=textStage(ov,env,BARS_CSS+`
#aoi-boot .tx .head{position:absolute;width:3px;background:${TXT.ACC};box-shadow:0 0 14px 3px rgba(46,107,168,.3);opacity:0;will-change:transform;animation:txHead 2.3s cubic-bezier(.45,.05,.55,.95) .45s both}
#aoi-boot .tx.wait .head{animation:txHead 2.3s cubic-bezier(.45,.05,.55,.95) .45s both,txHeadIdle 4s cubic-bezier(.45,.05,.55,.95) 2.75s infinite alternate}
#aoi-boot .tx.ld .head{animation:none;opacity:0;transition:opacity .35s}
@keyframes txHead{0%{opacity:0;transform:translateX(0)}5%{opacity:1}95%{opacity:1}100%{opacity:0;transform:translateX(var(--span))}}
@keyframes txHeadIdle{from{opacity:.35;transform:translateX(var(--span))}to{opacity:.35;transform:translateX(0)}}`);
  const T0=450,DUR=2300,G=barsGeom(T),rnd=mulberry(2028),span=G.W3+G.cell*.6,sx=G.x0-G.cell*.3;
  /* 헤드가 x 에 닿는 시각(이징이 대칭 easeInOut 이라 근사: 선형 + 가운데 보정은 생략) */
  const at=x=>T0+DUR*((x-sx)/span);
  for(const b of G.runs){const segs=[];let p=0;const k=b.cells>=4?2:1;
    for(let i=0;i<k;i++){const w=(1-p)/(k-i)*(.78+rnd()*.22);segs.push({p,w:Math.min(w,1-p),c:barsColor(rnd),d:Math.round(at(b.x+b.w*p))});p+=w+(i<k-1?.03:0);}
    barsMake(T.root,b,segs,60+b.r*40+b.li*30);}
  const head=document.createElement("i");head.className="head";head.style.cssText=`left:${sx}px;top:${G.y0-G.cell*.5}px;height:${G.cell*8}px;--span:${span}px`;T.root.appendChild(head);
  return barsCtl(T,3100);
}});
