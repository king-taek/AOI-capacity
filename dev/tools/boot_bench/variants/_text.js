/* 'AOI' 글자 장면 공통: 가운데 큰 글자 영역, 글꼴은 시스템(바깥 요청 0). 전부 합성 스레드(transform · opacity · clip-path), 프레임마다 JS 0 */
const TXT={INK:"#16202B",INK2:"#5A6673",INK3:"#AEB8C4",LINE:"#D3DAE2",ACC:"#2E6BA8",ACC2:"#8FB8E0",ERR:"#C5453C",WAIT:"#9DB4CE"};
function textStage(ov,env,css){
  const {W,H,red}=env,root=document.createElement("div");root.className="tx"+(red?" red":"");
  root.style.cssText=`position:absolute;left:0;top:0;width:${W}px;height:${H}px;overflow:hidden;font-family:${FONT}`;
  /* 움직임 줄이기: 완성 그림을 바로(ANIM-01, 11/25) — '.tx.red *' 는 장면 규칙(.tk{opacity:0} · .f{scaleX(0)})과 선택자 힘이 같아 뒤에 오는 장면 규칙이 이겼다(4초 동안 빈 바탕).
     같은 요소를 한 단계 더 긴 선택자로 다시 적는다 */
  const st=document.createElement("style");st.textContent=`#aoi-boot .tx *{box-sizing:border-box}\n#aoi-boot .tx.red *{animation:none!important;transition:none!important;opacity:1}\n`+css+
    `\n#aoi-boot .tx.red .tk,#aoi-boot .tx.red .nm,#aoi-boot .tx.red .num,#aoi-boot .tx.red .sep{opacity:1}\n#aoi-boot .tx.red .tk>.f{transform:none}\n`;root.appendChild(st);
  ov.insertBefore(root,ov.firstChild);
  const fs=Math.round(Math.max(96,Math.min(W*.19,H*.34)));   /* 글자 크기 */
  return{root,fs,cx:W/2,cy:H*.46};
}
