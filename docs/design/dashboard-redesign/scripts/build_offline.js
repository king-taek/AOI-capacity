/* ============================================================================
 * build_offline.js — aoi-data.js 와 오프라인 단일 HTML 만들기
 *
 * 아래 [원본] 두 블록은 실제로 돌린 코드 그대로입니다.
 * readFile / saveFile / replaceText / log 만 Node 용으로 끼워 넣었습니다.
 *
 *   node build_offline.js
 *
 * 그 다음 단계(단일 HTML 로 인라인)는 이 프로젝트의 번들러가 했습니다.
 * 저장소에서는 README.md 의 '오프라인 빌드' 절을 보세요.
 * ========================================================================== */

const fs = require('fs');
const readFile = async p => fs.readFileSync(p, 'utf8');
const saveFile = async (p, d) => fs.writeFileSync(p, d);
const replaceText = (t, a, b) => t.split(a).join(b);
const log = (...a) => console.log(...a);

(async () => {
/* ── [원본] 1. aoi-data.json → aoi-data.js (window.AOI_DATA) ──────────── */
const data = await readFile('aoi-data.json');
await saveFile('aoi-data.js', 'window.AOI_DATA='+data+';');

/* ── [원본] 2. 대시보드를 오프라인용으로 바꾸기 ────────────────────────── */
const src = await readFile('AOI-Dashboard.dc.html');
const tag = '<script src="aoi-data.js"><\/script>\n'
  + '<template id="__bundler_thumbnail"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
  + '<rect width="120" height="120" rx="18" fill="#2E6BA8"/>'
  + '<rect x="26" y="40" width="68" height="9" rx="4.5" fill="#fff" opacity=".95"/>'
  + '<rect x="26" y="56" width="46" height="9" rx="4.5" fill="#fff" opacity=".7"/>'
  + '<rect x="26" y="72" width="58" height="9" rx="4.5" fill="#C5453C"/></svg></template>\n';
let out = src.replace('</helmet>', tag + '</helmet>');
const a = 'const DATA_P=(window.__aoiFullP ||= fetch("aoi-data.json").then(r=>r.json()));';
const b = 'const DATA_P=(window.__aoiFullP ||= new Promise(res=>{const t=()=>window.AOI_DATA?res(window.AOI_DATA):setTimeout(t,30);t();}));';
if(!out.includes(a)) throw new Error('DATA_P not found');
out = replaceText(out, a, b);
log('len', out.length);
await saveFile('AOI-Dashboard-offline.dc.html', out);
})();
