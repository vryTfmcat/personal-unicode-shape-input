const DATA_URL = "data/initial-data.json";
const LETTERS = "abcdefghijklmnopqrstuvwxyz".split("");
const PAGE_BATCH = 400;

let pristine = null;
let state = null;
let patchState = null;
let activePage = "common";
let selectedId = null;
let query = "";
let navQuery = "";
let conflictOnly = false;
let displayLimit = PAGE_BATCH;
let toastTimer = null;
let itemIndex = new Map();
let pageLookup = new Map();
let pageIndex = new Map();
let codeIndex = new Map();
let favoriteIds = new Set();

const $ = (selector) => document.querySelector(selector);

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function pageById(id) { return pageLookup.get(id); }
function itemById(id) { return itemIndex.get(id); }
function selectedItem() { return selectedId ? itemById(selectedId) : null; }

function emptyPatch() {
  return { format: "unicode-key-editor-patch-v1", baseVersion: pristine.version, pages: {}, characters: {}, commonOrder: null };
}

async function init() {
  $("#saveStatus").textContent = "正在加载全量字库";
  pristine = await fetch(DATA_URL).then((response) => {
    if (!response.ok) throw new Error("无法读取初始数据");
    return response.json();
  });
  state = pristine;
  patchState = emptyPatch();
  const saved = localStorage.getItem(pristine.storageKey);
  if (saved) {
    try { applyPatch(JSON.parse(saved)); }
    catch { patchState = emptyPatch(); }
  }
  rebuildIndexes();
  bindStaticEvents();
  renderAll();
  $("#saveStatus").textContent = "本地草稿";
  window.keyEditor = {
    itemById,
    findCharacter: (char) => state.characters.find((item) => item.char === char) || null,
    codeCount: (code) => codeIndex.get(code) || 0,
    characters: () => state.characters,
  };
  document.dispatchEvent(new CustomEvent("key-editor-ready"));
}

function applyPatch(incoming) {
  if (incoming.format !== "unicode-key-editor-patch-v1" || incoming.baseVersion !== pristine.version) throw new Error("草稿版本不匹配");
  patchState = incoming;
  const pages = new Map(state.pages.map((page) => [page.id, page]));
  for (const [id, changes] of Object.entries(incoming.pages || {})) if (pages.has(id)) Object.assign(pages.get(id), changes);
  const characters = new Map(state.characters.map((item) => [item.id, item]));
  for (const [id, changes] of Object.entries(incoming.characters || {})) if (characters.has(id)) Object.assign(characters.get(id), changes);
  if (Array.isArray(incoming.commonOrder)) state.commonOrder = incoming.commonOrder;
}

function rebuildIndexes() {
  itemIndex = new Map(state.characters.map((item) => [item.id, item]));
  pageLookup = new Map(state.pages.map((page) => [page.id, page]));
  pageIndex = new Map(state.pages.map((page) => [page.id, []]));
  codeIndex = new Map();
  favoriteIds = new Set();
  for (const item of state.characters) {
    if (!pageIndex.has(item.pageId)) pageIndex.set(item.pageId, []);
    pageIndex.get(item.pageId).push(item);
    codeIndex.set(item.code, (codeIndex.get(item.code) || 0) + 1);
    if (item.favorite) favoriteIds.add(item.id);
  }
}

function bindStaticEvents() {
  $("#pageSearchInput").addEventListener("input", (event) => { navQuery = event.target.value.trim().toLowerCase(); renderNav(); });
  $("#searchInput").addEventListener("input", (event) => { query = event.target.value.trim().toLowerCase(); displayLimit = PAGE_BATCH; renderGrid(); });
  $("#conflictOnly").addEventListener("change", (event) => { conflictOnly = event.target.checked; displayLimit = PAGE_BATCH; renderGrid(); });
  $("#blockInput").addEventListener("input", (event) => { pageById(activePage).block = event.target.value; save(); });
  $("#exportButton").addEventListener("click", exportJson);
  $("#exportTsvButton").addEventListener("click", exportTsv);
  $("#importInput").addEventListener("change", importJson);
  $("#resetButton").addEventListener("click", resetState);
  $("#copyGlyphButton").addEventListener("click", copyGlyph);
  $("#favoriteInput").addEventListener("change", updateFavorite);
  $("#codeInput").addEventListener("input", updateCode);
  $("#pageSelect").addEventListener("change", (event) => moveItem(selectedId, event.target.value, false));
  $("#mainKeySelect").addEventListener("change", updateShapeKeys);
  $("#stateKeySelect").addEventListener("change", updateShapeKeys);
  $("#noteInput").addEventListener("input", (event) => { const item = selectedItem(); if (item) { item.note = event.target.value; save(); } });
}

