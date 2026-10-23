const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),editor=path.join(root,'原型/键位编辑器');
const load=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const base=load('原型/键位编辑器/data/mode-data.json'),book=load('数据/三模式/codebooks.json'),stage=load('数据/三模式/shape-stage.json');
const M=require(path.join(editor,'modes-core.js')),model=M.model(base,book,stage);
assert.equal(stage.id,base.shapeStage.id);assert.equal(model.characters.length,159345);
let count=stage.unclassified.length;const seen=new Set(stage.unclassified);
for(const [bucket,cps] of Object.entries(stage.buckets)){
 const chars=model.stageGroups.get(bucket);assert.deepEqual(chars.map(c=>c.char.codePointAt(0)),cps);
 for(const cp of cps){assert(!seen.has(cp));seen.add(cp);}count+=cps.length;
}
assert.equal(count,159345);assert.equal(seen.size,159345);
assert.equal(model.characters.filter(c=>c.stageShape?.reviewed).length,965);
const prefs={modes:['shape'],shapeView:'stage',chinese:false};
const result=model.query('i',prefs);assert(result.length>=804);assert.deepEqual(result.slice(0,804).map(r=>r.character.char.codePointAt(0)),stage.buckets.i);
assert.equal(new Set(result.map(r=>r.character.id)).size,result.length);
assert(result.some(r=>r.character.char==='○'));assert(result.some(r=>r.character.char==='O'));
for(const code of ['ii','ixxx','x','y','z'])assert.equal(model.query(code,prefs).length,0);
const historical=model.query('oe',{...prefs,shapeView:'legacy'});assert(historical.some(r=>r.character.char==='○'));
const circle=model.characters.find(c=>c.char==='○');assert.equal(circle.stageShape.bucket,'i');assert.equal(circle.shape.coarse,'oe');
const star=model.characters.find(c=>c.char==='✺');assert.equal(star.stageShape.bucket,'o');
const nodes=new Map();function node(){return {value:'',checked:false,hidden:false,textContent:'',children:[],classList:{toggle(){}},replaceChildren(...c){this.children=c;},append(){},addEventListener(){},set innerHTML(v){this._html=v;},get innerHTML(){return this._html||'';}};}
const document={querySelector(s){if(!nodes.has(s))nodes.set(s,node());return nodes.get(s);},createElement(){return node();},dispatchEvent(){}};
const context=vm.createContext({window:{UnicodeModes:M},document,console,CustomEvent:function(){},setTimeout,clearTimeout});
const source=fs.readFileSync(path.join(editor,'modes.js'),'utf8').replace(/mInit\(\)\.catch\([\s\S]*$/,'');vm.runInContext(source,context);
context.testBase=base;context.testBook=book;context.testModel=model;context.testStage=stage;
vm.runInContext('mBase=testBase;mBook=testBook;mModel=testModel;mStage=testStage;mPrefs={editMode:"shape",modes:["shape"],shapeView:"stage",chinese:false};mPage="i";',context);
assert.equal(vm.runInContext('mGroups().find(g=>g.id==="o").count',context),614);
assert.deepEqual(Array.from(vm.runInContext('mPageCharacters().map(c=>c.char.codePointAt(0))',context)),stage.buckets.i);
document.querySelector('#candidateInput').value='i';vm.runInContext('mRenderCandidates()',context);assert(document.querySelector('#candidateCount').textContent.includes('阶段桶'));
vm.runInContext('mPrefs.shapeView="legacy";mPage="oe";',context);assert(vm.runInContext('mPageCharacters().some(c=>c.char==="○")',context));
console.log('Stage snapshot identity/primary order/aliases/965 confirmations, strict one-key query, historical-code compatibility and editor UI functions passed.');
