"""Full non-Han strategy experiments; isolated drafts, frozen fourth keys, auditable scores."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import html
import json
import math
import time
import shutil
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
import numpy as np
from shape_lab_features import VERSION,FONT_SIZE,inventory,extract
from shape_lab_rules import (FIXED_REQUIRED,strategies,definitions,views,encode,vector)

PROJECT=Path(__file__).resolve().parents[1]
DATA=PROJECT/'数据'/'三模式'
LAB=DATA/'规则库'
RUNS=LAB/'运行'
WEIGHTS={'balance':.4,'memory':.4,'visual':.2}


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')


def palette():
    path=DATA/'全形第四位-当前布局.json';book=json.loads(path.read_text(encoding='utf-8'))
    mapping=book['fourth']
    for key,function in FIXED_REQUIRED.items():
        if mapping.get(key,{}).get('function')!=function:raise ValueError(f'第四位冻结键 {key} 已变化，先核对布局')
    return mapping,hashlib.sha256(path.read_bytes()).hexdigest()


def corpus(limit=None):
    path=PROJECT/'原型'/'键位编辑器'/'data'/'mode-data.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    chars=[{'cp':int(c['codepoint'][2:],16),'char':c['char'],'name':c['unicodeName'],
            'block':c['sourceBlock'],'plane':c['plane']} for c in data['characters'] if not c['han']]
    chars.sort(key=lambda c:c['cp'])
    return chars[:limit] if limit else chars,hashlib.sha256(path.read_bytes()).hexdigest()


def human_references():
    preferred={};gold={};reviewed={}
    for path in sorted(DATA.glob('全形*试验-*.json')):
        batch=json.loads(path.read_text(encoding='utf-8'))
        for row in batch['characters']:
            if not row.get('primaryReference',True):continue
            cp=int(row['codepoint'][2:],16)
            font=row.get('referenceFont',row.get('font'))
            if font:preferred[cp]=font
            if batch.get('status')!='approved-candidate':continue
            entries=row.get('codes',[{'code':row.get('proposedCode',row.get('code'))}])
            gold.setdefault(cp,set()).update(e['code'][-1] for e in entries if e.get('code'))
            reviewed[cp]=row
    return preferred,gold,reviewed


def cache_features(chars,fonts,input_hash,preferred,refresh=False):
    reference_hash=hashlib.sha256(json.dumps(preferred,sort_keys=True).encode()).hexdigest()
    manifest={'featureVersion':VERSION,'fontSizePx':FONT_SIZE,'inputHash':input_hash,
              'codepointsHash':hashlib.sha256(','.join(str(c['cp']) for c in chars).encode()).hexdigest(),
              'referenceHash':reference_hash,'fonts':[{'path':f['path'],'index':f.get('index',0),'family':f['family'],'sha256':f['sha256'],
                                                      'coverage':len(f['coverage'])} for f in fonts]}
    fingerprint=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:20]
    folder=LAB/'缓存';folder.mkdir(parents=True,exist_ok=True);target=folder/(fingerprint+'.jsonl.gz')
    if target.exists() and not refresh:
        with gzip.open(target,'rt',encoding='utf-8') as stream:records=[json.loads(line) for line in stream]
        if [r['cp'] for r in records]!=[c['cp'] for c in chars]:raise ValueError('特征缓存字符集合不一致')
        return records,manifest,str(target)
    reusable={}
    if not refresh:
        old_manifests=list(folder.glob('*.manifest.json'))
        old_manifests.sort(key=lambda p:(len(json.loads(p.read_text(encoding='utf-8'))['fonts']),p.stat().st_mtime),reverse=True)
        for old_manifest in old_manifests:
            prior=json.loads(old_manifest.read_text(encoding='utf-8'))
            if any(prior.get(k)!=manifest.get(k) for k in ('featureVersion','fontSizePx','inputHash','codepointsHash','referenceHash')):continue
            old_fonts=[{**f,'index':f.get('index',0)} for f in prior['fonts']]
            if manifest['fonts'][:len(old_fonts)]!=old_fonts:continue
            old_cache=old_manifest.with_name(old_manifest.name.replace('.manifest.json','.jsonl.gz'))
            if old_cache.exists():
                with gzip.open(old_cache,'rt',encoding='utf-8') as stream:
                    reusable={r['cp']:r for r in (json.loads(line) for line in stream) if r['feature']['observed']}
                print(f'追加字体，复用 {len(reusable)} 个已观测字形，只补测缺口',flush=True);break
    records=[];started=time.monotonic()
    temporary=target.with_suffix('.tmp')
    with gzip.open(temporary,'wt',encoding='utf-8') as stream:
        for i,char in enumerate(chars,1):
            record=reusable.get(char['cp'])
            if record is None:record=dict(char,feature=extract(char['char'],fonts,preferred.get(char['cp'])))
            records.append(record)
            stream.write(json.dumps(record,ensure_ascii=True,separators=(',',':'))+'\n')
            if i%1000==0:print(f'字形特征 {i}/{len(chars)}，可观测 {sum(r["feature"]["observed"] for r in records)}，{time.monotonic()-started:.1f}s',flush=True)
    temporary.replace(target);save(folder/(fingerprint+'.manifest.json'),manifest)
    return records,manifest,str(target)


def cluster_vectors(matrix,k,seed=20261012):
    mean=matrix.mean(axis=0);scale=np.maximum(matrix.std(axis=0),.05)
    x=((matrix-mean)/scale).astype(np.float32);rng=np.random.default_rng(seed)
    centres=[x[rng.integers(len(x))]];distance=np.full(len(x),np.inf,dtype=np.float32)
    for _ in range(1,k):
        distance=np.minimum(distance,((x-centres[-1])**2).mean(axis=1))
        weights=distance/distance.sum() if distance.sum()>0 else None
        centres.append(x[rng.choice(len(x),p=weights)])
    centres=np.array(centres);norm=(x*x).sum(axis=1)
    for _ in range(12):
        distances=norm[:,None]+(centres*centres).sum(axis=1)[None,:]-2*x@centres.T
        labels=distances.argmin(axis=1)
        new=np.array([x[labels==i].mean(axis=0) if np.any(labels==i) else centres[i] for i in range(k)])
        if np.max(np.abs(new-centres))<.005:centres=new;break
        centres=new
    return labels,{'mean':mean.tolist(),'scale':scale.tolist(),'centres':centres.tolist(),
                   'seed':seed,'iterations':12}


def entropy(counter,denominator=26):
    total=sum(counter.values())
    return -sum((v/total)*math.log(v/total) for v in counter.values() if v)/math.log(denominator) if total else 0.


def gini(counter):
    values=np.sort(np.array(list(counter.values()),dtype=float))
    if not len(values) or values.sum()==0:return 0.
    return float((2*np.arange(1,len(values)+1)-len(values)-1)@values/(len(values)*values.sum()))


def score(metrics,weights=WEIGHTS):
    if set(weights)!=set(WEIGHTS) or any(not math.isfinite(v) or v<0 for v in weights.values()) or sum(weights.values())<=0:
        raise ValueError('评分权重需非负，且至少一项大于0')
    total=sum(weights.values())
    raw=sum(metrics[k]*weights[k]/total for k in weights)
    return round(raw*(.6+.4*metrics['observedFraction']),3)


def aliases(f,view_list,spec,cluster_label=None):
    by_code={}
    if not f['observed']:return []
    expected={v['suffix'] for v in view_list}
    for i,view in enumerate(view_list):
        code=encode(f,view,spec,cluster_label)
        by_code.setdefault(code,[]).append(i)
    result=[{'code':code,'views':indices} for code,indices in sorted(by_code.items())]
    if {r['code'][-1] for r in result}!=expected:raise ValueError('策略丢失了冻结的第四位视图')
    maps=definitions(spec)
    for row in result:
        if len(row['code'])!=4 or any(key not in maps[i] for i,key in enumerate(row['code'][:3])):
            raise ValueError(f'{spec["id"]} 产生未登记的前三位键义：{row["code"]}')
    return result


def evaluate(records,spec,palette_mapping,gold,run,labels=None,matrix=None,all_views=None):
    distributions=[Counter() for _ in range(3)];all_distributions=[Counter() for _ in range(3)]
    prefixes=Counter();suffixes=Counter();hand=Counter();finger=Counter()
    sums=defaultdict(lambda:np.zeros(matrix.shape[1],dtype=np.float64));squares=Counter();mass=Counter()
    glyphs=0;path_count=0;mixed=0;all_code_count=0;gold_matches=0;gold_total=0;repeated=0.
    dictionary=definitions(spec);small_examples=[]
    assignment=run/'编码'/(spec['id']+'.jsonl.gz');assignment.parent.mkdir(parents=True,exist_ok=True)
    left=set('qwertasdfgzxcvb');fingers={**dict.fromkeys('qaz','左小指'),**dict.fromkeys('wsx','左无名指'),
        **dict.fromkeys('edc','左中指'),**dict.fromkeys('rfvtgb','左食指'),**dict.fromkeys('yuhjnm','右食指'),
        **dict.fromkeys('ik','右中指'),**dict.fromkeys('ol','右无名指'),**dict.fromkeys('p','右小指')}
    with gzip.open(assignment,'wt',encoding='utf-8') as stream:
        for i,record in enumerate(records):
            f=record['feature'];view_list=all_views[i]
            paths=aliases(f,view_list,spec,labels.get(i) if labels else None)
            stream.write(json.dumps({'cp':record['cp'],'char':record['char'],'status':'machine-draft' if paths else 'unobserved',
                                     'codes':paths,'unclassifiedGroup':None if paths else '未观测：待补字体或研究'},ensure_ascii=True,separators=(',',':'))+'\n')
            if not paths:
                for counts in all_distributions:counts['?']+=1
                continue
            glyphs+=1;path_count+=len(paths);weight=1/len(paths)
            if record['cp'] in gold:
                gold_total+=1;gold_matches+=bool({p['code'][-1] for p in paths}&gold[record['cp']])
            for path in paths:
                code=path['code'];prefix=code[:3];prefixes[prefix]+=weight;suffixes[code[-1]]+=weight
                for position,key in enumerate(prefix):
                    distributions[position][key]+=weight;all_distributions[position][key]+=weight
                    hand['左' if key in left else '右']+=weight;finger[fingers.get(key,'其他')]+=weight
                if len({view_list[j]['kind'] for j in path['views']})>1:mixed+=1
                if spec['algorithm']=='proportion' and any(view_list[j]['kind']=='body-size' for j in path['views']) and code[2] in 'svh':
                    repeated+=weight
                all_code_count+=1;sums[prefix]+=weight*matrix[i];squares[prefix]+=weight*float(matrix[i]@matrix[i]);mass[prefix]+=weight
            if len(small_examples)<12 and (record['cp'] in gold or record['cp'] in (0x1cc0,0x1cc1,0x1cc2)):
                small_examples.append({'char':record['char'],'cp':record['cp'],'font':f.get('font'),'codes':paths})
    within=sum(max(0.,squares[p]-(sums[p]@sums[p])/mass[p]) for p in mass)/max(1,glyphs)
    observed=matrix[[i for i,r in enumerate(records) if r['feature']['observed']]]
    between=float(((observed-observed.mean(axis=0))**2).sum(axis=1).mean()) if len(observed) else 1.
    cohesion=100*max(0.,min(1.,1-within/max(1e-8,between)))
    entropy_observed=100*sum(entropy(c) for c in distributions)/3
    entropy_all=100*sum(entropy(c,27) for c in all_distributions)/3
    hand_total=sum(hand.values());hand_balance=100*(1-abs(hand['左']-hand['右'])/hand_total) if hand_total else 0.
    digit_values=np.array([finger.get(k,0.) for k in ('左小指','左无名指','左中指','左食指','右食指','右中指','右无名指','右小指')])
    finger_balance=100*(1-float(np.abs(digit_values-digit_values.mean()).sum())/(2*max(1,digit_values.sum())))
    balance=.55*entropy_observed+.20*entropy_all+.15*hand_balance+.10*finger_balance
    ambiguity=mixed/max(1,all_code_count)
    concepts=sum(len(m) for m in dictionary)
    simplicity=1/(1+spec['branches']/26+concepts/78)
    redundancy=repeated/max(1,glyphs)
    memory=100*(.4*spec['semantic']+.3*spec['mnemonic']+.3*simplicity)*(1-.25*ambiguity-.10*redundancy)
    view_confidence=float(np.mean([v['confidence'] for vv in all_views for v in vv if v['suffix'] is not None])) if glyphs else 0.
    visual=.75*cohesion+.25*view_confidence*100
    metrics={'balance':round(balance,3),'memory':round(memory,3),'visual':round(visual,3),
             'observedFraction':glyphs/len(records),'coverageRecords':len(records),'fourCodeGlyphs':glyphs,
             'unobservedGlyphs':len(records)-glyphs,'codePaths':path_count,'meanPaths':path_count/max(1,glyphs),
             'entropyObserved':entropy_observed,'entropyAll':entropy_all,'handBalance':hand_balance,
             'fingerBalance':finger_balance,'cohesion':cohesion,'mixedObjectCodeFraction':ambiguity,
             'repeatedInformationFraction':redundancy,
             'prefixGini':gini(prefixes),'prefixCount':len(prefixes),
             'maxPrefixShare':max(prefixes.values(),default=0)/max(1,glyphs),
             'fourthReferenceHitRate':gold_matches/max(1,gold_total),'fourthReferenceCases':gold_total,
             'distribution':[dict(c) for c in distributions],'distributionAll':[dict(c) for c in all_distributions],
             'fourthDistribution':dict(suffixes),'topPrefixes':prefixes.most_common(12)}
    return dict(spec,metrics=metrics,score=score(metrics),dictionary=dictionary,assignment=str(assignment),examples=small_examples)


def frontier(results):
    return [r['id'] for r in results if not any(all(s['metrics'][k]>=r['metrics'][k] for k in WEIGHTS)
            and any(s['metrics'][k]>r['metrics'][k] for k in WEIGHTS) for s in results if s is not r)]


def reports(summary,run):
    rows=summary['strategies'];winner=rows[0]
    lines=['# 全形规则库全量实验', '', f"日期：{summary['date']}。实验版本 {summary['version']}。", '',
           f"范围：{summary['scope']['characters']} 个非汉字字符；每套策略均有全量记录。"
           f"可观测字形 {winner['metrics']['fourCodeGlyphs']}，未观测 {winner['metrics']['unobservedGlyphs']}。", '',
           '排除项目现有统一／兼容汉字；保留〇、部首、笔画、标点等非统一汉字符号。'
           '编码不读取数字／字母身份、Unicode名称、区块或平面；这些字段仅用于身份、排除范围和报告。', '',
           '第四位全表冻结，包括WASD、ZXCV、JK/NM；所有策略使用相同的观测视图及第四位取值。'
           '只比较前三位规则。未观测字形不猜大小、方向，也不补造第四位。', '',
           f"当前权重下暂优策略：**{winner['name']}**，得分 {winner['score']:.2f}。", '',
           '这是限定候选库、当前字体及代理指标下的暂优，不是对所有可能规则的数学最优，也不是已经验证的真人记忆最优。', '',
           '## 排名', '', '| 策略 | 综合 | 均衡 | 易记代理 | 视觉一致性代理 | 前三码组数 | 最大组占比 |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        m=r['metrics'];lines.append(f"| {r['name']} | {r['score']:.2f} | {m['balance']:.2f} | {m['memory']:.2f} | {m['visual']:.2f} | {m['prefixCount']} | {m['maxPrefixShare']:.2%} |")
    lines+=['', '## 评分定义', '',
            '- 均衡：前三位字符权重熵55%，含未观测组的熵20%，左右手负荷15%，八指负荷10%。熵以26个字母归一化，不强填空键。',
            '- 一字多码按每字符1/码数计权，不因多发码而虚增分布均匀度。',
            '- 易记代理：语义可解释性先验40%，字母联想先验30%，规则复杂度30%，混合描述对象同码扣分25%×发生率，已登记的比例信息重复扣分10%×发生率。先验全部可查，不等同于真人记忆测试；尚未自动识别所有跨层重复。',
            '- 视觉一致性代理：同前三码的归一化全字图像描述方差75%，观测视图置信先验25%。局部检索码可能被全字比较低估，不等同于分类正确率。',
            '- 综合默认均衡40%、易记40%、视觉20%，再乘(0.6+0.4×可观测字形比例)。所有策略同一字体覆盖，不靠忽略缺字提高分数。',
            '- 字号48px；整体尺寸固定试验档位0.35/0.60/0.90 em，构件相对主体尺寸固定0.18/0.35/0.50。两种参照与全部阈值不随候选策略调整，阈值仍待人工核验。',
            '- 每种分离墨部件/封闭空区最多取最大三处作为代表，未穷举所有对象。开口、角点等是图像启发式估计，需要后续字形抽查。', '',
            '## 人工核对辅助', '',
            f"已确认样本的固定末位入口命中率（暂优）：{winner['metrics']['fourthReferenceHitRate']:.2%}，"
            f"样本 {winner['metrics']['fourthReferenceCases']} 字。这里只比较末位集合，不比较优化中的前三位，也不是完整正确率。", '',
            '帕累托前沿：'+ '、'.join(summary['pareto']), '', '## 暂优策略前三位字义', '']
    for i,mapping in enumerate(winner['dictionary'],1):
        lines += [f'### 第{i}位', '', '| 字母 | 本策略含义 |','|---|---|']
        lines += [f'| `{key}` | {meaning} |' for key,meaning in sorted(mapping.items())]
        lines.append('')
    lines += ['## 交付文件', '', '交互排名：`规则策略实验报告.html`；完整摘要：`summary.json`；'
              '全量机器编码：`编码/策略ID.jsonl.gz`；共同观测对象：`观测视图.jsonl.gz`；可复算源代码与布局：`来源快照/`。字形缓存和字体校验清单位于规则库/缓存。', '',
              '参考字体包含系统字体与项目内补充字体，逐个文件校验值见summary.json。Egyptology Extended Font by Land of Kemet (https://landofkemet.com)，基于 Serge Rosmorduc 与 Serge J.P. Thomas 的 JSesh 字形，CeCILL v2.1；来源 https://github.com/LumabyteCo/egyptology-extended-font 。Noto 字体来源及许可证已保存在规则库/字体。参考字体可能影响轮廓和尺寸判断。', '',
              '实验输出与有效码本隔离，未覆盖人工确认路径，未发布到小狼毫。候选必须经字体缺失补齐、图形抽查与真人推码测试后再决定上线。', '']
    report=run/'规则策略实验报告.md';report.write_text('\n'.join(lines),encoding='utf-8')
    payload=json.dumps(summary,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    page='''<!doctype html><meta charset="utf-8"><title>全形规则策略实验</title><style>
body{font:16px system-ui;max-width:1200px;margin:28px auto;background:#f4f6f9;color:#1c2b39;padding:0 20px}h1{font-size:26px}section{background:white;border-radius:12px;padding:20px;margin:18px 0}table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #e0e6ed;text-align:left}.bar{height:17px;background:#4a91ce;display:inline-block;vertical-align:middle}label{display:inline-block;margin:12px}select,input{font:inherit}small{color:#566779}.keys{display:grid;grid-template-columns:repeat(13,1fr);gap:8px}.key{background:#ecf2f7;padding:8px;text-align:center}button{cursor:pointer}pre{white-space:pre-wrap}</style>
<h1>全形规则库 · 全量策略比较</h1><p id="scope"></p><small>只优化前三位。均衡与易记是可查的代理指标；暂优不等于真实记忆最优。</small>
<section><h2>调整综合权重</h2><label>均衡 <input id="balance" type="range" min="0" max="100" value="40"></label><label>易记 <input id="memory" type="range" min="0" max="100" value="40"></label><label>视觉 <input id="visual" type="range" min="0" max="100" value="20"></label><p id="winner"></p><table><thead><tr><th>策略</th><th>综合</th><th>均衡</th><th>易记代理</th><th>视觉代理</th><th>最大前三码组</th></tr></thead><tbody id="rank"></tbody></table></section>
<section><h2>查看具体策略</h2><select id="strategy"></select><h3>前三位分布</h3><div id="distribution"></div><h3>逐位含义</h3><div id="meaning"></div><h3>已核对样本的机器候选对照</h3><div id="examples"></div></section>
<section><h2>如何解读</h2><p>每套方案都有全量字符记录。无可用字体、不可见或无法渲染的字符单列待研究，不补造方向或大小。每字符多码均分统计权重。规则是确定性的图像启发式或视觉聚类，没有按Unicode名称、字母身份、区块分码。</p><p>第四位WASD、ZXCV、JK/NM以及当前其他已登记键保持原义。原人工码本没有被替换，本报告不是输入法部署。</p><p>视觉一致性是分组方差代理，易记评分含明确的人为先验，尚须真人推码测试。完整公式、字体、缓存校验及全量编码见同目录文件。</p></section>
<script>const data=PAYLOAD;const $=s=>document.getElementById(s);const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function update(){let keys=['balance','memory','visual'],sum=keys.reduce((n,k)=>n+Number($(k).value),0)||1;let rank=data.strategies.map(r=>({...r,current:keys.reduce((n,k)=>n+r.metrics[k]*Number($(k).value)/sum,0)*(.6+.4*r.metrics.observedFraction)})).sort((a,b)=>b.current-a.current);$('winner').textContent='当前权重暂优：'+rank[0].name+'，'+rank[0].current.toFixed(2);$('rank').innerHTML=rank.map(r=>'<tr><td>'+esc(r.name)+'</td><td>'+r.current.toFixed(2)+'</td><td>'+r.metrics.balance.toFixed(1)+'</td><td>'+r.metrics.memory.toFixed(1)+'</td><td>'+r.metrics.visual.toFixed(1)+'</td><td>'+(100*r.metrics.maxPrefixShare).toFixed(1)+'%</td></tr>').join('')}
function detail(){let r=data.strategies.find(r=>r.id===$('strategy').value);$('distribution').innerHTML=r.metrics.distribution.map((counts,i)=>{let max=Math.max(...Object.values(counts));return '<h4>第'+(i+1)+'位</h4><div class="keys">'+Array.from('abcdefghijklmnopqrstuvwxyz').map(k=>'<div class="key">'+k+'<br><span class="bar" style="width:'+Math.round(45*(counts[k]||0)/max)+'px"></span><br><small>'+Math.round(counts[k]||0)+'</small></div>').join('')+'</div>'}).join('');$('meaning').innerHTML=r.dictionary.map((m,i)=>'<h4>第'+(i+1)+'位</h4><p>'+Object.entries(m).map(([k,v])=>'<b>'+k+'</b> '+esc(v)).join('；')+'</p>').join('');$('examples').innerHTML=r.examples.map(e=>'<p><b>'+esc(e.char)+'</b> U+'+e.cp.toString(16).toUpperCase()+'：'+e.codes.map(c=>esc(c.code)+'（'+Array.from(c.code.slice(0,3)).map((k,i)=>esc(k+'='+r.dictionary[i][k])).join('；')+'；'+esc(c.code[3]+'='+data.fourth[c.code[3]].meaning)+'）').join('、')+'</p>').join('')}
$('scope').textContent=data.scope.characters+' 个非汉字；可观测 '+data.strategies[0].metrics.fourCodeGlyphs+'；未观测 '+data.strategies[0].metrics.unobservedGlyphs+'；'+data.strategies.length+' 套策略。';$('strategy').innerHTML=data.strategies.map(r=>'<option value="'+r.id+'">'+esc(r.name)+'</option>').join('');['balance','memory','visual'].forEach(k=>$(k).addEventListener('input',update));$('strategy').addEventListener('change',detail);update();detail();</script>'''.replace('PAYLOAD',payload)
    (run/'规则策略实验报告.html').write_text(page,encoding='utf-8')
    return str(report)


def run_experiment(limit=None,refresh=False,font_dirs=None,weights=None):
    started=time.monotonic();mapping,palette_hash=palette();chars,input_hash=corpus(limit)
    score({'balance':0.,'memory':0.,'visual':0.,'observedFraction':1.},weights or WEIGHTS)
    source_paths=[Path(__file__),PROJECT/'工具'/'shape_lab_rules.py',PROJECT/'工具'/'shape_lab_features.py',DATA/'全形第四位-当前布局.json']
    source_bytes={p.name:p.read_bytes() for p in source_paths}
    preferred,gold,reviewed=human_references()
    extra=list(font_dirs or [])
    if (LAB/'字体').exists() and LAB/'字体' not in extra:extra.append(LAB/'字体')
    fonts=inventory(Path('C:/Windows/Fonts'),extra,{c['cp'] for c in chars})
    if not fonts:raise RuntimeError('没有可解析的参考字体')
    candidates=strategies();LAB.mkdir(parents=True,exist_ok=True)
    library={'version':'shape-lab-v1','date':'2026-10-12','scope':'全部现有非统一／兼容汉字字符',
             'fourth':mapping,'fourthHash':palette_hash,'weights':weights or WEIGHTS,
             'scorePriorDisclosure':'semantic/mnemonic为人为可解释性先验，未做真人记忆试验',
             'strategies':[{**s,'dictionary':definitions(s)} for s in candidates]}
    save(LAB/'规则策略库.json',library)
    records,manifest,cache=cache_features(chars,fonts,input_hash,preferred,refresh)
    mapping_now,hash_now=palette()
    if hash_now!=palette_hash:raise RuntimeError('实验过程中第四位布局改变，停止而不是混用')
    all_views=[views(r['feature'],mapping) for r in records]
    matrix=np.stack([vector(r['feature']) for r in records]);observed_indices=[i for i,r in enumerate(records) if r['feature']['observed']]
    if not observed_indices:raise RuntimeError('本语料没有可观测字形，不能选择最优策略')
    mean=matrix[observed_indices].mean(axis=0) if observed_indices else np.zeros(matrix.shape[1])
    scale=np.maximum(matrix[observed_indices].std(axis=0),.1) if observed_indices else np.ones(matrix.shape[1])
    comparison=(matrix-mean)/scale
    run=RUNS/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    snapshot=run/'来源快照';snapshot.mkdir()
    for name,content in source_bytes.items():(snapshot/name).write_bytes(content)
    for name in ('来源清单.json','LICENSE-Noto.txt','LICENSE-Egyptology.md','ATTRIBUTION-Egyptology.txt'):
        source=LAB/'字体'/name
        if source.exists():shutil.copy2(source,snapshot/name)
    with gzip.open(run/'观测视图.jsonl.gz','wt',encoding='utf-8') as stream:
        for record,objects in zip(records,all_views):
            stream.write(json.dumps({'cp':record['cp'],'char':record['char'],'observed':record['feature']['observed'],
                'font':record['feature'].get('font'),'views':objects},ensure_ascii=True,separators=(',',':'))+'\n')
    cluster_cache={};results=[]
    for spec in candidates:
        print('评估 '+spec['name'],flush=True)
        labels=None
        if spec['algorithm']=='cluster':
            k=min(spec['clusters'],len(observed_indices))
            if k<1:labels={}
            else:
                if k not in cluster_cache:
                    predicted,model=cluster_vectors(matrix[observed_indices],k)
                    cluster_cache[k]={i:int(label) for i,label in zip(observed_indices,predicted)}
                    save(run/('视觉原型-'+str(k)+'.json'),model)
                labels=cluster_cache[k]
        result=evaluate(records,spec,mapping,gold,run,labels,comparison,all_views)
        result['score']=score(result['metrics'],weights or WEIGHTS);results.append(result)
    results.sort(key=lambda r:(-r['score'],r['id']))
    reasons=Counter(r['feature'].get('reason') for r in records if not r['feature']['observed'])
    summary={'version':'shape-lab-v1','date':'2026-10-12','run':str(run),'elapsedSeconds':time.monotonic()-started,
             'scope':{'characters':len(chars),'allNonHan':limit is None,'inputHash':input_hash,
                      'exclusion':'项目han标记：全部统一／兼容汉字，不排〇、部首、笔画、标点'},
             'fourth':mapping,'fourthHash':palette_hash,'featureCache':cache,'featureManifest':manifest,
             'sourceHashes':{name:hashlib.sha256(content).hexdigest() for name,content in source_bytes.items()},
             'featureViews':'所有策略共享，不能重排或臆造末位','weights':weights or WEIGHTS,
             'missingReasons':dict(reasons),'strategies':results,'pareto':frontier(results),
             'selected':{'id':results[0]['id'],'status':'provisional-score-winner','humanMemoryTested':False,
                         'reviewedCodebooksChanged':False,'rimePublished':False}}
    save(run/'summary.json',summary);report=reports(summary,run)
    save(LAB/'最新实验.json',{'run':str(run),'report':report,'winner':summary['selected'],
                         'allNonHan':limit is None,'characters':len(chars),'completed':True})
    return {'report':report,'run':str(run),'winner':results[0]['id'],'score':results[0]['score'],
            'characters':len(chars),'observed':results[0]['metrics']['fourCodeGlyphs'],
            'strategies':len(results),'elapsedSeconds':summary['elapsedSeconds']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,help='Smoke test only; omit for the full corpus')
    parser.add_argument('--refresh',action='store_true')
    parser.add_argument('--font-dir',type=Path,action='append',default=[])
    parser.add_argument('--weights',type=float,nargs=3,metavar=('BALANCE','MEMORY','VISUAL'))
    args=parser.parse_args()
    if args.limit is not None and args.limit<1:parser.error('limit必须大于0')
    weights=dict(zip(WEIGHTS,args.weights)) if args.weights is not None else None
    print(json.dumps(run_experiment(args.limit,args.refresh,args.font_dir,weights),ensure_ascii=False))


if __name__=='__main__':main()
