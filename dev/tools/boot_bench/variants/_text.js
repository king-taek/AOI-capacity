/* 'AOI' 글자 장면 공통: 가운데 큰 글자 영역, 글꼴은 시스템(바깥 요청 0). 전부 합성 스레드(transform · opacity · clip-path), 프레임마다 JS 0 */
const TXT={INK:"#16202B",INK2:"#5A6673",INK3:"#AEB8C4",LINE:"#D3DAE2",ACC:"#2E6BA8",ACC2:"#8FB8E0",ERR:"#C5453C",WAIT:"#9DB4CE"};
function textStage(ov,env,css){
  const {W,H,red}=env,root=document.createElement("div");root.className="tx"+(red?" red":"");
  root.style.cssText=`position:absolute;left:0;top:0;width:${W}px;height:${H}px;overflow:hidden;font-family:${FONT}`;
  const st=document.createElement("style");st.textContent=`#aoi-boot .tx *{box-sizing:border-box}\n#aoi-boot .tx.red *{animation:none!important;transition:none!important;opacity:1}\n`+css;root.appendChild(st);
  ov.insertBefore(root,ov.firstChild);
  const fs=Math.round(Math.max(96,Math.min(W*.19,H*.34)));   /* 글자 크기 */
  return{root,fs,cx:W/2,cy:H*.46};
}
