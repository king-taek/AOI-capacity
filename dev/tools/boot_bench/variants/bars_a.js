/* T2-A '줄마다 차오름' — 막대마다 구간 1~3개(한 줄 = 하루의 24시간 막대처럼), 읽는 순서(위→아래 · 왼→오른)로 차오른다. 기다릴 땐 '지금' 선 */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){
  const T=textStage(ov,env,BARS_CSS),G=barsGeom(T),rnd=mulberry(2026);let n=0;
  for(const b of G.runs){const d=150+b.r*110+b.li*70+n*18;n++;const segs=[];let p=0;const k=b.cells>=4?2+Math.floor(rnd()*2):1;
    for(let i=0;i<k;i++){const w=(1-p)/(k-i)*(.75+rnd()*.25);segs.push({p,w:Math.min(w,1-p),c:barsColor(rnd),d:d+120+i*110});p+=w+(i<k-1?.03:0);}
    barsMake(T.root,b,segs,d);}
  const now=document.createElement("i");now.className="now";now.style.cssText=`left:${G.x0-G.cell*.3}px;top:${G.y0-G.cell*.4}px;height:${G.cell*7.8}px;--span:${G.W3+G.cell*.6}px`;T.root.appendChild(now);
  return barsCtl(T,3000);
}});
