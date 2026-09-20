/* template.html 의 스크립트를 브라우저 없이 Node 에서 실행해 **모델 함수만** 검사하는 하네스.
   stdin 으로 JSON 을 받는다.
     { classify:[문구…] }                         → 문구별 {causes, outcome, norm_status, unmapped}
     { rows:[행 객체…], meta:{…}, rules?:{waitToObsEnd, denomToday} } → buildModel(rows, meta, rules) 결과(JSON)
     { embedded:{cols,pooled,pool,rows,meta}, rules? } → 접힌 payload 를 로더로 편 뒤 같은 결과
   DOM 은 아무것도 하지 않는 대역(stub)이다 — 화면은 Chromium 으로 따로 본다. 네트워크·파일 쓰기 없음. */
"use strict";
const fs=require("fs"),vm=require("vm"),path=require("path");
const html=fs.readFileSync(path.join(__dirname,"..","..","aoi_capacity","ui","assets","template.html"),"utf8");
let js=html.slice(html.indexOf("<script>\n")+9,html.lastIndexOf("</script>"));
js=js.replace(/loadDemo\(\);\s*$/,"");                       // 부팅은 하지 않는다
const input=JSON.parse(fs.readFileSync(0,"utf8"));
const stub=()=>new Proxy(function(){}, {get:(t,k)=>k===Symbol.toPrimitive?()=>"":k==="length"?0:k==="hidden"?false:stub(),set:()=>true,apply:()=>stub(),has:()=>true});
const ctx={document:stub(),window:{},navigator:{},localStorage:{getItem:()=>null,setItem(){}},matchMedia:()=>({matches:false}),innerWidth:1440,innerHeight:900,
  setTimeout:()=>0,clearTimeout(){},console,Date,Math,JSON,Set,Map,Object,Array,String,Number,Blob:function(){},URL:{createObjectURL:()=>""}};
ctx.window=ctx;vm.createContext(ctx);
vm.runInContext(js,ctx,{filename:"template.js"});
if(input.classify){ctx.__ph=input.classify;const m=vm.runInContext(`(function(){const o={};for(const s of __ph)o[s]={causes:normCauses(s),outcome:normOutcome(s),norm_status:normStatus(s),unmapped:isUnmappedStatus(s)};return o;})()`,ctx);process.stdout.write(JSON.stringify(m));process.exit(0);}
ctx.__in=input;
const out=vm.runInContext(`(function(){const I=__in;let rs=I.rows||[];let mt=I.meta||{};
  if(I.embedded){rs=unfold(I.embedded);mt=I.embedded.meta||mt;}
  return buildModel(rs,mt,I.rules||undefined);})()`,ctx);
process.stdout.write(JSON.stringify(out));
