/* T2-B 대기 동작 W3 점등 — 구간이 읽는 순서로 하나씩 밝아졌다 돌아온다(데이터가 차례로 들어온다) */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){return barsListScene(ov,env,"glow");}});
