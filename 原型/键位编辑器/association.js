const GRAPH_API = "/api/association-graph";
const GRAPH_DRAFT_KEY = "unicode-association-graph-draft-v1";
const ABC = "abcdefghijklmnopqrstuvwxyz".split("");

let graph = null;
let graphRevision = "";
let graphDirty = false;
let graphSaveTimer = null;
let selectedFeeling = { type: "pair", id: "rr" };
let selectedGraphNode = "u-25cb";
let graphMode = "focus";
let graphNodes = new Map();
let graphAdjacency = new Map();
let graphAllEdges = [];
let visibleGraphNodes = [];
let visibleGraphEdges = [];
let graphCamera = { x: 0, y: 0, scale: 1 };
let graphPointer = null;
let graphRenderPending = false;

const qa = (selector) => document.querySelector(selector);
const qaa = (selector) => [...document.querySelectorAll(selector)];
const deepClone = (value) => JSON.parse(JSON.stringify(value));

function toast(message) {
  const target = qa("#toast");
  target.textContent = message;
  target.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => target.classList.remove("show"), 2400);
}

function graphStatus(message, kind = "") {
  const status = qa("#saveStatus");
  status.textContent = message;
  status.classList.toggle("error-status", kind === "error");
}

async function loadGraph() {
  const response = await fetch(GRAPH_API, { cache: "no-store" });
  if (!response.ok) throw new Error("无法读取项目联想图谱");
  const payload = await response.json();
  graph = payload.graph;
  graphRevision = payload.revision;
  const draft = localStorage.getItem(GRAPH_DRAFT_KEY);
  if (draft) {
    try {
      const parsed = JSON.parse(draft);
      if (parsed.baseRevision === graphRevision && parsed.graph?.version === 1) {
        graph = parsed.graph;
        graphDirty = true;
        graphStatus("已恢复未保存图谱草稿");
      }
    } catch { localStorage.removeItem(GRAPH_DRAFT_KEY); }
  }
  rebuildGraphIndexes();
  renderFeelingWorkspace();
  renderGraphWorkspace(true);
  if (!graphDirty) graphStatus("图谱已连接项目文件");
}

function bindAssociationEvents() {
  qaa(".view-tab").forEach((button) => button.addEventListener("click", () => switchWorkspace(button.dataset.view)));
  qa("#pairSearchInput").addEventListener("input", renderPairMatrix);
  qaa(".graph-mode").forEach((button) => button.addEventListener("click", () => setGraphMode(button.dataset.mode)));
  qa("#themeSelect").addEventListener("change", () => renderGraphWorkspace(true));
  qa("#addThemeButton").addEventListener("click", addTheme);
  qa("#graphSearchInput").addEventListener("keydown", (event) => { if (event.key === "Enter") searchGraph(event.target.value); });
  qa("#snapshotGraphButton").addEventListener("click", createGraphSnapshot);
  qa("#exportGraphButton").addEventListener("click", exportGraph);
  qa("#importGraphInput").addEventListener("change", importGraph);
  const canvas = qa("#graphCanvas");
  canvas.addEventListener("pointerdown", graphPointerDown);
  canvas.addEventListener("pointermove", graphPointerMove);
  canvas.addEventListener("pointerup", graphPointerUp);
  canvas.addEventListener("pointercancel", graphPointerUp);
  canvas.addEventListener("dblclick", graphDoubleClick);
  canvas.addEventListener("wheel", graphWheel, { passive: false });
  window.addEventListener("resize", () => requestGraphRender());
}

function switchWorkspace(id) {
  qaa(".view-tab").forEach((button) => button.classList.toggle("active", button.dataset.view === id));
  qaa(".view-panel").forEach((panel) => panel.classList.toggle("active", panel.id === id));
  if (id === "graphView") setTimeout(() => renderGraphWorkspace(true), 0);
}

function markGraphDirty() {
  graphDirty = true;
  graphStatus("图谱有未保存修改");
  localStorage.setItem(GRAPH_DRAFT_KEY, JSON.stringify({ baseRevision: graphRevision, graph }));
  clearTimeout(graphSaveTimer);
  graphSaveTimer = setTimeout(saveGraph, 1500);
}

async function saveGraph() {
  if (!graphDirty) return;
  graphStatus("正在保存图谱");
  try {
    const response = await fetch(GRAPH_API, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ baseRevision: graphRevision, graph }),
    });
    const payload = await response.json();
    if (response.status === 409) {
      graphStatus("图谱版本冲突，请导出草稿后刷新", "error");
      toast("另一个页面已经修改图谱；当前草稿没有被覆盖");
      return;
    }
    if (!response.ok) throw new Error(payload.error || "保存失败");
    graphRevision = payload.revision;
    graphDirty = false;
    localStorage.removeItem(GRAPH_DRAFT_KEY);
    graphStatus("图谱已保存到项目");
  } catch (error) {
    graphStatus("保存失败，草稿仍在浏览器", "error");
    toast(error.message);
  }
}