function snapshotItem(item) {
  return { code: item.code, pageId: item.pageId, favorite: item.favorite, mainKey: item.mainKey, stateKey: item.stateKey, note: item.note };
}

function snapshotPage(page) {
  return { name: page.name, block: page.block, description: page.description, mainRules: clone(page.mainRules), stateRules: clone(page.stateRules) };
}

function save() {
  const item = selectedItem();
  const page = pageById(activePage);
  if (item) patchState.characters[item.id] = snapshotItem(item);
  if (page) patchState.pages[page.id] = snapshotPage(page);
  patchState.commonOrder = [...state.commonOrder];
  try {
    localStorage.setItem(pristine.storageKey, JSON.stringify(patchState));
    const status = $("#saveStatus");
    status.textContent = `已保存 ${Object.keys(patchState.characters).length} 个字符修改`;
    clearTimeout(save.statusTimer);
    save.statusTimer = setTimeout(() => { status.textContent = "本地草稿"; }, 1400);
  } catch {
    $("#saveStatus").textContent = "草稿空间不足，请导出 JSON";
  }
}

function pageItems(pageId) {
  if (pageId === "common") {
    const order = new Map(state.commonOrder.map((id, index) => [id, index]));
    return [...favoriteIds].map(itemById).filter(Boolean).sort((a, b) => (order.get(a.id) ?? 999999) - (order.get(b.id) ?? 999999) || a.codepoint.localeCompare(b.codepoint));
  }
  return pageIndex.get(pageId) || [];
}

function codeCounts(items) {
  return items.reduce((map, item) => map.set(item.code, (map.get(item.code) || 0) + 1), new Map());
}

function renderAll() {
  if (!pageById(activePage)) activePage = "common";
  renderNav();
  renderPageHeader();
  renderGrid();
  renderInspector();
}

function renderNav() {
  const nav = $("#pageNav");
  nav.replaceChildren();
  for (const page of state.pages) {
    const haystack = `${page.id} ${page.name} ${page.block}`.toLowerCase();
    if (navQuery && page.id !== activePage && !haystack.includes(navQuery)) continue;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "page-button" + (page.id === activePage ? " active" : "");
    button.dataset.pageId = page.id;
    const count = page.id === "common" ? favoriteIds.size : (pageIndex.get(page.id)?.length || 0);
    button.innerHTML = `<span class="page-prefix">${page.id === "common" ? "★" : page.prefix}</span><span class="page-name">${escapeHtml(page.name)}</span><span class="page-number">${count}</span>`;
    button.addEventListener("click", () => { activePage = page.id; query = ""; displayLimit = PAGE_BATCH; $("#searchInput").value = ""; renderAll(); });
    button.addEventListener("dragover", (event) => { event.preventDefault(); button.classList.add("drag-over"); });
    button.addEventListener("dragleave", () => button.classList.remove("drag-over"));
    button.addEventListener("drop", (event) => { event.preventDefault(); button.classList.remove("drag-over"); moveItem(event.dataTransfer.getData("text/plain"), page.id, true); });
    nav.append(button);
  }
}

function renderPageHeader() {
  const page = pageById(activePage);
  $("#prefixBadge").textContent = page.id === "common" ? "收藏层" : `${page.prefix}**`;
  $("#pageTitle").textContent = page.name;
  $("#pageDescription").textContent = page.description;
  $("#blockInput").value = page.block;
  renderRules("mainRules", page.mainRules);
  renderRules("stateRules", page.stateRules);
}

function renderRules(targetId, rules) {
  const target = document.getElementById(targetId);
  target.replaceChildren();
  for (const key of LETTERS) {
    const label = document.createElement("label");
    label.className = "rule-item";
    label.innerHTML = `<span>${key}</span>`;
    const input = document.createElement("input");
    input.value = rules[key] || "";
    input.setAttribute("aria-label", `${key} 键规则`);
    input.addEventListener("input", (event) => { rules[key] = event.target.value; save(); if (selectedItem()) renderInspector(); });
    label.append(input);
    target.append(label);
  }
}

function filteredItems(source, counts) {
  return source.filter((item) => {
    const haystack = `${item.char} ${item.code} ${item.codepoint} ${item.unicodeName}`.toLowerCase();
    return (!query || haystack.includes(query)) && (!conflictOnly || (counts.get(item.code) || 0) > 1);
  });
}

