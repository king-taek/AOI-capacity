/* T1 'O 는 렌즈' — AOI(자동 광학 검사)의 O 가 렌즈가 되어 A 와 I 를 차례로 검사한다. A 에서 결함 하나(Error 빨강)를 찾고 I 는 통과(파랑 점).
   렌즈는 translateX · scale(초점) 만, 글자는 color 전환 · 표식은 opacity — 전부 합성 스레드, 프레임마다 JS 0. 기다릴 땐 렌즈가 천천히 초점을 더듬는다(translateY 3px) */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){
  const T=textStage(ov,env,`
#aoi-boot .tx .w{position:absolute;top:50%;font-weight:700;line-height:1;color:${TXT.INK};opacity:0;transform:translateY(-50%);will-change:transform,opacity;animation:txIn .6s cubic-bezier(.22,1,.36,1) both;transition:color .5s cubic-bezier(.33,1,.68,1)}
#aoi-boot .tx .lens{position:absolute;opacity:0;will-change:transform;animation:txLens 3.4s cubic-bezier(.65,0,.35,1) both}
#aoi-boot .tx .lens .ring{position:absolute;inset:0;border-radius:50%;border:var(--sw) solid ${TXT.INK};background:radial-gradient(circle at 38% 34%,rgba(255,255,255,.75),rgba(255,255,255,0) 46%),rgba(143,184,224,.14);transition:border-color .5s cubic-bezier(.33,1,.68,1)}
#aoi-boot .tx .lens .hi{position:absolute;left:18%;top:12%;width:28%;height:12%;border-radius:50%;background:rgba(255,255,255,.9);transform:rotate(-28deg)}
#aoi-boot .tx .mark{position:absolute;opacity:0;border-radius:2px;animation:txMark .32s cubic-bezier(.22,1,.36,1) both}
#aoi-boot .tx .mark.err{background:${TXT.ERR};animation-delay:1.55s}#aoi-boot .tx .mark.ok{background:${TXT.ACC};border-radius:50%;animation-delay:2.55s}
#aoi-boot .tx.wait .lens{animation:txLens 3.4s cubic-bezier(.65,0,.35,1) both,txIdle 3.6s cubic-bezier(.45,.05,.55,.95) 3.4s infinite alternate}
#aoi-boot .tx.ld .w{color:${TXT.ACC}}#aoi-boot .tx.ld .lens .ring{border-color:${TXT.ACC}}
@keyframes txIn{from{opacity:0;transform:translateY(calc(-50% + 14px))}to{opacity:1;transform:translateY(-50%)}}
@keyframes txLens{0%{opacity:0;transform:translate(0,-44px)}12%{opacity:1;transform:translate(0,0)}22%{transform:translate(0,0)}
  36%{transform:translate(var(--ax),0) scale(1)}42%{transform:translate(var(--ax),0) scale(1.07)}50%{transform:translate(var(--ax),0) scale(1)}
  64%{transform:translate(var(--ix),0) scale(1)}70%{transform:translate(var(--ix),0) scale(1.07)}78%{transform:translate(var(--ix),0) scale(1)}
  100%{opacity:1;transform:translate(0,0)}}
@keyframes txIdle{from{transform:translate(0,0)}to{transform:translate(0,3px)}}
@keyframes txMark{from{opacity:0;transform:scale(.6)}to{opacity:1;transform:none}}`);
  const fs=T.fs,cx=T.cx,cy=T.cy,R=fs*.4,gap=fs*.16,aw=fs*.68,iw=fs*.26;   /* A 폭 · I 폭(글꼴 어림) */
  const total=aw+gap+R*2+gap+iw,x0=cx-total/2;
  const mk=(cls,txt,x)=>{const s=document.createElement("span");s.className="w "+cls;s.textContent=txt;s.style.cssText=`font-size:${fs}px;left:${x}px;animation-delay:${cls==="i"?".12s":"0s"}`;T.root.appendChild(s);return s;};
  mk("a","A",x0);mk("i","I",x0+aw+gap+R*2+gap);
  const lens=document.createElement("div");lens.className="lens";const lx=x0+aw+gap;
  lens.style.cssText=`left:${lx}px;top:${cy-R}px;width:${R*2}px;height:${R*2}px;--sw:${Math.max(5,fs*.075)}px;--ax:${(x0+aw/2)-(lx+R)}px;--ix:${(x0+aw+gap+R*2+gap+iw/2)-(lx+R)}px`;
  const ring=document.createElement("i");ring.className="ring";const hi=document.createElement("i");hi.className="hi";lens.appendChild(ring);lens.appendChild(hi);T.root.appendChild(lens);
  const mark=(cls,x,y,s)=>{const m=document.createElement("i");m.className="mark "+cls;m.style.cssText=`left:${x}px;top:${y}px;width:${s}px;height:${s}px`;T.root.appendChild(m);};
  mark("err",x0+aw*.62,cy+fs*.02,Math.max(6,fs*.07));   /* A 의 오른쪽 빗금에 결함 하나 */
  mark("ok",x0+aw+gap+R*2+gap+iw/2-fs*.035,cy+fs*.46,Math.max(6,fs*.07));   /* I 아래 통과 점 */
  const waitT=setTimeout(()=>{if(!T.root.classList.contains("ld"))T.root.classList.add("wait");},3400);
  return{post(m){if(m.type==="loaded"){clearTimeout(waitT);T.root.classList.add("ld");}},kill(){clearTimeout(waitT);},reveal(){}};
}});
