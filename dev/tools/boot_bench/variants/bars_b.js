/* T2-B '장비 목록'(D105) — 가동률 화면의 줄 7개(장비 이름 자리 · 숫자 블록 · 24시간 트랙)가 먼저 깔리고, 트랙 안의 바쁜 구간이 자라 AOI 를 쓴다(쉬는 시간은 회색 트랙).
   장면은 _bars.js 의 barsListScene, 대기 동작은 BARS_IDLE 의 하나 — 현택 11/1 결정 "glow"(점등: 구간이 읽는 순서로 차례로 밝아짐).
   걷힘(11/25 ANIM-02): 장면 0.16초 → 바탕은 0.1초 뒤부터 0.4초(곡선 .16,1,.3,1). 4초 전에 끝난 로딩은 걷히기 0.9초 전까지 점등을 잇다 색이 앉는다(ANIM-03) */
bootShell({sceneReveals:false,settleMs:500,fadeMs:400,fadeDelayMs:100,fadeEase:"cubic-bezier(.16,1,.3,1)",colorLeadMs:900,make(ov,env,api){return barsListScene(ov,env,"glow");}});
