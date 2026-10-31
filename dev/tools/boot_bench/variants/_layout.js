/* 장면 설명 L {rects,strokes,texts,arcs,lines,zones} — 대시보드(layoutSpec) · 웨이퍼(baseline waferLayout 이식). d:1 = 데이터 몫 */
function layoutDraw(W,H,kind){
  const L={texts:[],rects:[],strokes:[],zones:[],arcs:[],lines:[]},R=(x,y,w,h,c,d)=>L.rects.push({x,y,w,h,c,d:d?1:0});
  const INK="#16202B",INK2="#5A6673",INK3="#AEB8C4",LINE="#D3DAE2",TRACK="#DFE5EC",ERR="#C5453C";
  if(kind==="lot"){
    const LC={INK,INK2,INK3,LINE,TRACK,ACC:"#2E6BA8",DUP:"#8FB8DE",ERR,OV:"#F2C26B",SEV:"#D9731F"},r2=mulberry(4410);
    const pad=Math.round(Math.max(20,Math.min(W*.03,44))),capH=Math.max(34,H*.06),top=Math.round(pad*1.2),bot=H-capH-pad*.4,bh=bot-top,k=W<760?2:W/H>1.9?4:3,gap=Math.max(40,W*.05);
    const D=Math.min((W-pad*2-gap*(k-1))/k,bh*.74),r=D/2,cy=top+bh*.46,span=k*D+(k-1)*gap,x0=(W-span)/2;
    const nd=Math.max(9,Math.min(17,Math.round(D/22))),ds=D/nd*.98,gp=Math.max(1,ds*.12);
    const hot=[...Array(k)].map(()=>({a:r2()*6.28,d:.3+r2()*.5,s:.18+r2()*.2}));
    for(let w=0;w<k;w++){const cx=x0+w*(D+gap)+r;
      L.arcs.push({x:cx,y:cy,r:r,c:LC.INK2,lw:2});L.lines.push({pts:[[cx-r*.12,cy+r*.995],[cx,cy+r*.9],[cx+r*.12,cy+r*.995]],c:LC.INK2,lw:2});
      const lvl=w/(k-1||1);
      for(let iy=0;iy<nd;iy++)for(let ix=0;ix<nd;ix++){const x=cx-r+ix*D/nd+(D/nd-ds)/2,y=cy-r+iy*D/nd+(D/nd-ds)/2,ex=x+ds/2-cx,ey=y+ds/2-cy;
        if(Math.hypot(Math.abs(ex)+ds/2,Math.abs(ey)+ds/2)>r*.97)continue;
        R(x+gp/2,y+gp/2,ds-gp,ds-gp,LC.TRACK);
        const h=hot[w],hx=Math.cos(h.a)*h.d*r,hy=Math.sin(h.a)*h.d*r,dd=Math.hypot(ex-hx,ey-hy)/r,u=r2();
        let c=u<.94?LC.ACC:LC.DUP;if(dd<h.s*(.6+lvl*.8)&&u<.9)c=dd<h.s*.45?LC.SEV:LC.OV;else if(u>.988)c=LC.ERR;
        R(x+gp/2,y+gp/2,ds-gp,ds-gp,c,1);}
      L.zones.push({x:cx-r,y:cy-r,w:D,h:D});
      R(cx-r*.42,cy-r-Math.max(26,bh*.06),r*.36,Math.max(5,bh*.012),LC.INK3);R(cx-r*.42+r*.42,cy-r-Math.max(26,bh*.06)-1,r*.42,Math.max(7,bh*.016),LC.INK,1);
      const by=cy+r+Math.max(22,bh*.05);R(cx-r*.5,by,r*.3,Math.max(6,bh*.014),LC.INK3);R(cx-r*.5+r*.38,by-1,r*.24,Math.max(8,bh*.018),w===k-1?LC.SEV:LC.INK,1);R(cx+r*.2,by,r*.3,Math.max(6,bh*.014),LC.INK3);
      if(w<k-1){const ax=cx+r+gap*.18,bx=cx+r+gap*.82,ah=Math.max(5,gap*.12);L.lines.push({pts:[[ax,cy],[bx,cy]],c:LC.INK2,lw:2.5});L.lines.push({pts:[[bx-ah,cy-ah],[bx,cy],[bx-ah,cy+ah]],c:LC.INK2,lw:2.5});}}
    return L;}
  const sp=layoutSpec(W,H,mulberry(1030));
  for(const c of sp.cards){L.strokes.push({x:c.x,y:c.y,w:c.w,h:c.h,r:12,lw:1,c:LINE});const b=c.label;R(b.x,b.y,b.w,b.h,INK3);
    R(c.num.x,c.num.y,c.num.w,c.num.h,c.num.err?ERR:INK,1);L.zones.push({x:c.num.x,y:c.num.y,w:Math.min(c.w*.5,c.num.w*1.6),h:c.num.h});
    R(c.l1.x,c.l1.y,c.l1.w,c.l1.h,"#CBD3DC");R(c.l2.x,c.l2.y,c.l2.w,c.l2.h,"#CBD3DC");}
  if(sp.panel){const p=sp.panel;L.strokes.push({x:p.x,y:p.y,w:p.w,h:p.h,r:12,lw:1,c:LINE});
    for(const g of sp.legend){R(g.dot.x,g.dot.y,g.dot.w,g.dot.h,g.dot.c);R(g.txt.x,g.txt.y,g.txt.w,g.txt.h,INK3);}
    R(p.rule.x,p.rule.y,p.rule.w,p.rule.h,"#E7ECF1");
    for(const r of sp.rows){R(r.name.x,r.name.y,r.name.w,r.name.h,INK2);R(r.num.x,r.num.y,r.num.w,r.num.h,r.num.err?ERR:INK,1);L.zones.push({x:r.num.x,y:r.num.y-r.num.h*.4,w:r.num.w,h:r.num.h*1.8});
      R(r.track.x,r.track.y,r.track.w,r.track.h,TRACK);L.zones.push({x:r.track.x,y:r.track.y,w:r.track.w,h:r.track.h});
      for(const s of r.segs)R(s.x,r.track.y,s.w,r.track.h,s.c,1);
      R(r.badge.x,r.badge.y,r.badge.w,r.badge.h,r.badge.err?ERR:INK3,r.badge.err);if(r.sep)R(r.sep.x,r.sep.y,r.sep.w,r.sep.h,"#EEF1F4");}}
  return L;}
