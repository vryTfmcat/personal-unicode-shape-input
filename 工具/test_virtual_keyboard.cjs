const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const base=path.join(__dirname,'../原型/键位编辑器');
const C=require(path.join(base,'virtual-keyboard-core.js'));
const ctx={window:{}};vm.runInNewContext(fs.readFileSync(path.join(base,'virtual-keyboard-layouts.js'),'utf8'),ctx);
const layouts=JSON.parse(JSON.stringify(ctx.window.UNICODE_KEYBOARD_LAYOUTS));
for(const [i,count]of [[0,68],[1,110]]){
 const layout=layouts[i],keys=C.parseKle(layout.kle);assert.equal(keys.length,count);assert.equal(new Set(keys.map(k=>k.id)).size,count);
 assert(keys.every(k=>k.w>0&&k.h>0&&!C.outline(k).includes('NaN')));
 const f=keys.find(k=>k.label==='F');assert.equal(C.defaults(layout.id,keys)[f.id],i===0?'KeyE':'KeyF');
 const data={format:'unicode-keyboard-annotations-v1',layoutId:layout.id,geometryHash:C.signature(layout.kle),bindings:C.defaults(layout.id,keys),annotations:{base:{[f.id]:'Ⱝ𓆟a\u0301'},shift:{[f.id]:'👩‍💻'}}};
 assert.deepEqual(C.validate(JSON.parse(JSON.stringify(data)),layout,keys),data);
 assert.throws(()=>C.validate({...data,geometryHash:'wrong'},layout,keys));
 assert.throws(()=>C.validate({...data,annotations:{base:{unknown:'x'},shift:{}}},layout,keys));
 assert.throws(()=>C.validate({...data,bindings:{[f.id]:'<script>'}},layout,keys));
}
const razer=C.parseKle(layouts[1].kle),enter=razer.find(k=>k.label==='Enter'&&k.w2===1.5);
assert(enter);assert.equal(enter.x2,-.25);assert(C.outline(enter).includes('-0.2,0.05'));
const synthetic=C.parseKle([[{w:2},'wide','normal'],[{x:.5,y:.5,h:2},'tall','normal']]);
assert.equal(synthetic[1].w,1);assert.equal(synthetic[2].y,1.5);assert.equal(synthetic[2].x,.5);assert.equal(synthetic[3].h,1);
assert.throws(()=>C.parseKle([[{r:15},'rotation']]));
console.log('PASS: 68/110 keys, KLE offsets/resets, ISO outline, Colemak mapping, Unicode round-trip, invalid import rejection');
