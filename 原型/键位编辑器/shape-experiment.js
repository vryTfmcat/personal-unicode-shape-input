"use strict";
const $=s=>document.querySelector(s);
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function table(headers,rows){const t=el("table"),head=el("tr");headers.forEach(h=>head.append(el("th",h)));t.append(head);rows.forEach(row=>{const tr=el("tr");row.forEach(v=>tr.append(el("td",String(v))));t.append(tr);});const div=el("div",undefined,"scroll-table");div.append(t);return div;}
let data,model,report,reviews={decisions:[]},limit=80,current=[],selection=0;
const detailCache=new Map();
function glyph(row){
  if(row.preview){const n=el("span",undefined,"glyph-sprite");n.style.backgroundImage=`url("${row.preview.url}")`;n.style.backgroundPosition=`-${row.preview.x}px -${row.preview.y}px`;n.setAttribute("role","img");n.setAttribute("aria-label",row.char);return n;}
  return el("span",row.char,"glyph");
}
function objectGlyph(row,o){
  const frame=el("span",undefined,"object-frame");frame.append(glyph(row));
  const box=el("span",undefined,"object-box"),[x0,y0,x1,y1]=o.bbox;
  box.style.left=x0+"px";box.style.top=y0+"px";box.style.width=Math.max(3,x1-x0)+"px";box.style.height=Math.max(3,y1-y0)+"px";
  frame.append(box);frame.title="蓝框："+o.id;return frame;
}
async function select(row){
  const selected=++selection;
  if(row.detailUrl){
    $("#detail").replaceChildren(el("h2",`${row.char} · 正在读取路径依据…`));
    try {
      if(!detailCache.has(row.detailUrl)){
        const r=await fetch(row.detailUrl,{cache:"no-store"});if(!r.ok)throw Error("路径依据读取失败");
        const chunk=await r.json();if(chunk.experimentId!==data.id)throw Error("路径版本不一致");
        if(detailCache.size>=8)detailCache.delete(detailCache.keys().next().value);
        detailCache.set(row.detailUrl,chunk.records);
      }
      const full=detailCache.get(row.detailUrl).find(r=>r.cp===row.cp);if(!full)throw Error("该字符的路径依据缺失");row=full;
    }catch(e){if(selected===selection)$("#detail").append(el("p",e.message,"warning"));return;}
  }
  if(selected!==selection)return;
  const target=$("#detail");target.replaceChildren(el("h2",`${row.char} · U+${row.cp.toString(16).toUpperCase().padStart(4,"0")}`),glyph(row));
  target.append(el("p",`旧主桶 ${row.oldBucket}${row.oldReviewed?"（已确认）":""} → 候选主桶 ${row.bucket}；${row.familyKey?data.definitions.families[row.familyKey].meaning:"形族待定，仅保留第一位"}。`));
  target.append(el("p",`状态：机器候选，未替换旧确认。参考字体：${row.font?.family||"无法观测"}；${row.font?.path||""}`));
  if(row.warnings.length)target.append(el("p",row.warnings.join("；"),"warning"));
  target.append(el("p",`形族入口：${row.familyRoutes.map(r=>`${r.bucket}${r.familyKey}（${data.definitions.families[r.familyKey].meaning}，观察${r.target}）`).join("；")||"无"}`));
  const list=el("div",undefined,"path-list");
  for(const path of row.paths){const card=el("article",undefined,"path");card.append(el("h3",path.code));
    for(const e of path.evidence){const third=data.definitions.third[e.third],fourth=path.code.length===4?data.definitions.fourth[path.code[3]]:null;
      card.append(el("p",`${path.code[0]}＝主桶；${path.code[1]}＝${data.definitions.families[path.code[1]].meaning}；${e.third}＝${third.meaning}；${fourth?path.code[3]+"＝"+fourth.meaning:"停在三码，无补位"}`));
      const object=row.objects.find(o=>o.id===e.objectId);
      card.append(objectGlyph(row,object));
      card.append(el("p",`取形对象 ${e.objectId}（${object.kind}），范围 [${object.bbox.map(v=>Math.round(v*100)/100).join(", ")}]。${e.condition}。${e.attribute}。${e.status==="proposal"?"新增候选键义待审议":"沿用确认键义；本字符应用仍待审议"}。`,"evidence"));
    }list.append(card);
  }
  target.append(list);if(!row.paths.length)target.append(el("p","没有可靠的后三位路径；不补码。"));
}
function show(){
  const code=$("#code").value.trim().toLowerCase(),text=$("#character").value;
  current=text?model.characters(text):code?model.query(code):data.records;
  $("#resultCount").textContent=`${current.length.toLocaleString()} 个候选 · 显示 ${Math.min(limit,current.length)} 个 · ${text?"字符／码位检索":code?"前缀 "+code:"全部普通字符"}`;
  $("#results").replaceChildren(...current.slice(0,limit).map(row=>{const b=el("button",undefined,"tile");b.type="button";b.append(glyph(row),el("span",`${row.bucket} · ${row.familyKey||"待定族"}`),el("small","U+"+row.cp.toString(16).toUpperCase()));b.onclick=()=>select(row);return b;}));
  $("#more").hidden=limit>=current.length;
  if(text&&current.length===1)select(current[0]);
}
function setCode(code){$("#code").value=code;$("#character").value="";limit=80;show();renderFamilies();}
function renderFamilies(){
  const first=$("#code").value[0];$("#families").replaceChildren(...Object.entries(data.definitions.families).map(([key,f])=>{
    const buckets=data.familyBuckets[key]||[];const b=el("button",`${key} · ${f.meaning}`);b.type="button";b.disabled=!buckets.length;
    b.onclick=()=>setCode((first&&model.query(first+key).length?first:buckets[0])+key);return b;
  }));
}
function renderDefinitions(){
  if(reviews.boundaryDecisions?.length){$("#benchmarks").append(el("h3","本轮已确认的边界"),table(["已确认内容","适用范围"],reviews.boundaryDecisions.map(r=>[r.meaning,r.scope])),el("p",reviews.candidateDataStatus,"warning"));}

  for(const [key,f] of Object.entries(data.definitions.families)){const rep=data.representatives[key],d=el("div",undefined,"definition");
    d.append(el("h3",`${key} · ${f.meaning} · ${f.id}`),el("p",`主桶 ${rep.buckets.join(" / ")||"未分配"}；主族候选 ${rep.count} 字。待审议。`),el("p",f.boundary));
    const examples=el("div",undefined,"keys");for(const cp of [...new Set([...rep.centre.slice(0,6),...rep.boundary.slice(-4)])]){const r=model.byCp.get(cp);if(!r)continue;const b=el("button");b.append(glyph(r));b.onclick=()=>select(r);examples.append(b);}d.append(examples,el("p",`原型：${f.anchors.join(" ")}；反例提示：${f.counterexamples.join(" ")}。这些不是人工准确率的独立测试集。`));$("#familyDefinitions").append(d);
  }
  $("#rules").append(table(["第三位","功能ID／含义","状态","对象与条件","正例／反例"],Object.entries(data.definitions.third).map(([k,v])=>[k,v.function+" · "+v.meaning,v.status==="proposal"?(reviews.ruleDecisions?.some(r=>r.function===v.function&&r.decision==="accepted")?"功能已确认；字母与机器应用待审议":"新候选，未审议"):"旧键义已确认，机器应用待审议",v.condition,v.positive+" / "+v.negative])));
  $("#rules").append(el("p","旧试验键未自动启用："+Object.entries(data.definitions.legacyTrialKeys).map(([k,v])=>k+"="+v).join("；")));
  $("#fourth").append(el("h3","第四位 · 已确认布局"),table(["键","功能ID","含义"],Object.entries(data.definitions.fourth).map(([k,v])=>[k,v.function,v.meaning])));
  for(const b of data.benchmarks){const d=el("div",undefined,"definition");d.append(el("h3",b.characters.join(" ")+" · "+b.relation),el("p",b.rationale+"；人工状态："+(reviews.decisions.some(r=>r.decision==="accepted"&&r.benchmarkId===b.id&&JSON.stringify(r.characters)===JSON.stringify(b.characters)&&r.relation===b.relation&&r.rationale===b.rationale)?"本组关系已确认（不含字母、全族成员及主桶迁移）":"尚未审议")),el("p","机器预测："+Object.entries(b.predictions).map(([c,f])=>c+"→"+(f||"待定")).join("；")));$("#benchmarks").append(d);}
}
async function init(){
  const load=async path=>{const r=await fetch(path,{cache:"no-store"});if(!r.ok)throw Error(path+"读取失败");return r.json();};
  [data,report,reviews]=await Promise.all([load("data/shape-experiment.json"),load("data/shape-experiment-report.json"),load("data/shape-experiment-review.json")]);
  if(data.id!==report.experimentId)throw Error("数据与报告版本不一致，请重新载入");
  const profileResponse=await fetch('data/shape-review-profile.json',{cache:'no-store'});
  if(profileResponse.ok){const profile=await profileResponse.json();if(profile.enabled&&profile.experimentId===data.id)document.querySelector('.notice').textContent='本轮核对版 · 已接入主编辑器全形模式；小狼毫发布状态以发布记录为准。临时启用不代表逐字归属已确认。';}
  model=window.ShapeExperiment.model(data);
  $("#status").textContent=`${data.id} · ${data.records.length.toLocaleString()} 普通字符 · ${report.familyPending.toLocaleString()} 待定族 · ${report.pathCount.toLocaleString()} 条候选路径`;
  $("#buckets").replaceChildren(...[..."abcdefghijklmnopqrstuvw"].map(a=>{const b=el("button",`${a} · ${report.bucketCounts[a]||0}`);b.onclick=()=>setCode(a);return b;}));
  $("#report").append(el("p",`主桶变化提案 ${report.changedPrimary} 字，其中旧确认项 ${report.changedPreviouslyReviewed} 字。未改写旧确认；核对版临时启用不等于接受迁移。xyz与历史资料保持不变。`),
    table(["主桶","形族／子族","主族字符数"],data.bucketGroups.map(g=>[g.bucket,g.families.map(k=>data.definitions.families[k].meaning).join("＋")+(g.proportion?" · "+({tall:"纵长",balanced:"近等宽高",wide:"横展"}[g.proportion]):""),g.count])),
    table(["前缀长度","已占用前缀","候选中位数","最大候选数"],Object.entries(report.prefixDistribution).map(([n,r])=>[n,r.occupied,r.medianCandidates,r.maximumCandidates])),
    el("p",`有效第四位组合空间 ${report.fourthDefinedSpace.toLocaleString()}，四码已占用 ${report.occupiedFourCodes.toLocaleString()}；空组合 ${report.emptyFourthDefinedSpace.toLocaleString()}。不强填空键。`),
    el("p",report.humanEvaluation),el("p",report.limitations.join("；")),
    table(["偏离容量目标的桶","数量","原因"],Object.entries(report.capacityDeviations).map(([k,v])=>[k,v.count,v.reason])));
  const stable=await load("data/shape-experiment-stability.json");
  $("#stability").append(el("h3","渲染稳定性专项检查"),table(["字符","参考字体","五次字号／粗细预测","稳定","替代字体"],stable.map(r=>[r.char,r.font,r.views.map(v=>v.family||"待定").join(" / "),r.familyStable?"是":"否，待核对",r.alternateFont?`${r.alternateFont.font} → ${r.alternateFont.family||"未确认"}；${r.alternateFont.sameFamily?"同族":"待核对"}`:"无可用替代记录"])));
  $("#code").oninput=()=>{limit=80;$("#character").value="";show();renderFamilies();};
  $("#character").oninput=()=>{limit=80;$("#code").value="";show();};
  $("#clear").onclick=()=>{setCode("");$("#character").value="";};$("#more").onclick=()=>{limit+=80;show();};
  const initial=new URLSearchParams(location.search).get("char");if(initial)$("#character").value=initial;
  renderFamilies();renderDefinitions();show();
}
init().catch(e=>{$("#status").textContent="实验数据未能载入";$("#error").textContent=e.message;});
