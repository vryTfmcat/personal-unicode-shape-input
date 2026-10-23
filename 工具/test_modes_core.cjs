const assert=require('node:assert/strict');
const M=require('../原型/键位编辑器/modes-core.js');
const base={blocks:[{id:'b',prefixes:['gs'],rules:{}}],characters:[
 {id:'circle',char:'○',blockId:'b',blockCode:{code:'gsoe',status:'draft'},shape:{coarse:'oe',detail:null}},
 {id:'letter',char:'O',blockId:'b',blockCode:{code:'gsoi',status:'draft'},shape:{coarse:'oe',detail:null}},
 {id:'han',char:'零',blockId:'h',chinese:{extended:false,codes:[{code:'lkvv'}]}},
 {id:'ext',char:'〇',blockId:'s',chinese:{extended:true,codes:[{code:'lkvv'}]}}]};
const book={version:1,blockOverrides:{},shapeOverrides:{},prefixOverrides:{},rules:{},personal:{circle:[{code:'gsoe',enabled:true}],letter:[{code:'gsoe',enabled:true}]},metadata:{},commonOrder:[],migrations:{}};
let model=M.model(base,book);
assert.deepEqual(model.query('gsoe',{modes:['block','personal'],chinese:false}).map(r=>[r.character.char,r.sources]),[['○',['personal','block']],['O',['personal']]]);
assert.deepEqual(model.query('oe',{modes:['shape'],chinese:false}).map(r=>r.character.char),['○','O']);
assert.equal(model.query('oexx',{modes:['shape'],chinese:false}).length,0);
assert.deepEqual(model.query('lkvv',{modes:['block'],chinese:true,extended:false}).map(r=>r.character.char),['零']);
assert.deepEqual(model.query('lkvv',{modes:['block'],chinese:true,extended:true}).map(r=>r.character.char),['零','〇']);
const old={format:'unicode-key-editor-patch-v1',characters:{circle:{code:'yyyy',note:'旧笔记',favorite:true}},pages:{old:{name:'old'}},commonOrder:['circle']};
assert(M.migrateLegacy(book,old,'legacy',new Set(['circle','letter','han','ext'])));
assert(!M.migrateLegacy(book,old,'legacy',new Set(['circle','letter','han','ext'])));
assert.equal(book.personal.circle.find(a=>a.code==='yyyy').enabled,false);
assert.equal(book.metadata.circle.note,'旧笔记');assert.equal(book.metadata.circle.favorite,true);
assert.equal(M.model(base,book).byId.get('circle').blockCode.code,'gsoe');
book.shapeOverrides.circle={coarse:'oi',detail:null,status:'reviewed'};
assert.equal(M.model(base,book).byId.get('circle').personal[0].code,'gsoe');
book.prefixOverrides.gs='gg';assert.equal(M.model(base,book).byId.get('circle').blockCode.code,'ggoe');
let shift=M.shiftGesture();let down={code:'ShiftLeft',repeat:false,ctrlKey:false,altKey:false,metaKey:false};
shift.down(down);assert(shift.up(down));shift.down(down);shift.down({code:'KeyA'});assert(!shift.up(down));
shift.down(down);shift.down({...down,repeat:true});assert(shift.up(down));assert(!shift.up(down));
shift.down(down);shift.reset();assert(!shift.up(down));
assert.deepEqual(M.nextPreset(['block']),['shape']);assert.deepEqual(M.nextPreset(['block','shape']),['block','shape','personal']);
console.log('独立码本、候选合并与顺序、旧草稿迁移、Shift 手势验证通过。');
