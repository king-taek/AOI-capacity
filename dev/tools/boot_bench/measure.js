/* 시작 화면 렉 계측: node measure.js <html> [--cpu N] [--dpr D] [--w W] [--h H] [--label L] [--out file.json]
   · worker 프레임: rAF 콜백 간격(실제 fps) · 콜백 안 시간(JS+캔버스 명령)
   · 메인: long-animation-frame(LoAF) · rAF 간격 · 덮개 등장/걷힘/제거 시각 · 첫 화면 시각
   · CDP 트레이스: PipelineReporter 드롭 프레임(합성기 기준) */
const { chromium } = require("playwright");
const fs = require("fs");
const args = process.argv.slice(2);
const opt = { cpu: 1, dpr: 1, w: 1920, h: 1080, label: "", out: "", hold: 1500 };
let html = null;
for (let i = 0; i < args.length; i++) { const a = args[i]; if (a.startsWith("--")) { const k = a.slice(2); opt[k] = isNaN(args[i + 1]) ? args[i + 1] : Number(args[i + 1]); i++; } else html = a; }
if (!html) { console.error("html 경로가 필요합니다"); process.exit(2); }

const INIT = `(() => {
  const M = window.__m = { t0: performance.timeOrigin, loaf: [], longtask: [], raf: [], w: [], wOrigin: 0, seen: 0, revealAt: 0, gone: 0, view: 0, done: 0, workers: 0, fallback: false };
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) M.loaf.push([e.startTime, e.duration, e.blockingDuration || 0]); }).observe({ type: "long-animation-frame", buffered: true }); } catch (e) {}
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) M.longtask.push([e.startTime, e.duration]); }).observe({ type: "longtask", buffered: true }); } catch (e) {}
  const raf = () => { M.raf.push(performance.now()); if (!M.gone || performance.now() < M.gone + 2500) requestAnimationFrame(raf); };
  requestAnimationFrame(raf);
  /* 덮개 관찰 */
  const mo = new MutationObserver(() => {
    const b = document.getElementById("aoi-boot");
    if (b && !M.seen) { M.seen = performance.now(); new MutationObserver(() => { if (!M.revealAt && b.style.opacity === "0") M.revealAt = performance.now(); }).observe(b, { attributes: true, attributeFilter: ["style"] }); }
    if (!b && M.seen && !M.gone) M.gone = performance.now();
    if (!M.view && document.querySelector('main[data-key^="view:"]')) M.view = performance.now();
  });
  mo.observe(document, { childList: true, subtree: true, attributes: true, attributeFilter: ["style", "data-key"] });
  /* AOI_BOOT.done 시각 */
  let _b = null;
  Object.defineProperty(window, "AOI_BOOT", { configurable: true, get: () => _b, set: v => { _b = v; if (v && typeof v.done === "function") { const d = v.done.bind(v); v.done = (...a) => { if (!M.done) M.done = performance.now(); return d(...a); }; } } });
  /* Worker 계측: blob 스크립트 뒤에 rAF 래퍼를 붙인다 */
  const W0 = window.Worker;
  window.Worker = function (url, o) {
    let src = null;
    try { const x = new XMLHttpRequest(); x.open("GET", url, false); x.send(); src = x.responseText; } catch (e) {}
    if (src == null) return new W0(url, o);
    const extra = \`
;(function(){const R=self.requestAnimationFrame.bind(self);const F=[];let last=0;
  self.requestAnimationFrame=f=>R(ts=>{const s=performance.now();try{f(ts);}finally{const d=performance.now()-s;F.push(s,d,last?s-last:0);last=s;}});
  setInterval(()=>{if(F.length)self.postMessage({type:"__stat",origin:performance.timeOrigin,f:F.splice(0)});},200);})();\`;
    const u = URL.createObjectURL(new Blob([src + extra], { type: "text/javascript" }));
    const w = new W0(u, o); M.workers++;
    w.addEventListener("message", e => { const d = e.data; if (d && d.type === "__stat") { M.wOrigin = d.origin; for (let i = 0; i < d.f.length; i += 3) M.w.push([d.origin + d.f[i] - M.t0, d.f[i + 1], d.f[i + 2]]); } });
    return w;
  };
})();`;

