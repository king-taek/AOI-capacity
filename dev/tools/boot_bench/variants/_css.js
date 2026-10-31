/* CSS 스켈레톤 — DOM 요소 + CSS 키프레임(transform · opacity 만, 합성 스레드). 프레임마다 도는 JS 없음.
   data:true 면 숫자 블록 · 막대 구간도 그린다(2막 — 로딩 전엔 회청색으로 살랑, 로딩 끝나면 제 색으로 crossfade) */
function cssFrame(ov,env,opt){
  const {W,H,red}=env,root=document.createElement("div");root.className="bk"+(red?" red":"")+(opt.data?" dat":"");
  root.style.cssText=`position:absolute;left:0;top:0;width:${W}px;height:${H}px;overflow:hidden`;
  const st=document.createElement("style");
  st.textContent=`
#aoi-boot .bk *{position:absolute;box-sizing:border-box}
#aoi-boot .bk .ln{border:1px solid #D3DAE2;border-radius:12px;opacity:0;animation:bkIn .42s cubic-bezier(.16,1,.3,1) both}
#aoi-boot .bk .bl{background:#AEB8C4;opacity:0;animation:bkIn .36s cubic-bezier(.16,1,.3,1) both}
#aoi-boot .bk .rw{opacity:0;animation:bkRow .4s cubic-bezier(.16,1,.3,1) both}
#aoi-boot .bk .d{transform-origin:0 50%;opacity:0;animation:bkGrow .5s cubic-bezier(.16,1,.3,1) both}
#aoi-boot .bk .d>i{left:0;top:0;width:100%;height:100%;display:block}
#aoi-boot .bk .d>.g{background:#9DB4CE;opacity:.6;animation:bkSway 3.2s ease-in-out infinite;transition:opacity .45s ease-out}
#aoi-boot .bk .d>.c{opacity:0;transition:opacity .45s ease-out}
#aoi-boot .bk.ld .d>.g{opacity:0;animation:none}
#aoi-boot .bk.ld .d>.c{opacity:1}
#aoi-boot .bk.red *{animation:none!important;opacity:1}
#aoi-boot .bk.red .d>.g{opacity:.6}#aoi-boot .bk.red.ld .d>.g{opacity:0}
#aoi-boot .bk .wf{opacity:0;animation:bkIn .5s cubic-bezier(.16,1,.3,1) both}
#aoi-boot .bk .wd{clip-path:circle(0% at 50% 50%);animation:bkCirc 1.1s cubic-bezier(.3,0,.2,1) both}
#aoi-boot .bk .wd>svg{position:absolute;left:0;top:0}
#aoi-boot .bk .wd>.g{opacity:.6;animation:bkSway 3.2s ease-in-out infinite;transition:opacity .45s ease-out}
#aoi-boot .bk .wd>.c{opacity:0;transition:opacity .45s ease-out}
#aoi-boot .bk.ld .wd>.g{opacity:0;animation:none}#aoi-boot .bk.ld .wd>.c{opacity:1}
@keyframes bkIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes bkRow{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}
@keyframes bkGrow{from{opacity:0;transform:scaleX(.02)}to{opacity:1;transform:none}}
@keyframes bkSway{0%,100%{transform:translateY(-1.5px)}50%{transform:translateY(1.5px)}}
@keyframes bkCirc{from{clip-path:circle(0% at 50% 50%)}to{clip-path:circle(52% at 50% 50%)}}`;
  root.appendChild(st);
  const el=(cls,b,delay,extra)=>{const e=document.createElement("div");e.className=cls;e.style.cssText=`left:${b.x}px;top:${b.y}px;width:${Math.max(1,b.w)}px;height:${Math.max(1,b.h)}px;animation-delay:${delay}ms;${extra||""}`;return e;};
  const data=(b,c,delay,parent)=>{if(!opt.data)return;const d=el("d",b,delay);const g=document.createElement("i");g.className="g";g.style.animationDelay=(-(b.x*7+b.y*3)%3200)+"ms";
    const k=document.createElement("i");k.className="c";k.style.background=c;d.appendChild(g);d.appendChild(k);(parent||root).appendChild(d);};
  const INK="#16202B",INK2="#5A6673",INK3="#AEB8C4",ERR="#C5453C",TRACK="#DFE5EC";
  if(env.kind==="lot"){
    const L=layoutDraw(W,H,"lot"),NS="http://www.w3.org/2000/svg";
    const svg=document.createElementNS(NS,"svg");svg.setAttribute("width",W);svg.setAttribute("height",H);svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
    for(const a of L.arcs){const c=document.createElementNS(NS,"circle");c.setAttribute("cx",a.x);c.setAttribute("cy",a.y);c.setAttribute("r",a.r);c.setAttribute("fill","none");c.setAttribute("stroke",a.c);c.setAttribute("stroke-width",a.lw||1);svg.appendChild(c);}
    for(const l of L.lines){const p=document.createElementNS(NS,"polyline");p.setAttribute("points",l.pts.map(q=>q.join(",")).join(" "));p.setAttribute("fill","none");p.setAttribute("stroke",l.c);p.setAttribute("stroke-width",l.lw||1);p.setAttribute("stroke-linecap","round");p.setAttribute("stroke-linejoin","round");svg.appendChild(p);}
    for(const r of L.rects)if(!r.d&&r.w>4&&r.h>4){const q=document.createElementNS(NS,"rect");q.setAttribute("x",r.x);q.setAttribute("y",r.y);q.setAttribute("width",r.w);q.setAttribute("height",r.h);q.setAttribute("fill",r.c);svg.appendChild(q);}
    const fr=document.createElement("div");fr.className="wf";fr.style.cssText="left:0;top:0;width:100%;height:100%;animation-delay:120ms";fr.appendChild(svg);root.appendChild(fr);
    if(opt.data){L.zones.forEach((z,i)=>{const wd=el("wd",z,1500+i*520);
      const mk=cls=>{const s=document.createElementNS(NS,"svg");s.setAttribute("width",z.w);s.setAttribute("height",z.h);s.setAttribute("viewBox",`${z.x} ${z.y} ${z.w} ${z.h}`);s.setAttribute("class",cls);
        for(const r of L.rects)if(r.d&&r.x>=z.x&&r.x<z.x+z.w&&r.y>=z.y&&r.y<z.y+z.h){const q=document.createElementNS(NS,"rect");q.setAttribute("x",r.x);q.setAttribute("y",r.y);q.setAttribute("width",r.w);q.setAttribute("height",r.h);q.setAttribute("fill",cls==="g"?"#9DB4CE":r.c);s.appendChild(q);}return s;};
      wd.appendChild(mk("g"));wd.appendChild(mk("c"));root.appendChild(wd);});
      for(const r of L.rects)if(r.d&&!L.zones.some(z=>r.x>=z.x&&r.x<z.x+z.w&&r.y>=z.y&&r.y<z.y+z.h))data(r,r.c,1500);}
  }else{
    const sp=layoutSpec(W,H,mulberry(1030));
    sp.cards.forEach((c,i)=>{root.appendChild(el("ln",c,i*90));root.appendChild(el("bl",c.label,120+i*90));
      root.appendChild(el("bl",c.l1,200+i*90,"background:#CBD3DC"));root.appendChild(el("bl",c.l2,240+i*90,"background:#CBD3DC"));data(c.num,c.num.err?ERR:INK,1500+i*120);});
    if(sp.panel){const p=sp.panel;root.appendChild(el("ln",p,300));
      sp.legend.forEach((g,i)=>{root.appendChild(el("bl",g.dot,380+i*40,`background:${g.dot.c}`));root.appendChild(el("bl",g.txt,400+i*40));});
      root.appendChild(el("bl",p.rule,420,"background:#E7ECF1"));
      sp.rows.forEach((r,k)=>{const dl=440+k*55;const row=document.createElement("div");row.className="rw";row.style.cssText=`left:0;top:0;width:100%;height:100%;animation-delay:${dl}ms`;
        row.appendChild(el("bl",r.name,0,`background:${INK2};animation:none;opacity:1`));row.appendChild(el("bl",r.track,0,`background:${TRACK};animation:none;opacity:1`));
        if(r.sep)row.appendChild(el("bl",r.sep,0,"background:#EEF1F4;animation:none;opacity:1"));if(!r.badge.err)row.appendChild(el("bl",r.badge,0,"animation:none;opacity:1"));
        root.appendChild(row);
        data(r.num,r.num.err?ERR:INK,1600+k*60);r.segs.forEach((s,i)=>data({x:s.x,y:r.track.y,w:s.w,h:r.track.h},s.c,1750+k*60+i*45));if(r.badge.err)data(r.badge,ERR,1900+k*60);});}}
  ov.insertBefore(root,ov.firstChild);
  return{root,post(m){if(m.type==="loaded")root.classList.add("ld");},kill(){},reveal(){}};
}
