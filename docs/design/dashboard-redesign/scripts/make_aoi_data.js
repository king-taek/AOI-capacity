/* ============================================================================
 * make_aoi_data.js — "AOI_capacity 3.html" → aoi-data.json
 *
 * 아래 [원본] 블록은 프로젝트에서 실제로 돌려서 지금의 aoi-data.json 을 만든
 * 코드 그대로입니다. 한 글자도 고치지 않았습니다.
 *
 * 원래는 파일이 아니라 샌드박스에서 실행된 스크립트라 readFile / saveFile / log
 * 세 개를 환경이 제공했습니다. Node 에서 돌릴 수 있도록 그 세 개만 아래에
 * 끼워 넣었습니다. 이 shim 은 새로 쓴 것이고, 그 아래 [원본] 은 손대지 않았습니다.
 *
 *   node make_aoi_data.js "AOI_capacity 3.html" aoi-data.json
 *
 * Node 18 이상. 외부 의존성 없음.
 * ========================================================================== */

/* ── shim (새로 추가한 부분) ───────────────────────────────────────────── */
const fs = require('fs');
const IN  = process.argv[2] || 'AOI_capacity 3.html';
const OUT = process.argv[3] || 'aoi-data.json';
const readFile = async p => fs.readFileSync(p === 'uploads/AOI_capacity 3.html' ? IN : p, 'utf8');
const saveFile = async (p, d) => fs.writeFileSync(p === 'aoi-data.json' ? OUT : p, d);
const log = (...a) => console.log(...a);
/* ── shim 끝 ──────────────────────────────────────────────────────────── */

