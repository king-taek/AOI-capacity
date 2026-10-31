/* T2 '막대로 쓴 AOI' — 가동률 화면의 24시간 막대가 글자가 된다: 5×7 비트맵의 가로 줄(run)마다 막대 하나, 왼→오른으로 차오르고(scaleX),
   색은 범례 그대로(Scan 파랑 · Rescan 연파랑 · Test 보라 · Error 빨강). 값이 오기 전엔 회청색, 로딩 끝 = 제 색으로. 기다릴 땐 '지금' 선이 하루를 가로지른다(translateX) */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){
  const T=textStage(ov,env,`
#aoi-boot .tx .tk{position:absolute;border-radius:3px;background:${TXT.LINE};opacity:0;animation:txTk .35s cubic-bezier(.22,1,.36,1) both}
#aoi-boot .tx .tk>i{position:absolute;left:0;top:0;width:100%;height:100%;border-radius:3px;display:block}
#aoi-boot .tx .tk>.g{background:${TXT.WAIT};transform:scaleX(0);transform-origin:0 50%;animation:txFill .6s cubic-bezier(.16,1,.3,1) both;will-change:transform}
#aoi-boot .tx .tk>.c{opacity:0;transition:opacity .5s cubic-bezier(.33,1,.68,1)}
#aoi-boot .tx.ld .tk>.g{opacity:0;transition:opacity .5s cubic-bezier(.33,1,.68,1)}#aoi-boot .tx.ld .tk>.c{opacity:1}
#aoi-boot .tx .now{position:absolute;width:2px;background:${TXT.INK2};opacity:0;will-change:transform;transition:opacity .4s}
#aoi-boot .tx.wait .now{opacity:.55;animation:txNow 4.2s cubic-bezier(.45,.05,.55,.95) infinite}
#aoi-boot .tx.ld .now{opacity:0;animation:none}
@keyframes txTk{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}
@keyframes txFill{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes txNow{from{transform:translateX(0)}to{transform:translateX(var(--span))}}`);
  const G={A:[".###.","#...#","#...#","#####","#...#","#...#","#...#"],O:[".###.","#...#","#...#","#...#","#...#","#...#",".###."],I:["#####","..#..","..#..","..#..","..#..","..#..","#####"]};
  const cell=T.fs/7,bh=cell*.62,gapL=cell*1.4,W3=cell*5*3+gapL*2,x0=T.cx-W3/2,y0=T.cy-cell*3.5,rnd=mulberry(2026);
  const col=()=>{const u=rnd();return u<.66?TXT.ACC:u<.82?TXT.ACC2:u<.92?"#7A5BB5":TXT.ERR;};
  let n=0;["A","O","I"].forEach((ch,li)=>{G[ch].forEach((row,r)=>{let c=0;while(c<5){if(row[c]!=="#"){c++;continue;}let e=c;while(e<5&&row[e]==="#")e++;
    const x=x0+li*(cell*5+gapL)+c*cell,w=(e-c)*cell-cell*.18,y=y0+r*cell+(cell-bh)/2,d=150+r*110+li*70+n*18;n++;
    const tk=document.createElement("div");tk.className="tk";tk.style.cssText=`left:${x}px;top:${y}px;width:${w}px;height:${bh}px;animation-delay:${d}ms`;
    const g=document.createElement("i");g.className="g";g.style.animationDelay=(d+120)+"ms";const k=document.createElement("i");k.className="c";k.style.background=col();tk.appendChild(g);tk.appendChild(k);T.root.appendChild(tk);c=e;}});});
  const now=document.createElement("i");now.className="now";now.style.cssText=`left:${x0-cell*.3}px;top:${y0-cell*.4}px;height:${cell*7.8}px;--span:${W3+cell*.6}px`;T.root.appendChild(now);
  const waitT=setTimeout(()=>{if(!T.root.classList.contains("ld"))T.root.classList.add("wait");},3000);
  return{post(m){if(m.type==="loaded"){clearTimeout(waitT);T.root.classList.remove("wait");T.root.classList.add("ld");}},kill(){clearTimeout(waitT);},reveal(){}};
}});
