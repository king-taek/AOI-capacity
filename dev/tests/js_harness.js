/* template.html 의 스크립트를 브라우저 없이 Node 에서 실행해 **모델 함수만** 검사하는 하네스.
   stdin 으로 {rows:[...], today:"YYYY-MM-DD"?} 를 받아 build()·dayMetrics()·자재 이력 결과를 JSON 으로 낸다.
   DOM 은 아무것도 하지 않는 대역(stub)이다 — 화면 검증은 Chromium 으로 따로 한다(진행상황.md 실측). 네트워크·파일 쓰기 없음. */
"use strict";
const fs=require("fs"),vm=require("vm"),path=require("path");
const html=fs.readFileSync(path.join(__dirname,"..","..","aoi_capacity","ui","assets","template.html"),"utf8");
let js=html.slice(html.indexOf("<script>")+8,html.lastIndexOf("</script>"));
js=js.replace(/loadDemo\(\);\s*$/,"");                       // 부팅은 하지 않는다(rows 를 직접 넣는다)
js=js.replace("const todayKey=()=>dayKey(new Date());","const todayKey=()=>__today||dayKey(new Date());");   // '오늘' 을 고정할 수 있게
const stub=()=>new Proxy(function(){}, {get:(t,k)=>k===Symbol.toPrimitive?()=>"":k==="length"?0:k==="hidden"?false:stub(),set:()=>true,apply:()=>stub(),has:()=>true});
const doc=stub();
const ctx={document:doc,window:{},navigator:{},localStorage:{getItem:()=>null,setItem(){}},matchMedia:()=>({matches:false}),innerWidth:1440,innerHeight:900,
  setTimeout:()=>0,clearTimeout(){},console,Date,Math,JSON,Set,Map,Object,Array,String,Number,Blob:function(){},URL:{createObjectURL:()=>""}};
ctx.window=ctx;vm.createContext(ctx);
const input=JSON.parse(fs.readFileSync(0,"utf8"));
ctx.__today=input.today||"";
vm.runInContext(js,ctx,{filename:"template.js"});
ctx.__rows=input.rows;
const out=vm.runInContext(`(function(){rows=__rows.map(o=>({kind:"",job:"",setup:"",lot:"",wafer_id:"",status:"Pass",norm_status:"",scan_type:"",recipe:"",wafer_start_time:"",wafer_end_time:"",batch_start:"",batch_end:"",report:"",ini_match:"EXACT",data_issue:"",...o}));
  rows.forEach(r=>{r.norm_status=r.norm_status||normStatus(r.status);});
  D=build();const res={devices:devNames,days:dataDays(),per:{},attempts:[],index:{unresolved:D._index.nUnresolved,cross:D._index.nCross,same:D._index.nSame,dup:D._index.nDup}};
  for(const n of devNames){res.per[n]={};for(const k of dataDays()){const m=dayMetrics(D[n],k);res.per[n][k]={run:m.run,err:m.err,stop:m.stop,test:m.testRun,dup:m.dup,rescan:m.rescan,rework:m.rework,off:m.off,overlap:m.overlap,denom:m.denom,util:m.util,nErr:m.nErr,nWafer:m.nWafer,nTest:m.nTest,nDup:m.nDup,nRescan:m.nRescan,nCross:m.nCross,hasData:m.hasData,
      items:m.items.map(i=>({kind:i.kind,s:i.s,e:i.e,sec:i.sec,disp:i.g.disp,wafer:i.g.r.wafer_id,lot:i.g.r.lot}))};}}
  for(const a of D._index.attempts){res.attempts.push({dev:a.dev,wafer:a.r.wafer_id,lot:a.r.lot,report:a.r.report,timed:a.timed,s:a.s,rel:a.rel,conf:a.conf,no:a.no,of:a.of,prior:a.prior?{dev:a.prior.dev,s:a.prior.s}:null,disp:a.timed?a.g.disp:null,refs:a.timed?a.g.refs:null,rawDups:a.timed?a.g.rawDups:null,why:a.why});}
  const keys=dataDays();const f=fleetAvg(keys);res.fleet={util:f.util,sumUtil:f.sumUtil,n:f.n};
  res.loss=keys.map(k=>{const L=lossCalc(devNames.map(n=>({n,m:dayMetrics(D[n],k)})));const fa=fleetAvg([k]);return{k,ppSum:L.ppSum,util:fa.util,rows:L.rows.map(r=>[r.id,r.sec,r.pp])};});
  return res;})()`,ctx);
process.stdout.write(JSON.stringify(out));
