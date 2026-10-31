/* 입자 엔진(Worker + OffscreenCanvas) — baseline 장면의 경량판.
   달라진 점: ① 흐름장을 격자(24px)로 미리 계산해 120ms 마다만 갱신(입자마다 curl noise 4번 → 격자 조회) ② 팔레트 ≤ maxPal(Path2D 수)
   ③ 꼬리는 나는 입자만 · 느려지면(adaptive) 꼬리 생략 ④ dpr 상한 1 ⑤ 렌더 백엔드 path(Path2D) | pixel(Uint32 버퍼 · 반해상도 putImageData)
   ⑥ dataOnly(틀은 CSS 가, 입자는 데이터 몫만) ⑦ 숨은 탭이면 멈춤 */
function makeLib(mulberry){
  const P=new Uint8Array(512);{const p=[...Array(256).keys()],r=mulberry(5);for(let i=255;i>0;i--){const j=Math.floor(r()*(i+1));[p[i],p[j]]=[p[j],p[i]];}for(let i=0;i<512;i++)P[i]=p[i&255];}
  const g=(h,x,y)=>((h&1)?-x:x)+((h&2)?-y:y),L=(t,a,b)=>a+t*(b-a);
  function noise(x,y){let X=Math.floor(x),Y=Math.floor(y);x-=X;y-=Y;X&=255;Y&=255;const u=x*x*x*(x*(x*6-15)+10),v=y*y*y*(y*(y*6-15)+10),a=P[X]+Y,b=P[X+1]+Y;
    return L(v,L(u,g(P[a],x,y),g(P[b],x-1,y)),L(u,g(P[a+1],x,y-1),g(P[b+1],x-1,y-1)));}
  function curl(x,y,out){const e=.35,a=(noise(x,y+e)-noise(x,y-e))/(2*e),b=(noise(x+e,y)-noise(x-e,y))/(2*e);out[0]=a;out[1]=-b;}
  const mk=(w,h)=>{if(typeof OffscreenCanvas!=="undefined")return new OffscreenCanvas(w,h);const c=document.createElement("canvas");c.width=w;c.height=h;return c;};
  return{curl,rnd:mulberry,mk};
}
function engineCore(self,scene0,lib){
  let ctx,scene,running=false,paused=false,reduced=false,last=0;
  const S={t0:0,t:0,MIN:4000,real:0,rp:0,rpn:0,ri:0,tPh:0,loaded:false,v:0,vv:0,capA:.77,capR:0,capTau:800,planEnd:3300,complete:false,doneAt:0,revealAt:0,low:0,acc:0,accN:0};
  const plan=t=>{const x=Math.min(1,Math.max(0,(t-120)/(S.planEnd-120)));return 1-(1-x)*(1-x);};S.plan=plan;
  S.step=(now,dt)=>{const t=S.t=now-S.t0;
    const kk=1-Math.exp(-(now-S.tPh)/1700),rt=S.rp+(S.rpn-S.rp)*.85*kk;if(rt>S.real)S.real+=(rt-S.real)*Math.min(1,dt/140);
    const pl=plan(t),cap=S.loaded?1:S.capA*(1-Math.exp(-Math.max(0,t)/S.capTau))+S.capR*S.real,tg=S.loaded&&pl>=1?1.06:Math.min(pl,cap);
    if(reduced){if(tg>S.v)S.v=Math.min(1,tg);return;}
    const w=S.loaded?(S.t>S.MIN?26:18):10,n=dt>20?3:1,h=dt/1000/n;
    for(let i=0;i<n;i++){const a=w*w*(tg-S.v)-2*w*S.vv;S.vv+=a*h;const nv=S.v+S.vv*h;if(nv<S.v)S.vv=0;else S.v=Math.min(1,nv);}};
  self.onmessage=e=>{const m=e.data;
    if(m.type==="init"){const c=m.canvas;const bw=m.render==="pixel"?Math.ceil(m.w/2):Math.round(m.w*m.dpr),bh=m.render==="pixel"?Math.ceil(m.h/2):Math.round(m.h*m.dpr);
      c.width=bw;c.height=bh;ctx=c.getContext("2d");if(m.render!=="pixel")ctx.setTransform(m.dpr,0,0,m.dpr,0,0);
      reduced=m.reduced;S.MIN=m.min;S.t0=m.epoch-performance.timeOrigin;last=performance.now();S.tPh=last;
      scene=scene0(ctx,m.w,m.h,m.dpr,S,lib,m);running=true;loop();}
    else if(m.type==="phase"){S.ri=Math.max(S.ri,m.i);S.rp=m.p;S.rpn=m.pn;S.tPh=performance.now();}
    else if(m.type==="loaded"){S.loaded=true;}
    else if(m.type==="pause"){paused=true;}
    else if(m.type==="resume"){if(paused){paused=false;last=performance.now();if(running)loop();}}
    else if(m.type==="stop"){running=false;}};
  function loop(){if(!running||paused)return;const now=performance.now(),dt=Math.min(48,now-last);last=now;
    /* 적응: 최근 20프레임 평균 간격이 24ms 를 넘으면 꼬리 생략(low 1), 40ms 넘으면 흐름장 갱신도 줄임(low 2) */
    S.acc+=dt;S.accN++;if(S.accN>=20){const m=S.acc/S.accN;S.low=m>40?2:m>24?1:S.low===2&&m>24?1:m<=20?0:S.low;S.acc=0;S.accN=0;}
    S.step(now,dt);scene.frame(now,dt,reduced);
    if(S.loaded&&S.complete&&!S.doneAt)S.doneAt=now;
    if(S.doneAt&&S.t>=S.MIN&&!S.revealAt){S.revealAt=now;self.postMessage({type:"reveal",t:S.t});}
    if(S.revealAt&&now-S.revealAt>700){running=false;return;}
    self.requestAnimationFrame(loop);}
}
function engineScene(ctx,W,H,dpr,S,lib,m){
  const rnd=lib.rnd(77),BG=m.bg||"#F4F6F8",HOV="#9DB4CE",TRANS=!!m.transparent,PIX=m.render==="pixel",MAXP=m.maxPal||12,TRAIL=m.trails!==false;
  const N=m.N,SZMAX=Math.max(1.6,Math.min(2.4,W/700));
  const F=()=>new Float32Array(N),X=F(),Y=F(),VX=F(),VY=F(),PX=F(),PY=F(),TX=F(),TY=F(),RK=F(),SZ=F(),SP=F(),FX=F(),FY=F(),FVX=F(),FVY=F(),FT=F(),FD=F(),
        HX=F(),HY=F(),HA=F(),HW=F(),HP=F(),D=new Uint8Array(N),C=new Uint16Array(N),ST=new Uint8Array(N);
  let PAL=["#5A6673","#2E6BA8","#8FB8E0","#AEB8C4"],has=false,step=0,NS=0,ND=1,nSet=0,nStr=0,nDat=0,relaunched=false;
  for(let j=0;j<N;j++){X[j]=PX[j]=rnd()*W*1.25-W*.25;Y[j]=PY[j]=rnd()*H;SP[j]=.7+rnd()*.8;VX[j]=1.4*SP[j];C[j]=j%PAL.length;RK[j]=2;SZ[j]=2;
    HA[j]=3+rnd()*6;HW[j]=(2*Math.PI)/(2600+rnd()*1800);HP[j]=rnd()*6.283;}
  const ow=Math.max(1,Math.ceil(W)),oh=Math.max(1,Math.ceil(H)),off=lib.mk(ow,oh),o=off.getContext("2d",{willReadFrequently:true});
  const hex=s=>{s=String(s||"");if(s[0]==="#")return s.length===4?"#"+s[1]+s[1]+s[2]+s[2]+s[3]+s[3]:s.slice(0,7).toLowerCase();return"#5a6673";};
  const rgbOf=h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
  /* 흐름장 격자 */
  const CELL=24,gw=Math.ceil(W/CELL)+1,gh=Math.ceil(H/CELL)+1,GX=new Float32Array(gw*gh),GY=new Float32Array(gw*gh),fs=1/(W*.22),cv=[0,0];let gAt=-1e9;
  const gridUpdate=now=>{const tt=now*.00006;for(let gy=0;gy<gh;gy++)for(let gx=0;gx<gw;gx++){lib.curl(gx*CELL*fs+tt,gy*CELL*fs,cv);const i=gy*gw+gx;GX[i]=cv[0];GY[i]=cv[1];}gAt=now;};
  function build(L){
    const cols=new Map();for(const it of [...L.rects,...L.strokes,...(L.arcs||[]),...(L.lines||[])]){if(m.dataOnly&&!it.d)continue;const h=hex(it.c);cols.set(h,(cols.get(h)||0)+1);}
    const pal=[...cols.entries()].sort((a,b)=>b[1]-a[1]).slice(0,MAXP).map(e=>e[0]);if(!pal.length)pal.push("#5a6673");
    const prgb=pal.map(rgbOf),memo=new Map();
    const near=(r,g,b)=>{const k=(r<<16)|(g<<8)|b;let v=memo.get(k);if(v!==undefined)return v;let bd=1e9;v=0;for(let i=0;i<prgb.length;i++){const q=prgb[i],d=(q[0]-r)**2+(q[1]-g)**2+(q[2]-b)**2;if(d<bd){bd=d;v=i;}}memo.set(k,v);return v;};
    const draw=dat=>{o.clearRect(0,0,ow,oh);
      for(const r of L.rects)if(!!r.d===dat){o.fillStyle=r.c;o.fillRect(r.x,r.y,r.w,r.h);}
      if(!dat)for(const s of L.strokes){const lw=s.lw||1;o.strokeStyle=s.c;o.lineWidth=lw;o.beginPath();
        if(o.roundRect&&s.r)o.roundRect(s.x+lw/2,s.y+lw/2,Math.max(0,s.w-lw),Math.max(0,s.h-lw),Math.min(s.r,s.w/2,s.h/2));else o.rect(s.x+lw/2,s.y+lw/2,Math.max(0,s.w-lw),Math.max(0,s.h-lw));o.stroke();}
      for(const a of L.arcs||[])if(!!a.d===dat){o.beginPath();o.arc(a.x,a.y,a.r,0,Math.PI*2);o.strokeStyle=a.c;o.lineWidth=a.lw||1;o.stroke();}
      for(const l of L.lines||[])if(!!l.d===dat){o.strokeStyle=l.c;o.lineWidth=l.lw||1;o.lineCap="round";o.beginPath();l.pts.forEach((q,i)=>i?o.lineTo(q[0],q[1]):o.moveTo(q[0],q[1]));o.stroke();}
      return o.getImageData(0,0,ow,oh).data;};
    const iS=m.dataOnly?null:draw(false),iD=draw(true);o.clearRect(0,0,ow,oh);
    if(!step){let ink=0;for(let y=0;y<oh;y+=2)for(let x=0;x<ow;x+=2){const i=(y*ow+x)*4+3;if((iS&&iS[i]>=110)||iD[i]>=110)ink+=4;}step=Math.max(1.5,Math.min(8,Math.sqrt(ink/(N*1.1))));}
    const pick=(img,st)=>{const out=[];if(!img)return out;for(let y0=0;y0<oh;y0+=st)for(let x0=0;x0<ow;x0+=st){let bi=-1,ba=109,bx=0,by=0;
        for(let y=Math.floor(y0);y<Math.min(oh,Math.floor(y0+st));y++)for(let x=Math.floor(x0);x<Math.min(ow,Math.floor(x0+st));x++){const i=(y*ow+x)*4;if(img[i+3]>ba){ba=img[i+3];bi=i;bx=x;by=y;}}
        if(bi<0)continue;out.push(bx+.5+(rnd()-.5)*.4,by+.5+(rnd()-.5)*.4,near(img[bi],img[bi+1],img[bi+2]),Math.min(SZMAX,st*.72));}return out;};
    return{pal,S:pick(iS,step),D:pick(iD,step)};}
  const zoneOf=(L,x,y)=>{let best=null,ba=1e18;for(const z of L.zones||[]){if(x>=z.x-1&&x<=z.x+z.w+1&&y>=z.y-1&&y<=z.y+z.h+1){const a=z.w*z.h;if(a<ba){ba=a;best=z;}}}return best;};
  /* 렌더 백엔드 */
  let lay,lc,img,buf,layer,bw,bh,PC,PT,PH,bgU;
  const u32=(h,a)=>{const c=rgbOf(h);return((a<<24)|(c[2]<<16)|(c[1]<<8)|c[0])>>>0;};
  const mix=(h,b,t)=>{const c=rgbOf(h),d=rgbOf(b);return"#"+[0,1,2].map(i=>Math.round(c[i]+(d[i]-c[i])*t).toString(16).padStart(2,"0")).join("");};
  if(PIX){bw=Math.ceil(W/2);bh=Math.ceil(H/2);img=ctx.createImageData(bw,bh);buf=new Uint32Array(img.data.buffer);layer=new Uint32Array(bw*bh);bgU=TRANS?0:u32(BG,255);layer.fill(bgU);}
  else{lay=lib.mk(Math.max(1,Math.round(W*dpr)),Math.max(1,Math.round(H*dpr)));lc=lay.getContext("2d");lc.scale(dpr,dpr);}
  const setPal=()=>{if(PIX){PC=PAL.map(h=>u32(h,255));PT=PAL.map(h=>TRANS?u32(h,110):u32(mix(h,BG,.55),255));PH=TRANS?u32(HOV,160):u32(mix(HOV,BG,.3),255);}};
  const plot=(x,y,c)=>{const px=x>>1,py=y>>1;if(px>=0&&px<bw&&py>=0&&py<bh)buf[py*bw+px]=c;};
  const bake=()=>{if(PIX){layer.fill(bgU);for(let j=0;j<N;j++)if(ST[j]===2){const px=TX[j]>>1,py=TY[j]>>1;if(px>=0&&px<bw&&py>=0&&py<bh)layer[py*bw+px]=PC[C[j]];}}
    else{lc.clearRect(0,0,W,H);const ps=PAL.map(()=>new Path2D());for(let j=0;j<N;j++)if(ST[j]===2)ps[C[j]].rect(TX[j]-SZ[j]/2,TY[j]-SZ[j]/2,SZ[j],SZ[j]);for(let c=0;c<PAL.length;c++){lc.fillStyle=PAL[c];lc.fill(ps[c]);}}
    nSet=nStr=nDat=0;for(let j=0;j<N;j++)if(ST[j]===2){nSet++;if(D[j])nDat++;else nStr++;}};
  const fly=(j,now,d)=>{FX[j]=X[j];FY[j]=Y[j];FT[j]=now;FD[j]=d;};
  function assign(L){
    const b=build(L);PAL=b.pal;setPal();const sp=b.S,dp=b.D,ns=sp.length/4,nd=dp.length/4;if(!ns&&!nd)return;
    let nS=Math.round(N*ns/(ns+nd));if(ns&&!nS)nS=1;if(nd&&nS===N)nS=N-1;
    const pick=(n,tot)=>{const a=[...Array(tot).keys()];for(let i=tot-1;i>0;i--){const r=Math.floor(rnd()*(i+1));[a[i],a[r]]=[a[r],a[i]];}const o=[];for(let i=0;o.length<n&&tot;i++)o.push(a[i%tot]);return o;};
    const sP=pick(nS,ns),dP=pick(N-nS,nd);let a0=1e9,a1=-1e9,b0=1e9,b1=-1e9;const raw=new Float32Array(N);
    for(let j=0;j<N;j++){const dd=j>=sP.length?1:0,k=dd?dP[j-sP.length]:sP[j],src=dd?dp:sp;if(k===undefined)continue;
      const tx=src[k*4],ty=src[k*4+1];TX[j]=tx;TY[j]=ty;C[j]=src[k*4+2];D[j]=dd;SZ[j]=src[k*4+3];
      raw[j]=dd?ty/H*.7+tx/W*.26+rnd()*.04:ty/H*.86+tx/W*.1+rnd()*.04;
      if(dd){b0=Math.min(b0,raw[j]);b1=Math.max(b1,raw[j]);const z=zoneOf(L,tx,ty);if(z){HX[j]=z.x+rnd()*z.w;HY[j]=z.y+z.h*(.15+.7*rnd());}else{HX[j]=tx+(rnd()-.5)*W*.05;HY[j]=ty+(rnd()-.5)*4;}}
      else{a0=Math.min(a0,raw[j]);a1=Math.max(a1,raw[j]);}}
    NS=0;for(let j=0;j<N;j++){RK[j]=D[j]?.79+.2*(raw[j]-b0)/Math.max(1e-6,b1-b0):.76*(raw[j]-a0)/Math.max(1e-6,a1-a0);if(!D[j])NS++;}
    NS=Math.max(1,NS);ND=Math.max(1,N-NS);has=true;bake();}
  assign(m.L);
  if(!TRANS&&!PIX){ctx.fillStyle=BG;ctx.fillRect(0,0,W,H);}
  return{count:N,
    frame(now,dt,red){
      const v=S.v,k=dt/16.7,ent=Math.min(1,Math.max(0,S.t)/380),deadline=S.t0+3850,fl=1,low=S.low,trails=TRAIL&&low<1;
      if(now-gAt>(low>=2?360:120))gridUpdate(now);
      let lines,dots,fresh,hl,hd;
      if(PIX){buf.set(layer);}
      else{if(TRANS)ctx.clearRect(0,0,W,H);else{ctx.globalAlpha=red?1:.32;ctx.fillStyle=BG;ctx.fillRect(0,0,W,H);ctx.globalAlpha=1;}
        lines=PAL.map(()=>new Path2D());dots=PAL.map(()=>new Path2D());fresh=PAL.map(()=>new Path2D());hl=new Path2D();hd=new Path2D();}
      let nf=0;
      if(S.loaded&&has&&!relaunched){relaunched=true;for(let j=0;j<N;j++){if(ST[j]!==1)continue;const s=Math.min(1,(now-FT[j])/FD[j]);if(FD[j]*(1-s)<=340)continue;
        const q=1-s,e1=12*s*q*q,g1=q*(1-3*s);FVX[j]=((TX[j]-FX[j])*e1+FVX[j]*FD[j]*g1)/FD[j];FVY[j]=((TY[j]-FY[j])*e1+FVY[j]*FD[j]*g1)/FD[j];fly(j,now,280+rnd()*60);}}
      const wind=x=>2.2*Math.sin(now*.0012-x*.012);
      const seg=(p,j)=>{let ax=PX[j],ay=PY[j];const dx=X[j]-ax,dy=Y[j]-ay,l=Math.hypot(dx,dy);if(l>14){ax=X[j]-dx*14/l;ay=Y[j]-dy*14/l;}p.moveTo(ax,ay);p.lineTo(X[j]+.01,Y[j]);};
      const tail=(j,c)=>{const dx=X[j]-PX[j],dy=Y[j]-PY[j];plot(X[j]-dx*.6,Y[j]-dy*.6,c);plot(X[j]-dx*1.2,Y[j]-dy*1.2,c);};
      const settle=j=>{ST[j]=2;X[j]=TX[j];Y[j]=TY[j];nSet++;if(D[j])nDat++;else nStr++;nf++;
        if(PIX){const px=TX[j]>>1,py=TY[j]>>1;if(px>=0&&px<bw&&py>=0&&py<bh)layer[py*bw+px]=PC[C[j]];}else fresh[C[j]].rect(TX[j]-SZ[j]/2,TY[j]-SZ[j]/2,SZ[j],SZ[j]);};
      for(let j=0;j<N;j++){
        if(ST[j]===2)continue;PX[j]=X[j];PY[j]=Y[j];
        if(ST[j]===0&&v>=RK[j]){
          if(red){settle(j);continue;}
          ST[j]=1;FVX[j]=VX[j]/16.7;FVY[j]=VY[j]/16.7;
          let d=S.loaded?(now>deadline?200+rnd()*90:now>deadline-250?260+rnd()*120:320+rnd()*160):440+rnd()*220;if(now<deadline)d=Math.min(d,Math.max(220,deadline-now));fly(j,now,d);}
        if(ST[j]===0){
          const an=D[j]?Math.min(1,Math.max(0,(v-.45)/.25)):0;
          if(red){if(an>0){if(PIX)plot(HX[j],HY[j],PH);else hd.rect(HX[j]-SZ[j]/2,HY[j]-SZ[j]/2,SZ[j],SZ[j]);}continue;}
          if(X[j]<-2&&an<.3){X[j]+=VX[j]*k*fl;PX[j]=X[j];continue;}
          if(an<1){const gi=Math.min(gh-1,Math.max(0,(Y[j]/CELL)|0))*gw+Math.min(gw-1,Math.max(0,(X[j]/CELL)|0)),r=.07*(1-an)*k;
            VX[j]+=((GX[gi]*2.2+1.25)*SP[j]*fl-VX[j])*r;VY[j]+=(GY[gi]*2.2*SP[j]*fl-VY[j])*r;}
          if(an>0){const gx=HX[j]+HA[j]*Math.sin(now*HW[j]+HP[j])+wind(HX[j]),gy=HY[j]+.9*Math.sin(now*HW[j]*1.37+HP[j]*2);
            VX[j]+=(gx-X[j])*.011*an*k;VY[j]+=(gy-Y[j])*.011*an*k;const dm=Math.pow(1-.13*an,k);VX[j]*=dm;VY[j]*=dm;
            const vm=Math.hypot(VX[j],VY[j]);if(vm>9){VX[j]*=9/vm;VY[j]*=9/vm;}}
          X[j]+=VX[j]*k;Y[j]+=VY[j]*k;
          if(an<.5){if(X[j]>W+6){X[j]=-6-rnd()*40;PX[j]=X[j];Y[j]=PY[j]=an>0?HY[j]+(rnd()-.5)*H*.08:rnd()*H;VX[j]=1.4*SP[j];}if(Y[j]<-6){Y[j]+=H+12;PY[j]=Y[j];}else if(Y[j]>H+6){Y[j]-=H+12;PY[j]=Y[j];}}
          if(PIX){if(D[j]){plot(X[j],Y[j],PH);if(trails)tail(j,PH);}else{plot(X[j],Y[j],PT[C[j]]);if(trails)tail(j,PT[C[j]]);}}
          else{if(D[j]){if(trails)seg(hl,j);if(an>.6||!trails)hd.rect(X[j]-SZ[j]*.4,Y[j]-SZ[j]*.4,SZ[j]*.8,SZ[j]*.8);}else{if(trails)seg(lines[C[j]],j);else dots[C[j]].rect(X[j]-SZ[j]*.4,Y[j]-SZ[j]*.4,SZ[j]*.8,SZ[j]*.8);}}
          continue;}
        const s=Math.min(1,(now-FT[j])/FD[j]),q=1-s,E=1-q*q*q*(1+3*s),g=s*q*q;
        X[j]=FX[j]+(TX[j]-FX[j])*E+FVX[j]*FD[j]*g;Y[j]=FY[j]+(TY[j]-FY[j])*E+FVY[j]*FD[j]*g;
        if(s>=1){settle(j);continue;}
        if(PIX){plot(X[j],Y[j],PC[C[j]]);if(trails)tail(j,PT[C[j]]);}else{if(trails)seg(lines[C[j]],j);dots[C[j]].rect(X[j]-SZ[j]/2,Y[j]-SZ[j]/2,SZ[j],SZ[j]);}}
      if(PIX){ctx.putImageData(img,0,0);}
      else{if(nf)for(let c=0;c<PAL.length;c++){lc.fillStyle=PAL[c];lc.fill(fresh[c]);}
        ctx.drawImage(lay,0,0,W,H);ctx.lineWidth=1;ctx.lineCap="round";
        ctx.strokeStyle=HOV;ctx.globalAlpha=.4*ent;if(trails)ctx.stroke(hl);ctx.globalAlpha=.75;ctx.fillStyle=HOV;ctx.fill(hd);ctx.globalAlpha=1;
        for(let c=0;c<PAL.length;c++){if(trails){ctx.strokeStyle=PAL[c];ctx.globalAlpha=.38*ent;ctx.stroke(lines[c]);ctx.globalAlpha=1;}ctx.fillStyle=PAL[c];ctx.fill(dots[c]);}}
      S.complete=has&&nSet>=N;
    }};
}
/* 메인 스레드 쪽: 캔버스 요소 + Worker(blob) — OffscreenCanvas 가 없으면 같은 장면을 메인 스레드에서 */
function workerScene(ov,env,api,cfg){
  const {W,H}=env,cv=document.createElement("canvas");
  cv.style.cssText=`position:absolute;left:0;top:0;display:block;width:${W}px;height:${H}px;${cfg.render==="pixel"?"image-rendering:pixelated;":""}transition:opacity .5s ease-out;will-change:opacity`;
  ov.insertBefore(cv,ov.firstChild);
  const dpr=Math.min(cfg.dprMax||1,window.devicePixelRatio||1);
  const init={type:"init",w:W,h:H,dpr,reduced:env.red,min:env.MIN,epoch:env.epoch,bg:env.bg,kind:env.kind,L:layoutDraw(W,H,env.kind),
    N:cfg.N,render:cfg.render||"path",trails:cfg.trails!==false,maxPal:cfg.maxPal||12,dataOnly:!!cfg.dataOnly,transparent:!!cfg.transparent};
  const onMsg=d=>{if(d&&d.type==="reveal")api.reveal();};
  let port;
  try{
    if(!cv.transferControlToOffscreen||typeof Worker==="undefined"||typeof OffscreenCanvas==="undefined")throw 0;
    const src=`"use strict";const mulberry=${mulberry};const makeLib=${makeLib};const engineScene=${engineScene};(${engineCore})(self,engineScene,makeLib(mulberry));`;
    const url=URL.createObjectURL(new Blob([src],{type:"text/javascript"})),wk=new Worker(url);URL.revokeObjectURL(url);
    const offc=cv.transferControlToOffscreen();wk.onmessage=e=>onMsg(e.data);wk.onerror=()=>api.reveal();
    wk.postMessage({...init,canvas:offc},[offc]);port={post:m=>wk.postMessage(m),kill:()=>wk.terminate()};
  }catch(e){
    const shim={postMessage:m=>setTimeout(()=>onMsg(m)),requestAnimationFrame:f=>requestAnimationFrame(f),onmessage:null};
    engineCore(shim,engineScene,makeLib(mulberry));shim.onmessage({data:{...init,canvas:cv}});
    port={post:m=>shim.onmessage({data:m}),kill:()=>shim.onmessage({data:{type:"stop"}})};
  }
  return{post:port.post,kill:port.kill,reveal(){cv.style.opacity="0";}};
}