async function createGraphSnapshot() {
  try {
    await saveGraph();
    const response = await fetch(`${GRAPH_API}/snapshot`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "快照失败");
    toast(`已创建图谱快照：${payload.snapshot}`);
  } catch (error) { toast(error.message); }
}

function exportGraph() {
  const blob = new Blob([JSON.stringify(graph, null, 2) + "\n"], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = `association-graph-${new Date().toISOString().slice(0, 10)}.json`; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

function importGraph(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const incoming = JSON.parse(reader.result);
      if (incoming.version !== 1 || !Array.isArray(incoming.pairs) || incoming.pairs.length !== 676) throw new Error("不是有效的 v1 联想图谱");
      if (!confirm("导入会替换当前图谱内容，并立即保存到项目。继续吗？")) return;
      graph = incoming; rebuildGraphIndexes(); markGraphDirty(); saveGraph(); renderFeelingWorkspace(); renderGraphWorkspace(true);
    } catch (error) { toast(`导入失败：${error.message}`); }
    event.target.value = "";
  };
  reader.readAsText(file, "utf-8");
}

function renderFeelingWorkspace() {
  renderLetterList();
  renderPairMatrix();
  renderFeelingInspector();
}

function renderLetterList() {
  const target = qa("#letterList");
  target.replaceChildren(...graph.letters.map((letter) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `letter-card${selectedFeeling.type === "letter" && selectedFeeling.id === letter.key ? " active" : ""}`;
    button.style.setProperty("--letter-color", letter.color || "#8f887b");
    button.innerHTML = `<strong>${letter.key}</strong><span>${escapeAssociation(letter.meanings.join("、") || "尚未定义")}</span>`;
    button.addEventListener("click", () => { selectedFeeling = { type: "letter", id: letter.key }; renderFeelingWorkspace(); });
    return button;
  }));
}

function renderPairMatrix() {
  const query = qa("#pairSearchInput").value.trim().toLowerCase();
  const target = qa("#pairMatrix");
  const fragment = document.createDocumentFragment();
  for (const pair of graph.pairs) {
    const text = `${pair.code} ${pair.labels.join(" ")} ${pair.description} ${pair.tags.join(" ")}`.toLowerCase();
    const matches = !query || text.includes(query);
    const button = document.createElement("button");
    button.type = "button";
    button.className = `pair-cell${pair.labels.length ? " defined" : ""}${selectedFeeling.type === "pair" && selectedFeeling.id === pair.code ? " active" : ""}${matches ? "" : " filtered"}`;
    if (pair.color) button.style.setProperty("--pair-color", pair.color);
    button.innerHTML = `<strong>${pair.code}</strong><span>${escapeAssociation(pair.labels.slice(0, 2).join("·"))}</span>`;
    button.title = pair.description || pair.labels.join("、") || `${pair.code} 尚未定义`;
    button.addEventListener("click", () => { selectedFeeling = { type: "pair", id: pair.code }; renderFeelingWorkspace(); });
    fragment.append(button);
  }
  target.replaceChildren(fragment);
}

