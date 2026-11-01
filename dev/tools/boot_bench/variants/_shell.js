/* 공통 껍데기 — 덮개 · 단계 글자(DOM, 합성 스레드 애니메이션) · AOI_BOOT API · 4초 최소 · 걷힘(opacity 만). 장면은 make() 가 만든다. */
var prev=document.getElementById("aoi-boot");if(prev&&prev.parentNode)prev.parentNode.removeChild(prev);
window.AOI_BOOT=null;
const MIN=4000,LABELS=["결과 파일 여는 중","데이터 읽는 중","기록 펼치는 중","계산 중","화면 그리는 중"],PW=[.08,.34,.12,.36,.10],TH=[];
{let a=0;for(const w of PW){TH.push(a);a+=w;}}
const FONT='"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",sans-serif';
function mulberry(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
/* 창 크기에 맞춘 고정 대시보드 모양(baseline 의 fixedLayout 과 같은 자리) — 모든 변형이 같은 틀을 쓴다 */
function layoutSpec(W,H,rnd){
  const SEG=[["#2E6BA8",.62],["#8FB8E0",.14],["#7A5BB5",.08],["#C5453C",.07],["#E8B7B3",.09]];
  const seg=()=>{let u=rnd(),i=0;while(i<SEG.length-1&&u>SEG[i][1]){u-=SEG[i][1];i++;}return SEG[i][0];};
  const pad=Math.round(Math.max(20,Math.min(W*.03,44))),gap=Math.round(pad*.6),y0=Math.round(pad*1.2),kh=Math.round(Math.max(88,Math.min(H*.17,140))),cw=(W-pad*2-gap*2)/3;
  const cards=[];for(let i=0;i<3;i++){const x=pad+i*(cw+gap),ix=x+Math.min(22,cw*.08);
    cards.push({x,y:y0,w:cw,h:kh,ix,label:{x:ix,y:y0+kh*.17,w:cw*.24,h:kh*.075},num:{x:ix,y:y0+kh*.33,w:cw*(.16+.06*((i*7)%3)),h:kh*.27,err:i===1},
      l1:{x:ix,y:y0+kh*.72,w:cw*.62,h:kh*.055},l2:{x:ix,y:y0+kh*.84,w:cw*.44,h:kh*.055}});}
  const capH=Math.max(34,H*.06),py=y0+kh+pad,ph=H-py-capH-pad*.4,rows=[],legend=[];let panel=null;
  if(ph>70){panel={x:pad,y:py,w:W-pad*2,h:ph};
    const ix=pad+Math.min(22,W*.016),rh=Math.round(Math.max(30,Math.min(44,H*.052))),lx=ix+Math.max(90,W*.11),rx=W-pad-Math.max(70,W*.07);
    let gx=ix;for(const [c] of SEG){legend.push({dot:{x:gx,y:py+rh*.42,w:rh*.24,h:rh*.24,c},txt:{x:gx+rh*.34,y:py+rh*.46,w:rh*.9,h:rh*.16}});gx+=rh*1.6;}
    panel.rule={x:pad,y:py+rh*.95,w:W-pad*2,h:1};
    const n=Math.max(1,Math.floor((ph-rh*1.2)/rh));
    for(let k=0;k<n;k++){const y=py+rh*1.2+k*rh,mid=y+rh/2,th=Math.max(8,rh*.4),uw=rh*.8,segs=[];
      let p=rnd()*.18;while(p<.92){const w=.015+rnd()*.07;if(p+w>1)break;segs.push({x:lx+(rx-lx)*p,w:(rx-lx)*w,c:seg()});p+=w+.02+rnd()*.12;}
      rows.push({y,mid,name:{x:ix,y:mid-rh*.09,w:rh*1.6,h:rh*.18},num:{x:lx-uw-rh*.5,y:mid-rh*.11,w:uw,h:rh*.22,err:k%4===1},track:{x:lx,y:mid-th/2,w:rx-lx,h:th},segs,
        badge:k%3===0?{x:rx+rh*.6,y:mid-rh*.09,w:rh*.5,h:rh*.18,err:true}:{x:rx+rh*.6,y:mid-1,w:rh*.4,h:2,err:false},sep:k<n-1?{x:pad,y:y+rh,w:W-pad*2,h:1}:null});}}
  return{pad,cards,panel,legend,rows,capH};}
function bootShell(o){
  try{
    const W=Math.max(1,window.innerWidth||document.documentElement.clientWidth||0),H=Math.max(1,window.innerHeight||document.documentElement.clientHeight||0);
    if(W<240||H<200||!document.body)return;
    let red=false;try{red=!!(window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches);}catch(e){}
    const bg=(getComputedStyle(document.documentElement).getPropertyValue("--bg")||"").trim()||"#F4F6F8";
    const ov=document.createElement("div");ov.id="aoi-boot";ov.setAttribute("aria-hidden","true");
    const fade=o.fadeMs||600;
    ov.style.cssText=`position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:2147483000;background:${bg};pointer-events:none;overflow:hidden;opacity:1;transition:opacity ${fade}ms cubic-bezier(.33,0,.15,1)`;
    document.body.appendChild(ov);
    /* 단계 글자 + 진행선: DOM. 글자 교체는 WAAPI(transform · opacity), 진행선은 scaleX 전환 — 둘 다 합성 스레드 */
    const cfs=Math.max(10,Math.min(14,W*.0118)),cx=Math.max(16,W*.024),cy=Math.max(18,H*.05),lw=Math.max(60,W*.08);
    const cap=document.createElement("div");cap.style.cssText=`position:absolute;left:${cx}px;bottom:${cy-cfs*.9}px;display:flex;align-items:center;gap:${cfs*.9}px;font:600 ${cfs}px ${FONT};color:#46525E;opacity:0;transition:opacity .3s ease-out;will-change:opacity`;
    const lab=document.createElement("span");lab.style.cssText=`position:relative;display:inline-block;height:${cfs*1.4}px;line-height:${cfs*1.4}px;overflow:hidden`;
    const bar=document.createElement("span");bar.style.cssText=`position:relative;display:inline-block;width:${lw}px;height:2px;background:#DCE2E9`;
    const fill=document.createElement("i");fill.style.cssText="position:absolute;left:0;top:0;width:100%;height:100%;background:#2E6BA8;transform:scaleX(0);transform-origin:0 50%;transition:transform .45s cubic-bezier(.2,.7,.2,1)";
    bar.appendChild(fill);cap.appendChild(lab);cap.appendChild(bar);ov.appendChild(cap);
    let li=-1,curS=null;const setLabel=i=>{if(i===li)return;const old=curS;li=i;const s=document.createElement("span");s.textContent=LABELS[i];s.style.cssText="display:inline-block;white-space:nowrap";lab.appendChild(s);curS=s;
      if(red){if(old)old.remove();return;}
      if(old){old.style.position="absolute";old.style.left="0";old.animate([{transform:"translateY(0)",opacity:1},{transform:`translateY(-${cfs*.45}px)`,opacity:0}],{duration:240,easing:"cubic-bezier(.33,1,.68,1)",fill:"forwards"}).onfinish=()=>old.remove();}
      s.animate([{transform:`translateY(${cfs*.45}px)`,opacity:0},{transform:"translateY(0)",opacity:1}],{duration:240,easing:"cubic-bezier(.33,1,.68,1)"});};
    const setFill=p=>{fill.style.transform=`scaleX(${Math.max(0,Math.min(1,p))})`;};
    requestAnimationFrame(()=>{cap.style.opacity="1";setLabel(0);setFill(.04);});
    /* 계획 단계(4초 계획 곡선) — 실제 단계보다 앞서지 않는다 */
    let real=0;const planT=[0,120+PW[0]*3200,120+(TH[1]+PW[1])*3200,120+(TH[2]+PW[2])*3200,120+(TH[3]+PW[3])*3200];
    const tick=()=>{if(gone)return;const t=performance.now();let i=0;while(i<4&&t>=planT[i+1])i++;setLabel(Math.min(i,real));if(!loadedAt)setFill(Math.min(.9,.04+t/MIN*.6));
      if(!loadedAt||t<MIN+1000)setTimeout(tick,200);};setTimeout(tick,200);
    const env={W,H,red,bg,kind:document.documentElement.getAttribute("data-boot")||"",epoch:performance.timeOrigin||Date.now()-performance.now(),MIN,LABELS,TH,PW};
    let gone=false,loadedAt=0,fallback=0,revealed=false;const after=[];let scene=null;
    const finish=()=>{if(gone)return;gone=true;clearTimeout(fallback);try{scene&&scene.kill&&scene.kill();}catch(e){}if(ov.parentNode)ov.parentNode.removeChild(ov);window.AOI_BOOT=null;
      for(const f of after.splice(0))setTimeout(()=>{try{f();}catch(e){}},0);};
    const reveal=()=>{if(revealed||gone)return;revealed=true;cap.style.opacity="0";try{scene&&scene.reveal&&scene.reveal();}catch(e){}ov.style.opacity="0";setTimeout(finish,fade+80);};
    const api={reveal,env,ov};
    scene=o.make(ov,env,api)||{};
    window.AOI_BOOT={
      phase(i){if(gone)return;real=Math.max(real,i);try{scene.post&&scene.post({type:"phase",i,p:TH[i]||0,pn:(TH[i]||0)+(PW[i]||0)});}catch(e){}},
      done(){if(gone||loadedAt)return;loadedAt=performance.now();real=4;setFill(1);try{scene.post&&scene.post({type:"loaded"});}catch(e){}
        const left=Math.max(0,MIN-performance.now());
        if(!o.sceneReveals)setTimeout(reveal,Math.max(left,o.settleMs||400));
        fallback=setTimeout(reveal,left+2500);},
      later(f){if(gone)setTimeout(f,0);else after.push(f);},
      abort(){finish();}};
    document.addEventListener("visibilitychange",()=>{try{scene.post&&scene.post({type:document.hidden?"pause":"resume"});}catch(e){}});
  }catch(e){try{const x=document.getElementById("aoi-boot");if(x&&x.parentNode)x.parentNode.removeChild(x);}catch(_){}window.AOI_BOOT=null;try{console.warn("시작 화면을 띄우지 못했습니다(화면은 그대로 열립니다):",e);}catch(_){}}
}
