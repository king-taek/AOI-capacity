/* template.html 의 스크립트를 브라우저 없이 Node 에서 실행해 **모델 함수만** 검사하는 하네스.
   stdin 으로 JSON 을 받아 build()·dayMetrics()·자재 이력 결과를 JSON 으로 낸다.
     { rows:[...], meta?:{...}, today?:"YYYY-MM-DD", viewer_now?:"ISO"|ms, summary?:true }
   - `viewer_now`: 열람 시계(Date.now · new Date()) 를 고정한다 — 재현 가능한 기준선을 위해.
   - `today`: 옛 테스트 호환 — 집계 기준일을 직접 고정한다(todayKey 치환). metrics_ref 는 meta.generated_iso 로 준다(D40).
   - `summary`: 장비·날짜별 items 목록 대신 전체 합계만 낸다(15만 행 실데이터용).
   DOM 은 아무것도 하지 않는 대역(stub)이다 — 화면 검증은 Chromium 으로 따로 한다(진행상황.md 실측). 네트워크·파일 쓰기 없음. */
"use strict";
const fs=require("fs"),vm=require("vm"),path=require("path");
const html=fs.readFileSync(path.join(__dirname,"..","..","aoi_capacity","ui","assets","template.html"),"utf8");
let js=html.slice(html.indexOf("<script>")+8,html.lastIndexOf("</script>"));
js=js.replace(/loadDemo\(\);\s*$/,"");                       // 부팅은 하지 않는다(rows 를 직접 넣는다)
js=js.replace("const todayKey=()=>dayKey(new Date());","const todayKey=()=>__today||dayKey(new Date());");   // 옛 방식(오늘 고정)
js=js.replace("const todayKey=()=>dayKey(metricsRef());","const todayKey=()=>__today||dayKey(metricsRef());"); // D40 이후
const input=JSON.parse(fs.readFileSync(0,"utf8"));
/* 열람 시계 고정 — Date.now() 와 인자 없는 new Date() 만 바꾼다. 인자가 있는 생성은 그대로다. */
const NOW=input.viewer_now==null?Date.now():(typeof input.viewer_now==="number"?input.viewer_now:new Date(input.viewer_now).getTime());
class FakeDate extends Date{constructor(...a){if(a.length===0)super(NOW);else super(...a);}static now(){return NOW;}}
const stub=()=>new Proxy(function(){}, {get:(t,k)=>k===Symbol.toPrimitive?()=>"":k==="length"?0:k==="hidden"?false:stub(),set:()=>true,apply:()=>stub(),has:()=>true});
const doc=stub();
const ctx={document:doc,window:{},navigator:{},localStorage:{getItem:()=>null,setItem(){}},matchMedia:()=>({matches:false}),innerWidth:1440,innerHeight:900,
  setTimeout:()=>0,clearTimeout(){},console,Date:FakeDate,Math,JSON,Set,Map,Object,Array,String,Number,Blob:function(){},URL:{createObjectURL:()=>""}};