function renderGrid() {
  const all = pageItems(activePage);
  const counts = codeCounts(all);
  const items = filteredItems(all, counts);
  const shown = items.slice(0, displayLimit);
  const collisions = [...counts.values()].filter((count) => count > 1).reduce((sum, count) => sum + count, 0);
  const overFive = [...counts.values()].filter((count) => count > 5).length;
  $("#pageCount").textContent = `${all.length.toLocaleString()} 字符`;
  $("#conflictSummary").textContent = `${shown.length.toLocaleString()}/${items.length.toLocaleString()} 显示 · ${collisions.toLocaleString()} 同码${overFive ? ` · ${overFive} 组超限` : ""}`;
  const grid = $("#glyphGrid");
  grid.replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const item of shown) {
    const count = counts.get(item.code) || 1;
    const card = document.createElement("button");
    card.type = "button";
    card.className = `glyph-card${item.id === selectedId ? " selected" : ""}${count > 5 ? " over-five" : ""}`;
    card.draggable = true;
    card.title = item.unicodeName;
    card.innerHTML = `${item.favorite ? '<span class="favorite-star">★</span>' : ""}${count > 1 ? `<span class="collision-dot${count > 5 ? " hot" : ""}">${count}</span>` : ""}<span class="glyph">${escapeHtml(item.char)}</span><span class="glyph-code">${escapeHtml(item.code)}</span><span class="glyph-cp">${item.codepoint}</span>`;
    card.addEventListener("click", () => { selectedId = item.id; renderGrid(); renderInspector(); });
    card.addEventListener("dragstart", (event) => { event.dataTransfer.setData("text/plain", item.id); event.dataTransfer.effectAllowed = "move"; card.classList.add("dragging"); });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
    fragment.append(card);
  }
  if (items.length > shown.length) {
    const more = document.createElement("button");
    more.type = "button";
    more.className = "load-more";
    more.textContent = `继续显示 ${Math.min(PAGE_BATCH, items.length - shown.length).toLocaleString()} 个`;
    more.addEventListener("click", () => { displayLimit += PAGE_BATCH; renderGrid(); });
    fragment.append(more);
  }
  grid.append(fragment);
  $("#emptyState").hidden = items.length !== 0;
}

function renderInspector() {
  const item = selectedItem();
  $("#inspectorEmpty").hidden = Boolean(item);
  $("#inspectorBody").hidden = !item;
  if (!item) return;
  $("#inspectorGlyph").textContent = item.char;
  $("#inspectorCodepoint").textContent = item.codepoint;
  $("#inspectorName").textContent = item.unicodeName;
  $("#favoriteInput").checked = item.favorite;
  $("#codeInput").value = item.code;
  setCodeHint(item);
  $("#noteInput").value = item.note || "";
  $("#sourceBlock").textContent = item.sourceBlock;
  const pages = state.pages.filter((page) => page.id !== "common");
  $("#pageSelect").replaceChildren(...pages.map((page) => new Option(`${page.prefix} · ${page.name}`, page.id, false, item.pageId === page.id)));
  const rulePage = pageById(item.pageId) || pageById(activePage);
  fillKeySelect($("#mainKeySelect"), rulePage.mainRules, item.mainKey || item.code[2] || "");
  fillKeySelect($("#stateKeySelect"), rulePage.stateRules, item.stateKey || item.code[3] || "");
  renderInspectorMetadataOnly(item);
}

function fillKeySelect(select, rules, selected) {
  select.replaceChildren(...LETTERS.map((key) => new Option(`${key} · ${rules[key] || "未定义"}`, key, false, key === selected)));
}

function changeCodeIndex(oldCode, newCode) {
  if (oldCode === newCode) return;
  codeIndex.set(oldCode, Math.max(0, (codeIndex.get(oldCode) || 1) - 1));
  codeIndex.set(newCode, (codeIndex.get(newCode) || 0) + 1);
}

function moveItem(id, targetPageId, fromDrag) {
  const item = itemById(id);
  const target = pageById(targetPageId);
  if (!item || !target) return;
  if (targetPageId === "common" && fromDrag) {
    item.favorite = true;
    favoriteIds.add(item.id);
    if (!state.commonOrder.includes(item.id)) state.commonOrder.push(item.id);
    showToast(`${item.char} 已加入常用字符；原码 ${item.code} 保持不变`);
  } else if (targetPageId !== "common" && item.pageId !== targetPageId) {
    const oldPage = item.pageId;
    const oldCode = item.code;
    const suffix = (item.code || "qq").slice(-2).padEnd(2, "q");
    const oldMembers = pageIndex.get(oldPage) || [];
    const position = oldMembers.indexOf(item);
    if (position >= 0) oldMembers.splice(position, 1);
    pageIndex.get(targetPageId).push(item);
    item.pageId = targetPageId;
    item.code = target.prefix + suffix;
    item.mainKey = suffix[0];
    item.stateKey = suffix[1];
    changeCodeIndex(oldCode, item.code);
    showToast(`${item.char} 已移动到 ${target.prefix}，新码 ${item.code}`);
  }
  selectedId = item.id;
  save();
  renderAll();
}

