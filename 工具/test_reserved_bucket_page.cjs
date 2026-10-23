const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const optimized=process.argv.includes('--optimized');
const root=path.resolve(__dirname,'..','数据','三模式','规则库',optimized?'首次优化':'保留桶布局');
const latest=JSON.parse(fs.readFileSync(path.join(root,optimized?'最新优化.json':'最新分桶.json'),'utf8'));
const html=fs.readFileSync(path.join(latest.run,'单层分桶核对.html'),'utf8');
const nodes={};const context=vm.createContext({document:{getElementById(id){return nodes[id] ||= {value:'',innerHTML:'',textContent:'',addEventListener(){}}}}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
assert.strictEqual(nodes.buckets.innerHTML.split('<article>').length-1,26);
assert.strictEqual(nodes.buckets.innerHTML.split('<img ').length-1,23);
assert(/暂时[^<]*空/.test(nodes.buckets.innerHTML));
for(const [char,bucket] of [['一','z'],['가','y'],['𗀀','y'],['あ','y'],['𘬀','y']]){
  vm.runInContext(`$('bucket').value='${bucket}';$('query').value='${char}';show()`,context);
  assert(nodes.count.textContent.includes('1，'));assert(nodes.results.innerHTML.includes(char));
}
vm.runInContext("$('bucket').value='x';$('query').value='';show()",context);
assert(nodes.count.textContent.includes('0，'));
vm.runInContext("$('bucket').value='y';$('query').value='ㄅ';show()",context);
assert(nodes.count.textContent.includes('0，'));
console.log('23张普通桶代表图、xyz特殊卡片、中文和排除文字查询、x空桶与注音保留检查通过。');
