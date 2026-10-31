/* V2 픽셀 버퍼 — 같은 장면, 입자 10,000, Path2D · stroke 없이 Uint32 버퍼(반해상도)에 직접 찍고 putImageData 한 번 */
bootShell({sceneReveals:true,fadeMs:600,make(ov,env,api){return workerScene(ov,env,api,{N:Math.max(600,Math.round(Math.min(10000,env.W*env.H/200))),render:"pixel"});}});
