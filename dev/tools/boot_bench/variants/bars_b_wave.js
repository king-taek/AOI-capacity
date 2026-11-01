/* T2-B 대기 동작 W1 파도 — 글자 구간이 왼→오른으로 살짝 들렸다 내려온다(열마다 위상) */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){return barsListScene(ov,env,"wave");}});