/* ── [원본] 여기부터 아래는 실제로 돌린 코드 그대로 ────────────────────── */
(async () => {
const html = await readFile('uploads/AOI_capacity 3.html');
const s0=html.indexOf('<script type="application/json" id="embedded">'), e0=html.indexOf('</scr'+'ipt>',s0);
const S=JSON.parse(html.slice(s0+'<script type="application/json" id="embedded">'.length,e0));
const {cols,pooled,pool,rows,meta}=S; const ps=new Set(pooled); const idx={}; cols.forEach((c,i)=>idx[c]=i);
const val=(r,c)=>{const v=r[idx[c]];return ps.has(c)?pool[v]:v;};
const MON={jan:0,feb:1,mar:2,apr:3,may:4,jun:5,jul:6,aug:7,sep:8,oct:9,nov:10,dec:11};
function P(s){ if(!s) return null; let t=String(s).trim();
  let m=t.match(/^(\d{1,2})-([A-Za-z]{3})-(\d{2})\s+(\d{1,2}):(\d{2}):(\d{2})\s*(AM|PM)?$/i);
  if(m){let h=+m[4];if(m[7]){const pm=m[7].toUpperCase()==='PM';if(pm&&h<12)h+=12;if(!pm&&h===12)h=0;}return new Date(2000+ +m[3],MON[m[2].toLowerCase()],+m[1],h,+m[5],+m[6]);}
  m=t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*(AM|PM)?$/i);
  if(m){let h=+m[4];if(m[7]){const pm=m[7].toUpperCase()==='PM';if(pm&&h<12)h+=12;if(!pm&&h===12)h=0;}return new Date(+m[3],+m[1]-1,+m[2],h,+m[5],+m[6]);}
  return null;}
const R1=/^(.+?)_(\d{4})_(.+)_(\d{1,2}-[A-Za-z]{3}-\d{2})_\((\d{2}\.\d{2}\.\d{2})\)_BatchReport\.html?$/i;
const R2=/^(.+)_(\d{1,2}-[A-Za-z]{3}-\d{2})_\((\d{2}\.\d{2}\.\d{2})\)_BatchReport\.html?$/i;
const KEEP=new Set(['DIA','2D','3D','EDGE','CENTER','RE','SRD','RESCAN','PCM','DUMMY','SPT']);
const DROPW=new Set(['PIDV','WBG','FS','BUMP','TOP','BUMPTOP','STRIP','REWORK','RW','PR','UBM','CUP']);
const kn=t=>{const u=t.toUpperCase();return KEEP.has(u)||DROPW.has(u)||/^PIDS\d*$/.test(u)||/^RDL\d*$/.test(u)||/^TPDV\d*$/.test(u);};
function lotName(rep,fb){ if(!rep) return fb||'';
  let fl=null; const m=rep.match(R1);
  if(m) fl=m[3]; else { const m2=rep.match(R2); if(m2){const p=m2[1].split('_');fl=p[p.length-1];} }
  if(!fl) return fb||''; fl=fl.trim();
  let pt=fl.split('_'); while(pt.length>1&&/^(setup\d*|\d{4})$/i.test(pt[0])) pt.shift();
  fl=pt.join('_');
  const sg=fl.split(/([-_ +]+)/);
  if(!/^[A-Za-z0-9]{3}$/.test(sg[0])) return fl;
  for(let i=2;i<sg.length;i+=2){ if(sg[i]!==undefined&&sg[i]!==''&&!kn(sg[i])) return fl; }
  let o=sg[0];
  for(let i=1;i<sg.length;i+=2){const sp=sg[i],tk=sg[i+1]; if(tk===undefined)break; if(KEEP.has(tk.toUpperCase())) o+=sp+tk;}
  return o; }
const JM={"RKENDALLPI4DG":"RKENDALLA0PI4"};
function jobKey(s){ const tk=String(s||'').toUpperCase().split(/[\s_\-]+/).filter(Boolean); const o=[];
  for(let i=0;i<tk.length;i++){ let t=tk[i];
    if(t==='TEST'&&i===0) continue; if(t==='LIVE'||t==='COPY') continue;
    if(/^\d{4}COPY$/.test(t)) continue;
    if(t==='AOI'&&/^\d+$/.test(tk[i+1]||'')){i++;continue;}
    if(/^AOI\d+$/.test(t)) continue;
    if(t==='AO') t='A0';
    o.push(t.replace(/^(\d{7})PD$/,'$1')); }
  while(o.length>1&&/^\d{4}$/.test(o[o.length-1])) o.pop();
  const k=o.join(''); return JM[k]||k; }
const CR=[["WAFER_LOST",/wafer\s+lost|failed\s+to\s+sense\s+wafer|failed\s+to\s+move\s+wafer|could\s+not\s+be\s+detected\s+on\s+hand|wafer\s+handling\s+failure|failed\s+on\s+movetostation/i],["HW_ERROR",/hardware\s+failure/i],["ID_READ_ERROR",/failed\s+to\s+read\s+wafer\s+id/i],["ID_FORMAT_ERROR",/wafer\s+id\s+mask\s+length|wafer\s+id\s+read\s+does\s+not\s+match/i],["SCAN_ERROR",/scan\s*(?:2d|3d)?\s*error/i],["ALIGN_ERROR",/alignment\s+error|alignment\s+failed|prealigner\s+fail/i],["PREALIGNER_RESPONSE_ERROR",/prealigner:\s*expected\s+status\s+field\s+was\s+not\s+found/i],["AUTO_FOCUS_ERROR",/auto\s+focus\s+error/i],["FOCUS_MAPPING_ERROR",/focus\s+mapping\s+error/i],["MOTION_ERROR",/motor->get_position|motion\s+failed\s+to\s+get_continuousscanstatus|acsmotor::get_position/i],["CLEAN_REF_ERROR",/clean\s+reference\s+error/i],["NOTHING_TO_SCAN",/nothing\s+to\s+scan/i],["RECIPE_ERROR",/far\s*model|illegal\s+lot\s+name|wafer\s+map\s+import\s+failed|multi\s*recipe\s+error/i],["CONTROL_TIMEOUT",/abort\s+timed-?out/i],["GRAY_LEVEL_LIMIT",/gray\s+level\s+average\s+exceeds/i],["HANDLING_ERROR",/robot\s+operation\s+failed|movetabletostoredposandlock|wafer\s+move\s+failure/i]];
const causeOf=t=>{const x=String(t||'').trim();for(const[c,rx]of CR)if(rx.test(x))return c;return null;};
const RT=new Set(['RE','RESCAN','REWORK','SRD','R']);
const matKey=(j,l,w)=>jobKey(j)+'|'+String(l||'').toUpperCase().split(/[-_ #+,'%.~]+/).filter(x=>x&&!RT.has(x)).join('')+'|'+String(w||'').toUpperCase().replace(/[^A-Z0-9]/g,'');
const dk=x=>`${x.getFullYear()}-${String(x.getMonth()+1).padStart(2,'0')}-${String(x.getDate()).padStart(2,'0')}`;
const all=[];
for(const r of rows){
  const ws=P(val(r,'wafer_start_time')), we=P(val(r,'wafer_end_time')), bs=P(val(r,'batch_start')), be=P(val(r,'batch_end'));
  const an=ws||bs; if(!an) continue;
  const st=String(val(r,'status')||'').trim(), rl=String(val(r,'lot')||''), wid=String(val(r,'wafer_id')||''), rp=String(val(r,'report')||'');
  const job=String(val(r,'job')||''), lot=lotName(rp,rl);
  all.push({dev:val(r,'device'),t:an.getTime(),s:ws?ws.getTime():null,e:we?we.getTime():null,timed:!!ws,
    bs:bs?bs.getTime():null, bend:be?be.getTime():(bs?bs.getTime():null),
    c:causeOf(st),status:st,report:rp,job,lot,test:/TEST/i.test(rl),key:matKey(job,lot,wid),day:dk(an)});
}
all.sort((a,b)=>a.t-b.t);
const seen=new Map();
for(const w of all){const p=seen.get(w.key); w.rel=(p&&!p.c)?1:0; seen.set(w.key,w);}
const SP={job:[],lot:[],rep:[],st:[]},SM={job:new Map(),lot:new Map(),rep:new Map(),st:new Map()};
const put=(k,v)=>{v=v||'';const m=SM[k];if(m.has(v))return m.get(v);const i=SP[k].length;SP[k].push(v);m.set(v,i);return i;};
function dayStats(list,ds){
  const base=new Date(ds+'T00:00:00').getTime();
  const mm=t=>Math.max(0,Math.min(1440,Math.round((t-base)/60000)));
  const iv=list.map(w=>{const a=mm(w.s||w.t); const b=(w.timed&&w.e&&w.e>w.s)?mm(w.e):(w.c?Math.min(1440,a+3):a);
    return {a,b,w,k:w.c?1:(w.test?2:(w.rel?4:0))};});
  iv.sort((x,y)=>x.a-y.a||x.b-y.b);
  const mg=[];
  for(const g of iv){const L=mg[mg.length-1];
    if(L&&g.k===L.k&&g.a-L.b<=3){L.b=Math.max(L.b,g.b);L.ws.push(g.w);} else mg.push({a:g.a,b:g.b,k:g.k,ws:[g.w]});}
  let run=0,err=0,test=0,dup=0;
  for(const g of mg){const L=g.b-g.a;if(g.k===0)run+=L;else if(g.k===1)err+=L;else if(g.k===2)test+=L;else dup+=L;}
  const ct={},lotCt={},sl=new Set();
  const give=(w,m)=>{const lk=w.report||(w.job+'\u0001'+w.lot),k=lk+'\u0002'+w.c;
    const nw=!sl.has(k); if(nw) sl.add(k);
    const g=ct[w.c]||[0,0]; if(nw)g[0]++; g[1]+=m; ct[w.c]=g;
    const L=lotCt[lk]||(lotCt[lk]={}); const q=L[w.c]||[0,0]; q[0]=1; q[1]+=m; L[w.c]=q;};
  let stop=0;
  for(let i=0;i<mg.length;i++){const g=mg[i]; if(g.k!==1)continue;
    const es=g.ws.filter(w=>w.c); if(!es.length)continue;
    const nx=mg[i+1]; let gap=nx?Math.max(0,nx.a-g.b):0; if(gap>240)gap=240;
    stop+=gap; const sh=((g.b-g.a)+gap)/es.length;
    for(const w of es) give(w,sh);}
  for(const w of list){if(!w.c)continue; if(!mg.some(g=>g.k===1&&g.ws.includes(w))) give(w,0);}
  const lots=new Map();
  for(const w of list){const lk=w.report||(w.job+'\u0001'+w.lot);
    const L=lots.get(lk)||{job:w.job,lot:w.lot,a:1441,b:0,ba:1441,bb:0,w:0,dup:0,test:0,rep:w.report,st:''};
    L.w++; if(w.c&&!L.st) L.st=w.status; if(w.rel)L.dup++; if(w.test)L.test++;
    const A=mm(w.s||w.t),B=mm(w.e||w.t); if(A<L.a)L.a=A; if(B>L.b)L.b=B;
    if(w.bs){const ba=mm(w.bs),bb=mm(w.bend||w.bs); if(ba<L.ba)L.ba=ba; if(bb>L.bb)L.bb=bb;}
    lots.set(lk,L);}
  const rnd=o=>{const r={};for(const[k,v]of Object.entries(o))r[k]=[v[0],Math.round(v[1])];return r;};
  let dayE=0;
  const out=[...lots.entries()].map(([lk,L])=>{const cs=rnd(lotCt[lk]||{}); const n=Object.keys(cs).length; dayE+=n; return {L,cs,n};})
    .filter(x=>x.L.b>x.L.a||x.n||x.L.bb>x.L.ba)          /* ★ 배치 구간만 있어도 남긴다 */
    .sort((x,y)=>(x.L.a<1441?x.L.a:x.L.ba)-(y.L.a<1441?y.L.a:y.L.ba));
  return {r:run,x:err,t:test,d:dup,s:stop,w:list.length,e:dayE,
    seg:mg.map(g=>[g.a,g.b,g.k]),ct:rnd(ct),
    lots:out.map(({L,cs,n})=>[put('job',L.job),put('lot',L.lot),L.a,L.b,L.w,n,L.dup,L.test,put('rep',L.rep),cs,n?put('st',L.st):-1,
      L.ba<1441?L.ba:0, L.bb>L.ba?L.bb:(L.ba<1441?L.ba:0)])};
}
const dev=meta.devices.map(x=>x.name);
const days=[...new Set(all.map(w=>w.day))].sort();
const bdd={}; for(const w of all){((bdd[w.dev]||={})[w.day]||=[]).push(w);}
const detail={}; for(const dy of days){const O={};for(const dv of dev){const l=(bdd[dv]||{})[dy]; if(l)O[dv]=dayStats(l,dy);} detail[dy]=O;}
/* cv · bseg · be */
const cov={},bat={};
for(const w of all){ const c=((cov[w.dev]||={})[w.day]||=[0,0]); c[1]++; if(w.timed)c[0]++;
  if(w.bs){const k=w.dev+'|'+w.day+'|'+w.report; if(!bat[k])bat[k]={dv:w.dev,day:w.day,a:w.bs,b:w.bend||w.bs};} }
const bdd2={}; for(const b of Object.values(bat)) ((bdd2[b.dv]||={})[b.day]||=[]).push(b);
for(const [dy,ds] of Object.entries(detail)) for(const [dv,t] of Object.entries(ds)){
  const c=(cov[dv]||{})[dy]||[0,1]; t.cv=Math.round(c[0]/Math.max(1,c[1])*100);
  const t0=new Date(dy+'T00:00:00').getTime(), mm=v=>Math.max(0,Math.min(1440,Math.round((v-t0)/60000)));
  const lst=((bdd2[dv]||{})[dy]||[]).sort((x,y)=>x.a-y.a); const mgd=[];
  for(const b of lst){const a=mm(b.a),e=Math.max(a,mm(b.b)); const L=mgd[mgd.length-1];
    if(L&&a-L[1]<=3) L[1]=Math.max(L[1],e); else mgd.push([a,e]);}
  t.bseg=mgd; t.be=mgd.reduce((x,g)=>x+(g[1]-g[0]),0);
}
const uj={}; for(const dy of days) for(const dv of dev){const t=(detail[dy]||{})[dv]; if(!t)continue; for(const L of t.lots) uj[L[0]]=(uj[L[0]]||0)+1;}
const gm={}; SP.job.forEach((n,i)=>{(gm[jobKey(n)]||=[]).push(i);});
const jobGroups=[]; const jobG=new Array(SP.job.length).fill(0);
for(const ids of Object.values(gm)){const mem=ids.map(i=>[i,uj[i]||0]).sort((a,b)=>b[1]-a[1]);
  const gi=jobGroups.length; jobGroups.push({l:mem[0][0],m:mem}); for(const i of ids) jobG[i]=gi;}
await saveFile('aoi-data.json',JSON.stringify({day:'2026-09-18',generated:meta.generated,devices:dev,days,pool:SP,detail,jobG,jobGroups,
  scope:meta.devices.map(x=>({n:x.name,note:x.note,reports:x.reports}))}));
const t4=detail['2026-09-18']['AOI-4'];
log('AOI-4 lots '+t4.lots.length+'개 (배치 '+t4.bseg.length+') cv'+t4.cv+'% · Error Lot '+t4.lots.filter(L=>L[5]).length);
log(t4.lots.slice(0,4).map(L=>`  ${SP.lot[L[1]]} ba${L[11]}–${L[12]} w${L[4]} e${L[5]}`).join('\n'));
log('AOI-8 lots '+detail['2026-09-18']['AOI-8'].lots.length);
})();