ctx.window=ctx;vm.createContext(ctx);
ctx.__today=input.today||"";
vm.runInContext(js,ctx,{filename:"template.js"});
ctx.__rows=input.rows;ctx.__meta=input.meta||{};ctx.__summary=!!input.summary;
const out=vm.runInContext(`(function(){rows=__rows.map(o=>({kind:"",job:"",setup:"",lot:"",wafer_id:"",status:"Pass",norm_status:"",scan_type:"",recipe:"",wafer_start_time:"",wafer_end_time:"",batch_start:"",batch_end:"",report:"",ini_match:"EXACT",data_issue:"",...o}));
  meta=__meta;if(typeof prepareRows==="function")prepareRows(rows);else rows.forEach(r=>{r.norm_status=r.norm_status||normStatus(r.status);});
  D=build();const keys=dataDays();
  const res={devices:devNames,days:keys,per:{},attempts:[],index:{unresolved:D._index.nUnresolved,cross:D._index.nCross,same:D._index.nSame,dup:D._index.nDup},
    class_version:typeof CLASS_VERSION==="number"?CLASS_VERSION:null,today:todayKey()};
  const T=["run","err","stop","test","abort","dup","rescan","rework","off","overlap","denom"],C=["nErr","nWafer","nTest","nAbort","nDup","nRescan","nCross","nRework","nUnk"];
  const tot={};T.concat(C).forEach(k=>tot[k]=0);const bad=[];
  for(const n of devNames){res.per[n]={};for(const k of keys){const m=dayMetrics(D[n],k);const o={run:m.run,err:m.err,stop:m.stop,test:m.testRun,abort:m.abortRun,nAbort:m.nAbort,dup:m.dup,rescan:m.rescan,rework:m.rework,off:m.off,overlap:m.overlap,denom:m.denom,util:m.util,nErr:m.nErr,nWafer:m.nWafer,nTest:m.nTest,nDup:m.nDup,nRescan:m.nRescan,nCross:m.nCross,nRework:m.nRework,nUnk:m.nUnk||0,hasData:m.hasData};
      if(!__summary)o.items=m.items.map(i=>({kind:i.kind,s:i.s,e:i.e,sec:i.sec,disp:i.g.disp,wafer:i.g.r.wafer_id,lot:i.g.r.lot}));
      if(m.future)continue;T.concat(C).forEach(x=>tot[x]+=o[x]||0);
      /* 시간 항등식: run+err+stop+test+off = denom (abort 는 partition 이거나 run 의 부분집합 — 어느 쪽이든 항등식은 아래 둘 중 하나) */
      const s1=o.run+o.err+o.stop+o.test+o.off,s2=s1+o.abort;if(Math.abs(s1-o.denom)>1e-6&&Math.abs(s2-o.denom)>1e-6)bad.push([n,k,s1,s2,o.denom]);
      if(__summary){res.per[n][k]={util:o.util,hasData:o.hasData,denom:o.denom,run:o.run};}else res.per[n][k]=o;}}
  res.totals=tot;res.identity_violations=bad;
  const rel={},conf={},disp={};let timed=0;
  for(const a of D._index.attempts){rel[a.rel]=(rel[a.rel]||0)+1;conf[a.conf]=(conf[a.conf]||0)+1;if(a.timed){timed++;disp[a.g.disp]=(disp[a.g.disp]||0)+1;}
    if(!__summary)res.attempts.push({dev:a.dev,wafer:a.r.wafer_id,lot:a.r.lot,report:a.r.report,timed:a.timed,s:a.s,rel:a.rel,conf:a.conf,no:a.no,of:a.of,prior:a.prior?{dev:a.prior.dev,s:a.prior.s}:null,disp:a.timed?a.g.disp:null,abortFlag:a.timed?!!a.g.abort:!!a.abort,refs:a.timed?a.g.refs:null,rawDups:a.timed?a.g.rawDups:null,why:a.why,mk:a.mk,pk:a.pk});}
  res.model={attempts:D._index.attempts.length,timed_attempts:timed,relations:rel,confidence:conf,display_of_timed_attempts:disp};
  const f=fleetAvg(keys);res.fleet={util:f.util,sumUtil:f.sumUtil,n:f.n};
  res.loss=keys.map(k=>{const L=lossCalc(devNames.map(n=>({n,m:dayMetrics(D[n],k)})));const fa=fleetAvg([k]);return{k,ppSum:L.ppSum,util:fa.util,rows:L.rows.map(r=>[r.id,r.sec,r.pp])};});
  if(typeof qualitySummary==="function")res.quality=qualitySummary();
  if(typeof occurrenceIndex==="function"&&D._occ)res.occurrences=D._occ.summary?D._occ.summary():null;
  return res;})()`,ctx);
process.stdout.write(JSON.stringify(out));
