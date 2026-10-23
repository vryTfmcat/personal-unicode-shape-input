const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
const root = path.resolve(__dirname, '..');
const latest = JSON.parse(fs.readFileSync(path.join(root,'数据','三模式','规则库','最新实验.json'),'utf8'));
function execute(name, initial) {
  const elements = {};
  const context = vm.createContext({document:{getElementById(id){return elements[id] ||= {value:initial[id] || '',innerHTML:'',textContent:'',addEventListener(){}}}}});
  const html = fs.readFileSync(path.join(latest.run,name+'.html'),'utf8');
  vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
  return {elements, run:code=>vm.runInContext(code,context)};
}
const rank = execute('规则策略实验报告',{balance:'40',memory:'40',visual:'20',strategy:'shape-fine'});
assert(rank.elements.winner.textContent.includes('轮廓优先'));
assert(rank.elements.rank.innerHTML.split('<tr>').length===19);
rank.run("['balance','memory','visual'].forEach(k=>$(k).value='0');update()");
assert(rank.elements.winner.textContent.includes('非零权重'));
const review = execute('逐字符核对',{kind:'char',query:'CϹ'});
assert(review.elements.count.textContent.includes('2 个字符'));
assert(review.elements.result.innerHTML.includes('第4位'));
assert(review.elements.result.innerHTML.includes('第四位描述对象'));
review.run("$('kind').value='code';$('query').value='cge';render()");
assert(review.elements.result.innerHTML.includes('cged'));
review.run("$('kind').value='pending';render()");
assert(review.elements.count.textContent.includes('6133'));
review.run("$('kind').value='char';$('query').value='U+0043';render()");
assert(review.elements.count.textContent.includes('1 个字符'));
console.log('排名、零权重、字符/码位/前缀检索、待补字形、四位字义和描述对象检查通过。');