function renderFeelingInspector() {
  const body = qa("#pairInspectorBody");
  qa("#pairInspectorEmpty").hidden = true;
  body.hidden = false;
  if (selectedFeeling.type === "letter") {
    const letter = graph.letters.find((item) => item.key === selectedFeeling.id);
    body.innerHTML = `<div class="feeling-code">${letter.key}</div><h2>字母感觉</h2><p class="muted-copy">它是组合的背景，不会限制双字母产生独立意义。</p>
      <label class="form-field">中文感觉<input id="feelingLabels" value="${escapeAttribute(letter.meanings.join("、"))}" placeholder="危险、尖锐"></label>
      <label class="form-field">来源与说明<textarea id="feelingDescription" rows="7">${escapeAssociation(letter.note)}</textarea></label>
      <label class="form-field">颜色<input id="feelingColor" type="color" value="${safeColor(letter.color)}"></label>`;
    qa("#feelingLabels").addEventListener("input", (event) => { letter.meanings = splitLabels(event.target.value); markGraphDirty(); renderLetterList(); });
    qa("#feelingDescription").addEventListener("input", (event) => { letter.note = event.target.value; markGraphDirty(); });
    qa("#feelingColor").addEventListener("input", (event) => { letter.color = event.target.value; markGraphDirty(); renderLetterList(); });
  } else {
    const pair = graph.pairs.find((item) => item.code === selectedFeeling.id);
    const left = graph.letters.find((item) => item.key === pair.code[0]);
    const right = graph.letters.find((item) => item.key === pair.code[1]);
    body.innerHTML = `<div class="feeling-code pair">${pair.code}</div><h2>独立双字母感受</h2>
      <div class="component-feelings"><span>${left.key} · ${escapeAssociation(left.meanings.join("、") || "未定义")}</span><span>${right.key} · ${escapeAssociation(right.meanings.join("、") || "未定义")}</span></div>
      <label class="form-field">中文标签<input id="feelingLabels" value="${escapeAttribute(pair.labels.join("、"))}" placeholder="可以填写多个感受"></label>
      <label class="form-field">独特描述<textarea id="feelingDescription" rows="7" placeholder="这个组合让你想到什么？">${escapeAssociation(pair.description)}</textarea></label>
      <label class="form-field">标签<input id="feelingTags" value="${escapeAttribute(pair.tags.join("、"))}" placeholder="情绪、空间、触感……"></label>
      <label class="form-field">颜色<input id="feelingColor" type="color" value="${safeColor(pair.color)}"></label>
      <button id="openPairGraph" class="button primary wide" type="button">在图谱中查看 ${pair.code}</button>`;
    qa("#feelingLabels").addEventListener("input", (event) => { pair.labels = splitLabels(event.target.value); markGraphDirty(); renderPairMatrix(); });
    qa("#feelingDescription").addEventListener("input", (event) => { pair.description = event.target.value; markGraphDirty(); });
    qa("#feelingTags").addEventListener("input", (event) => { pair.tags = splitLabels(event.target.value); markGraphDirty(); });
    qa("#feelingColor").addEventListener("input", (event) => { pair.color = event.target.value; markGraphDirty(); renderPairMatrix(); });
    qa("#openPairGraph").addEventListener("click", () => { selectedGraphNode = `pair-${pair.code}`; switchWorkspace("graphView"); setGraphMode("focus"); });
  }
}

