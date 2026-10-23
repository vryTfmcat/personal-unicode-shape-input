const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),editor=path.join(root,'原型/键位编辑器');
const load=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const data=load('原型/键位编辑器/data/shape-experiment.json'),report=load('原型/键位编辑器/data/shape-experiment-report.json');
const M=require(path.join(editor,'shape-experiment-core.js')),model=M.model(data);
assert.equal(data.id,report.experimentId);assert.equal(data.active,false);assert.equal(data.records.length,28223);
const all=new Set(data.records.map(r=>r.cp));
const stage=load('数据/三模式/shape-stage.json');
for(const bucket of 'xyz'){assert.deepEqual(data.collections[bucket],stage.buckets[bucket]);for(const cp of data.collections[bucket]){assert(!all.has(cp));all.add(cp);}}
assert.deepEqual(data.unclassified,stage.unclassified);data.unclassified.forEach(cp=>{assert(!all.has(cp));all.add(cp);});assert.equal(all.size,159345);
for(const n of [1,2,3,4])assert([...model.index.keys()].some(code=>code.length===n));
assert(data.bucketGroups.some(g=>g.families.length>1),'第一位应聚合相近形族，第二位不能完全退化为重复信息');
assert.equal(model.query('zzzz').length,0);assert.equal(model.query('aaaaa').length,0);assert.equal(model.query('!').length,0);
for(const text of ['○','O','0','✺','□','▫']){
 const [row]=model.characters(text);assert(row);assert.equal(model.characters('U+'+row.cp.toString(16))[0].cp,row.cp);
 assert(model.query(row.bucket).some(r=>r.cp===row.cp));
 for(const code of row.codes){assert.equal(new Set(model.query(code).map(r=>r.cp)).size,model.query(code).length);assert(model.query(code).some(r=>r.cp===row.cp));}
 const chunk=JSON.parse(fs.readFileSync(path.join(editor,row.detailUrl),'utf8'));assert.equal(chunk.experimentId,data.id);
 const full=chunk.records.find(r=>r.cp===row.cp);assert.deepEqual(full.paths.map(p=>p.code),row.codes);
 const objectIds=new Set(full.objects.map(o=>o.id));
 for(const p of full.paths)for(const e of p.evidence){assert.equal(e.objectId,e.fourthObjectId);assert(objectIds.has(e.objectId));assert.equal(data.definitions.third[e.third].function,e.rule);}
 assert(fs.existsSync(path.join(editor,row.preview.url)));
}
assert.notEqual(model.characters('O')[0].cp,model.characters('0')[0].cp);
assert.equal(model.characters('○O0').length,3);
for(const char of '○◯O0')assert.equal(model.characters(char)[0].familyKey,'o');
for(const char of '✳✴✵✷✺')assert.equal(model.characters(char)[0].familyKey,'r');
const oldModel=require(path.join(editor,'modes-core.js')).model(load('原型/键位编辑器/data/mode-data.json'),load('数据/三模式/codebooks.json'),stage);
assert(oldModel.query('oe',{modes:['shape'],shapeView:'legacy',chinese:false}).some(r=>r.character.char==='○'));
assert(oldModel.query('i',{modes:['shape'],shapeView:'stage',chinese:false}).some(r=>r.character.char==='○'));
const corrupt=structuredClone(data);corrupt.records[0].bucket='z';assert.throws(()=>M.model(corrupt));
assert.equal(data.definitions.fourth.c.function,'size.medium');
assert(Object.values(data.definitions.third).some(r=>r.status==='proposal'));
console.log(JSON.stringify({passed:true,identities:all.size,ordinary:data.records.length,prefixes:model.index.size,paths:report.pathCount,legacyCompatible:true}));
