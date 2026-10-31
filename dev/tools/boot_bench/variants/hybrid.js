/* V4 하이브리드 — 틀은 CSS 스켈레톤(1막), 데이터 몫(숫자 블록 · 막대 구간)만 입자 ≤ 1,800 개가 날아와 앉는다(투명 캔버스, Worker) */
bootShell({sceneReveals:true,fadeMs:600,make(ov,env,api){const f=cssFrame(ov,env,{data:false});
  const w=workerScene(ov,env,api,{N:Math.max(400,Math.round(Math.min(1800,env.W*env.H/1100))),render:"path",maxPal:8,dprMax:1,dataOnly:true,transparent:true});
  return{post(m){f.post(m);w.post(m);},kill(){w.kill();},reveal(){w.reveal();}};}});