function splitLabels(value) { return [...new Set(value.split(/[，,、]/).map((item) => item.trim()).filter(Boolean))]; }
function safeColor(value) { return /^#[0-9a-f]{6}$/i.test(value || "") ? value : "#8f887b"; }

function rebuildGraphIndexes() {
  graphNodes = new Map();
  graph.letters.forEach((item) => graphNodes.set(`letter-${item.key}`, { id: `letter-${item.key}`, type: "letter", data: item }));
  graph.pairs.forEach((item) => graphNodes.set(`pair-${item.code}`, { id: `pair-${item.code}`, type: "pair", data: item }));
  graph.characters.forEach((item) => graphNodes.set(item.id, { id: item.id, type: "character", data: item }));
  graph.concepts.forEach((item) => graphNodes.set(item.id, { id: item.id, type: "concept", data: item }));
  graph.themes.forEach((item) => graphNodes.set(item.id, { id: item.id, type: "theme", data: item }));
  graphAdjacency = new Map([...graphNodes.keys()].map((id) => [id, []]));
  const themeEdges = graph.concepts.flatMap((concept) => concept.themes.map((themeId) => ({
    id: `derived-${themeId}-${concept.id}`, source: themeId, target: concept.id,
    relation: "归入主题", status: "confirmed", origin: "derived-theme", note: "",
  })));
  graphAllEdges = [...graph.edges, ...themeEdges];
  for (const edge of graphAllEdges) {
    if (!graphAdjacency.has(edge.source) || !graphAdjacency.has(edge.target)) continue;
    graphAdjacency.get(edge.source).push({ edge, other: edge.target });
    graphAdjacency.get(edge.target).push({ edge, other: edge.source });
  }
}

function setGraphMode(mode) {
  graphMode = mode;
  qaa(".graph-mode").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  qa("#themePickerWrap").hidden = mode !== "theme";
  renderGraphWorkspace(true);
}

function renderGraphWorkspace(resetCamera = false) {
  if (!graph) return;
  rebuildGraphIndexes();
  renderThemeSelect();
  buildVisibleGraph();
  if (resetCamera) fitGraphCamera();
  renderGraphInspector();
  qa("#graphSummary").textContent = `${visibleGraphNodes.length.toLocaleString()} 节点 · ${visibleGraphEdges.length.toLocaleString()} 关系`;
  requestGraphRender();
}

function renderThemeSelect() {
  const select = qa("#themeSelect");
  const current = select.value || graph.themes[0]?.id || "";
  select.replaceChildren(...graph.themes.map((item) => new Option(item.label, item.id, false, item.id === current)));
}

function buildVisibleGraph() {
  let ids = new Set();
  if (graphMode === "focus") {
    if (!graphNodes.has(selectedGraphNode)) selectedGraphNode = "u-25cb";
    ids.add(selectedGraphNode);
    let frontier = [selectedGraphNode];
    const depth = Math.max(1, Math.min(2, Number(graph.views.focusDepth) || 2));
    for (let level = 0; level < depth; level++) {
      const next = [];
      for (const id of frontier) for (const link of graphAdjacency.get(id) || []) if (!ids.has(link.other)) { ids.add(link.other); next.push(link.other); }
      frontier = next;
    }
  } else if (graphMode === "theme") {
    const themeId = qa("#themeSelect").value || graph.themes[0]?.id;
    ids.add(themeId);
    const conceptIds = graph.concepts.filter((item) => item.themes.includes(themeId)).map((item) => item.id);
    conceptIds.forEach((id) => ids.add(id));
    for (const id of conceptIds) for (const link of graphAdjacency.get(id) || []) ids.add(link.other);
  } else ids = new Set(graphNodes.keys());
  visibleGraphNodes = [...ids].map((id) => graphNodes.get(id)).filter(Boolean);
  visibleGraphEdges = graphAllEdges.filter((edge) => ids.has(edge.source) && ids.has(edge.target));
  assignDefaultPositions();
}

function assignDefaultPositions() {
  if (graphMode === "focus") {
    const root = selectedGraphNode;
    const distance = new Map([[root, 0]]);
    const queue = [root];
    while (queue.length) {
      const id = queue.shift();
      for (const link of graphAdjacency.get(id) || []) if (!distance.has(link.other) && visibleGraphNodes.some((node) => node.id === link.other)) { distance.set(link.other, distance.get(id) + 1); queue.push(link.other); }
    }
    const layers = new Map();
    for (const node of visibleGraphNodes) { const layer = distance.get(node.id) || 0; if (!layers.has(layer)) layers.set(layer, []); layers.get(layer).push(node); }
    for (const [layer, nodes] of layers) nodes.forEach((node, index) => {
      if (layer === 0) node.position = { x: 0, y: 0 };
      else { const angle = Math.PI * 2 * index / nodes.length - Math.PI / 2; node.position = { x: Math.cos(angle) * 240 * layer, y: Math.sin(angle) * 180 * layer }; }
    });
    return;
  }
  const saved = graph.views.positions[graphMode] || (graph.views.positions[graphMode] = {});
  const groups = { letter: [], pair: [], theme: [], concept: [], character: [] };
  visibleGraphNodes.forEach((node) => groups[node.type].push(node));
  groups.letter.forEach((node, index) => node.position = saved[node.id] ? xy(saved[node.id]) : { x: 90 + (index % 13) * 82, y: 80 + Math.floor(index / 13) * 70 });
  groups.pair.forEach((node, index) => node.position = saved[node.id] ? xy(saved[node.id]) : { x: 90 + (index % 26) * 48, y: 270 + Math.floor(index / 26) * 42 });
  groups.theme.forEach((node, index) => node.position = saved[node.id] ? xy(saved[node.id]) : { x: 1500, y: 80 + index * 100 });
  groups.concept.forEach((node, index) => node.position = saved[node.id] ? xy(saved[node.id]) : { x: 1750 + (index % 8) * 125, y: 80 + Math.floor(index / 8) * 95 });
  groups.character.forEach((node, index) => node.position = saved[node.id] ? xy(saved[node.id]) : { x: 2900 + (index % 40) * 56, y: 80 + Math.floor(index / 40) * 55 });
  if (graphMode === "theme") {
    const theme = groups.theme[0]; if (theme) theme.position = saved[theme.id] ? xy(saved[theme.id]) : { x: 0, y: 0 };
    groups.concept.forEach((node, index) => { if (!saved[node.id]) { const a = Math.PI * 2 * index / Math.max(1, groups.concept.length); node.position = { x: Math.cos(a) * 260, y: Math.sin(a) * 200 }; } });
    groups.character.concat(groups.letter, groups.pair).forEach((node, index, arr) => { if (!saved[node.id]) { const a = Math.PI * 2 * index / Math.max(1, arr.length); node.position = { x: Math.cos(a) * 520, y: Math.sin(a) * 390 }; } });
  }
}

function xy(value) { return { x: Number(value[0]) || 0, y: Number(value[1]) || 0 }; }

function fitGraphCamera() {
  const wrap = qa("#graphCanvasWrap");
  const width = Math.max(400, wrap.clientWidth), height = Math.max(300, wrap.clientHeight);
  if (!visibleGraphNodes.length) { graphCamera = { x: width / 2, y: height / 2, scale: 1 }; return; }
  const xs = visibleGraphNodes.map((node) => node.position.x), ys = visibleGraphNodes.map((node) => node.position.y);
  const minX = Math.min(...xs) - 80, maxX = Math.max(...xs) + 80, minY = Math.min(...ys) - 80, maxY = Math.max(...ys) + 80;
  const scale = Math.max(.08, Math.min(1.15, Math.min(width / (maxX - minX), height / (maxY - minY))));
  graphCamera = { x: width / 2 - ((minX + maxX) / 2) * scale, y: height / 2 - ((minY + maxY) / 2) * scale, scale };
}

function requestGraphRender() {
  if (graphRenderPending) return;
  graphRenderPending = true;
  requestAnimationFrame(() => { graphRenderPending = false; drawGraph(); });
}

function drawGraph() {
  if (!graph) return;
  const canvas = qa("#graphCanvas"), wrap = qa("#graphCanvasWrap");
  const dpr = window.devicePixelRatio || 1, width = Math.max(400, wrap.clientWidth), height = Math.max(300, wrap.clientHeight);
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) { canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr); canvas.style.width = `${width}px`; canvas.style.height = `${height}px`; }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f7f2e9"; ctx.fillRect(0, 0, width, height);
  ctx.save(); ctx.translate(graphCamera.x, graphCamera.y); ctx.scale(graphCamera.scale, graphCamera.scale);
  ctx.lineWidth = 1 / graphCamera.scale;
  for (const edge of visibleGraphEdges) {
    const a = graphNodes.get(edge.source), b = graphNodes.get(edge.target); if (!a?.position || !b?.position) continue;
    ctx.strokeStyle = edge.status === "suggested" ? "rgba(135,126,110,.24)" : "rgba(126,82,57,.5)";
    ctx.setLineDash(edge.status === "suggested" ? [5 / graphCamera.scale, 5 / graphCamera.scale] : []);
    ctx.beginPath(); ctx.moveTo(a.position.x, a.position.y); ctx.lineTo(b.position.x, b.position.y); ctx.stroke();
  }
  ctx.setLineDash([]);
  for (const node of visibleGraphNodes) drawNode(ctx, node);
  ctx.restore();
}

