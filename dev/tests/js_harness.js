/* template.html 의 스크립트를 브라우저 없이 Node 에서 실행해 **모델·순수 렌더 함수**를 검사하는 하네스.
   stdin 으로 JSON 을 받는다.
     { classify:[문구…] }                                   → 문구별 {causes, outcome, norm_status, unmapped}
     { rows:[행 객체…], meta:{…}, rules?:RULES 모양 }        → buildModel(rows, meta, rules) 결과(JSON)
         rules 를 주지 않으면 template 의 RULES(product 프로필) 그대로. legacy 는 {profile:"legacy", waitToObsEnd:false, denomToday:false,
         abortIsError:false, estimateFromBatch:false} — 네 스위치를 끈 디자인 스크립트 동일성 검사용.
     { embedded:{cols,pooled,pool,rows,meta}, rules? }      → 접힌 payload 를 로더(unfold)로 편 뒤 같은 결과
     { globals:["JOB_ALIAS","MODEL_VERSION",…] }            → template 의 전역 상수 값들
     { screen:{rows, meta, state?:{…}, calls:[[함수이름, 인자…], …]} }
         → init() 이 하는 준비(devStatus · applySettings · buildModel · state.dayI)를 한 뒤 전역 함수를 차례로 불러 반환값을 돌려준다
           (homeHtml · reportHtml · errPopupHtml 같은 순수 문자열 렌더 함수, reportUrl · collectChip · causeText · lotKey 같은 도우미).
   DOM 은 아무것도 하지 않는 대역(stub)이다 — 화면이 실제로 그려지고 눌리는지는 Chromium(test_dashboard_browser.py)으로 따로 본다. 네트워크·파일 쓰기 없음. */
"use strict";
const fs=require("fs"),vm=require("vm"),path=require("path");
const html=fs.readFileSync(path.join(__dirname,"..","..","aoi_capacity","ui","assets","template.html"),"utf8");
let js=html.slice(html.indexOf("<script>\n")+9,html.lastIndexOf("</script>"));
js=js.replace(/loadDemo\(\);\s*$/,"");                       // 부팅은 하지 않는다
const input=JSON.parse(fs.readFileSync(0,"utf8"));
const stub=()=>new Proxy(function(){}, {get:(t,k)=>k===Symbol.toPrimitive?()=>"":k==="length"?0:k==="hidden"?false:stub(),set:()=>true,apply:()=>stub(),has:()=>true});
const ctx={document:stub(),window:{},navigator:{},localStorage:{getItem:()=>null,setItem(){}},matchMedia:()=>({matches:false}),innerWidth:1440,innerHeight:900,
  setTimeout:()=>0,clearTimeout(){},console,Date,Math,JSON,Set,Map,Object,Array,String,Number,Blob:function(){},URL:{createObjectURL:()=>""},CSS:{escape:s=>String(s)}};
ctx.window=ctx;vm.createContext(ctx);
vm.runInContext(js,ctx,{filename:"template.js"});
/* 출력이 수 MB 일 수 있어 process.exit 을 부르지 않는다(파이프 쓰기가 잘린다) — 쓰고 자연스럽게 끝낸다. */
const emit=o=>{process.stdout.write(JSON.stringify(o===undefined?null:o));};
if(input.classify){ctx.__ph=input.classify;emit(vm.runInContext(`(function(){const o={};for(const s of __ph)o[s]={causes:normCauses(s),outcome:normOutcome(s),norm_status:normStatus(s),unmapped:isUnmappedStatus(s)};return o;})()`,ctx));}
else if(input.globals){ctx.__g=input.globals;emit(vm.runInContext(`(function(){const o={};for(const n of __g)o[n]=eval(n);return o;})()`,ctx));}
else if(input.screen){ctx.__sc=input.screen;
  emit(vm.runInContext(`(function(){const I=__sc;rows=I.rows||[];meta=I.meta||{};
    for(const d of (meta.devices||[]))if(d.status)devStatus[d.name]={status:d.status,error:d.error||"",readErrors:d.read_errors||0};
    applySettings(meta);D=buildModel(rows,meta);state.dayI=D.day?D.days.indexOf(D.day):-1;Object.assign(state,I.state||{});
    return (I.calls||[]).map(([fn,...args])=>{const f=eval(fn);const v=typeof f==="function"?f.apply(null,args):f;return v===undefined?null:v;});})()`,ctx));}
else{ctx.__in=input;
  emit(vm.runInContext(`(function(){const I=__in;let rs=I.rows||[];let mt=I.meta||{};
    if(I.embedded){rs=unfold(I.embedded);mt=I.embedded.meta||mt;}
    return buildModel(rs,mt,I.rules||undefined);})()`,ctx));}
