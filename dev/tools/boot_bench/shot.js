/* node shot.js <html> <prefix> [times ms…] : 시작 화면 장면을 시각별로 찍는다 */
const { chromium } = require("playwright"); const path = require("path");
(async () => { const [html, prefix, ...ts] = process.argv.slice(2); const times = ts.length ? ts.map(Number) : [1200, 2600, 3800];
  const b = await chromium.launch(); const c = await b.newContext({ viewport: { width: 1366, height: 768 } }); const p = await c.newPage();
  const errs = []; p.on("pageerror", e => errs.push(String(e))); p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  const t0 = Date.now(); await p.goto("file://" + path.resolve(html), { waitUntil: "commit" });
  for (const t of times) { const w = t - (Date.now() - t0); if (w > 0) await p.waitForTimeout(w); await p.screenshot({ path: `${prefix}_${t}.png` }); }
  console.log(prefix, errs); await b.close(); })();
