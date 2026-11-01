/* T2-B '장비 목록'(D105) — 가동률 화면의 줄 7개(장비 이름 자리 · 숫자 블록 · 24시간 트랙)가 먼저 깔리고, 트랙 안의 바쁜 구간이 자라 AOI 를 쓴다(쉬는 시간은 회색 트랙).
   장면은 _bars.js 의 barsListScene, 대기 동작은 BARS_IDLE 의 하나(지금 template: sway — 줄 흔들흔들 + '지금' 선) */
bootShell({sceneReveals:false,settleMs:500,fadeMs:600,make(ov,env,api){return barsListScene(ov,env,"sway");}});
