const assert=require('node:assert/strict');
const M=require('../原型/键位编辑器/modes-core.js');
const base={blocks:[],characters:[
 {id:'latin',char:'O',blockId:'latin',blockCode:null,shape:null,chinese:null},
 {id:'circle',char:'○',blockId:'geometry',blockCode:null,shape:null,chinese:null}]};
const path=code=>({code,enabled:true,status:'reviewed'});
const book={prefixOverrides:{},rules:{},blockOverrides:{},personal:{},metadata:{},shapeOverrides:{
 latin:{coarse:'oe',detail:null,paths:[path('oesc')]},
 circle:{coarse:'oe',detail:null,paths:[path('oesc'),path('oesv')]}}};
let m=M.model(base,book),prefs={modes:['shape'],chinese:false};
assert.deepEqual(m.query('oesc',prefs).map(r=>r.character.id),['latin','circle']);
assert.equal(m.query('oes',prefs).length,2);assert.equal(m.query('oe',prefs).length,2);
assert.equal(m.query('oexx',prefs).length,0);
book.shapeOverrides.circle.paths[0].enabled=false;m=M.model(base,book);
assert.deepEqual(m.query('oesc',prefs).map(r=>r.character.id),['latin']);
assert.equal(m.query('oe',prefs).length,2);
console.log('多路径、前缀、停用、同码不同字符身份与去重检查通过');
