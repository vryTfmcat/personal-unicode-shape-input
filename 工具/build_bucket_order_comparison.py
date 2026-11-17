"""Same canonical bindings, two lookup orders; no rule or allocation writes."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/代表字实际查找测试'
OUT=PARENT/'分桶前后置对照'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def api(s):
    with urlopen('http://127.0.0.1:8765/api/shape-overview/'+s,timeout=60) as r:return json.load(r)

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/'原型/键位编辑器/data/structure-count-bindings.json',ROOT/'数据/三模式/规则库/四键实验/人工审议.json',ROOT/'原型/键位编辑器/shape_overview.py',ROOT/'原型/键位编辑器/shape-key-overview.js']
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in protected}
    previous=json.loads((PARENT/'代表字查找基线.json').read_text(encoding='utf-8'))
    rows=[];verified=0
    for r in previous['records']:
        d=api('detail?allocation=1&cp='+str(r['cp']));pairs=[];short=[]
        for p in d['paths']:
            code=p['code']
            if len(code)!=4:short.append(dict(code=code,count=d['codeCounts'][code]));continue
            rotated=code[1:]+code[0]
            assert rotated[-1]+rotated[:3]==code
            # All full-code candidate counts are independently replayed in the current mode.
            q=api('query?allocation=1&prefix='+code)
            assert q['total']==d['codeCounts'][code]
            target=api('query?allocation=1&prefix='+code+'&text=U%2B'+format(r['cp'],'X'))
            assert target['total']==1
            pairs.append(dict(canonical=code,rotated=rotated,count=q['total'],compatibility=p.get('compatibilityOnly',False),preferred=p.get('preferred',False)))
            verified+=1
        rows.append(dict(char=r['char'],cp=r['cp'],image=r['image'],pairs=pairs,short=short))
    data=dict(id='bucket-order-comparison-20261025-v1',date=datetime.now().astimezone().isoformat(),status='保留分桶与后三位规则，仅对照查询顺序；非已部署模式',rows=rows,fullCodeChecks=verified,
        baseline=api('bootstrap')['structureBindings']['version'],protectedHashes=hashes,
        shortCodePolicy='本轮三码保持原样，后置模式如何与四码前缀并存待设计，不直接旋转为可输入短码',
        prefixPolicy='后置前三位BCD需跨所有分桶检索再去重；候选可能更多，未生成全库索引，不用12字样本伪造人数')
    assert hashes=={p.relative_to(ROOT).as_posix():digest(p) for p in protected}
    (OUT/'分桶前后置对照.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    html=Path(__file__).with_name('bucket_order_comparison_template.html').read_text(encoding='utf-8').replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
    (OUT/'分桶前后置对照.html').write_text(html,encoding='utf-8')
    (ROOT/'原型/键位编辑器/shape-layout-comparison.html').write_text(html,encoding='utf-8')
    lines=['# 保留分桶：前置与后置查询对照','',data['status'],'',
      '用户决定保留原分桶，接受精准查询时记桶的成本；不再推进上版“主体/对象/属性/值”的职责重构。',
      '规范码仍ABCD。前置查询ABCD；后置查询BCDA，明确模式后转换回ABCD读取同一索引，不新增第二套权威码表。B/C/D字母及原对象、属性、计数规则均不变。',
      '', '|字|原规范码|后置显示|完整四码候选|','|---|---|---|---|']
    for r in rows:
        for p in r['pairs']:lines.append('|'+r['char']+'|'+p['canonical']+'|'+p['rotated']+'|'+str(p['count'])+'|')
        if r['short']:lines.append('|'+r['char']+'|'+' '.join(p['code'] for p in r['short'])+'|三码暂不变换|另定短码策略|')
    lines+=['','## 边界','',
      '- 四码旋转是一一对应，完整码的候选集合不变。只输入后置前三位BCD会跨桶，必须并集去重，候选可能更多；桶只是晚一点选择，未消失。',
      '- 后置模式的第四位是桶；原第四位属性移到第三位。不能同时把新第四位用于大小。',
      '- O仍是原规则ioqu→oqui，不等于已接受ioqc或把q改为空心圆；圆族尺寸与填充冗余作为独立局部规则问题另审。',
      '- 分桶有缩小查询范围的作用，但现有桶是否均匀、如何改善边界仍需实测，不声称已均衡。',
      '- 必须显式切换前置/后置，不自动猜输入是哪种，避免同一字符串在两种解释下撞义。',
      '- t/b集合入口、无细码字符、三码/短码和混合路径不能按四码机械旋转；本轮不迁移，也不改变历史84/t-b4362。',
      '- 页面全码按钮通过转换回原码调用只读API，属于查询适配演示；跨桶前缀索引、公共总览模式切换、Rime部署尚未实现。',
      '', '## 下一步','',
      '先按同一规范数据实现跨桶前缀并集查询并实测人数、去重和性能；再决定公共总览的双方式切换。保留第一位的实际作用，在原桶内逐步修正边界和局部规则。']
    (OUT/'分桶前后置对照说明.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(rows=len(rows),fullCodeChecks=verified,protectedUnchanged=True)))

if __name__=='__main__':build()
