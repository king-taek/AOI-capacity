/* V3 CSS 스켈레톤 — 캔버스 · Worker 없음. 틀(1막) 과 숫자 · 막대(2막) 전부 DOM + CSS 키프레임(transform · opacity), 합성 스레드만 */
bootShell({sceneReveals:false,settleMs:450,fadeMs:600,make(ov,env,api){return cssFrame(ov,env,{data:true});}});
