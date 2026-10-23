"use strict";
const M = window.UnicodeModes;
const m$ = selector => document.querySelector(selector);
const modeLabels = {block: "区块", shape: "全形", personal: "收藏", chinese: "中文", extended: "中文扩展"};
const mEscape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
const BOOK_DRAFT = "unicode-codebooks-recovery-v1", PREF_KEY = "unicode-modes-preferences-v1";
let mBase, mBook, mModel, mStage = null, mRevision, mDirty = false, mSaving = null, mConflict = false, mGeneration = 0, mTimer;
let mPrefs = {editMode: "block", modes: ["block"], chinese: false, extended: false, shapeView: "stage"};
let mPage = "", mSelected = "u-25cb", mLimit = 96, mQueryLimit = 60, mPrefixPreview = null;
let mReview=null,mReviewManifest=null;
function mUsingStage() { return !!mStage && mPrefs.editMode === "shape" && mPrefs.shapeView === "stage"; }
function mUsingReview(){return !!mReview&&mPrefs.editMode==='shape'&&mPrefs.shapeView==='review';}
function mReviewKeyTable(){
  if(!mReview)return;
  const defs=mReview.definitions, first={x:'组合与附加标记',y:'排除文字收纳',z:'中文与汉字构件'};
  for(const g of mReview.bucketGroups)first[g.bucket]=g.families.map(k=>defs.families[k].meaning).join('＋')+(g.proportion?' · '+({wide:'横展',tall:'纵长',balanced:'近等宽高'}[g.proportion]):'');
  for(const r of mReview.records)if(!first[r.bucket])first[r.bucket]='旧桶入口 · 形族待定';
  const tables=[['第一位 · 主桶',first],['第二位 · 形族',Object.fromEntries(Object.entries(defs.families).map(([k,v])=>[k,v.meaning]))],['第三位 · 取形规则',Object.fromEntries(Object.entries(defs.third).map(([k,v])=>[k,v.meaning]))],['第四位 · 所取对象属性',Object.fromEntries(Object.entries(defs.fourth).map(([k,v])=>[k,v.meaning]))]];
  m$('#shapeReviewRules').innerHTML=`<p>${mEscape(mReview.id)} · 核对用候选，临时启用不代表逐字归属已确认。双环字母未分配；待分类字符不补码。第四位c表示尺寸“中”，不表示居中。</p>`+tables.map(([title,keys])=>`<h3>${title}</h3><div class="rules-grid">${[...'abcdefghijklmnopqrstuvwxyz'].map(k=>`<span class="rule-item"><strong>${k}</strong> ${mEscape(keys[k]||'未分配')}</span>`).join('')}</div>`).join('');
}

