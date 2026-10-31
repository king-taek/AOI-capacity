/* V5 스캔 라인 — 장면을 캔버스에 **한 번** 그리고(틀 · 회청색 데이터 · 제 색 데이터 세 겹), 스캔 헤드가 위→아래로 지나며 clip-path 로 드러낸다.
   프레임마다 도는 JS 0 — clip-path · transform · opacity 는 전부 합성 스레드(WAAPI/CSS) */
bootShell({sceneReveals:false,settleMs:450,fadeMs:600,make(ov,env,api){
  const {W,H,red}=env,L=layoutDraw(W,H,env.kind),dpr=Math.min(1.5,window.devicePixelRatio||1);
  const mk=()=>{const c=document.createElement("canvas");c.width=Math.round(W*dpr);c.height=Math.round(H*dpr);c.style.cssText=`position:absolute;left:0;top:0;width:${W}px;height:${H}px;will-change:clip-path,opacity`;const x=c.getContext("2d");x.scale(dpr,dpr);return[c,x];};
  const draw=(o,dat,grey)=>{for(const r of L.rects)if(!!r.d===dat){o.fillStyle=grey?"#B7C6D6":r.c;o.fillRect(r.x,r.y,r.w,r.h);}
    if(!dat)for(const s of L.strokes){const lw=s.lw||1;o.strokeStyle=s.c;o.lineWidth=lw;o.beginPath();if(o.roundRect&&s.r)o.roundRect(s.x+lw/2,s.y+lw/2,Math.max(0,s.w-lw),Math.max(0,s.h-lw),Math.min(s.r,s.w/2,s.h/2));else o.rect(s.x+lw/2,s.y+lw/2,s.w-lw,s.h-lw);o.stroke();}
    for(const a of L.arcs||[])if(!!a.d===dat){o.beginPath();o.arc(a.x,a.y,a.r,0,Math.PI*2);o.strokeStyle=a.c;o.lineWidth=a.lw||1;o.stroke();}
    for(const l of L.lines||[])if(!!l.d===dat){o.strokeStyle=l.c;o.lineWidth=l.lw||1;o.lineCap="round";o.lineJoin="round";o.beginPath();l.pts.forEach((q,i)=>i?o.lineTo(q[0],q[1]):o.moveTo(q[0],q[1]));o.stroke();}};
  const [A,ax]=mk(),[B,bx]=mk(),[C,cx]=mk();draw(ax,false);draw(bx,true,true);draw(cx,true,false);C.style.opacity="0";C.style.transition="opacity .45s ease-out";B.style.transition="opacity .45s ease-out";
  const head=document.createElement("div");head.style.cssText=`position:absolute;left:0;top:-3px;width:${W}px;height:3px;background:linear-gradient(90deg,rgba(46,107,168,0),#2E6BA8 30%,#2E6BA8 70%,rgba(46,107,168,0));box-shadow:0 0 18px 4px rgba(46,107,168,.28);will-change:transform;opacity:0`;
  const wrap=document.createElement("div");wrap.style.cssText=`position:absolute;left:0;top:0;width:${W}px;height:${H}px;overflow:hidden`;
  [A,B,C,head].forEach(e=>wrap.appendChild(e));ov.insertBefore(wrap,ov.firstChild);
  const DUR=3300,EASE="cubic-bezier(.45,.05,.55,.95)";
  if(!red){
    A.animate([{clipPath:"inset(0 0 100% 0)"},{clipPath:"inset(0 0 0% 0)"}],{duration:DUR,delay:150,easing:EASE,fill:"both"});
    for(const c of [B,C])c.animate([{clipPath:"inset(0 0 100% 0)"},{clipPath:"inset(0 0 0% 0)"}],{duration:DUR,delay:420,easing:EASE,fill:"both"});
    head.animate([{transform:"translateY(0)",opacity:0},{opacity:1,offset:.04},{opacity:1,offset:.96},{transform:`translateY(${H+6}px)`,opacity:0}],{duration:DUR+300,delay:150,easing:EASE,fill:"both"});
    /* 기다림: 회청색 데이터 겹이 살랑(opacity · 미세 translateY) */
    B.animate([{transform:"translateY(-1px)",opacity:1},{transform:"translateY(1px)",opacity:.75},{transform:"translateY(-1px)",opacity:1}],{duration:3200,delay:DUR+600,iterations:Infinity,easing:"ease-in-out"});
  }
  return{post(m){if(m.type==="loaded"){for(const a of B.getAnimations())if(a.effect.getTiming().iterations===Infinity)a.cancel();B.style.opacity="0";C.style.opacity="1";}},kill(){},reveal(){}};
}});