function updateFavorite(event) {
  const item = selectedItem();
  if (!item) return;
  item.favorite = event.target.checked;
  if (item.favorite) {
    favoriteIds.add(item.id);
    if (!state.commonOrder.includes(item.id)) state.commonOrder.push(item.id);
  } else favoriteIds.delete(item.id);
  save(); renderNav(); renderGrid();
}

function updateCode(event) {
  const item = selectedItem();
  if (!item) return;
  const normalized = event.target.value.toLowerCase().replace(/[^a-z]/g, "").slice(0, 4);
  event.target.value = normalized;
  const oldCode = item.code;
  item.code = normalized;
  item.mainKey = normalized[2] || "";
  item.stateKey = normalized[3] || "";
  changeCodeIndex(oldCode, normalized);
  save(); setCodeHint(item); renderGrid(); renderInspectorMetadataOnly(item);
}

function updateShapeKeys() {
  const item = selectedItem();
  if (!item) return;
  const oldCode = item.code;
  item.mainKey = $("#mainKeySelect").value;
  item.stateKey = $("#stateKeySelect").value;
  const owner = pageById(item.pageId);
  const prefix = owner?.prefix || (item.code || "qq").slice(0, 2).padEnd(2, "q");
  item.code = prefix + item.mainKey + item.stateKey;
  changeCodeIndex(oldCode, item.code);
  save(); renderGrid(); renderInspector();
}

function setCodeHint(item) {
  const hint = $("#codeHint");
  const valid = /^[a-z]{2,4}$/.test(item.code);
  hint.textContent = valid ? "允许 2–4 个小写字母；四码可拆为前缀 + 形符。" : "请输入 2–4 个英文字母。";
  hint.className = valid ? "" : "error";
}

function renderInspectorMetadataOnly(item) {
  const same = codeIndex.get(item.code) || 0;
  $("#sameCodeCount").textContent = `${same} 个${same > 5 ? "（超过候选上限）" : ""}`;
}

async function copyGlyph() {
  const item = selectedItem();
  if (!item) return;
  try { await navigator.clipboard.writeText(item.char); showToast(`已复制 ${item.char}`); }
  catch { showToast("浏览器未允许自动复制，请手动选择字符"); }
}

function exportJson() {
  patchState.commonOrder = [...state.commonOrder];
  download(`unicode-key-editor-patch-${dateStamp()}.json`, JSON.stringify(patchState, null, 2), "application/json;charset=utf-8");
}

function exportTsv() {
  $("#saveStatus").textContent = "正在生成全量 TSV";
  setTimeout(() => {
    const header = ["字符", "码位", "输入码", "页面", "常用", "Unicode名称"];
    const rows = state.characters.map((item) => [item.char, item.codepoint, item.code, item.pageId, item.favorite ? "true" : "false", item.unicodeName]);
    const text = [header, ...rows].map((row) => row.map(tsvCell).join("\t")).join("\n") + "\n";
    download(`unicode-keymap-${dateStamp()}.tsv`, text, "text/tab-separated-values;charset=utf-8");
    $("#saveStatus").textContent = "本地草稿";
  }, 30);
}

function importJson(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const incoming = JSON.parse(reader.result);
      if (incoming.format !== "unicode-key-editor-patch-v1" || incoming.baseVersion !== pristine.version) throw new Error("这不是当前全量字库的修改草稿");
      localStorage.setItem(pristine.storageKey, JSON.stringify(incoming));
      window.location.reload();
    } catch (error) { showToast(`导入失败：${error.message}`); }
    event.target.value = "";
  };
  reader.readAsText(file, "utf-8");
}

function resetState() {
  if (!window.confirm("确定恢复到项目生成的全量初始键位吗？当前浏览器里的修改会被覆盖。")) return;
  localStorage.removeItem(pristine.storageKey);
  window.location.reload();
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

function dateStamp() { return new Date().toISOString().slice(0, 10); }
function tsvCell(value) { return String(value).replace(/[\t\r\n]+/g, " "); }
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]); }
function showToast(message) { const toast = $("#toast"); toast.textContent = message; toast.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove("show"), 2200); }

init().catch((error) => { document.body.innerHTML = `<main style="padding:40px;font-family:sans-serif"><h1>编辑器启动失败</h1><p>${escapeHtml(error.message)}</p><p>请使用“启动键位编辑器.cmd”，不要直接双击 index.html。</p></main>`; });