function mStatus(message, error=false) { m$("#bookStatus").textContent = message; m$("#bookStatus").classList.toggle("error-status", error); }
function mToast(message) { const t = m$("#toast"); t.textContent = message; t.classList.add("show"); clearTimeout(mToast.timer); mToast.timer = setTimeout(() => t.classList.remove("show"), 3000); }
function mRecovery() { localStorage.setItem(BOOK_DRAFT, JSON.stringify({baseRevision: mRevision, codebooks: mBook})); }
function mChanged(rebuild=true) {
  mGeneration++; mDirty = true;
  try { mRecovery(); } catch { mStatus("恢复草稿空间不足；请立即导出码本", true); }
  if (rebuild) { mModel = M.model(mBase, mBook, mStage,mReview); mRenderNav(); mRenderGrid(); mRenderCandidates(); mRenderStats(); }
  clearTimeout(mTimer); mTimer = setTimeout(() => mFlush().catch(error => mStatus(error.message, true)), 900);
  mStatus("待保存到项目");
}
async function mFlush() {
  if (mSaving) return mSaving;
  if (mConflict) throw Error("版本冲突：请导出当前草稿，再载入项目最新码本");
  mSaving = (async () => {
    while (mDirty) {
      const generation = mGeneration;
      const response = await fetch("/api/codebooks", {method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify({baseRevision: mRevision, codebooks: M.clone(mBook)})});
      const payload = await response.json();
      if (!response.ok) {
        if (response.status === 409) mConflict = true;
        throw Error(response.status === 409 ? "另一窗口已保存；当前草稿已保留，请导出后重新载入" : payload.error);
      }
      mRevision = payload.revision;
      mDirty = generation !== mGeneration;
      if (mDirty) mRecovery(); else localStorage.removeItem(BOOK_DRAFT);
    }
    mStatus("码本已保存到项目");
  })();
  try { await mSaving; } finally { mSaving = null; }
}
function mStorePrefs() { localStorage.setItem(PREF_KEY, JSON.stringify(mPrefs)); }
function mSetMode(mode, single=false) {
  mPrefs.editMode = mode;
  if (single) mPrefs.modes = [mode];
  mPage = ""; mLimit = 96;
  document.querySelectorAll(".mode-button").forEach(b => b.classList.toggle("active", b.dataset.mode === mode));
  m$("#personalTools").hidden = mode !== "personal";
  ["saveStatus", "snapshotGraphButton", "exportGraphButton"].forEach(id => m$("#"+id).hidden = mode !== "personal");
  m$("#importGraphInput").closest("label").hidden = mode !== "personal";
  document.querySelectorAll(".view-panel").forEach(p => p.classList.toggle("active", p.id === "characterView"));
  document.querySelectorAll("[data-source]").forEach(c => { c.checked = mPrefs.modes.includes(c.dataset.source); });
  m$("#hanEnabled").checked = mPrefs.chinese; m$("#hanExtended").checked = mPrefs.extended;
  m$("#modeDescription").textContent = {block: "平面 → 区块。四码机器初稿；真实区块固定，局部规则由你核定。", shape: "跨区块按图形查找。两码查形族；已确认的细分路径可查三／四码。机器粗分类与待核对路径分别标明。", personal: "个人收藏码独立保存。旧码是待选资料，默认停用；这里的修改不会更改区块码或全形码。"}[mode];
  m$("#shapeStageControl").hidden = mode !== "shape" || !mStage;
  m$("#shapeStageSummary").hidden = mode !== "shape" || !mStage;
  m$('#shapeReviewSummary').hidden=!mUsingReview();
  m$("#shapeView").value = mPrefs.shapeView;
  m$('#publishBooks').textContent=mReview?'发布本轮核对版到小狼毫':'发布到小狼毫';
  m$("#candidateInput").placeholder = mStage && mPrefs.shapeView === "stage" ? "例如 i：输入一个桶字母查询阶段分桶" : "例如 oe：查询历史两码形族";
  if (mUsingStage()) m$("#modeDescription").textContent = "阶段分桶：a–w 按图形相似度排列；输入一个桶字母查询主归属及补充入口。后三位尚未制定，不生成完整四码。本阶段未发布到小狼毫。";
  if(mUsingReview()){m$('#shapeStageSummary').hidden=true;m$('#modeDescription').textContent='本轮核对版：主桶 → 形族 → 规则 → 对象属性。一至四键均可查询；临时键位与小狼毫使用同一版本，逐字归属仍待你核对。';m$('#candidateInput').placeholder='输入1–4个字母，逐层检查候选';}
  mStorePrefs(); mRenderNav(); mRenderGrid(); mRenderInspector(); mRenderCandidates(); mRenderStats();
}
function mCurrentCode(c) { return mUsingReview()?c.shapeReview?`${c.shapeReview.bucket}${c.shapeReview.familyKey||''} · ${c.shapeReview.codes.length}条路径`:'待分类':mUsingStage() ? c.stageShape ? `桶 ${c.stageShape.bucket}` : "待分类" : mPrefs.editMode === "block" ? c.blockCode?.code || "" : mPrefs.editMode === "shape" ? c.shape?.coarse || "" : c.personal.map(a => a.code + (a.enabled ? "" : "·停用")).join(" "); }
function mSearch(c, text) {
  return `${c.char} ${c.codepoint} ${c.unicodeName} ${c.sourceBlock} ${c.blockCode?.code || ""} ${c.shape?.coarse || ""} 桶${c.stageShape?.bucket||""} ${c.personal.map(a=>a.code).join(" ")} ${c.chinese?.codes.map(a=>a.code).join(" ") || ""}`.toLowerCase().includes(text);
}
function mGroups() {
  if (mPrefs.editMode === "block") return mModel.blocks.map(b => ({id:b.id, label:b.name, detail:b.han ? "汉字研究 · 不占前缀" : b.prefixes.join(" / "), plane:b.plane, count:b.count}));
  if (mPrefs.editMode === "shape") {
    if(mUsingReview())return [...'abcdefghijklmnopqrstuvwxyz'].map(k=>({id:k,label:`${k} · 主桶`,detail:'核对版主归属与补充入口',count:mModel.reviewIndex.get(k)?.length||0})).concat([...mModel.reviewIndex].filter(([k])=>k.length===2).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>({id:k,label:`${k} · ${mReview.definitions.families[k[1]]?.meaning||'形族'}`,detail:'两键形族入口',count:v.length})),[{id:'unclassified',label:'待分类 · 不补码',detail:'保留全部字符浏览',count:mReview.unclassified.length}]);
    if (mUsingStage()) return [...mModel.stageGroups].map(([bucket, chars]) => ({id:bucket,label:`${bucket} · ${bucket==="x"?"组合与附加标记":bucket==="y"?"排除文字收纳":bucket==="z"?"中文与汉字构件":"图形桶"}`,detail:"xyz".includes(bucket)?"独立收纳 · 不计普通桶容量":"主归属 · 按图形相似度排列",count:chars.length})).concat([{id:"unclassified",label:"未分类 · 待补字形",detail:"保留研究浏览",count:mModel.characters.filter(c=>!c.stageShape).length}]);
    const groups = [...mModel.indexes.shape.entries()].filter(([code])=>code.length===2).sort(([a],[b])=>a.localeCompare(b)).map(([code,chars]) => ({id:code,label:`${code} · ${mBase.shapeRules.main[code[0]]} / ${mBase.shapeRules.state[code[1]]}`, detail:"跨区块形族", count:chars.length}));
    groups.unshift({id:"unclassified",label:"未分类 · 待核对",detail:"没有可靠粗形依据",count:mModel.characters.filter(c=>!c.han&&!c.shape?.coarse).length});
    return groups;
  }
  return [{id:"favorites",label:"常用收藏",detail:"收藏不等于启用输入码",count:mModel.characters.filter(c=>c.favorite).length},
    {id:"enabled",label:"已启用收藏码",detail:"独立的 2–4 字母别名",count:mModel.characters.filter(c=>c.personal.some(a=>a.enabled)).length},
    {id:"legacy",label:"待选旧码",detail:"已保留；默认停用",count:mModel.characters.filter(c=>c.personal.some(a=>!a.enabled)).length}];
}
function mRenderNav() {
  const groups = mGroups();
  if (!groups.some(g=>g.id===mPage)) mPage = mPrefs.editMode === "block" ? groups.find(g=>g.label === "Geometric Shapes")?.id || "block-25a0" : mPrefs.editMode === "shape" ? mUsingReview() ? mReview.records.find(r=>r.cp===0x25cb)?.bucket||"a" : mUsingStage() ? "i" : "oe" : "favorites";
  if (!groups.some(g=>g.id===mPage)) mPage = groups[0]?.id || "";
  const search = m$("#pageSearchInput").value.toLowerCase().trim();
  const nav = m$("#pageNav"); nav.replaceChildren();
  let plane = null, parent = nav;
  groups.filter(g=>`${g.label} ${g.detail} ${g.plane ?? ""}`.toLowerCase().includes(search)).forEach(g => {
    if (g.plane !== undefined && g.plane !== plane) {
      plane = g.plane;
      const section = document.createElement("details"); section.open = true;
      const title = document.createElement("summary"); title.textContent = `平面 ${plane}`; section.append(title); nav.append(section); parent = section;
    }
    const b = document.createElement("button"); b.className = "page-button" + (g.id===mPage?" active":""); b.type="button";
    b.innerHTML = `<span class="page-name">${mEscape(g.label)}<small>${mEscape(g.detail)}</small></span><span class="page-number">${g.count.toLocaleString()}</span>`;
    b.onclick=()=>{mPage=g.id;mLimit=96;mRenderNav();mRenderGrid();mRenderRuleEditor();};
    b.ondragover=event=>event.preventDefault();
    b.ondrop=event=>{event.preventDefault();const c=mModel.byId.get(event.dataTransfer.getData("text/plain"));if(!c)return;
      if(mUsingStage()||mUsingReview()){mToast("当前核对视图不通过拖动改写归属；备注仍可保存，历史形码可另行维护。");return;}
      if(mPrefs.editMode==="shape" && g.id!=="unclassified") {mBook.shapeOverrides[c.id]={...(mBook.shapeOverrides[c.id]||{}),coarse:g.id,detail:null,status:"draft",ruleVersion:"coarse-v1",reference:"用户拖动分类；待核对"};mChanged();}
      else if(mPrefs.editMode==="personal" && g.id==="favorites") {mMeta(c.id).favorite=true;if(!mBook.commonOrder.includes(c.id))mBook.commonOrder.push(c.id);mChanged();}
      else mToast("真实 Unicode 区块固定；请在详情选择本区块前缀");};
    parent.append(b);
  });
  mRenderRuleEditor();
}
function mPageCharacters() {
  if(mPrefs.editMode==="block") return mModel.characters.filter(c=>c.blockId===mPage);
  if(mUsingReview())return mPage==='unclassified'?mModel.characters.filter(c=>!c.shapeReview):mModel.reviewIndex.get(mPage)||[];
  if(mUsingStage()) return mPage==="unclassified"?mModel.characters.filter(c=>!c.stageShape):mModel.stageGroups.get(mPage)||[];
  if(mPrefs.editMode==="shape") return mPage==="unclassified"?mModel.characters.filter(c=>!c.han&&!c.shape?.coarse):mModel.indexes.shape.get(mPage)||[];
  const result=mModel.characters.filter(c=>mPage==="favorites"?c.favorite:mPage==="enabled"?c.personal.some(a=>a.enabled):c.personal.some(a=>!a.enabled));
  const rank=new Map(mBook.commonOrder.map((id,i)=>[id,i]));return result.sort((a,b)=>(rank.get(a.id)??1e9)-(rank.get(b.id)??1e9));
}
function mCard(c,code,sources="") {
  const card=document.createElement("button");card.type="button";card.className="glyph-card"+(mSelected===c.id?" selected":"");card.draggable=true;
  card.innerHTML=`${c.favorite?'<span class="favorite-star">★</span>':""}<span class="glyph">${mEscape(c.char)}</span><span class="glyph-code">${mEscape(code||"未编码")}</span><span class="glyph-cp">${c.codepoint}</span><span class="glyph-page">${mEscape(sources||c.sourceBlock)}</span>`;
  card.title=`${c.unicodeName}\n${c.sourceBlock}`;
  card.onclick=()=>{mSelected=c.id;mRenderInspector();};card.ondragstart=e=>e.dataTransfer.setData("text/plain",c.id);return card;
}
function mRenderGrid() {
  const search=m$("#searchInput").value.toLowerCase().trim(), local=m$("#searchCurrentPage").checked;
  const all=mUsingStage()?[...mModel.stageGroups.values()].flat().concat(mModel.characters.filter(c=>!c.stageShape)):mModel.characters;
  const chars=(search&&!local?all:mPageCharacters()).filter(c=>!search||mSearch(c,search));
  const grid=m$("#glyphGrid");grid.replaceChildren(...chars.slice(0,mLimit).map(c=>mCard(c,mCurrentCode(c))));
  if(chars.length>mLimit){const more=document.createElement("button");more.className="load-more";more.textContent="继续显示 96 个";more.onclick=()=>{mLimit+=96;mRenderGrid();};grid.append(more);}
  m$("#pageTitle").textContent=mGroups().find(g=>g.id===mPage)?.label||"字符";
  m$("#pageCount").textContent=`${Math.min(chars.length,mLimit).toLocaleString()} / ${chars.length.toLocaleString()} 字符`;
}
function mRenderStats() {
  const entries=[...mModel.indexes.block.values()];
  const collisions=entries.filter(a=>a.length>1).length;
  const activeShape=mPrefs.shapeView==="review"&&mReview?mModel.reviewIndex:mPrefs.shapeView==="stage"&&mStage?mModel.stageIndex:mModel.indexes.shape;
  const codeSources=new Map();for(const mode of ["personal","block","shape"])for(const code of (mode==="shape"?activeShape:mModel.indexes[mode]).keys())codeSources.set(code,(codeSources.get(code)||0)+1);
  const overlap=[...codeSources.values()].filter(n=>n>1).length;
  const prefixes=new Set(mModel.blocks.flatMap(b=>b.prefixes));
  const shapeOverlap=[...prefixes].filter(code=>activeShape.has(code)).length;
  m$("#modeStatistics").textContent=`${mBase.statistics.nonHan.toLocaleString()} 非汉字 · ${prefixes.size}/676 前缀 · ${676-prefixes.size} 未分配前缀 · ${prefixes.size*676-mModel.indexes.block.size} 区块内空位 · ${collisions} 区块重码组 · ${overlap} 跨模式重合码 · ${shapeOverlap} 前缀与全形入口交叠`;
}
function mRenderCandidates() {
  const code=m$("#candidateInput").value.toLowerCase().replace(/[^a-z]/g,"").slice(0,4);m$("#candidateInput").value=code;
  const rows=mModel.query(code,mPrefs), target=m$("#candidateGrid");
  target.replaceChildren(...rows.slice(0,mQueryLimit).map(r=>mCard(r.character,code,r.sources.map(s=>s==="shape"&&mStage&&mPrefs.shapeView==="stage"?`全形·${r.character.stageShape?.bucket===code?"主归属":"补充入口"}`:modeLabels[s]).join("＋"))));
  if(rows.length>mQueryLimit){const more=document.createElement("button");more.className="load-more";more.textContent="继续显示候选";more.onclick=()=>{mQueryLimit+=60;mRenderCandidates();};target.append(more);}
  m$("#candidateCount").textContent=code?`${rows.length.toLocaleString()} 候选 · ${mPrefs.modes.map(s=>modeLabels[s]).join("＋")}${mPrefs.chinese?"＋中文":""}${mPrefs.shapeView==="stage"&&mStage?" · 全形使用阶段桶入口":""}`:mStage&&mPrefs.shapeView==="stage"?"全形阶段版：输入 1 个 a–w 字母查桶；多余字母不会被忽略。区块／收藏仍使用原有码。":"输入 2–4 字母测试；全形两码查族，三／四码查已启用路径";
  if(mReview&&mPrefs.shapeView==='review')m$('#candidateCount').textContent=code?`${rows.length.toLocaleString()} 候选 · 本轮全形核对版`:'输入1–4个字母逐层查询；候选不截断，不足四键也可选字。';
}
function mMeta(id) {return mBook.metadata[id] ||= {};}
function mRenderInspector() {
  document.dispatchEvent(new CustomEvent("unicode-character-selected", {detail:{id:mSelected}}));
  const c=mModel.byId.get(mSelected), panel=m$("#modeInspector");if(!c){panel.textContent="点选一个字符";return;}
  const block=mModel.blocks.find(b=>b.id===c.blockId);
  panel.innerHTML=`<div class="inspector-head"><span class="inspector-glyph">${mEscape(c.char)}</span><div><h2>${c.codepoint}</h2><p>${mEscape(c.unicodeName)}</p></div></div>
    <button class="button primary" id="mCopy">复制字符</button><label class="check-control"><input id="mFavorite" type="checkbox" ${c.favorite?"checked":""}>常用收藏</label>
    <dl class="metadata"><div><dt>固定来源</dt><dd>平面 ${c.plane} · ${mEscape(c.sourceBlock)}</dd></div><div><dt>区块码</dt><dd>${mEscape(c.blockCode?.code||"汉字不占前缀")} · ${c.blockCode?.status==="reviewed"?"已核对":"机器初稿"}</dd></div><div><dt>${mStage?"历史全形码":"全形码"}</dt><dd>${mEscape(c.shape?.coarse||"未分类")} · ${(c.shape?.paths||[]).filter(p=>p.enabled&&p.status==="reviewed").map(p=>p.code).join(" / ")||"细分未启用"} · ${c.shape?.status==="reviewed"?"已核对":"待核对"}</dd></div><div><dt>阶段主桶</dt><dd>${c.stageShape?mEscape(c.stageShape.bucket)+" · 桶内第 "+(c.stageShape.rank+1)+" 位":"未分类"}</dd></div><div><dt>小鹤码</dt><dd>${mEscape(c.chinese?.codes.map(a=>a.code+a.marks).join(" / ")||"未接入")}</dd></div></dl>
    <div id="modeEditFields"></div>
    <label class="form-field">备注<textarea id="mNote" rows="3">${mEscape(c.metadata.note||"")}</textarea></label>
    <details><summary>真实读音资料 · IPA 文本</summary><label class="form-field">语言<input id="mLanguage" value="${mEscape(c.metadata.language||"")}"></label><label class="form-field">被转写的原文<input id="mPronunciationText" value="${mEscape(c.metadata.pronunciationText||"")}"></label><label class="form-field">IPA<input id="mIPA" value="${mEscape(c.metadata.ipa||"")}"></label><label class="form-field">来源／生成器版本<input id="mPronunciationSource" value="${mEscape(c.metadata.pronunciationSource||"")}"></label><label class="form-field">审核说明<input id="mPronunciationStatus" value="${mEscape(c.metadata.pronunciationStatus||"")}"></label><p>无独立读音时可留空；名称朗读需注明。不存储音频。</p></details>`;
  m$("#mCopy").onclick=()=>navigator.clipboard.writeText(c.char).then(()=>mToast("已复制字符")).catch(()=>mToast("请手动复制字符"));
  m$("#mFavorite").onchange=e=>{mMeta(c.id).favorite=e.target.checked;if(e.target.checked&&!mBook.commonOrder.includes(c.id))mBook.commonOrder.push(c.id);mChanged();};
  [["mNote","note"],["mLanguage","language"],["mIPA","ipa"],["mPronunciationText","pronunciationText"],["mPronunciationSource","pronunciationSource"],["mPronunciationStatus","pronunciationStatus"]].forEach(([id,key])=>m$("#"+id).oninput=e=>{mMeta(c.id)[key]=e.target.value;mChanged(false);});
  const fields=m$("#modeEditFields");
  if(mUsingReview()){
    const r=c.shapeReview;
    fields.innerHTML=`<h3>本轮核对版</h3><p>${r?`主桶 ${r.bucket}；主形族 ${mEscape(r.semanticPrimaryFamilyId||r.familyId||'待定／收纳')}；${r.codes.length}条候选取形路径`:'尚无可靠编码，仅保留字符浏览'}</p><p>旧主桶：${mEscape(r?.oldBucket||r?.bucket||"无")} ${r?.oldReviewed?"（旧归属已确认）":""}。临时启用用于核对，不改变旧确认状态。${r?.pendingKeyboardFamilyIds?.length?'本形族字母尚未分配，只保留第一位入口。':''}</p><p>${mEscape((r?.codes||[]).join(' · ')||'后三位无可靠路径，不补码。')}</p><p><a href="shape-experiment.html?char=${encodeURIComponent(c.char)}" target="_blank">查看此字符的取形对象和全部依据</a></p>`;
    return;
  }
  if(mUsingStage()) {
    const s=c.stageShape;
    fields.innerHTML=`<h3>当前阶段分桶</h3><p>${s?`主归属：<strong>${s.bucket}</strong> · 桶内顺序 ${s.rank+1} · ${s.reviewed?"已确认归属":"机器分组，待逐字核对"}`:"尚未分桶"}</p><p>补充入口：${mEscape(s?.aliases.join(" / ")||"无")}</p><p>后续三位：留空，尚未分配。上方旧全形码仅为历史资料，不代表当前桶规则。</p><p>${mEscape(mStage.title)}；本轮归属保持固定。</p>`;
    return;
  }
  if(mPrefs.editMode==="block") {
    if(!c.blockCode){fields.innerHTML="<p>汉字保留研究浏览，可在收藏模式设置自己的码。</p>";return;}
    fields.innerHTML=`<label class="form-field">本区块前缀<select id="mBlockPrefix">${block.prefixes.map(p=>`<option ${c.blockCode.code.startsWith(p)?"selected":""}>${p}</option>`).join("")}</select></label><label class="form-field">区块四码<input id="mBlockCode" maxlength="4" value="${c.blockCode.code}"></label><p id="mCollision"></p><button id="mConfirm" class="button">确认此区块码</button><button id="mResetCode" class="button quiet">恢复机器建议</button>`;
    const saveCode=code=>{if(!/^[a-z]{4}$/.test(code)||!block.prefixes.includes(code.slice(0,2))){mToast("需要四个小写字母，并使用本区块拥有的前缀");mRenderInspector();return;}mBook.blockOverrides[c.id]={mode:"block",code,status:"draft",ruleVersion:mBook.rules[block.id]?.version||block.rules.version||"user-v1",evidence:"用户修改局部码"};mChanged();mRenderInspector();};
    m$("#mBlockCode").onchange=e=>saveCode(e.target.value.trim().toLowerCase());m$("#mBlockPrefix").onchange=e=>saveCode(e.target.value+c.blockCode.code.slice(2));
    const same=mModel.indexes.block.get(c.blockCode.code)||[];m$("#mCollision").textContent=same.length>1?`此码有 ${same.length} 个字符，请核对冲突：${same.map(i=>i.char).join(" ")}`:"此区块码唯一";
    m$("#mConfirm").onclick=()=>{mBook.blockOverrides[c.id]={...c.blockCode,status:"reviewed"};mChanged();mRenderInspector();};m$("#mResetCode").onclick=()=>{delete mBook.blockOverrides[c.id];mChanged();mRenderInspector();};
  } else if(mPrefs.editMode==="shape") {
    fields.innerHTML=`<div class="key-pair"><label class="form-field">第一位 · 主形<select id="mMain"><option value="">未分类</option>${Object.entries(mBase.shapeRules.main).map(([k,v])=>`<option value="${k}" ${c.shape?.coarse?.[0]===k?"selected":""}>${k} · ${mEscape(v)}</option>`).join("")}</select></label><label class="form-field">第二位 · 状态<select id="mState"><option value="">未分类</option>${Object.entries(mBase.shapeRules.state).map(([k,v])=>`<option value="${k}" ${c.shape?.coarse?.[1]===k?"selected":""}>${k} · ${mEscape(v)}</option>`).join("")}</select></label></div><label class="form-field">参考字体与判断依据<textarea id="mShapeReference">${mEscape(c.shape?.reference||"")}</textarea></label><p>第三、四位尚未制定，保持为空。${mEscape(c.shape?.evidence||"")}</p><button id="mConfirm" class="button">确认粗分类</button>`;
    function saveShape(reviewed=false){const a=m$("#mMain").value,b=m$("#mState").value;if((a&&!b)||(!a&&b)){mToast("请完整选择主形与状态");return;}mBook.shapeOverrides[c.id]={...(c.shape||{}),coarse:a&&b?a+b:null,detail:null,status:reviewed?"reviewed":"draft",ruleVersion:"coarse-v1",reference:m$("#mShapeReference").value};mChanged();mRenderInspector();}
    m$("#mMain").onchange=()=>saveShape();m$("#mState").onchange=()=>saveShape();m$("#mShapeReference").onchange=()=>saveShape();m$("#mConfirm").onclick=()=>saveShape(true);
    const paths=document.createElement("details");paths.open=true;paths.innerHTML="<summary>已核对的细分路径（每条独立启用）</summary>";
    (c.shape?.paths||[]).forEach((p,index)=>{const label=document.createElement("label");label.className="check-control";const check=document.createElement("input");check.type="checkbox";check.checked=p.enabled;check.disabled=p.status!=="reviewed";
      label.append(check,document.createTextNode(p.code+" · "+p.basis+" · "+p.font));check.onchange=()=>{const value=structuredClone(c.shape);value.paths[index].enabled=check.checked;mBook.shapeOverrides[c.id]=value;mChanged();mRenderInspector();};paths.append(label);});
    if(!(c.shape?.paths||[]).length){const note=document.createElement("p");note.textContent="此字尚无确认的四码路径；不会补造细分。";paths.append(note);}fields.append(paths);
    const trial=document.createElement("details");trial.innerHTML='<summary>规则试验与候选对照</summary><label class="form-field">试验形族（两码）<input id="mTrialCode" maxlength="2" placeholder="例如 oe"></label><button class="button" id="mTrialCompare">与当前形族对照</button><p id="mTrialComparison"></p><label class="form-field">后两位细分规则草案<textarea id="mTrialNote" rows="4" placeholder="记录拆分假设、参考字体和验证例子"></textarea></label><button class="button" id="mTrialSave">保存试验笔记</button><p>试验笔记独立保存；试验路径不会自动进入正式查询。</p>';fields.append(trial);
    m$("#mTrialCompare").onclick=()=>{const code=m$("#mTrialCode").value.trim().toLowerCase();if(!/^[a-z]{2}$/.test(code)){mToast("请输入两字母形族");return;}const current=mModel.indexes.shape.get(c.shape?.coarse)||[],proposed=mModel.indexes.shape.get(code)||[];m$("#mTrialComparison").textContent=`当前 ${c.shape?.coarse||"未分类"}：${current.length} 字；试验 ${code}：${proposed.length} 字。示例：${proposed.slice(0,24).map(x=>x.char+" "+x.codepoint).join("，")}`;m$("#mTrialNote").value=mBook.shapeExperiments?.[code]||"";};
    m$("#mTrialSave").onclick=()=>{const code=m$("#mTrialCode").value.trim().toLowerCase();if(!/^[a-z]{2}$/.test(code)){mToast("请输入两字母形族");return;}(mBook.shapeExperiments||={})[code]=m$("#mTrialNote").value;mChanged(false);mToast("已保存试验笔记");};
  } else {
    fields.innerHTML=`<h3>独立收藏别名</h3><div id="mAliases"></div><label class="form-field">新增收藏码<input id="mAliasInput" maxlength="4" placeholder="2–4 个字母"></label><button id="mAddAlias" class="button">添加并启用</button>`;
    c.personal.forEach(a=>{const row=document.createElement("div");row.className="alias-item";row.innerHTML=`<code>${mEscape(a.code)}</code><label><input type="checkbox" ${a.enabled?"checked":""}>启用</label><button type="button">移除</button><small>${mEscape(a.origin||a.note||"个人收藏")}</small>`;row.querySelector("input").onchange=e=>{const alias=mBook.personal[c.id].find(x=>x.code===a.code);alias.enabled=e.target.checked;if(alias.enabled)alias.status="reviewed";mChanged();};row.querySelector("button").onclick=()=>{mBook.personal[c.id]=mBook.personal[c.id].filter(x=>x.code!==a.code);mChanged();mRenderInspector();};m$("#mAliases").append(row);});
    m$("#mAddAlias").onclick=()=>{try{mAddPersonal(c.id,m$("#mAliasInput").value.trim().toLowerCase());mRenderInspector();}catch(e){mToast(e.message);}};
  }
}
function mAddPersonal(id,code,note="") {
  if(!mModel.byId.has(id)||!/^[a-z]{2,4}$/.test(code))throw Error("收藏码必须为 2–4 个小写字母");
  const aliases=mBook.personal[id] ||= [],old=aliases.find(a=>a.code===code);
  if(old){old.enabled=true;old.status="reviewed";}else aliases.push({mode:"personal",code,enabled:true,status:"reviewed",ruleVersion:"personal-v1",note,origin:"个人设置"});mChanged();
}
function mRenderRuleEditor() {
  const panel=m$("#rulesPanel"),b=mModel.blocks.find(x=>x.id===mPage);
  panel.hidden=mPrefs.editMode!=="block"||!b||b.han;if(panel.hidden)return;
  let draftRules=null;m$("#applyLocalRules").disabled=true;
  m$("#applyLocalRules").onclick=()=>{if(!draftRules)return;mBook.rules[b.id]=draftRules;mChanged(false);m$("#applyLocalRules").disabled=true;mToast("局部规则说明已保存；现有编码保持稳定");};
  m$("#ruleNote").textContent=b.rules.note||"仅属于本区块";
  for(const field of ["main","state"]){const target=m$(field==="main"?"#mainRules":"#stateRules");target.replaceChildren();for(const key of "abcdefghijklmnopqrstuvwxyz"){
    const label=document.createElement("label");label.className="rule-item";label.innerHTML=`<span>${key}</span><input value="${mEscape(b.rules[field][key]||"")}" aria-label="${key} 局部规则">`;
    label.querySelector("input").onchange=e=>{draftRules||=M.clone(mBook.rules[b.id]||b.rules);draftRules[field][key]=e.target.value;draftRules.version="user-local-v1";const current=mBook.rules[b.id]||b.rules,affected=mModel.characters.filter(c=>c.blockId===b.id&&(["main","state"].some((name,i)=>draftRules[name][c.blockCode.code[i+2]]!==current[name][c.blockCode.code[i+2]])));m$("#ruleImpact").textContent=`将更新键义，涉及 ${affected.length} 字：${affected.slice(0,12).map(c=>c.char+" "+c.codepoint+" "+c.blockCode.code).join("，")}。应用后保存说明，输入码与人工确认保持稳定。`;m$("#applyLocalRules").disabled=false;};target.append(label);
  }}
  m$("#prefixDraft").value=b.prefixes.join(" ");m$("#applyPrefix").disabled=true;mPrefixPreview=null;
  m$("#previewPrefix").onclick=()=>{
    const proposed=m$("#prefixDraft").value.trim().split(/[\s,，/]+/),original=mBase.blocks.find(x=>x.id===b.id).prefixes;
    const all=mModel.blocks.filter(x=>x.id!==b.id).flatMap(x=>x.prefixes);
    if(proposed.length!==original.length||proposed.some(p=>!/^[a-z]{2}$/.test(p)||all.includes(p))||new Set(proposed).size!==proposed.length){mToast("前缀数量须保持一致，且不能占用其他区块前缀");return;}
    mPrefixPreview={original,proposed,current:b.prefixes,blockId:b.id};
    m$("#ruleImpact").textContent=`将影响 ${b.count} 字：${b.prefixes.map((p,i)=>p+" → "+proposed[i]).join("；")}。例：${mModel.characters.filter(c=>c.blockId===b.id).slice(0,8).map(c=>c.char+" "+c.blockCode.code+" → "+proposed[b.prefixes.indexOf(c.blockCode.code.slice(0,2))]+c.blockCode.code.slice(2)).join("，")}`;m$("#applyPrefix").disabled=false;
  };
  m$("#applyPrefix").onclick=()=>{if(!mPrefixPreview)return;const p=mPrefixPreview;p.original.forEach((key,i)=>mBook.prefixOverrides[key]=p.proposed[i]);Object.entries(mBook.blockOverrides).forEach(([id,v])=>{if(mModel.byId.get(id).blockId===p.blockId){const i=p.current.indexOf(v.code.slice(0,2));if(i>=0)v.code=p.proposed[i]+v.code.slice(2);}});mChanged();mRenderInspector();};
}
function mDownload(name,value,type="application/json") {const url=URL.createObjectURL(new Blob([value],{type})),a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function mInit() {
  const [baseResponse,bookResponse]=await Promise.all([fetch("data/mode-data.json"),fetch("/api/codebooks",{cache:"no-store"})]);
  if(!baseResponse.ok||!bookResponse.ok)throw Error("无法载入三模式数据；请重启编辑器服务");
  mBase=await baseResponse.json();const payload=await bookResponse.json();mBook=payload.codebooks;mRevision=payload.revision;
  if(mBase.shapeStage){const response=await fetch(mBase.shapeStage.url,{cache:"no-store"});if(!response.ok)throw Error("阶段分桶数据载入失败");mStage=await response.json();if(mStage.id!==mBase.shapeStage.id)throw Error("阶段分桶与基础数据版本不同，请刷新");}
  try{const prefs=JSON.parse(localStorage.getItem(PREF_KEY));if(prefs&&["block","shape","personal"].includes(prefs.editMode)&&Array.isArray(prefs.modes)&&prefs.modes.length&&prefs.modes.every(k=>["block","shape","personal"].includes(k)))mPrefs={...mPrefs,...prefs};}catch{}
  const reviewResponse=await fetch('data/shape-review-profile.json',{cache:'no-store'});
  if(reviewResponse.ok){mReviewManifest=await reviewResponse.json();if(mReviewManifest.enabled){const rr=await fetch(mReviewManifest.url,{cache:'no-store'});if(!rr.ok)throw Error('核对版索引载入失败');const raw=await rr.arrayBuffer();const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),x=>x.toString(16).padStart(2,'0')).join('');if(hash!==mReviewManifest.indexSHA256)throw Error('核对版索引指纹不一致');mReview=JSON.parse(new TextDecoder().decode(raw));if(mReview.id!==mReviewManifest.experimentId)throw Error('核对版版本不一致');}}
  else if(reviewResponse.status!==404)throw Error('核对版版本入口读取失败');
  m$('#shapeView option[value="review"]').disabled=!mReview;
  if(mReview&&mPrefs.shapeReviewId!==mReview.id){mPrefs.shapeView='review';mPrefs.shapeReviewId=mReview.id;}
  if(!mStage&&!mReview)mPrefs.shapeView="legacy";
  if(!mReview&&mPrefs.shapeView==='review')mPrefs.shapeView=mStage?'stage':'legacy';
  mReviewKeyTable();
  m$("#shapeView").onchange=e=>{mPrefs.shapeView=e.target.value;mPage="";mQueryLimit=60;mSetMode("shape");};
  if(mStage)m$("#shapeStageSummaryText").innerHTML=`<p>${mEscape(mStage.title)} · ${mStage.statistics.ordinary.toLocaleString()} 普通桶字符 · ${mStage.statistics.reviewed} 项已确认归属。o 为普通图形桶。</p><p>以下问题留待后续，本阶段不继续优化：</p><ol>${mStage.deferredProblems.map(p=>`<li>${mEscape(p)}</li>`).join("")}</ol>`;
  const known=new Set(mBase.characters.map(c=>c.id));
  try{const draft=JSON.parse(localStorage.getItem(BOOK_DRAFT));if(draft){if(draft.baseRevision===mRevision){mBook=draft.codebooks;mDirty=true;mGeneration++;}else{localStorage.setItem(BOOK_DRAFT+"-conflict",JSON.stringify(draft));localStorage.removeItem(BOOK_DRAFT);}}const conflict=JSON.parse(localStorage.getItem(BOOK_DRAFT+"-conflict"));if(conflict){m$("#recoveryConflict").hidden=false;m$("#exportRecovery").hidden=false;m$("#exportRecovery").onclick=()=>mDownload("冲突恢复草稿.json",JSON.stringify(conflict,null,2));}}catch(e){mToast("恢复草稿读取失败，原稿仍保留");}
  try{const old=localStorage.getItem("unicode-key-editor-v3");if(old){let h=2166136261;for(const c of old)h=Math.imul(h^c.charCodeAt(0),16777619);if(M.migrateLegacy(mBook,JSON.parse(old),"browser-v3-"+(h>>>0).toString(16),known)){mDirty=true;mGeneration++;}}}catch(e){mToast("旧草稿需要手动导入："+e.message);}
  mModel=M.model(mBase,mBook,mStage,mReview);
  document.querySelectorAll(".mode-button").forEach(b=>b.onclick=()=>mSetMode(b.dataset.mode,true));
  document.querySelectorAll("[data-source]").forEach(c=>c.onchange=()=>{let selected=[...document.querySelectorAll("[data-source]:checked")].map(x=>x.dataset.source);if(!selected.length){c.checked=true;return;}mPrefs.modes=selected;mStorePrefs();mRenderCandidates();});
  m$("#hanEnabled").onchange=e=>{mPrefs.chinese=e.target.checked;mStorePrefs();mRenderCandidates();};m$("#hanExtended").onchange=e=>{mPrefs.extended=e.target.checked;mStorePrefs();mRenderCandidates();};
  m$("#candidateInput").oninput=()=>{mQueryLimit=60;mRenderCandidates();};m$("#searchInput").oninput=()=>{mLimit=96;mRenderGrid();};m$("#searchCurrentPage").onchange=()=>mRenderGrid();m$("#pageSearchInput").oninput=mRenderNav;
  m$("#exportButton").onclick=()=>mDownload("unicode-codebooks.json",JSON.stringify(mBook,null,2));
  m$("#exportTsvButton").onclick=()=>{const rows=[["字符","码位","固定区块","区块码","历史全形粗码","历史全形细分","收藏码","小鹤码","备注","阶段主桶","阶段桶内顺序","阶段补充入口","阶段归属已确认","阶段版本","核对版主桶","核对版主形族","核对版形族入口","核对版取形码","核对版版本"]];mModel.characters.forEach(c=>rows.push([c.char,c.codepoint,c.sourceBlock,c.blockCode?.code||"",c.shape?.coarse||"",(c.shape?.paths||[]).filter(p=>p.enabled&&p.status==="reviewed").map(p=>p.code).join(" "),c.personal.map(a=>a.code+":"+(a.enabled?"enabled":"disabled")).join(" "),c.chinese?.codes.map(a=>a.code+a.marks).join(" ")||"",c.metadata.note||"",c.stageShape?.bucket||"",c.stageShape?c.stageShape.rank+1:"",c.stageShape?.aliases.join(" ")||"",c.stageShape?.reviewed?"yes":"no",mStage?.id||"",c.shapeReview?.bucket||"",c.shapeReview?.semanticPrimaryFamilyId||c.shapeReview?.familyId||"",(c.shapeReview?.familyRoutes||[]).map(r=>r.bucket+r.familyKey).join(" "),(c.shapeReview?.codes||[]).join(" "),mReview?.id||""]));mDownload("unicode-three-modes.tsv",rows.map(r=>r.map(v=>String(v).replace(/[\t\r\n]/g," ")).join("\t")).join("\n"),"text/tab-separated-values;charset=utf-8");};
  m$("#importInput").onchange=async e=>{const file=e.target.files[0];if(!file)return;try{const data=JSON.parse(await file.text());if(data.format==="unicode-key-editor-patch-v1")M.migrateLegacy(mBook,data,"import-"+file.name+"-"+file.size,known);else if(data.version===1&&data.blockOverrides&&data.personal)mBook=data;else throw Error("不是码本或旧版草稿");mChanged();mRenderInspector();await mFlush();}catch(error){mStatus(error.message,true);}e.target.value="";};
  m$("#snapshotBooks").onclick=async()=>{try{await mFlush();const r=await fetch("/api/codebooks/snapshot",{method:"POST"});const p=await r.json();if(!r.ok)throw Error(p.error);mToast("已创建码本快照");}catch(e){mStatus(e.message,true);}};
  m$("#checkHanSource").onclick=async()=>{const button=m$("#checkHanSource");button.disabled=true;try{const r=await fetch("/api/codebooks/source-check"),p=await r.json();if(!r.ok)throw Error(p.error);m$("#hanSourceDiff").hidden=false;m$("#hanSourceDiff").open=true;m$("#hanSourceDiffText").textContent=`新增 ${p.added.length} 字；移除 ${p.removed.length} 字；修改 ${p.changed.length} 字。\n当前 SHA256：${p.currentSha256}\n`+JSON.stringify(p,null,2);}catch(e){mToast("来源检查失败："+e.message);}finally{button.disabled=false;}};
  m$("#reloadBooks").onclick=()=>{if(mDirty)mDownload("未保存码本.json",JSON.stringify(mBook,null,2));location.reload();};
  m$("#publishBooks").onclick=async()=>{if(mUsingStage()){mToast("阶段分桶尚未形成完整形码，本次不发布。原有码本请切换到历史形码后使用发布功能。");return;}const b=m$("#publishBooks");b.disabled=true;try{await mFlush();mStatus("正在构建、隔离验证并部署小狼毫…");const r=await fetch("/api/codebooks/publish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({baseRevision:mRevision})});const p=await r.json();if(!r.ok)throw Error(p.error);mStatus("小狼毫已部署并验证");mToast("小狼毫已同步；备份："+p.backup);}catch(e){mStatus("发布未完成："+e.message,true);}finally{b.disabled=false;}};
  m$("#reviewSample").onclick=()=>{const samples=["Geometric Shapes","Sundanese Supplement","Basic Latin"],i=samples.indexOf(mModel.blocks.find(b=>b.id===mPage)?.name);mSetMode("block");mPage=mModel.blocks.find(b=>b.name===samples[(i+1)%samples.length]).id;mRenderNav();mRenderGrid();mToast("逐字点选确认；全形粗分类在全形模式单独核对");};
  const shift=M.shiftGesture();window.addEventListener("keydown",e=>shift.down(e));window.addEventListener("keyup",e=>{if(shift.up(e)){mPrefs.modes=M.nextPreset(mPrefs.modes);mSetMode(mPrefs.modes.length===1?mPrefs.modes[0]:mPrefs.editMode);mToast("候选来源："+mPrefs.modes.map(x=>modeLabels[x]).join("＋"));}});window.addEventListener("blur",()=>shift.reset());window.addEventListener("beforeunload",e=>{if(mDirty){mRecovery();e.preventDefault();e.returnValue="";}});
  window.keyEditor={getSelectedItem:()=>mModel.byId.get(mSelected)||null,itemById:id=>mModel.byId.get(id),findCharacter:char=>mModel.characters.find(c=>c.char===char),characters:()=>mModel.characters,codeCount:code=>mModel.query(code,{modes:["personal","block","shape"],shapeView:mPrefs.shapeView,chinese:false}).length,codeLimit:()=>Infinity,
    getPersonal:id=>mBook.personal[id]||[],addPersonal:mAddPersonal,removePersonal:(id,code)=>{mBook.personal[id]=(mBook.personal[id]||[]).filter(a=>a.code!==code);mChanged();}};
  mSetMode(mPrefs.editMode);mRenderStats();mStatus("码本已连接项目文件");
  m$("#hanInfo").textContent=`URO ${mBase.chineseSource.uro.toLocaleString()} 字；扩展与〇 ${mBase.chineseSource.extended} 字。来源 2026-09-30；${mBase.chineseSource.issues.length} 条异常码待补。`;
  document.dispatchEvent(new CustomEvent("key-editor-ready"));if(mDirty)await mFlush();
}
mInit().catch(error=>{mStatus(error.message,true);m$("#modeDescription").textContent="数据载入失败；保留草稿，重新启动本地服务后刷新。";});
