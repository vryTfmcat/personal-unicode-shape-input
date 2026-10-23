// Cross-check every editor review prefix against the Python/Rime source index.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),M=require('../原型/键位编辑器/modes-core.js');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const manifest=read('数据/三模式/全形核对版.json');
const data=read(manifest.indexPath),base=read('原型/键位编辑器/data/mode-data.json'),book=read('数据/三模式/codebooks.json');
const expected=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const model=M.model(base,book,null,data);
assert.equal(model.characters.length,159345);assert.equal(model.reviewIndex.size,Object.keys(expected.hashes).length);
let associations=0;
for(const [code,rows] of model.reviewIndex){
  associations+=rows.length;
  const cps=rows.map(c=>c.char.codePointAt(0));assert.equal(new Set(cps).size,cps.length);
  const hash=crypto.createHash('sha256').update(cps.join(',')).digest('hex');
  assert.equal(hash,expected.hashes[code],`Editor/Rime order mismatch: ${code}`);
}
assert.equal(model.query('zzzz',{modes:['shape'],shapeView:'review',chinese:false}).length,0);
for(const length of [1,2,3,4]){
  const code=[...model.reviewIndex.keys()].find(k=>k.length===length);assert(code);
  assert.deepEqual(model.query(code,{modes:['shape'],shapeView:'review',chinese:false}).map(r=>r.character.id),model.reviewIndex.get(code).map(c=>c.id));
}
const pending=new Set(data.unclassified);
assert(model.characters.filter(c=>pending.has(c.char.codePointAt(0))).every(c=>!c.shapeReview));
assert(model.query('oe',{modes:['shape'],shapeView:'legacy',chinese:false}).length>0);
console.log(JSON.stringify({passed:true,experimentId:data.id,identities:model.characters.length,prefixes:model.reviewIndex.size,associations,allPrefixOrdersMatch:true,pendingUncoded:true,legacyAvailable:true}));