(async () => {
  const browser = await chromium.launch({ args: ["--disable-gpu-vsync"] });   // vsync 없이도 rAF 는 60Hz 로 돈다(BeginFrame 60Hz)
  const ctx = await browser.newContext({ viewport: { width: opt.w, height: opt.h }, deviceScaleFactor: opt.dpr });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  await page.addInitScript(INIT);
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Performance.enable");
  if (opt.cpu > 1) await cdp.send("Emulation.setCPUThrottlingRate", { rate: opt.cpu });
  const trace = [];
  const names = {}; cdp.on("Tracing.dataCollected", d => { for (const e of d.value) { names[e.name] = (names[e.name] || 0) + 1; if (e.name === "PipelineReporter" || e.name === "DroppedFrame") trace.push(e); } });
  await cdp.send("Tracing.start", { categories: "disabled-by-default-devtools.timeline,disabled-by-default-devtools.timeline.frame,benchmark,viz,cc", transferMode: "ReportEvents" });
  const tNav = Date.now();
  await page.goto("file://" + require("path").resolve(html), { waitUntil: "commit" });
  try { await page.waitForFunction(() => window.__m && window.__m.gone, null, { timeout: 60000 }); } catch (e) { errors.push("덮개가 걷히지 않음(60s)"); }
  await page.waitForTimeout(opt.hold);
  const M = await page.evaluate(() => window.__m);
  const metrics = await cdp.send("Performance.getMetrics").catch(() => null);
  await cdp.send("Tracing.end");
  await new Promise(r => cdp.once("Tracing.tracingComplete", r));
  await browser.close();

  /* ── 요약 ── */
  const q = (a, p) => { if (!a.length) return 0; const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
  const win0 = M.seen || 0, win1 = M.gone || (M.seen + 12000);
  const wf = M.w.filter(f => f[0] >= win0 && f[0] <= win1);
  const wInt = wf.map(f => f[2]).filter(x => x > 0), wDur = wf.map(f => f[1]);
  const mRaf = M.raf.filter(t => t >= win0 && t <= win1 + 300);
  const mInt = mRaf.slice(1).map((t, i) => t - mRaf[i]);
  const revInt = (() => { const a = M.raf.filter(t => M.revealAt && t >= M.revealAt - 50 && t <= M.gone + 300); return a.slice(1).map((t, i) => t - a[i]); })();
  const loafIn = M.loaf.filter(l => l[0] >= win0 && l[0] <= win1);
  const loafAfter = M.loaf.filter(l => l[0] > win1 && l[0] <= win1 + 2500);
  const tr = trace.filter(e => e.name === "PipelineReporter" && e.ph === "b" && e.args && e.args.frame_reporter);
  const droppedEv = trace.filter(e => e.name === "DroppedFrame").length;
  const states = {}; for (const e of tr) { const s = e.args.frame_reporter.state; states[s] = (states[s] || 0) + 1; }
  const dropped = tr.filter(e => e.args.frame_reporter.state === "STATE_DROPPED").length;
  const droppedSmooth = tr.filter(e => e.args.frame_reporter.state === "STATE_DROPPED" && e.args.frame_reporter.affects_smoothness).length;
  const out = {
    label: opt.label || html, html, cpu: opt.cpu, dpr: opt.dpr, w: opt.w, h: opt.h, errors, workers: M.workers,
    t: { seen: r(M.seen), view: r(M.view), done: r(M.done), revealAt: r(M.revealAt), gone: r(M.gone) },
    worker: { frames: wf.length, fpsEff: wInt.length ? r(1000 / (wInt.reduce((a, b) => a + b, 0) / wInt.length)) : 0,
      intP50: r(q(wInt, .5)), intP95: r(q(wInt, .95)), intMax: r(q(wInt, 1)), over20: wInt.filter(x => x > 20).length, over34: wInt.filter(x => x > 34).length,
      durP50: r(q(wDur, .5)), durP95: r(q(wDur, .95)), durMax: r(q(wDur, 1)), durSum: r(wDur.reduce((a, b) => a + b, 0)) },
    main: { rafFrames: mRaf.length, intP50: r(q(mInt, .5)), intP95: r(q(mInt, .95)), intMax: r(q(mInt, 1)), over34: mInt.filter(x => x > 34).length,
      loafCount: loafIn.length, loafSum: r(loafIn.reduce((a, l) => a + l[1], 0)), loafMax: r(Math.max(0, ...loafIn.map(l => l[1]))), blocking: r(loafIn.reduce((a, l) => a + l[2], 0)),
      loafAfterSum: r(loafAfter.reduce((a, l) => a + l[1], 0)),
      reveal: { frames: revInt.length, intP95: r(q(revInt, .95)), intMax: r(q(revInt, 1)), over34: revInt.filter(x => x > 34).length } },
    compositor: { reported: tr.length, dropped, droppedSmooth, droppedEv, states, names: opt.debug ? names : undefined },
    metrics: metrics ? Object.fromEntries(metrics.metrics.filter(m => /TaskDuration|ScriptDuration|LayoutDuration|RecalcStyleDuration|JSHeapUsedSize|ThreadTime/.test(m.name)).map(m => [m.name, r(m.value)])) : null,
  };
  function r(x) { return x == null ? x : Math.round(x * 10) / 10; }
  if (opt.out) fs.writeFileSync(opt.out, JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