function drawNode(ctx, node) {
  const radius = node.type === "character" ? 22 : node.type === "theme" ? 20 : node.type === "concept" ? 17 : 14;
  const selected = node.id === selectedGraphNode;
  ctx.beginPath(); ctx.arc(node.position.x, node.position.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = nodeColor(node); ctx.fill();
  ctx.lineWidth = (selected ? 4 : 1) / graphCamera.scale;
  ctx.strokeStyle = selected ? "#a2472f" : "rgba(56,49,39,.28)"; ctx.stroke();
  const showLabel = graphCamera.scale > .42 || selected || node.type === "theme";
  if (showLabel) {
    ctx.font = `${node.type === "character" ? 20 : 11}px ${node.type === "character" ? '"Segoe UI Symbol"' : '"Microsoft YaHei UI"'}`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = node.type === "character" ? "#27251f" : "#fff";
    ctx.fillText(nodeLabel(node).slice(0, 12), node.position.x, node.position.y);
    if (selected && node.type !== "character") { ctx.font = "11px Microsoft YaHei UI"; ctx.fillStyle = "#27251f"; ctx.fillText(nodeLabel(node).slice(0, 20), node.position.x, node.position.y + radius + 13); }
  }
}

function nodeColor(node) {
  if (node.type === "letter" || node.type === "pair" || node.type === "theme") return node.data.color || (node.type === "pair" ? "#87654e" : "#557b52");
  if (node.type === "concept") return node.data.status === "suggested" ? "#9b9589" : "#a2472f";
  return "#fffdf7";
}

function nodeLabel(node) {
  if (node.type === "letter") return node.data.key;
  if (node.type === "pair") return node.data.code;
  if (node.type === "character") return node.data.char;
  return node.data.label;
}

function screenToWorld(x, y) { return { x: (x - graphCamera.x) / graphCamera.scale, y: (y - graphCamera.y) / graphCamera.scale }; }
function hitNode(x, y) {
  const world = screenToWorld(x, y);
  for (let index = visibleGraphNodes.length - 1; index >= 0; index--) {
    const node = visibleGraphNodes[index], radius = node.type === "character" ? 25 : 20;
    if (Math.hypot(world.x - node.position.x, world.y - node.position.y) <= radius) return node;
  }
  return null;
}

function pointerPosition(event) { const rect = qa("#graphCanvas").getBoundingClientRect(); return { x: event.clientX - rect.left, y: event.clientY - rect.top }; }
function graphPointerDown(event) {
  const point = pointerPosition(event), node = hitNode(point.x, point.y);
  graphPointer = { id: event.pointerId, start: point, last: point, node, moved: false };
  qa("#graphCanvas").setPointerCapture(event.pointerId);
  if (node) { selectedGraphNode = node.id; renderGraphInspector(); requestGraphRender(); }
}
function graphPointerMove(event) {
  if (!graphPointer || graphPointer.id !== event.pointerId) return;
  const point = pointerPosition(event), dx = point.x - graphPointer.last.x, dy = point.y - graphPointer.last.y;
  if (Math.hypot(point.x - graphPointer.start.x, point.y - graphPointer.start.y) > 3) graphPointer.moved = true;
  if (graphPointer.node) { graphPointer.node.position.x += dx / graphCamera.scale; graphPointer.node.position.y += dy / graphCamera.scale; }
  else { graphCamera.x += dx; graphCamera.y += dy; }
  graphPointer.last = point; requestGraphRender();
}
function graphPointerUp(event) {
  if (!graphPointer || graphPointer.id !== event.pointerId) return;
  if (graphPointer.node && graphPointer.moved && graphMode !== "focus") {
    const saved = graph.views.positions[graphMode] || (graph.views.positions[graphMode] = {});
    saved[graphPointer.node.id] = [Math.round(graphPointer.node.position.x), Math.round(graphPointer.node.position.y)]; markGraphDirty();
  }
  graphPointer = null;
}
function graphDoubleClick(event) { const point = pointerPosition(event), node = hitNode(point.x, point.y); if (node) { selectedGraphNode = node.id; setGraphMode("focus"); } }
function graphWheel(event) {
  event.preventDefault(); const point = pointerPosition(event), before = screenToWorld(point.x, point.y);
  const factor = event.deltaY < 0 ? 1.12 : .89; graphCamera.scale = Math.max(.06, Math.min(3, graphCamera.scale * factor));
  graphCamera.x = point.x - before.x * graphCamera.scale; graphCamera.y = point.y - before.y * graphCamera.scale; requestGraphRender();
}

function searchGraph(value) {
  const query = value.trim().toLowerCase(); if (!query) return;
  const matches = [...graphNodes.values()].filter((node) => `${node.id} ${nodeLabel(node)} ${JSON.stringify(node.data)}`.toLowerCase().includes(query));
  if (!matches.length) { toast("没有找到对应节点"); return; }
  selectedGraphNode = matches[0].id; setGraphMode("focus"); toast(`找到 ${matches.length} 个节点，已聚焦第一个`);
}

function renderGraphInspector() {
  const target = qa("#graphInspector"), node = graphNodes.get(selectedGraphNode);
  if (!node) { target.innerHTML = `<div class="inspector-empty"><span>∞</span><p>从图谱中选择字符、概念或双字母。</p></div>`; return; }
  const links = graphAdjacency.get(node.id) || [];
  target.innerHTML = `<div class="graph-node-head"><span class="node-type">${nodeTypeName(node.type)}</span><div class="graph-node-symbol">${escapeAssociation(nodeLabel(node))}</div><h2>${escapeAssociation(nodeTitle(node))}</h2></div>
    <div id="nodeEditor"></div><section class="relation-section"><div class="relation-heading"><h3>关联 ${links.length}</h3></div><div id="relationList" class="relation-list"></div></section>`;
  renderNodeEditor(node);
  const list = qa("#relationList");
  if (!links.length) list.innerHTML = `<p class="muted-copy">暂时没有关系。</p>`;
  else list.replaceChildren(...links.map(({ edge, other }) => relationCard(edge, graphNodes.get(other))));
}

function renderNodeEditor(node) {
  const target = qa("#nodeEditor");
  if (node.type === "character") {
    const aliases = graph.rimeAliases.filter((item) => item.characterId === node.id);
    target.innerHTML = `<dl class="metadata compact-meta"><div><dt>码位</dt><dd>${node.data.codepoint}</dd></div><div><dt>机器定位码</dt><dd>${node.data.machineCode}</dd></div><div><dt>形码</dt><dd>${node.data.shapeSuffix}</dd></div></dl>
      <div class="add-relation"><h3>添加中文联想</h3><input id="newConceptInput" placeholder="例如：完整、回归、庇护"><button id="addConceptRelation" class="button primary" type="button">添加</button></div>
      <section class="alias-section"><h3>已启用联想码 ${aliases.length}</h3><div id="aliasList"></div></section>`;
    qa("#addConceptRelation").addEventListener("click", () => addConceptForNode(node.id, qa("#newConceptInput").value));
    const aliasList = qa("#aliasList");
    aliasList.replaceChildren(...aliases.map((alias) => {
      const row = document.createElement("div"); row.className = "alias-row";
      row.innerHTML = `<code>${alias.prefix}${alias.suffix}</code><span>${alias.enabled ? "已启用" : "未启用"}</span><button type="button" aria-label="删除别名">×</button>`;
      row.querySelector("button").addEventListener("click", () => { graph.rimeAliases = graph.rimeAliases.filter((item) => item.id !== alias.id); markGraphDirty(); renderGraphWorkspace(); });
      return row;
    }));
  } else if (node.type === "concept") {
    target.innerHTML = `<label class="form-field">中文概念<input id="conceptLabel" value="${escapeAttribute(node.data.label)}"></label>
      <label class="form-field">近义词<input id="conceptSynonyms" value="${escapeAttribute(node.data.synonyms.join("、"))}"></label>
      <label class="form-field">说明<textarea id="conceptNote" rows="4">${escapeAssociation(node.data.note || "")}</textarea></label>
      <div class="theme-checks">${graph.themes.map((theme) => `<label><input type="checkbox" value="${theme.id}" ${node.data.themes.includes(theme.id) ? "checked" : ""}>${escapeAssociation(theme.label)}</label>`).join("")}</div>
      <button id="confirmConcept" class="button primary wide" type="button">${node.data.status === "confirmed" ? "已确认" : "确认这条个人联想"}</button>`;
    qa("#conceptLabel").addEventListener("input", (event) => { node.data.label = event.target.value; markGraphDirty(); requestGraphRender(); });
    qa("#conceptSynonyms").addEventListener("input", (event) => { node.data.synonyms = splitLabels(event.target.value); markGraphDirty(); });
    qa("#conceptNote").addEventListener("input", (event) => { node.data.note = event.target.value; markGraphDirty(); });
    qaa(".theme-checks input").forEach((input) => input.addEventListener("change", () => { node.data.themes = qaa(".theme-checks input:checked").map((item) => item.value); markGraphDirty(); }));
    qa("#confirmConcept").addEventListener("click", () => { node.data.status = "confirmed"; node.data.source = "user-confirmed"; graph.edges.filter((edge) => edge.source === node.id || edge.target === node.id).forEach((edge) => { if (edge.status === "suggested") edge.status = "confirmed"; }); markGraphDirty(); renderGraphWorkspace(); });
  } else if (node.type === "theme") {
    target.innerHTML = `<label class="form-field">主题名称<input id="themeLabelInput" value="${escapeAttribute(node.data.label)}"></label><label class="form-field">颜色<input id="themeColorInput" type="color" value="${safeColor(node.data.color)}"></label>`;
    qa("#themeLabelInput").addEventListener("input", (event) => { node.data.label = event.target.value; markGraphDirty(); renderThemeSelect(); requestGraphRender(); });
    qa("#themeColorInput").addEventListener("input", (event) => { node.data.color = event.target.value; markGraphDirty(); requestGraphRender(); });
  } else {
    target.innerHTML = `<p class="muted-copy">${node.type === "pair" ? escapeAssociation(node.data.labels.join("、") || "这个双字母尚未定义") : escapeAssociation(node.data.meanings.join("、") || "这个字母尚未定义")}</p><button id="editFeelingButton" class="button primary wide" type="button">前往双字母感觉编辑</button>`;
    qa("#editFeelingButton").addEventListener("click", () => { selectedFeeling = { type: node.type, id: node.type === "pair" ? node.data.code : node.data.key }; switchWorkspace("pairView"); renderFeelingWorkspace(); });
  }
}

function relationCard(edge, other) {
  const card = document.createElement("div"); card.className = `relation-card ${edge.status}`;
  card.innerHTML = `<div><strong>${escapeAssociation(nodeLabel(other))}</strong><span>${escapeAssociation(edge.relation)} · ${edge.status === "suggested" ? "机器建议" : "已确认"}</span></div><div class="relation-actions"></div>`;
  const actions = card.querySelector(".relation-actions");
  if (edge.status === "suggested") {
    const confirmButton = document.createElement("button"); confirmButton.type = "button"; confirmButton.textContent = "确认";
    confirmButton.addEventListener("click", () => { edge.status = "confirmed"; edge.origin = "user-confirmed"; const concept = other.type === "concept" ? other : graphNodes.get(edge.source)?.type === "concept" ? graphNodes.get(edge.source) : null; if (concept) { concept.data.status = "confirmed"; concept.data.source = "user-confirmed"; } markGraphDirty(); renderGraphWorkspace(); }); actions.append(confirmButton);
  }
  if ((graphNodes.get(edge.source)?.type === "character" && other.type === "concept") || (graphNodes.get(edge.target)?.type === "character" && other.type === "concept")) {
    const character = graphNodes.get(edge.source)?.type === "character" ? graphNodes.get(edge.source) : graphNodes.get(edge.target);
    const concept = other.type === "concept" ? other : graphNodes.get(edge.source)?.type === "concept" ? graphNodes.get(edge.source) : null;
    const enableButton = document.createElement("button"); enableButton.type = "button"; enableButton.textContent = "启用码";
    enableButton.addEventListener("click", () => enableAlias(character, concept)); actions.append(enableButton);
  }
  const deleteButton = document.createElement("button"); deleteButton.type = "button"; deleteButton.textContent = "删除";
  deleteButton.addEventListener("click", () => { graph.edges = graph.edges.filter((item) => item.id !== edge.id); rebuildGraphIndexes(); markGraphDirty(); renderGraphWorkspace(); }); actions.append(deleteButton);
  return card;
}

function addConceptForNode(nodeId, rawLabel) {
  const label = rawLabel.trim(); if (!label) { toast("先填写一个中文联想"); return; }
  let concept = graph.concepts.find((item) => item.label === label);
  if (!concept) { concept = { id: `concept-user-${Date.now().toString(36)}`, label, synonyms: [], themes: [], status: "confirmed", source: "user-confirmed", note: "" }; graph.concepts.push(concept); }
  const key = `${nodeId}|联想|${concept.id}`;
  if (!graph.edges.some((edge) => edge.source === nodeId && edge.target === concept.id)) graph.edges.push({ id: `edge-user-${hashText(key)}`, source: nodeId, target: concept.id, relation: "联想", status: "confirmed", origin: "user-confirmed", note: "" });
  rebuildGraphIndexes(); markGraphDirty(); selectedGraphNode = nodeId; renderGraphWorkspace();
}

function enableAlias(character, concept) {
  const prefix = prompt(`为“${concept.data.label}”选择双字母感受：`, "");
  if (prefix === null) return;
  const normalized = prefix.toLowerCase().replace(/[^a-z]/g, "").slice(0, 2);
  if (!graph.pairs.some((pair) => pair.code === normalized)) { toast("请输入两个小写字母，例如 rr"); return; }
  const suffixInput = prompt("确认后两位形码：", character.data.shapeSuffix);
  if (suffixInput === null) return;
  const suffix = suffixInput.toLowerCase().replace(/[^a-z]/g, "").slice(0, 2);
  if (!/^[a-z]{2}$/.test(suffix)) { toast("形码必须是两个小写字母"); return; }
  const code = normalized + suffix;
  const baseCharacters = new Set();
  if (window.keyEditor) window.keyEditor.characters().filter((item) => item.code === code).forEach((item) => baseCharacters.add(item.char));
  graph.rimeAliases.filter((item) => item.enabled && item.prefix + item.suffix === code).forEach((item) => { const node = graphNodes.get(item.characterId); if (node) baseCharacters.add(node.data.char); });
  baseCharacters.add(character.data.char);
  if (baseCharacters.size > 5) { toast(`${code} 会产生第 ${baseCharacters.size} 个候选，已拒绝启用`); return; }
  const id = `alias-${character.id}-${normalized}-${suffix}`;
  const existing = graph.rimeAliases.find((item) => item.id === id);
  if (existing) { existing.enabled = true; if (!existing.associationIds.includes(concept.id)) existing.associationIds.push(concept.id); }
  else graph.rimeAliases.push({ id, characterId: character.id, prefix: normalized, suffix, enabled: true, primary: false, associationIds: [concept.id], note: "" });
  const pairId = `pair-${normalized}`;
  if (!graph.edges.some((edge) => edge.source === pairId && edge.target === concept.id)) graph.edges.push({ id: `edge-user-${hashText(pairId + concept.id)}`, source: pairId, target: concept.id, relation: "唤起", status: "confirmed", origin: "user-confirmed", note: "" });
  const pair = graph.pairs.find((item) => item.code === normalized); if (!pair.labels.includes(concept.data.label)) pair.labels.push(concept.data.label);
  rebuildGraphIndexes(); markGraphDirty(); renderFeelingWorkspace(); renderGraphWorkspace(); toast(`已启用 ${character.data.char} = ${code}`);
}

function addTheme() {
  const label = prompt("新主题名称："); if (!label?.trim()) return;
  const theme = { id: `theme-user-${Date.now().toString(36)}`, label: label.trim(), color: "#557b52" };
  graph.themes.push(theme); selectedGraphNode = theme.id; markGraphDirty(); setGraphMode("theme");
}

function nodeTypeName(type) { return ({ letter: "字母感觉", pair: "双字母感受", character: "Unicode 字符", concept: "中文概念", theme: "主题" })[type] || type; }
function nodeTitle(node) { if (node.type === "character") return node.data.unicodeName; if (node.type === "pair") return node.data.labels.join("、") || "尚未定义"; if (node.type === "letter") return node.data.meanings.join("、") || "尚未定义"; return node.data.label; }
function hashText(text) { let hash = 2166136261; for (const char of text) { hash ^= char.codePointAt(0); hash = Math.imul(hash, 16777619); } return (hash >>> 0).toString(36); }
function escapeAssociation(value) { return String(value ?? "").replace(/[&<>"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[char]); }
function escapeAttribute(value) { return escapeAssociation(value).replace(/'/g, "&#039;"); }

bindAssociationEvents();
loadGraph().catch((error) => { graphStatus("联想图谱加载失败", "error"); toast(error.message); });
