"""Local human revisions: dependent marks to x, requested wedge group to o; no full reclustering."""
import argparse,copy,gzip,json,re,hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw

PROJECT=Path(__file__).resolve().parents[1]
LAB=PROJECT/'数据/三模式/规则库'
ROOT=LAB/'人工核对'
ACTIVE='abcdefghijklmnopqrstuvw'
MARKS={'Mn','Mc','Me'}

def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def rebase(path):
    value = str(path).replace(chr(92), '/')
    marker = '/' + PROJECT.name + '/'
    if marker in value:
        return PROJECT / value.split(marker, 1)[1]
    candidate = Path(value)
    return candidate if candidate.is_absolute() else PROJECT / candidate


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--all-cuneiform',action='store_true')
    args=parser.parse_args()
    source=rebase(json.loads((LAB/'首次优化/最新优化.json').read_text(encoding='utf-8'))['run'])
    before=json.loads((source/'全部收纳.json').read_text(encoding='utf-8'))
    rows=copy.deepcopy(before['characters']);rowmap={r['cp']:r for r in rows}
    data=json.loads((PROJECT/'原型/键位编辑器/data/mode-data.json').read_text(encoding='utf-8'))
    meta={int(r['codepoint'][2:],16):r for r in data['characters']}
    oldsummary=json.loads((source/'摘要.json').read_text(encoding='utf-8'))
    model=json.loads((source/'模型.json').read_text(encoding='utf-8'))
    with gzip.open(rebase(model['qualityRecords']),'rt',encoding='utf-8') as stream:qa=list(map(json.loads,stream))
    observed_cp=[q['cp'] for q in qa]
    with np.load(rebase(model['featureCache'])) as f:
        visual=(f['pixels']-np.array(model['pixelMean'],dtype='float32'))@np.array(model['basis'],dtype='float32')/model['visualScale']
        structural=(f['stats']-np.array(model['structureMean']))/np.array(model['structureScale'])*np.array(model['structureWeights'])
        x=np.concatenate([visual,structural,f['hog']*model['hogMultiplier']],1).astype('float32')
    indices={cp:i for i,cp in enumerate(observed_cp)}
    centres=np.array(model['centres'],dtype='float32')
    excluded=[];group=[];changes=[]
    for r in rows:
        category=meta[r['cp']]['category']
        if r['primary'] not in ('y','z') and category in MARKS:
            excluded.append(r['cp'])
            r.update(primary='x',aliases=[],status='reviewed-dependent-collection',
                category=category,collectionReason='组合/附加/变体标记；从独立主体字形聚类移出')
        block=meta[r['cp']]['sourceBlock']
        is_wedge=block.startswith(('Cuneiform','Early Dynastic Cuneiform'))
        old=rowmap[r['cp']]['primary']  # row has not otherwise been moved except marks; wedge entries are nonmarks.
        if is_wedge and old and (args.all_cuneiform or old in ('n','o','q')):
            group.append(r['cp'])
            r.update(primary='o',aliases=[],status='reviewed-wedge-family',
                reviewReason='用户确认的楔笔视觉族合并')
    # Preserve all remaining primary assignments. Repair only newly underfull buckets with minimum added distance.
    counts=Counter(r['primary'] for r in rows if r['primary'])
    locked=set(excluded)|set(group)
    fills=[]
    for target in ACTIVE:
        need=max(0,500-counts[target])
        if not need:continue
        target_index=ACTIVE.index(target);candidates=[]
        for r in rows:
            if r['cp'] in locked or r['cp'] not in indices or r['primary'] not in ACTIVE:continue
            original=r['primary']
            if original==target or counts[original]<=500:continue
            vector=x[indices[r['cp']]]
            increase=float(((vector-centres[target_index])**2).sum()-((vector-centres[ACTIVE.index(original)])**2).sum())
            candidates.append((increase,r['cp']))
        for increase,cp in sorted(candidates):
            r=rowmap[cp];old=r['primary']
            if counts[old]<=500:continue
            r.update(primary=target,aliases=sorted(set([old,*r['aliases']])-{target})[:2],
                status='capacity-local-adjustment',reviewReason='附加符号移出后的最小代价补位')
            counts[old]-=1;counts[target]+=1
            fills.append({'cp':cp,'char':r['char'],'before':old,'after':target,'addedDistance':increase})
            need-=1
            if not need:break
        if need:raise ValueError('局部补位容量不足')
    counts=Counter(r['primary'] for r in rows if r['primary'])
    assert all(500<=counts[k]<=2000 for k in ACTIVE)
    oldmap={r['cp']:r for r in before['characters']}
    changed_cp=set(excluded)|set(group)|{r['cp'] for r in fills}
    for r in rows:
        if r['cp'] not in changed_cp:
            assert r['primary']==oldmap[r['cp']]['primary'] and r['aliases']==oldmap[r['cp']]['aliases']
    for r in rows:
        old=oldmap[r['cp']]
        if r['primary']!=old['primary'] or r['aliases']!=old['aliases']:
            changes.append({'cp':r['cp'],'char':r['char'],'before':old['primary'],'after':r['primary'],
                'beforeAliases':old['aliases'],'afterAliases':r['aliases'],'reason':r.get('reviewReason',r.get('collectionReason'))})
    assert [r for r in rows if r['primary'] in ('y','z')]==[r for r in before['characters'] if r['primary'] in ('y','z')]
    run=ROOT/'运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    save(run/'全部收纳.json',dict(before,characters=rows))
    save(run/'冻结分组.json',{'version':'human-review-v1','capacity':{'plannedLower':500,'plannedUpper':2000},
        'characters':[r for r in rows if r['primary'] not in ('y','z')]})
    rules={'version':'human-review-v1','date':'2026-10-13','source':str(source),
        'x':{'categories':sorted(MARKS),'priority':'只处理普通池，保留y/z现有收纳','members':excluded,
            'capacityExempt':True,'dottedCircleDisplayOnly':True},
        'wedgeFamily':{'target':'o','sourceBuckets':'all' if args.all_cuneiform else ['n','o','q'],
            'members':group,'basis':'用户明确的楔笔视觉族；不以此推断其他文字块合并'},
        'independentExamplesKept':[ord(c) for c in '֊٠۰܂࠾◌']}
    save(run/'人工约束.json',rules)
    save(run/'局部迁移.json',{'changes':changes,'capacityFills':fills})
    newcentres=centres.copy()
    for k in ACTIVE:
        members=[indices[r['cp']] for r in rows if r['primary']==k]
        newcentres[ACTIVE.index(k)]=x[members].mean(0)
    for r in rows:
        if r['primary'] and r['primary'] in ACTIVE:
            r['distance']=float(((x[indices[r['cp']]]-newcentres[ACTIVE.index(r['primary'])])**2).sum())
    model.update(centres=newcentres.tolist(),manualRules=str(run/'人工约束.json'),qualityRecords=str(rebase(model['qualityRecords'])),
        featureCache=str(rebase(model['featureCache'])))
    save(run/'模型.json',model)
    save(run/'全部收纳.json',dict(before,characters=rows))
    save(run/'冻结分组.json',{'version':'human-review-v1','capacity':{'plannedLower':500,'plannedUpper':2000},
        'characters':[r for r in rows if r['primary'] not in ('y','z')]})
    preview=run/'全部字符预览';preview.mkdir()
    for k in ACTIVE:
        text=''.join(r['char'] for r in rows if r['primary']==k)
        assert not any(c in text for c in '\r\n\u2028\u2029')
        (preview/(k+'.md')).write_bytes(text.encode('utf-8'))
    marks=[r for r in rows if r['primary']=='x']
    (preview/'x_原始字符.md').write_bytes(''.join(r['char'] for r in marks).encode('utf-8'))
    (preview/'x_占位圈预览.md').write_bytes(''.join('◌'+r['char'] for r in marks).encode('utf-8'))
    # Actual locked primary glyphs for the representative cards; relocated project font paths are resolved on read.
    source_data=PROJECT/'数据/三模式/规则库/运行/20261012-123535/summary.json'
    feature_source=json.loads(source_data.read_text(encoding='utf-8'))
    with gzip.open(rebase(feature_source['featureCache']),'rt',encoding='utf-8') as stream:features={r['cp']:r['feature'] for r in map(json.loads,stream)}
    image_dir=run/'代表字形';image_dir.mkdir()
    label=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',12);fonts={};reps={}
    for k in ACTIVE:
        members=sorted((r for r in rows if r['primary']==k),key=lambda r:(r['distance'],r['cp']))
        chosen=members[:8]+members[-4:];reps[k]=[{'cp':r['cp'],'char':r['char']} for r in chosen]
        image=Image.new('RGB',(480,300),'white');draw=ImageDraw.Draw(image)
        for i,r in enumerate(chosen):
            f=features[r['cp']];key=(str(rebase(f['fontPath'])),f.get('fontIndex',0))
            if key not in fonts:fonts[key]=ImageFont.truetype(key[0],48,index=key[1])
            font=fonts[key];box=font.getbbox(r['char']);left=(i%4)*120;top=(i//4)*100
            draw.rectangle((left,top,left+119,top+99),outline='#d7dee7')
            draw.text((left+60-(box[2]-box[0])/2-box[0],top+38-(box[3]-box[1])/2-box[1]),r['char'],font=font,fill='#172d43')
            draw.text((left+10,top+72),f'U+{r["cp"]:04X}',font=label,fill='#5b7085')
            draw.text((left+10,top+85),'centre' if i<8 else 'edge',font=label,fill='#5b7085')
        image.save(image_dir/(k+'.png'))
    page=(source/'单层分桶核对.html').read_text(encoding='utf-8')
    old_payload=json.loads(re.search(r'const data=(.*?);const \$=',page,re.S).group(1))
    extras={r['cp']:r.get('qualityNote') for r in old_payload['rows']}
    displayrows=copy.deepcopy(rows)
    for r in displayrows:
        r['qualityNote']=extras.get(r['cp']) or ('附加/变体标记收纳' if r['primary']=='x' else '特殊收纳')
        if r['primary']=='x':r['displayChar']='◌'+r['char']
    summary=copy.deepcopy(oldsummary)
    summary.update(date='2026-10-13',run=str(run),baseline=str(source),counts=dict(counts),
        reserved={'x':counts['x'],'y':counts['y'],'z':counts['z']},representatives=reps,
        ordinaryScope=sum(r['primary'] not in ('x','y','z') for r in rows),
        ordinaryAssigned=sum(counts[k] for k in ACTIVE),pending=sum(r['primary'] is None for r in rows),
        reviewedMarks=len(excluded),wedgeGroup=len(group),capacityFills=len(fills),
        manualRevision=True,primaryChanged=sum(r['before']!=r['after'] for r in changes))
    # Do not re-present old optimization scores as scores for this manually revised partition.
    summary.pop('comparisons',None);summary.pop('winner',None)
    summary['assigned']=sum(counts.values())
    summary['capacity'].update(scope=summary['ordinaryScope'],observed=summary['ordinaryAssigned'])
    save(run/'摘要.json',summary)
    payload=json.dumps({'summary':summary,'rows':displayrows},ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    page=re.sub(r'const data=.*?;const \$=',lambda m:'const data='+payload+';const $=',page,count=1,flags=re.S)
    page=page.replace("esc(r.char)","esc(r.displayChar||r.char)")
    page=page.replace("k==='x'?'暂时留空'","k==='x'?'组合、附加与变体标记；占位圈仅用于展示'")
    page=page.replace('x/y/z布局不变，尚未发布输入法。','x为组合附加标记专桶；楔笔族局部合并到o。占位圈仅用于预览，正式码本和输入法未发布。')
    page=page.replace('<h2>26桶代表字形</h2>','<p><a href="x附加符号核对.html">x附加符号独立核对</a> · <a href="人工修正说明.md">局部修改与改进建议</a></p><h2>26桶代表字形</h2>')
    (run/'单层分桶核对.html').write_text(page,encoding='utf-8')
    xpayload=json.dumps([dict(r,name=meta[r['cp']]['unicodeName'],category=meta[r['cp']]['category']) for r in marks],ensure_ascii=True,separators=(',',':'))
    xp=r'''<!doctype html><meta charset="utf-8"><title>x附加符号核对</title><style>body{font:16px system-ui;margin:28px;background:#f4f6f9;color:#21374c}table{width:100%;background:white;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #dce4ec;text-align:left}.glyph{font-size:30px}input,button{font:inherit;padding:8px}</style><h1>x · 组合与附加标记</h1><p>◌只作为展示基字符。保存与复制的是单个真实码位，不包含占位圈；变体选择符等可能没有独立可见字形。</p><input id="q" placeholder="字符、U+码位或名称"><button id="go">查询</button><p id="count"></p><table><thead><tr><th>展示</th><th>码位</th><th>类别</th><th>Unicode名称</th><th>实际字符</th></tr></thead><tbody id="rows"></tbody></table><script>const data=PAYLOAD;const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function show(){let q=$('q').value.trim(),cp=/^U\+[0-9a-f]+$/i.test(q)?parseInt(q.slice(2),16):null;let found=data.filter(r=>!q||(cp!==null?r.cp===cp:r.char===q||r.name.toLowerCase().includes(q.toLowerCase())));$('count').textContent='共'+found.length+'个，显示前300个';$('rows').innerHTML=found.slice(0,300).map(r=>'<tr><td class="glyph">'+esc('◌'+r.char)+'</td><td>U+'+r.cp.toString(16).toUpperCase()+'</td><td>'+r.category+'</td><td>'+esc(r.name)+'</td><td><button data-cp="'+r.cp+'">复制真实字符</button></td></tr>').join('');}document.addEventListener('click',async e=>{let cp=e.target.dataset.cp;if(cp){await navigator.clipboard.writeText(String.fromCodePoint(Number(cp)));e.target.textContent='已复制';}});$('go').onclick=show;$('q').addEventListener('keydown',e=>{if(e.key==='Enter')show()});show();</script>'''.replace('PAYLOAD',xpayload)
    (run/'x附加符号核对.html').write_text(xp,encoding='utf-8')
    descriptions=[
        ('a','窄竖干、括号、末端钩'),('b','S形与连弧'),('c','斜笔、尖角与角折'),('d','密集复合图案'),
        ('e','多弧、多孔及侧开口轮廓'),('f','竖干与短横骨架'),('g','上部框/角连接竖干'),('h','横展框架和多竖干'),
        ('i','圆环/椭圆主体'),('j','包围框内的标记'),('k','并列拱/连环与多干结构'),('l','V/Y与下尖角'),
        ('m','斜向与曲折轮廓'),('n','横展复合轮廓'),('o','楔笔复合族及近邻复杂图形'),
        ('p','纵向复杂轮廓'),('q','折线、斜接与波折'),('r','A/X/交叉骨架'),('s','紧凑填充轮廓'),
        ('t','竖横相交、T形/分叉'),('u','栅格与重复条纹'),('v','点块和小型填充轮廓'),('w','长横线、箭头与横向细形')]
    notes=['# 首次人工核对修正','','本版是局部修正，保留上轮主体布局；没有全量重聚类。', '',
        f'组合/附加/变体标记{len(excluded)}字移入x，其中2018字原有普通桶，251字原待补字形。x是特殊收纳桶，不适用500～2000限制。y/z逐条保留。', '',
        f'n/o/q的楔笔视觉族共{len(group)}字统一到o；其他桶中的楔笔字符暂不自动并入。该规则来自用户确认，不是宣称机器自行学会。', '',
        f'普通桶移出附加符号后，v低于500；只补入{len(fills)}个按旧特征增加距离最少的独立字符，其他主归属保留。补位保留原入口作别名，清单见局部迁移.json。', '',
        '圆圈是基字符占位提示，不等于无法输入；真实字符是附加标记码位，通常应用到前面的基字符。实际U+25CC仍是独立图形，保留普通分桶。',
        '用户列出的֊、٠、۰、܂、࠾是独立标点或数字，未因外观小而移入x。x页面复制按钮只复制真实码位，不复制人为加的占位圈。', '',
        '参考：[Unicode 17组合字符定义](https://unicode.org/versions/Unicode17.0.0/core-spec/chapter-3/)。', '',
        '## 各桶下一轮可核对的主体概括','','这些是对截图主体趋势的概括，不是正式键义或每字已经符合的判定。','',
        '| 桶 | 截图主体趋势 |','|---|---|']
    notes += [f'| {k} | {v} |' for k,v in descriptions]
    notes += ['', '## 后续改进建议','',
        '1. 先检查去掉组合标记之后的形族纯度，尤其i/j/v的空心、包围和填充区别；不立即全量洗牌。',
        '2. 用户确认的楔笔族用成员级同族约束保存；其余桶中的楔笔样本仍可列候选，不按整个文字区块自动合并。',
        '3. 人工相似约束与容量分开处理。主归属优先遵守已确认形族；边界多码保留，但不让别名把已移出的符号又带回原桶。',
        '4. 后续补充轮廓方向、开口边、主干数量和附件相对位置；在独立人工留出样本上检验，不复用机器近邻分数充当本版准确率。',
        '', '旧版全部保留。正式编辑器码本、小狼毫、第三和第四位未改动。',
        '', '参考字体归属：Egyptology Extended by Land of Kemet，基于Rosmorduc与Thomas的JSesh字形，CeCILL v2.1；字体锁定来源沿用上轮。','']
    (run/'人工修正说明.md').write_text('\n'.join(notes),encoding='utf-8')
    save(run/'校验报告.json',{'ok':True,'identities':len(rows),'ordinaryAssigned':sum(counts[k] for k in ACTIVE),
        'pending':sum(r['primary'] is None for r in rows),'minBucket':min(counts[k] for k in ACTIVE),
        'maxBucket':max(counts[k] for k in ACTIVE),'x':counts['x'],'wedgeGroup':len(group),'localFills':len(fills),
        'reservedYZUnchanged':True,'otherPrimaryUnchanged':True})
    save(ROOT/'最新人工核对.json',{'run':str(run),'source':str(source),'completed':True,'effectiveCodebooksChanged':False})
    save(ROOT/'现行人工约束.json',rules)
    (run/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'run':str(run),'counts':dict(counts),'x':counts['x'],'wedgeGroup':len(group),
        'wedgeMoved':sum(oldmap[cp]['primary']!='o' for cp in group),'localFills':len(fills),
        'primaryChanges':sum(r['before']!=r['after'] for r in changes)},ensure_ascii=False))

if __name__=='__main__':main()
