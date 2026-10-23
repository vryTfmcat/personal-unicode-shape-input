/* A read-only client. All four review rounds share the same pinned source. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = value => Number(value).toLocaleString('zh-CN');
  const cpName = cp => 'U+' + cp.toString(16).toUpperCase().padStart(4, '0');
  const names = {primary:'主入口', component:'可靠构件', supplement:'局部／补充', pending:'待核'};
  const positions = ['','第一位 · 主桶','第二位 · 视觉形族','第三位 · 对象／结构','第四位 · 对象属性'];
  const queueNames = {first:'普通字仅第一位', prior:'原有细分入口待补回', withdrawn:'上轮撤回末条入口', historical:'历史145字尚待恢复', affected:'上轮受影响旧确认字', unclassified:'全局未分类'};
  const statusNames = {confirmed:'沿用已确认键义；检测阈值仍是试验', proposal:'候选定义；不代表逐字确认', 'trial-binding':'独立试验绑定', 'accepted-independent-trial':'已接受独立试验键义', 'reserved-collection':'保留集合，不参与普通形族', 'historical-retained':'历史入口保留，不视作新键义'};
  statusNames['draft-released']='独立草案已释放此第一位；旧入口仍在v14兼容视图保留';
  statusNames['independent-draft']='独立草案试用，非已部署键义';
  let boot, round = 1, position = 1, selectedKey = 'i', params = {}, offset = 0, total = 0;
  let queryTicket = 0, detailTicket = 0, collisionTicket = 0, collisions = [], groupLimit = 80, selectedCp = null;
  const detailCache = new Map();
  let allocationMode=false, originalKeys;

  async function api(endpoint, values = {}) {
    if(allocationMode && ['query','detail','collisions'].includes(endpoint))values={...values,allocation:1};
    const response = await fetch('/api/shape-overview/' + endpoint + '?' + new URLSearchParams(values));
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || '读取失败');
    return value;
  }
  function fail(error) { $('error').textContent = '读取失败：' + error.message; }
  function focusResults(nav) {
    if($('error').textContent){$('error').scrollIntoView({block:'start'});return;}
    $(nav).scrollIntoView({block:'start',behavior:'instant'});
    $('resultHeading').focus({preventScroll:true});
  }
  const uGroupNames={six:'同样六层的新候选 · 22',three:'三层字形 · 8',two:'两层字形 · 4',stable:'规则内稳定新候选 · 131',unstable:'相似但检测不稳 · 22',broad:'短条／多段等边界 · 28',new:'全部新近似候选 · 181'};
  function uExpansionButtons() {
    return Object.entries(uGroupNames).map(([key,label])=>`<button data-uexpansion="${key}" aria-pressed="${params.uExpansion===key}" aria-controls="results">${label}</button>`).join('');
  }
  function selectUExpansion(kind) {
    params={uExpansion:kind};$('prefix').value='';$('character').value='';
    $('resultHeading').textContent='u相似扩展候选 · '+uGroupNames[kind]+'（尚未加入）';
    history.replaceState(null,'','#round='+round+'&uExpansion='+kind);
    query().then(()=>{if(params.uExpansion===kind)focusResults('uExpansionNav');});
  }
  const chvcNames={all:'全部原组',preferred:'可靠细码优先',positive:'九扰动分叉正证据',pending:'分叉入口待核',
    never:'上轮0/9次检出',partial:'上轮部分变体检出',fallback:'上轮未选出稳定细码',holes:'稳定有闭孔',attachments:'稳定外附件',parts:'稳定多部件',bars:'稳定连接横笔组',centre:'上轮中心交点缺口',largest:'全原组联合最大组',residual:'上轮最大剩余组',currentResidual:'当前最大剩余组'};
  function chvcButtons() {
    return Object.entries(chvcNames).map(([k,v])=>`<button data-chvc="${k}" aria-pressed="${params.chvcTrial===k}">${v}</button>`).join('');
  }
  function selectChvc(kind) {
    params={chvcTrial:kind};$('prefix').value='';$('character').value='';
    $('resultHeading').textContent='chvc结构试验 · '+chvcNames[kind];
    history.replaceState(null,'','#round=3&chvcTrial='+kind);
    query().then(()=>{if(params.chvcTrial===kind)focusResults('chvcResultNav');});
  }
  function renderChvc() {
    const t=boot.chvcTrial;if(!t)return;
    $('chvcPanel').hidden=false;const c=t.capacity;
    $('chvcSummary').innerHTML=`<p>上一轮固定原组 ${c.cohort} 字，逐字九扰动复核。${c.preferSpecific} 字优先使用已有可靠结构细码，${c.unresolvedFallback} 字当时仍需细分或核实检测。原始兼容 chvc 仍为 ${c.legacyChvcCandidates} 候选，未部署。</p><p>上轮 ${t.stableCentralGap} 字稳定识别到单个中心交点，${boot.centreTrial?'已进入本轮o中心试验，完整候选量见上方。':'尚未生成中心新码。'}未通过稳定检测不推翻既有人工确认，例如T原有chmw继续保留。</p><p>下表仍是上一轮这1,562字的语义分组快照。多特征组合未绑定字母，不是已实现的四键候选数；“未稳定提取”计入结果，不当作没有此结构。</p>`;
    $('chvcButtons').innerHTML=chvcButtons();
    $('chvcComparison').innerHTML=Object.entries(t.comparisons).map(([key,g])=>`<p><strong>${esc(t.featureNames[key]||'四类结构组合（诊断）')}</strong>：${g.groupCount} 组，最大 ${g.maxGroup} 字；按字符计的候选中位数 ${g.medianCharacterBurden}；落在不超过20字组内 ${g.charactersInGroupsAtMost20} 字。</p>`).join('');
    const f=t.fallbackCombination;
    $('chvcComparison').insertAdjacentHTML('beforeend',`<p><strong>移出418字首选后再分析</strong>：剩余 ${f.cohort} 字按四类结构分 ${f.groupCount} 组，最大 ${f.maxGroup} 字；第二大 ${f.largestGroups[1].count}，第三大 ${f.largestGroups[2].count}。这仍是诊断分组，不是新四键码。</p>`);
    $('chvcComparison').insertAdjacentHTML('beforeend',`<p><strong>下一批检测排查</strong>：原组有 ${t.noForkSupport} 字在九种变体均未通过分叉检验，${t.partialForkSupport} 字在部分变体通过。前者检查对象／入口，后者检查栅格与检测稳定性；两者均不直接判错或删除。</p>`);
  }
  const centreNames={stable:'稳定新增中心码',preferred:'本轮新增首选',gap:'上轮101字中心缺口',unstable:'未稳定，不加新码',all:'全部基准候选',frozen:'与418字保留入口重叠'};
  function centreButtons() {
    return Object.entries(centreNames).map(([k,v])=>`<button data-centre="${k}" aria-pressed="${params.centre===k}">${v}</button>`).join('');
  }
  function renderCentre() {
    const c=boot.centreTrial;if(!c)return;
    $('centrePanel').hidden=!allocationMode;
    $('centreSummary').innerHTML=`<p>扫描 ${num(c.ordinaryScanned)} 普通字，分叉相关 ${num(c.forkRelatedCharacters)} 字；基准中心候选 ${num(c.baseCentreCharacters)} 字，九扰动稳定新增 ${num(c.stableCharacters)} 字／${num(c.newCharacterCodePairs)} 条路径，未稳定 ${num(c.unstableCharacters)} 字未加码。</p><p>${Object.entries(c.codeCounts).map(([code,n])=>`<button data-prefix="${code}">${code} · ${n} 候选</button>`).join(' ')}。本轮新增首选 ${c.newPreferredCharacters} 字；原418字首选全部保留。</p><p>仅接入“h分叉→m单个交点→o中心”。相对本路径主体而非画布；o字母与0.12中心区阈值仍为独立试验，未部署。上轮101字只是子集，不是新码总人数；一至三键人数没有增加。</p>`;
    $('centreButtons').innerHTML=centreButtons();
    $('centreSummary').insertAdjacentHTML('beforeend',`<p>原chvc组本轮另有 ${c.newChvcPreferred} 字取得具体首选，连同原418字共 ${c.currentChvcSpecificPreferred} 字；尚无本轮具体首选 ${c.remainingChvcWithoutSpecificPreference} 字，最大剩余诊断组 ${c.currentLargestResidual} 字。原始兼容chvc仍为1,562候选，不混称降到${c.currentLargestResidual}。</p>`);
  }
  function selectCentre(kind) {
    params={centre:kind};$('prefix').value='';$('character').value='';
    $('resultHeading').textContent='中心属性独立试验 · '+centreNames[kind];
    history.replaceState(null,'','#round='+round+'&centre='+kind);
    query().then(()=>{if(params.centre===kind)focusResults('centreResultNav');});
  }
  const thickNames={improved:'检测改善',newStable:'新增九扰动稳定',stable:'修复后稳定支持',pending:'仍待核',all:'原组全部'};
  function thickButtons() {
    return Object.entries(thickNames).map(([k,v])=>`<button data-thick="${k}" aria-pressed="${params.thickRepair===k}">${v}</button>`).join('');
  }
  function renderThick() {
    const r=boot.thickForkRepair;if(!r)return;
    $('thickPanel').hidden=false;const s=r.statistics;
    $('thickSummary').innerHTML=`<p>固定原chvc ${s.cohort} 字重新复核。九扰动稳定支持 ${s.stableBefore} → ${s.stableAfter}，新增稳定 ${s.newlyStable} 字，检测改善 ${s.improvedCharacters} 字，仍待核 ${s.remainingUnstable} 字。旧正证据全部保留。</p><p>T已从6/9恢复9/9。高密度交点仍须有同一连通墨块的真实出口与局部凹口；没有直接调高密度阈值。200个随机实心凸多边形及实心三角／方／圆反例未误收。</p><p>本轮仅修检测，不改418字及中心试验的162字首选，不重建码表、不改变重码人数。拟物入口与字母尚未分配，未部署。</p>`;
    $('thickButtons').innerHTML=thickButtons();
  }
  function selectThick(kind) {
    params={thickRepair:kind};$('prefix').value='';$('character').value='';
    $('resultHeading').textContent='粗笔误拒复核 · '+thickNames[kind];
    history.replaceState(null,'','#round='+round+'&thickRepair='+kind);
    query().then(()=>{if(params.thickRepair===kind)focusResults('thickResultNav');});
  }
  function allocationControls() {
    const d=boot.cleanupDraft;if(!d)return;
    $('allocationModes').hidden=false;$('allocationStatus').hidden=false;$('cleanupQueues').hidden=!allocationMode;
    document.querySelectorAll('[data-allocation]').forEach(b=>b.setAttribute('aria-pressed',String((b.dataset.allocation==='draft')===allocationMode)));
    $('version').textContent=allocationMode?'独立视图：v14 + 旧桶草案'+(boot.chvcTrial?' + chvc结构优先试验':'')+(boot.centreTrial?' + o中心试验':'')+'（不是全量重建）':'独立版：'+boot.run+' · 生成器 v14 · 原始旧码兼容';
    const c=boot.capacity,extra=allocationMode?d.recoveredCharacters:0;
    $('stats').textContent=`普通字符 ${num(c.ordinary)} · 有细分路径 ${num(c.withPaths+extra)} · 仅第一位 ${num(boot.queueCounts.first-extra)} · 路径 ${num(c.paths+(allocationMode?d.newCharacterCodePairs+(boot.centreTrial?.newCharacterCodePairs||0):0))}`;
    renderCentre();
    $('allocationStatus').textContent=allocationMode?`草案已移除六个旧桶的历史主桶归属：u线群42、v块面1、现有r三角形4；b／g／j为空键，t已预留拟物、收入待审，尚未迁移字符。主桶待定396字，其中93字仍有可靠补充入口。10项历史确认及全部旧码在原版保留，未部署。`:'当前为原始v14：历史保留桶和旧查询结果不变；可切回“旧桶清空草案”比较。';
    const buttons=[['all','清空前后对照',443],['allocated','草案已分配',47],['pending','草案主桶待定',d.pendingPrimary],['recovered','补回稳定新路径',d.recoveredCharacters],['reviewed','历史确认保护',d.historicalFirstConfirmationsPreserved]].map(([key,label,count])=>`<button data-cleanup="${key}" aria-pressed="false" aria-controls="results">${label} · ${count}</button>`).join('');
    $('cleanupQueues').innerHTML=buttons;
    $('cleanupResultNav').innerHTML=buttons;
  }
  function selectCleanup(kind) {
    params={cleanup:kind};$('prefix').value='';$('character').value='';
    $('resultHeading').textContent={all:'旧桶清空前后对照（独立草案）',allocated:'草案中的47字主桶分配',pending:'主桶待定，不强行归类',recovered:'已补回稳定新路径',reviewed:'历史确认保护清单（原确认未迁移）'}[kind];
    history.replaceState(null,'','#round='+round+'&cleanup='+kind);
    query().then(()=>{
      if(params.cleanup!==kind)return;
      focusResults('cleanupResultNav');
    });
  }
  function setAllocation(active) {
    allocationMode=active;boot.keys=active?boot.allocationKeys:originalKeys;
    detailCache.clear();++detailTicket;selectedCp=null;
    $('detail').innerHTML='<h2>字符详情</h2><p>未选择字符</p>';
    allocationControls();renderKeys();renderCoverageQueues();setRound(round);
  }
  function renderCoverageQueues() {
    const counts=allocationMode?boot.allocationQueueCounts:boot.queueCounts;
    $('queues').innerHTML=Object.entries(queueNames).map(([key,label])=>`<button data-queue="${key}" aria-pressed="false">${label} · ${num(counts[key])}</button>`).join('');
    if(boot.historicalPilot)$('queues').insertAdjacentHTML('beforeend',`<button data-trial="history">旧桶整理与新用途 · ${boot.historicalPilot.count}</button>`);
    if(boot.cleanupDraft && allocationMode)$('queues').insertAdjacentHTML('beforeend','<button data-cleanup="pending">草案主桶待定 · 396</button>');
  }
  function glyph(row, box) {
    const p = row.preview;
    const valid = p && /^data\/shape-experiment-glyphs\/[a-z0-9-]+\/\d{3}\.png$/.test(p.url);
    const style = valid ? `background-image:url('${p.url}');background-position:-${Number(p.x)}px -${Number(p.y)}px` : '';
    const frame = box && box.length === 4 ? `<span class="box" style="left:${Number(box[0])}px;top:${Number(box[1])}px;width:${Math.max(1,box[2]-box[0])}px;height:${Math.max(1,box[3]-box[1])}px"></span>` : '';
    return `<span class="glyph" role="img" aria-label="${esc(row.char)} ${cpName(row.cp)}" style="${style}">${valid ? '' : esc(row.char)}${frame}</span>`;
  }
  function characterButtons(rows) {
    return rows.map(r => `<button type="button" class="sample-character" data-cp="${r.cp}" title="${cpName(r.cp)}">${glyph(r)}<small>${cpName(r.cp)}</small></button>`).join('');
  }
  function renderKeys() {
    $('positions').innerHTML = positions.slice(1).map((name,i) => `<button data-position="${i+1}" aria-pressed="${position===i+1}">${name}</button>`).join('');
    const keys = boot.keys.filter(k => k.position === position).map(k => allocationMode && position===1 && k.key==='t' ? {...k,assigned:true,meaning:'拟物·收入待审',status:'pictorial-intake',condition:'拟物及象征标志、指示牌、游戏图标、物象装饰等分类已确认；收入t后退出其他几何桶，不设双入口个例。0字表示尚未迁移，不是没有候选。',anchors:['😸','𓆟','☀','☁','☾'],counterexamples:['♥','♡','♀','♂','♠','♣','♦']} : k);
    const order = 'qwertyuiopasdfghjklzxcvbnm';
    $('keyboard').innerHTML = [...order].map(key => {
      const k = keys.find(v => v.key === key);
      return `<button class="key ${k.assigned?'':'empty'}" data-key="${key}" aria-pressed="${key===selectedKey}" title="${esc(k.meaning || '未分配')}：${num(k.count)} 字"><strong>${key}</strong><span>${esc(k.status==='historical-retained'?'历史第一位保留':k.meaning || '未分配')}</span><small>${num(k.count)} 字</small></button>`;
    }).join('');
    const k = keys.find(k => k.key === selectedKey);
    const examples = k.anchors || (k.positive ? [...k.positive] : []);
    const negative = k.counterexamples || (k.negative ? [...k.negative] : []);
    $('keyInfo').innerHTML = `<h3>${position} / ${k.key}：${esc(k.meaning || '未分配')}</h3><p>${esc(statusNames[k.status] || (k.assigned ? '快照定义；人工确认范围以核对记录为准' : '保留空键，不猜造功能'))} · ${num(k.count)} 个去重字符</p>${k.condition||k.boundary ? `<p>${esc(k.condition || k.boundary)}</p>` : ''}<p>定义例字：${esc(examples.join(' ') || '未提供')}　反例：${esc(negative.join(' ') || '未提供')}</p><div class="toolbar">${characterButtons(k.examples)}</div>`;
    if(k.status==='pictorial-intake')$('keyInfo').insertAdjacentHTML('beforeend','<p><a href="pictorial-intake-review.html">打开 t 拟物收入全量初稿</a></p>');
    if(k.status==='historical-retained' && boot.historicalPilot) $('keyInfo').insertAdjacentHTML('beforeend',`<p><button data-trial="history" data-oldkey="${k.key}">旧 ${k.key} 桶整理结果</button></p>`);
    if(allocationMode && position===1 && selectedKey==='u')$('keyInfo').insertAdjacentHTML('beforeend','<p>2026-10-22已确认保留“线群／层列”查找方向；仍为独立版，未部署。</p>');
    if(position===1 && selectedKey==='u' && boot.uExpansion)$('keyInfo').insertAdjacentHTML('beforeend',`<p>全体28,223普通字扫描：另有131个规则内稳定候选、22个检测不稳的相似字、28个短条或多段边界候选。当前u仍为42字，新候选未迁移。</p><div class="toolbar">${uExpansionButtons()}</div><details><summary>九种字号、粗细检查的实际含义</summary><p>同一字体按48、96、128三个渲染字号分别生成字形，归一到64×64像素，再各做一像素墨迹收缩、原样、膨胀，共3×3＝9种。粗细是程序模拟，不是换成字体真实粗体。</p><p>它只检测程序是否稳定识别同一线群，不证明跨字体一致、查法自然或应该改主桶。未通过的相似字仍保留供核对。</p></details>`);
    if(allocationMode && position===1 && selectedKey==='v')$('keyInfo').insertAdjacentHTML('beforeend','<p>当前只有 🬨（U+1FB28）通过块面试验的九种字号、粗细检查。这是清空旧v桶后重新纳入的新用途候选，不是漏清；原v桶其余15字未强行归入。v尚未确认冻结。</p>');
    if(allocationMode && position===4 && selectedKey==='o' && boot.centreTrial)$('keyInfo').insertAdjacentHTML('beforeend','<p>本轮仅用于h分叉形族的m单个交点；中心相对该路径的主体测量，既有八向位置不变。</p><button data-centre="stable">查看中心码完整候选</button>');
  }
  function renderHistorical() {
    const h=boot.historicalPilot;
    if(!h)return;
    $('historicalPanel').hidden=false;
    $('historicalSummary').innerHTML=`<p>旧桶 t／u／j／v／b 共 ${h.requestedFiveCount} 字，补入 g 后共 ${h.count} 字；涉及旧第一位人工确认 ${h.historicallyReviewed} 字。只整理观察与候选，不清空旧桶、不写入编码。</p><p>现有形族九扰动补回候选 ${h.existingStableProposals} 字。线群试验：基准 ${h.trials.u.baseCount}，稳定 ${h.trials.u.stableCount}；块面试验：基准 ${h.trials.v.baseCount}，稳定 ${h.trials.v.stableCount}。数量仅限这443字，不代表全量容量。</p><p>第一位 u／v 尚未绑定。线群试验与第二位 u“U形”不同；块面暂只测2×3／3×2台阶拼块，不涵盖全部斜切块。九扰动只限锁定字体，异字体分歧保留。</p><p>程序排查：无主形族记录可能跳过后续对象补回检测；全量生成器尚未修改。</p>`;
    $('historicalButtons').innerHTML=`<button data-trial="history">全部旧桶 · ${h.count}</button>`+Object.entries(h.summary).map(([k,v])=>`<button data-trial="history" data-oldkey="${k}">旧 ${k} · ${v.total}</button>`).join('')+`<button data-trial="u">u 线群候选 · ${h.trials.u.stableCount}</button><button data-trial="v">v 块面候选 · ${h.trials.v.stableCount}</button><button data-trial="existing">现有形族补回候选 · ${h.existingStableProposals}</button><button data-trial="reviewed">旧确认字 · ${h.historicallyReviewed}</button>`;
    $('historicalCategories').innerHTML=Object.entries(h.categories).map(([label,count])=>`<button data-pilotcategory="${esc(label)}">${esc(label)} · ${count}</button>`).join('');
  }
  function selectTrial(trial,oldKey='',category='') {
    if(round!==1)setRound(1);
    $('historicalPanel').open=true;
    params={trial};if(oldKey)params.oldKey=oldKey;if(category)params.category=category;
    $('prefix').value='';$('character').value='';
    const labels={history:oldKey?'旧 '+oldKey+' 桶整理':'全部历史保留桶整理',u:'u 线群／层列 · 独立试验候选',v:'v 不规则实心块面 · 窄范围试验候选',existing:'现有形族补回候选（未写入码表）',reviewed:'历史第一位确认字（未迁移）',category};
    $('resultHeading').textContent=labels[trial]||'独立试验';
    $('historicalFigure').hidden=!['u','v','existing'].includes(trial);
    if(!$('historicalFigure').hidden){$('historicalImage').src='/api/shape-overview/asset?id=historical-'+trial;$('historicalCaption').textContent='仅标识原墨迹。来源：20261022-historical-buckets-pilot-v1；非新码表、非人工确认。';}
    history.replaceState(null,'','#round=1&pilot='+encodeURIComponent(trial)+(oldKey?'&oldKey='+oldKey:''));
    query();
  }
  function historicalDetail(row) {
    const h=row.historicalPilot;if(!h)return '';
    const proposal=h.existingFamilyProbe;
    return `<div class="pilot-detail"><h3>旧桶整理 · ${esc(h.category)}</h3><p>${esc(h.reason)}</p><p>旧第一位 ${esc(h.oldBucket)}${h.historicallyReviewed?' · 有历史确认，迁移须另行审议':''}；现有编码 ${h.codesBefore.length} 条，未增删。</p>${proposal?`<p>现有形族探测：${esc(proposal.family)}；比较前缀 ${esc(proposal.proposedBucket+proposal.family)}。九扰动通过 ${proposal.variants.filter(v=>v.passed).length}/9，${proposal.stable?'稳定候选，未写入':'不稳定，不补码'}。</p>`:''}${Object.entries(h.probes).map(([key,p])=>`<p>新用途 ${key}：${p.base?'基准通过，九扰动 '+p.stability.variants.filter(v=>v.passed).length+'/9，'+(p.stability.passed?'稳定候选':'不纳入稳定候选'):'基准未通过'}。</p>`).join('')}<p>跨字体：${h.alternateFontDisagreement?'已有分歧，仍需单独核查':'本次不代表跨字体已一致'}；与源字形墨迹差 ${h.lockedSpriteMismatchPixels} 像素。</p></div>`;
  }
  async function query(reset = true) {
    if (reset) offset = 0;
    $('cleanupResultNav').hidden=!allocationMode || !params.cleanup;
    $('uExpansionNav').hidden=!params.uExpansion;
    $('chvcResultNav').hidden=!params.chvcTrial;
    $('centreResultNav').hidden=!params.centre;
    $('thickResultNav').hidden=!params.thickRepair;
    if(params.thickRepair)$('thickResultNav').innerHTML=thickButtons();
    document.querySelectorAll('[data-thick]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.thick===params.thickRepair)));
    if(params.centre)$('centreResultNav').innerHTML=centreButtons();
    document.querySelectorAll('[data-centre]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.centre===params.centre)));
    if(params.chvcTrial)$('chvcResultNav').innerHTML=chvcButtons();
    document.querySelectorAll('[data-chvc]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.chvc===params.chvcTrial)));
    if(params.uExpansion)$('uExpansionNav').innerHTML=uExpansionButtons();
    document.querySelectorAll('[data-uexpansion]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.uexpansion===params.uExpansion)));
    document.querySelectorAll('[data-cleanup]').forEach(b=>b.setAttribute('aria-pressed',String(allocationMode && b.dataset.cleanup===params.cleanup)));
    const ticket = ++queryTicket;
    $('error').textContent = '';
    $('resultStatus').textContent = '正在读取候选……';
    try {
      const result = await api('query', {...params, offset});
      if (ticket !== queryTicket) return;
      total = result.total;
      $('resultStatus').textContent = `${num(total)} 个去重字符 · 全部候选，没有按证据层隐藏`;
      $('groupCounts').textContent = Object.entries(result.groups).map(([k,v]) => `${names[k]} ${num(v)}`).join('　') + (result.audit ? `　几何专项复核：支持 ${num(result.audit.geometrySupported)}，待核 ${num(result.audit.uncertainRetained)}（来源 v13，非人工确认）` : '');
      $('results').innerHTML = result.rows.map(r => `<button class="candidate layer-${esc(r.layer || '')} ${selectedCp===r.cp?'selected':''}" data-cp="${r.cp}" title="${esc(r.reason || r.geometry)}">${glyph(r)}<small>${cpName(r.cp)}${r.layer ? ' · '+names[r.layer] : ''}</small>${result.audit?'<small>'+esc(r.geometry.startsWith('几何')?'几何支持':r.geometry.startsWith('证据')?'证据待核':'专项未覆盖')+'</small>':''}<code>${esc((r.preferredCodes?.length ? r.preferredCodes : r.codes).slice(0,2).join(' ') || r.bucket || '未分配')}</code></button>`).join('') || '<p>本条件没有字符。</p>';
      result.rows.forEach(r=>{if(r.historicalCategory)$('results').querySelector(`[data-cp="${r.cp}"]`).insertAdjacentHTML('beforeend',`<small class="trial-category">${esc(r.historicalCategory)}</small>`);});
      result.rows.forEach(r=>{if(r.draftOnly)$('results').querySelector(`[data-cp="${r.cp}"]`).insertAdjacentHTML('beforeend',`<small class="trial-category">${r.primaryPending?'主桶待定':esc(r.bucket)+' 桶草案'} · 原 ${esc(r.legacyFirstAlias)}</small>`);});
      result.rows.forEach(r=>{if(r.uExpansionCategory)$('results').querySelector(`[data-cp="${r.cp}"]`).insertAdjacentHTML('beforeend',`<small class="trial-category">${esc(r.uExpansionCategory)} · 尚未加入u</small>`);});
      result.rows.forEach(r=>{if(r.centreStatus)$('results').querySelector(`[data-cp="${r.cp}"]`).insertAdjacentHTML('beforeend',`${r.centreCodes?.length?'<code>中心：'+esc(r.centreCodes.join(' '))+'</code>':''}<small class="trial-category">${esc(r.centreStatus)}</small>`);});
      result.rows.forEach(r=>{if(r.thickRepairStatus)$('results').querySelector(`[data-cp="${r.cp}"]`).insertAdjacentHTML('beforeend',`<small class="trial-category">${esc(r.thickRepairStatus)} · 局部交点证据</small>`);});
      result.rows.forEach(r=>{if(r.chvcPriority){const node=$('results').querySelector(`[data-cp="${r.cp}"]`),t=r.chvcPriority;
        node.querySelector('code').textContent=(r.centrePreferenceApplied?r.preferredCodes:t.preferredCodes.length?t.preferredCodes:t.oldPreferredCodes).slice(0,2).join(' ')||'原码保留／检测待核';
        node.insertAdjacentHTML('beforeend',`<small class="trial-category">${r.centrePreferenceApplied?'本轮中心码首选':esc(t.status)}</small>`);}});
      $('page').textContent = total ? `${offset+1}–${Math.min(total,offset+60)} / ${num(total)}` : '0 / 0';
      $('prev').disabled = offset === 0;
      $('next').disabled = offset + 60 >= total;
    } catch (error) { if (ticket === queryTicket) { $('resultStatus').textContent = ''; fail(error); } }
  }
  function selectPrefix(prefix) {
    params = {prefix};
    $('prefix').value = prefix;
    $('character').value = '';
    $('resultHeading').textContent = '编码 ' + prefix;
    query();
  }
  async function showDetail(cp) {
    const ticket = ++detailTicket;
    selectedCp = cp;
    $('detail').innerHTML = '<h2>正在读取字符详情……</h2>';
    try {
      const cacheKey=(allocationMode?'draft:':'original:')+cp;
      let row = detailCache.get(cacheKey);
      if (!row) { row = await api('detail', {cp}); detailCache.set(cacheKey,row); }
      if (ticket !== detailTicket) return;
      const pathHtml = (row.paths || []).map(path => `<div class="path"><button data-prefix="${esc(path.code)}">${esc(path.code)}</button><span>${num(row.codeCounts[path.code])} 候选${path.preferred ? ' · 当前首选' : ''}</span><p>${[...path.code].map((key,i) => esc((boot.keys.find(k => k.position===i+1&&k.key===key)||{}).meaning || key)).join(' → ')}</p>${path.evidence.map(e => {
        const object = (row.objects || []).find(o => o.id === e.objectId);
        return `<div class="evidence">${glyph(row,object?.bbox)}<div><p>对象：${esc(e.objectId)}${e.fourthObjectId!==e.objectId ? '；第四位对象：'+esc(e.fourthObjectId) : ''}</p><p>属性：${esc(e.attribute)}</p><p>规则：${esc(e.rule)} · ${esc(e.familyTarget)}</p><p class="muted">${object?.bbox ? '蓝框仅为对象定位框，不是精确墨迹掩膜。' : '本对象未提供定位框；不绘制猜测框。'}</p></div></div>`;
      }).join('')}</div>`).join('');
      $('detail').innerHTML = `<h2>${esc(row.char)} <small>${cpName(row.cp)}</small></h2><div class="heroGlyph">${glyph(row)}</div><p>普通第一位：${esc(row.bucket || '无')}　主形族：${esc(row.familyKey || '待定')}</p><p>${row.oldReviewed ? '历史确认仅涉及旧第一位，不等于当前全部路径已确认。' : '逐字入口未自动计为人工确认。'}</p>${row.reason ? `<p>${esc(row.reason)}</p>` : ''}${row.suggestions?.length ? '<h3>可比较的可靠入口</h3><div class="toolbar">'+row.suggestions.map(s=>`<button data-prefix="${s.code}">${s.code} · ${s.allCandidates} 候选${s.preferred?' · 首选':''}</button>`).join('')+'</div>' : ''}<h3>全部路径 · ${num(row.paths?.length || 0)} 条</h3>${pathHtml || '<p>当前没有可靠细分路径；保留身份与已有第一位，不猜补。</p>'}${row.routeAmendments?.length ? '<h3>撤回／修正记录</h3><p>'+row.routeAmendments.map(esc).join('<br>')+'</p>' : ''}${row.warnings?.length ? '<h3>检测提示</h3><p>'+row.warnings.map(esc).join('<br>')+'</p>' : ''}<details><summary>原始对象与依据</summary><pre>${esc(JSON.stringify({font:row.font,objects:row.objects,familyRoutes:row.familyRoutes},null,2))}</pre></details>`;
      const header=$('detail').querySelector('.heroGlyph');
      if(header && row.historicalPilot)header.insertAdjacentHTML('afterend',historicalDetail(row));
      if(header && row.chvcTrial){const t=row.chvcTrial;header.insertAdjacentHTML('afterend',`<div class="pilot-detail"><h3>chvc结构试验 · ${esc(t.status)}</h3><p>局部分叉正证据 ${t.forkPositiveVariants}/9。${t.preferredCodes.length?'试验优先：'+esc(t.preferredCodes.join(' '))+'；chvc降为兼容备选。':'尚未据此删除原入口。'}</p><p>${Object.entries(t.stableFeatures).map(([k,v])=>esc(boot.chvcTrial.featureNames[k])+ '：'+esc(v)).join('；')}</p>${t.choices.map(c=>`<p><button data-prefix="${c.code}">${c.code} · v14全量 ${c.allCandidatesV14} 候选</button> ${esc(c.evidence[0].reason)}</p>`).join('')}<p>部件数是分离墨块，不是笔画；未稳定提取不等于结构不存在。组合特征尚未绑定新键。下方路径的原首选标记保留供对照，本段才是此次试验优先级。</p></div>`);}
      if(header && row.chvcPreferenceApplied)header.nextElementSibling.lastElementChild.textContent='本草案已将下方首选标记和查询推荐同步为结构细码优先；全部原路径仍保留。切回v14原始／旧码兼容可查看原首选。部件数不是笔画，组合特征尚未绑定新键。';
      if(header && row.cleanupDraft){const d=row.cleanupDraft;header.insertAdjacentHTML('afterend',`<div class="pilot-detail"><h3>独立清空草案：原 ${esc(d.oldBucket)} → ${esc(d.draftBucket||'主桶待定')}</h3><p>${esc(d.allocationBasis)}</p><p>保留旧码 ${d.oldCodes.length} 条；新增稳定候选码 ${d.newCodes.length} 条。旧第一位 ${esc(d.legacyFirstAlias)} 在原版兼容视图保留。</p><p>${d.historicalFirstKeyConfirmed?'原第一位有人工作过确认；原确认记录未迁移。':'新增检测路径不视作逐字人工确认。'}</p></div>`);}
      if(header && row.uExpansion){const e=row.uExpansion,o=e.strictObject||e.broadObject,s=e.strictStability||e.broadStability;header.insertAdjacentHTML('afterend',`<div class="pilot-detail"><h3>u线群近似观察 · ${esc(e.category)}</h3><p>${o.layerCount}层，${o.pieceCount}个墨块；每层分段 ${esc(o.piecesPerLayer.join('／'))}。线本身${o.memberDirection==='h'?'横向':'纵向'}，整组${o.arrangement==='i'?'上下':'左右'}排列。</p><p>${s?s.variants.filter(v=>v.passed).length+'/9种通过；'+(s.passed?'程序检测稳定':'程序检测尚不稳定'):'未做稳定性判断'}。${e.alreadyInU?'原已保留在u。':'仅列近似候选，原桶和编码未变。'}</p><p>稳定性不是人工自然性确认；较短块或三段层列需要另核边界。</p></div>`);}
      if(header && row.centreTrial){const t=row.centreTrial;header.insertAdjacentHTML('afterend',`<div class="pilot-detail"><h3>o中心 · ${t.stable?'九扰动稳定':'未稳定，不增加新码'}</h3><p>${t.paths.map(p=>esc(p.code)+' · '+num(boot.centreTrial.codeCounts[p.code])+'候选').join('；')||'原有入口保留。'}${t.frozenPreference?'；保留上轮具体首选 '+esc(t.frozenPreference.join(' '))+'。':''}</p><p>${row.centrePreferenceApplied?'本草案首选已同步为中心码，原有路径保留。':'没有因新增中心属性覆盖既有具体首选。'}</p><p>所选对象始终是单个交点，第四位描述它相对本路径主体的位置；不是观察窗口尺寸。</p><details><summary>各对象的中心区边界及稳定性</summary><pre>${esc(JSON.stringify(t.objectsChecked,null,2))}</pre></details></div>`);}
      if(header && row.thickForkRepair && row.thickForkRepair.improved){const t=row.thickForkRepair;header.insertAdjacentHTML('afterend',`<div class="pilot-detail"><h3>粗笔误拒修复 · ${t.beforePositiveVariants}/9 → ${t.afterPositiveVariants}/9</h3><p>新增正证据来自同一连通墨块的真实出口及局部凹口，不把实心凸块的细化骨架当成分叉。本段是最新检测结果；下方旧路径与上轮试验统计保留作对照。</p><details><summary>逐变体证据</summary><pre>${esc(JSON.stringify(t.variants,null,2))}</pre></details></div>`);}
      document.querySelectorAll('#results [data-cp]').forEach(b=>b.classList.toggle('selected',Number(b.dataset.cp)===cp));
    } catch (error) { if (ticket === detailTicket) { $('detail').innerHTML = ''; fail(error); } }
  }
  function renderCollisions() {
    const filter = $('collisionFilter').value.toLowerCase();
    const rows = collisions.filter(g=>g.code.startsWith(filter));
    $('collisions').innerHTML = rows.slice(0,groupLimit).map(g=>`<button data-prefix="${g.code}"><span>${g.code}</span><small>${num(g.count)}</small></button>`).join('') || '<p>没有匹配编码。</p>';
    $('moreGroups').hidden = groupLimit >= rows.length;
  }
  async function loadCollisions() {
    const ticket = ++collisionTicket;
    try { const result = await api('collisions',{length:$('length').value}); if(ticket!==collisionTicket)return; collisions=result.groups; groupLimit=80; renderCollisions(); } catch(error) { fail(error); }
  }
  function chooseQueue(queue) {
    params = {queue}; $('prefix').value = ''; $('character').value = '';
    $('resultHeading').textContent = queueNames[queue];
    const notes = {first:'普通字符中全部只有第一位的队列。包含“原有细分入口待补回”，两项不能相加。',prior:'原来有细分路径、现只保留第一位的字符；尚无可靠证据，不直接恢复旧入口。',withdrawn:'v13 撤回错误入口后失去末条细分路径的 33 字。v14 没有新增撤回；此处保留上轮队列。',historical:'固定的历史145字队列：52字已补回，93字待处理。历史确认只涉及旧第一位。',affected:'𐏓、𒌋、𐎓：上轮受影响的旧第一位确认字，不属于固定145字队列。',unclassified:'全局尚未分配普通第一位的字符，与普通桶内“只有第一位”是不同问题。'};
    $('queueNote').textContent = notes[queue];
    document.querySelectorAll('[data-queue]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.queue===queue)));
    query();
  }
  function setRound(value) {
    round = value;
    for (let i=1;i<=4;i++) $('round'+i).hidden = i!==round;
    document.querySelectorAll('[data-round]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.round)===round)));
    if(round===1) { params={position,key:selectedKey}; $('prefix').value=''; $('character').value=''; $('resultHeading').textContent=`${positions[position]} / ${selectedKey}`; query(); }
    if(round===2) { params={text:'○●□■☆★∥=∴∵QODTEFB𐎊•▪◾'}; $('prefix').value=''; $('character').value=''; $('resultHeading').textContent='代表字与边界样本'; query(); }
    if(round===3) { loadCollisions(); selectPrefix('chvc'); }
    if(round===4) chooseQueue('first');
    history.replaceState(null,'','#round='+round);
  }
  function restoreLocation() {
    const values=new URLSearchParams(location.hash.slice(1));
    const initial=Number(values.get('round'));
    setRound(initial>=1&&initial<=4?initial:1);
    const pilot=values.get('pilot');
    if(boot.historicalPilot && ['history','u','v','existing','reviewed'].includes(pilot))selectTrial(pilot,values.get('oldKey')||'');
    const cleanup=values.get('cleanup');
    if(allocationMode && ['all','pending','recovered','reviewed','allocated'].includes(cleanup))selectCleanup(cleanup);
    const expansion=values.get('uExpansion');
    if(boot.uExpansion && Object.hasOwn(uGroupNames,expansion))selectUExpansion(expansion);
    const chvc=values.get('chvcTrial');
    if(boot.chvcTrial && Object.hasOwn(chvcNames,chvc))selectChvc(chvc);
    const centre=values.get('centre');
    if(boot.centreTrial && Object.hasOwn(centreNames,centre))selectCentre(centre);
    const thick=values.get('thickRepair');
    if(boot.thickForkRepair && Object.hasOwn(thickNames,thick))selectThick(thick);
  }
  window.addEventListener('hashchange',()=>{if(boot)restoreLocation();});
  document.addEventListener('click',event=>{
    const b = event.target.closest('button'); if(!b || !boot)return;
    if(b.dataset.round) setRound(Number(b.dataset.round));
    else if(b.dataset.uexpansion) selectUExpansion(b.dataset.uexpansion);
    else if(b.dataset.chvc) selectChvc(b.dataset.chvc);
    else if(b.dataset.centre) selectCentre(b.dataset.centre);
    else if(b.dataset.thick) selectThick(b.dataset.thick);
    else if(b.dataset.allocation) setAllocation(b.dataset.allocation==='draft');
    else if(b.dataset.cleanup) selectCleanup(b.dataset.cleanup);
    else if(b.dataset.trial) selectTrial(b.dataset.trial,b.dataset.oldkey||'');
    else if(b.dataset.pilotcategory) selectTrial('category','',b.dataset.pilotcategory);
    else if(b.dataset.position) {position=Number(b.dataset.position);renderKeys();params={position,key:selectedKey};$('prefix').value='';$('character').value='';$('resultHeading').textContent=`${positions[position]} / ${selectedKey}`;query();}
    else if(b.dataset.key) {selectedKey=b.dataset.key;renderKeys();params={position,key:selectedKey};$('prefix').value='';$('character').value='';$('resultHeading').textContent=`${positions[position]} / ${selectedKey}`;query();}
    else if(b.dataset.prefix) selectPrefix(b.dataset.prefix);
    else if(b.dataset.cp) showDetail(Number(b.dataset.cp));
    else if(b.dataset.queue) chooseQueue(b.dataset.queue);
    else if(b.dataset.sample) {params={text:b.dataset.sample};$('prefix').value='';$('character').value='';$('resultHeading').textContent='样本 '+b.dataset.sample;query();showDetail(b.dataset.sample.codePointAt(0));$('proof').hidden=!b.dataset.proof;if(b.dataset.proof)$('proofImage').src='/api/shape-overview/asset?id='+b.dataset.proof;}
  });
  $('search').addEventListener('submit',event=>{event.preventDefault();params={prefix:$('prefix').value.toLowerCase(),text:$('character').value.trim()};$('resultHeading').textContent='自定义查询';query();});
  $('clear').onclick=()=>{params={};$('prefix').value='';$('character').value='';$('resultHeading').textContent='全部普通字符';query();};
  $('prev').onclick=()=>{offset=Math.max(0,offset-60);query(false);};
  $('next').onclick=()=>{if(offset+60<total){offset+=60;query(false);}};
  $('length').onchange=loadCollisions;
  $('collisionFilter').oninput=()=>{groupLimit=80;renderCollisions();};
  $('moreGroups').onclick=()=>{groupLimit+=80;renderCollisions();};

  (async()=>{
    try {
      boot = await api('bootstrap');
      originalKeys=boot.keys;
      allocationMode=Boolean(boot.cleanupDraft);
      if(allocationMode)boot.keys=boot.allocationKeys;
      const c=boot.capacity;
      $('version').textContent='独立版：'+boot.run+' · 生成器 v14';
      $('stats').textContent=`普通字符 ${num(c.ordinary)} · 有细分路径 ${num(c.withPaths)} · 仅第一位 ${num(boot.queueCounts.first)} · 路径 ${num(c.paths)} · 四键最大候选 ${num(c.prefixDistribution['4'].maximumCandidates)}`;
      $('provenance').innerHTML=`<p>独立全量：${esc(boot.id)}</p><p>索引 SHA-256：${esc(boot.sha256)}</p><p>现行部署配置（未改动）：${esc(JSON.stringify(boot.deployed))}</p><p>键义接受、检测几何证据、逐字查找习惯确认是三个不同层次。机器提出路径不等于逐字确认。b 双环、z 连接横笔组均为独立试验。</p><p>第三位选对象，第四位描述同一个对象。交点观察窗口不编码尺寸；线的方向与构件组排列分别解释。圆／方保留尺寸系列；星形主体不加尺寸路径。</p><p>大重码六组专项几何证据来源：${esc(boot.auditVersion)}。其他组没有同等级专项复核，不自动标成证据成立。</p>`;
      $('samples').innerHTML=[['○●','空心／实心圆'],['□■','空心／实心方'],['☆★','星形填充'],['∥=','线组排列'],['∴∵','点组朝向'],['QO','圆环／尾笔','Q'],['D','主体／构件','D'],['T','分叉／误钩'],['EF','连接横笔数量','EF'],['B𐎊•▪◾','双入口边界']].map(([chars,label,proof])=>`<button data-sample="${esc(chars)}" ${proof?'data-proof="'+proof+'"':''}>${esc(chars)} · ${label}</button>`).join('');
      renderCoverageQueues();
      $('majorGroups').innerHTML=['chvc','mdez','ajvg','cxvc','iocv','crvg','chzt','chzb'].map(code=>`<button data-prefix="${code}">${code}</button>`).join('');
      renderKeys();
      renderHistorical();
      renderChvc();
      renderThick();
      allocationControls();
      restoreLocation();
    } catch(error) { $('version').textContent='独立版未能读取，不显示旧版替代数据。'; fail(error); }
  })();
})();
