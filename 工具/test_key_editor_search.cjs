// Exercise the editor's real search and navigation with the full character data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..', '原型', '键位编辑器');
class Element {
  constructor() { this.children = []; this.events = {}; this.value = ''; }
  replaceChildren(...children) { this.children = children; }
  append(child) {
    if (child.fragment) this.children.push(...child.children);
    else this.children.push(child);
  }
  addEventListener(type, callback) { this.events[type] = callback; }
  setAttribute(name, value) { this[name] = value; }
  get childElementCount() { return this.children.length; }
  dataset = {};
  classList = { add() {}, remove() {} };
}
const elements = new Map();
const storage = new Map();
const get = (selector) => {
  if (!elements.has(selector)) elements.set(selector, new Element());
  return elements.get(selector);
};
const context = vm.createContext({
  localStorage: { setItem: (key, value) => storage.set(key, value) },
  setTimeout: () => 1,
  clearTimeout: () => {},
  document: {
    querySelector: get,
    getElementById: (id) => get('#' + id),
    createElement: () => new Element(),
    createDocumentFragment: () => Object.assign(new Element(), { fragment: true }),
  },
  Option: function(text, value) { return { text, value }; },
  data: JSON.parse(fs.readFileSync(path.join(root, 'data', 'initial-data.json'), 'utf8')),
});
const source = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
vm.runInContext(source.slice(0, source.lastIndexOf('\ninit().catch')), context);
const run = (code) => vm.runInContext(code, context);
run('state = data; rebuildIndexes(); bindStaticEvents(); renderAll();');
const symbolCode = context.data.characters.find(item => item.char === '᳆').code;
const input = (selector, value) => get(selector).events.input({ target: { value } });
const glyphs = () => get('#glyphGrid').children.filter((card) => card.draggable);

// Searching from an unrelated page must find the requested symbol globally.
input('#searchInput', '᳆');
assert.equal(glyphs().length, 1);
assert.ok(glyphs()[0].innerHTML.includes(symbolCode));
assert.equal(glyphs()[0].children[0].textContent, 'Sundanese Supplement');
assert.match(get('#conflictSummary').textContent, /全库搜索/);
glyphs()[0].events.click();
assert.equal(get('#codeInput').value, symbolCode);

// The sidebar must hide unrelated active pages and open matching characters.
input('#pageSearchInput', '᳆');
assert.equal(get('#pageNav').children.length, 1);
get('#pageNav').children[0].events.click();
assert.equal(get('#searchInput').value, '᳆');
assert.equal(get('#searchCurrentPage').checked, true);
assert.equal(glyphs().length, 1);
assert.match(get('#conflictSummary').textContent, /本页搜索/);

// Codes, codepoints and names all search across pages, case-insensitively.
get('#searchCurrentPage').events.change({ target: { checked: false } });
for (const value of [symbolCode.toUpperCase(), 'U+1CC6', 'SUNDANESE PUNCTUATION BINDU DA SATANGA', '𓆟']) {
  input('#searchInput', value);
  assert.ok(glyphs().length > 0, value);
  assert.match(get('#conflictSummary').textContent, /全库搜索/);
}
input('#searchInput', '᳆');
get('#conflictOnly').events.change({ target: { checked: true } });
assert.equal(glyphs().length, run(`(codeIndex.get(${JSON.stringify(symbolCode)}) || 0) > 1 ? 1 : 0`));
get('#conflictOnly').events.change({ target: { checked: false } });

input('#pageSearchInput', 'zzzz-no-such-character');
assert.match(get('#pageNav').children[0].textContent, /没有匹配/);
input('#pageSearchInput', 'Sundanese Supplement');
assert.equal(get('#pageNav').children.length, 1);
get('#pageNav').children[0].events.click();
assert.equal(get('#searchInput').value, '');
assert.equal(glyphs().length, run('pageItems(activePage).length'));

run('activePage = "common";');
input('#searchInput', '᳆');
get('#searchCurrentPage').events.change({ target: { checked: true } });
assert.equal(glyphs().length, run('pageItems("common").filter(item => item.char === "᳆").length'));
get('#searchCurrentPage').events.change({ target: { checked: false } });
assert.equal(glyphs().length, 1);
input('#searchInput', 'zzzz-no-such-character');
assert.equal(get('#emptyState').hidden, false);
assert.match(get('#emptyState p').textContent, /全库/);
input('#searchInput', '');
assert.equal(glyphs().length, run('Math.min(PAGE_BATCH, pageItems(activePage).length)'));

// A broad global query retains batching and the load-more action.
input('#searchInput', 'U+');
assert.equal(glyphs().length, 400);
get('#glyphGrid').children.at(-1).events.click();
assert.equal(glyphs().length, 800);
console.log('全库搜索、区块定位、详情编辑、本页筛选、同码筛选及分页校验通过。');

// Shape edits must preserve a personally chosen sound/association prefix.
run('pristine = data; patchState = emptyPatch(); selectedId = "u-1cc0";');
input('#codeInput', 'zzcy');
get('#mainKeySelect').value = 'c';
get('#stateKeySelect').value = 'i';
get('#stateKeySelect').events.change();
assert.equal(run('selectedItem().code'), 'zzci');
input('#noteInput', '曲线；内含；待字体复核');
const patch = JSON.parse(storage.get(context.data.storageKey));
assert.equal(patch.characters['u-1cc0'].code, 'zzci');
assert.equal(patch.characters['u-1cc0'].note, '曲线；内含；待字体复核');
context.localStorageValue = JSON.stringify(patch);
context.freshData = JSON.parse(fs.readFileSync(path.join(root, 'data', 'initial-data.json'), 'utf8'));
run('state = freshData; pristine = freshData; applyPatch(JSON.parse(localStorageValue)); rebuildIndexes();');
assert.equal(run('selectedItem().code'), 'zzci');
assert.equal(run('selectedItem().note'), '曲线；内含；待字体复核');
assert.equal(run('codeIndex.get("zzci")'), 1);
console.log('个人前缀保留、形码修改、备注保存及草稿重新载入校验通过。');

// Reviewed visual families allow ten; the ordinary machine-code limit stays five.
assert.equal(run('codeLimit("gsoe")'), 10);
assert.equal(run('codeLimit("zzzz")'), 5);
run('selectedId = "u-25ef"; codeIndex.set("gsoe", 10); renderInspectorMetadataOnly(selectedItem());');
assert.doesNotMatch(get('#sameCodeCount').textContent, /超过/);
run('codeIndex.set("gsoe", 11); renderInspectorMetadataOnly(selectedItem());');
assert.match(get('#sameCodeCount').textContent, /超过/);
console.log('常见图形十候选边界与普通码五候选规则校验通过。');
