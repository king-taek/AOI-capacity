/* V1 경량화 — 같은 '데이터 입자' 장면, 입자 6,000 · 흐름장 격자 · 팔레트 12 · dpr 1 · 적응형 꼬리 · 흐림 없는 걷힘 */
bootShell({sceneReveals:true,fadeMs:600,make(ov,env,api){return workerScene(ov,env,api,{N:Math.max(600,Math.round(Math.min(12000,env.W*env.H/150))),render:"path",maxPal:12,dprMax:1});}});
