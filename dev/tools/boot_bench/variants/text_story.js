/* T3 '검사 이력 4초' — 이 화면의 용어대로: 스캔 빔이 지나며 글자가 Scan 파랑이 되고, I 가 Error(빨강 · 짧게 흔들림)로 잡혀 Rescan(연파랑) 뒤 PASS(파랑)로 끝난다.
   글자색은 겹(ink · 파랑 · 빨강 · 연파랑)의 opacity 키프레임, 빔은 translateX, 흔들림은 transform — 전부 합성 스레드 */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){
  const T=textStage(ov,env,`
#aoi-boot .tx .w{position:absolute;top:50%;font-weight:700;line-height:1;opacity:0;transform:translateY(-50%);animation:txIn .55s cubic-bezier(.22,1,.36,1) both;will-change:transform,opacity}
#aoi-boot .tx .w>b{position:absolute;left:0;top:0;font-weight:700;color:${TXT.INK};opacity:0}
#aoi-boot .tx .w>b.k{position:relative;opacity:1}
#aoi-boot .tx .w>b.s{color:${TXT.ACC};animation:txOn .25s cubic-bezier(.33,1,.68,1) both;animation-delay:var(--ts)}
#aoi-boot .tx .w.i>b.e{color:${TXT.ERR};animation:txErr 1s cubic-bezier(.33,1,.68,1) 1.75s both}
#aoi-boot .tx .w.i{animation:txIn .55s cubic-bezier(.22,1,.36,1) .16s both,txShake .42s cubic-bezier(.36,.07,.19,.97) 1.78s}
#aoi-boot .tx .w.i>b.r{color:${TXT.ACC2};animation:txRe .9s cubic-bezier(.33,1,.68,1) 2.75s both}
#aoi-boot .tx .beam{position:absolute;width:3px;background:${TXT.ACC};box-shadow:0 0 14px 3px rgba(46,107,168,.3);opacity:0;will-change:transform;animation:txBeam 1s cubic-bezier(.45,.05,.55,.95) .7s both,txBeam2 .7s cubic-bezier(.45,.05,.55,.95) 2.35s both}
#aoi-boot .tx.wait .beam{animation:txBeam 1s cubic-bezier(.45,.05,.55,.95) .7s both,txBeam2 .7s cubic-bezier(.45,.05,.55,.95) 2.35s both,txBeamIdle 3.8s cubic-bezier(.45,.05,.55,.95) 3.2s infinite alternate}
#aoi-boot .tx.ld .beam{animation:none;opacity:0;transition:opacity .35s}
@keyframes txIn{from{opacity:0;transform:translateY(calc(-50% + 12px))}to{opacity:1;transform:translateY(-50%)}}
@keyframes txOn{to{opacity:1}}
@keyframes txErr{0%{opacity:0}18%{opacity:1}82%{opacity:1}100%{opacity:0}}
@keyframes txRe{0%{opacity:0}20%{opacity:1}75%{opacity:1}100%{opacity:0}}
@keyframes txShake{10%,90%{transform:translate(-2px,-50%)}20%,80%{transform:translate(3px,-50%)}30%,50%,70%{transform:translate(-4px,-50%)}40%,60%{transform:translate(4px,-50%)}}
@keyframes txBeam{0%{opacity:0;transform:translateX(0)}6%{opacity:1}94%{opacity:1}100%{opacity:0;transform:translateX(var(--span))}}
@keyframes txBeam2{0%{opacity:0;transform:translateX(var(--i0))}10%{opacity:1}90%{opacity:1}100%{opacity:0;transform:translateX(var(--i1))}}
@keyframes txBeamIdle{from{opacity:.3;transform:translateX(var(--span))}to{opacity:.3;transform:translateX(0)}}`);
  const fs=T.fs,cx=T.cx,cy=T.cy,aw=fs*.68,ow=fs*.72,iw=fs*.26,gap=fs*.1,total=aw+gap+ow+gap+iw,x0=cx-total/2;
  const letter=(cls,txt,x,w,ts)=>{const s=document.createElement("span");s.className="w "+cls;s.style.cssText=`font-size:${fs}px;left:${x}px;--ts:${ts}ms`;
    const layers=cls==="i"?["k","s","e","r"]:["k","s"];for(const l of layers){const b=document.createElement("b");b.className=l;b.textContent=txt;s.appendChild(b);}T.root.appendChild(s);};
  /* 빔이 글자 가운데를 지나는 시각(0.7s 출발 · 1s 동안 total 을 지남)에 Scan 파랑으로 */
  const at=x=>700+1000*((x-x0)/total);
  letter("a","A",x0,aw,at(x0+aw/2));letter("o","O",x0+aw+gap,ow,at(x0+aw+gap+ow/2));letter("i","I",x0+aw+gap+ow+gap,iw,at(x0+total-iw/2));
  const beam=document.createElement("i");beam.className="beam";beam.style.cssText=`left:${x0-fs*.08}px;top:${cy-fs*.58}px;height:${fs*1.16}px;--span:${total+fs*.16}px;--i0:${total-iw+fs*.04}px;--i1:${total+fs*.16}px`;T.root.appendChild(beam);
  const waitT=setTimeout(()=>{if(!T.root.classList.contains("ld"))T.root.classList.add("wait");},3300);
  return{post(m){if(m.type==="loaded"){clearTimeout(waitT);T.root.classList.add("ld");}},kill(){clearTimeout(waitT);},reveal(){}};
}});
