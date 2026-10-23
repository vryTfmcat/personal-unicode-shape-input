"""Make o a pure wedge family and refresh the user-requested single-line Markdown previews."""
import copy,gzip,json,re,sys
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

PROJECT=Path(__file__).resolve().parents[1]
LAB=PROJECT/'数据/三模式/规则库'
ROOT=LAB/'人工核对'
ACTIVE='abcdefghijklmnopqrstuvw'
WEDGE_BLOCKS={'Cuneiform','Cuneiform Numbers and Punctuation','Early Dynastic Cuneiform','Ugaritic','Old Persian'}
from external_paths import shape_dependency_dir
sys.path.insert(0, str(shape_dependency_dir()))
from ortools.graph.python import min_cost_flow
from apply_visual_review import rebase,save

def redistribute(cost,lower,upper):
    n,k=cost.shape
    assert sum(lower)<=n<=sum(upper)
    f=min_cost_flow.SimpleMinCostFlow()
    arcs=f.add_arcs_with_capacity_and_unit_cost(np.repeat(np.arange(n,dtype='int32'),k),
        n+np.tile(np.arange(k,dtype='int32'),n),np.ones(n*k,dtype='int64'),
        np.rint(np.maximum(0,cost).flatten()*100000).astype('int64'))
    f.add_arcs_with_capacity_and_unit_cost(np.arange(n,n+k,dtype='int32'),np.full(k,n+k,dtype='int32'),
        np.array(upper,dtype='int64')-np.array(lower,dtype='int64'),np.zeros(k,dtype='int64'))
    f.set_nodes_supplies(np.arange(n+k+1,dtype='int32'),np.r_[np.ones(n,dtype='int64'),-np.array(lower,dtype='int64'),-(n-sum(lower))])
    if f.solve()!=f.OPTIMAL:raise RuntimeError('局部分配未得到最优解')
    flows=f.flows(arcs).reshape(n,k);assert np.all(flows.sum(1)==1)
    return flows.argmax(1)

def main():
    source=Path(json.loads((ROOT/'最新人工核对.json').read_text(encoding='utf-8'))['run'])
    active_rules=json.loads((source/'人工约束.json').read_text(encoding='utf-8'))
    if not active_rules.get('wedgeFamily',{}).get('pure',False):
        raise RuntimeError('楔笔专桶约束已由用户取消；此历史工具不能再应用到现行分组。')
    old=json.loads((source/'全部收纳.json').read_text(encoding='utf-8'))
    before={r['cp']:r for r in old['characters']};rows=copy.deepcopy(old['characters'])
    meta={int(r['codepoint'][2:],16):r for r in json.loads((PROJECT/'原型/键位编辑器/data/mode-data.json').read_text(encoding='utf-8'))['characters']}
    model=json.loads((source/'模型.json').read_text(encoding='utf-8'))
    with gzip.open(rebase(model['qualityRecords']),'rt',encoding='utf-8') as f:qa=list(map(json.loads,f))
    with np.load(rebase(model['featureCache'])) as f:
        visual=(f['pixels']-np.array(model['pixelMean'],dtype='float32'))@np.array(model['basis'],dtype='float32')/model['visualScale']
        structural=(f['stats']-np.array(model['structureMean']))/np.array(model['structureScale'])*np.array(model['structureWeights'])
        matrix=np.concatenate([visual,structural,f['hog']*model['hogMultiplier']],1).astype('float32')
    indices={q['cp']:i for i,q in enumerate(qa)};centres=np.array(model['centres'],dtype='float32')
    wedge=[];outgoing=[]
    for r in rows:
        if meta[r['cp']]['sourceBlock'] in WEDGE_BLOCKS:
            assert r['primary'] not in ('x','y','z')
            wedge.append(r['cp']);r.update(primary='o',aliases=[],status='reviewed-wedge-family' if r['cp'] in indices else 'reviewed-wedge-pending-glyph',
                reviewReason='所有楔笔组成的字符归o；含苏美尔-阿卡德、乌加里特及古波斯')
        else:
            r['aliases']=[k for k in r['aliases'] if k!='o']
            if r['primary']=='o':outgoing.append(r);r['primary']=None
    fixed=Counter(r['primary'] for r in rows if r['primary'])
    targets=[k for k in ACTIVE if k!='o']
    vectors=matrix[[indices[r['cp']] for r in outgoing]]
    target_centres=centres[[ACTIVE.index(k) for k in targets]]
    cost=np.maximum(0,(vectors*vectors).sum(1)[:,None]+(target_centres*target_centres).sum(1)[None,:]-2*vectors@target_centres.T)
    labels=redistribute(cost,[max(0,500-fixed[k]) for k in targets],[2000-fixed[k] for k in targets])
    for r,j in zip(outgoing,labels):
        target=targets[int(j)];r.update(primary=target,status='reviewed-nonwedge-redistributed',reviewReason='o清除非楔笔字符，按原特征近邻和剩余容量整体分配')
        r['aliases']=[k for k in r['aliases'] if k!=target]
    counts=Counter(r['primary'] for r in rows if r['primary'])
    assert all(500<=counts[k]<=2000 for k in ACTIVE)
    assert all(r['primary']=='o' and not r['aliases'] for r in rows if r['cp'] in wedge)
    assert all(r['cp'] in wedge for r in rows if r['primary']=='o' or 'o' in r['aliases'])
    assert [r for r in rows if r['primary'] in ('x','y','z')]==[r for r in old['characters'] if r['primary'] in ('x','y','z')]
    affected=set(wedge)|{r['cp'] for r in outgoing}
    assert all(r['primary']==before[r['cp']]['primary'] for r in rows if r['cp'] not in affected)
    new_centres=centres.copy()
    for k in ACTIVE:new_centres[ACTIVE.index(k)]=matrix[[indices[r['cp']] for r in rows if r['primary']==k and r['cp'] in indices]].mean(0)
    for r in rows:
        if r['primary'] and r['primary'] in ACTIVE:r['distance']=float(((matrix[indices[r['cp']]]-new_centres[ACTIVE.index(r['primary'])])**2).sum()) if r['cp'] in indices else None
    changes=[{'cp':r['cp'],'char':r['char'],'before':before[r['cp']]['primary'],'after':r['primary'],
        'beforeAliases':before[r['cp']]['aliases'],'afterAliases':r['aliases'],'reason':r.get('reviewReason')}
        for r in rows if r['primary']!=before[r['cp']]['primary'] or r['aliases']!=before[r['cp']]['aliases']]
    run=ROOT/'运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    save(run/'全部收纳.json',dict(old,characters=rows))
    save(run/'冻结分组.json',{'version':'pure-wedge-o-v1','capacity':{'plannedLower':500,'plannedUpper':2000},
        'characters':[r for r in rows if r['primary'] not in ('y','z')]})
    rules=json.loads((source/'人工约束.json').read_text(encoding='utf-8'))
    rules.update(version='pure-wedge-o-v1',date='2026-10-13')
    rules['wedgeFamily']={'target':'o','members':wedge,'blocks':sorted(WEDGE_BLOCKS),'pure':True,
        'otherCharactersForbidden':True,'aliasesOutsideO':False,
        'basis':'用户要求凡是楔笔组成者归o，非楔笔移出；Unicode 17确认三类楔形文字',
        'reference':'https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-11/'}
    save(run/'人工约束.json',rules);save(run/'局部迁移.json',{'source':str(source),'changes':changes})
    model.update(centres=new_centres.tolist(),manualRules=str(run/'人工约束.json'));save(run/'模型.json',model)
    preview=run/'全部字符预览';preview.mkdir()
    for k in ACTIVE+'x':
        text=''.join(r['char'] for r in rows if r['primary']==k)
        assert not any(c in text for c in '\r\n\u2028\u2029')
        (preview/(k+'.md')).write_bytes(text.encode('utf-8'))
    # Preserve locked reference glyphs; unrenderable wedge signs stay named pending entries, not fabricated images.
    fsource=json.loads((PROJECT/'数据/三模式/规则库/运行/20261012-123535/summary.json').read_text(encoding='utf-8'))
    with gzip.open(rebase(fsource['featureCache']),'rt',encoding='utf-8') as f:features={r['cp']:r['feature'] for r in map(json.loads,f)}
    directory=run/'代表字形';directory.mkdir();fonts={};font_label=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',12);reps={}
    for k in ACTIVE:
        members=sorted((r for r in rows if r['primary']==k and r['cp'] in indices),key=lambda r:(r['distance'],r['cp']))
        chosen=members[:8]+members[-4:];reps[k]=[{'cp':r['cp'],'char':r['char']} for r in chosen]
        image=Image.new('RGB',(480,300),'white');draw=ImageDraw.Draw(image)
        for i,r in enumerate(chosen):
            f=features[r['cp']];key=(str(rebase(f['fontPath'])),f.get('fontIndex',0))
            if key not in fonts:fonts[key]=ImageFont.truetype(key[0],48,index=key[1])
            font=fonts[key];box=font.getbbox(r['char']);left=i%4*120;top=i//4*100
            draw.rectangle((left,top,left+119,top+99),outline='#d7dee7')
            draw.text((left+60-(box[2]-box[0])/2-box[0],top+38-(box[3]-box[1])/2-box[1]),r['char'],font=font,fill='#172d43')
            draw.text((left+10,top+72),f'U+{r["cp"]:04X}',font=font_label,fill='#5b7085')
        image.save(directory/(k+'.png'))
    summary=json.loads((source/'摘要.json').read_text(encoding='utf-8'))
    summary.update(run=str(run),baseline=str(source),counts=dict(counts),assigned=sum(counts.values()),
        ordinaryAssigned=sum(counts[k] for k in ACTIVE),ordinaryObserved=sum(r['primary'] in ACTIVE for r in rows if r['cp'] in indices),
        pending=sum(r['primary'] is None for r in rows),representatives=reps,
        wedgeGroup=len(wedge),wedgePendingGlyph=sum(cp not in indices for cp in wedge),oPure=True,
        nonWedgeMovedOut=len(outgoing),wedgeMovedIn=sum(before[cp]['primary']!='o' for cp in wedge))
    summary['capacity'].update(scope=summary['ordinaryScope'],observed=summary['ordinaryObserved'])
    save(run/'摘要.json',summary)
    page=(source/'单层分桶核对.html').read_text(encoding='utf-8');old_payload=json.loads(re.search(r'const data=(.*?);const \$=',page,re.S).group(1))
    extra={r['cp']:r for r in old_payload['rows']};display=copy.deepcopy(rows)
    for r in display:
        for name in ('qualityNote','displayChar'):
            if name in extra[r['cp']]:r[name]=extra[r['cp']][name]
    payload=json.dumps({'summary':summary,'rows':display},ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    page=re.sub(r'const data=.*?;const \$=',lambda m:'const data='+payload+';const $=',page,count=1,flags=re.S)
    page=page.replace('楔笔族局部合并到o','o只收纳楔笔族，非楔笔已移出').replace('人工修正说明.md','纯楔笔修正说明.md')
    (run/'单层分桶核对.html').write_text(page,encoding='utf-8')
    (run/'x附加符号核对.html').write_bytes((source/'x附加符号核对.html').read_bytes())
    # Refresh exactly the user-requested historical preview folder, with a recoverable snapshot.
    target=PROJECT/'数据/三模式/规则库/首次优化/运行/20261012-171242/全部字符预览'
    backup=run/'更新前MD备份';backup.mkdir()
    for k in ACTIVE+'x':
        oldfile=target/(k+'.md')
        if oldfile.exists():(backup/(k+'.md')).write_bytes(oldfile.read_bytes())
        oldfile.write_bytes((preview/(k+'.md')).read_bytes())
    aggregate=target/'a-w.md'
    if aggregate.exists():(backup/'a-w.md').write_bytes(aggregate.read_bytes())
    aggregate_text='\n\n'.join('# '+k+'\n'+(preview/(k+'.md')).read_bytes().decode('utf-8') for k in ACTIVE)
    aggregate.write_bytes(aggregate_text.encode('utf-8'))
    (preview/'a-w.md').write_bytes(aggregate_text.encode('utf-8'))
    save(target.parent/'预览来源.json',{'source':str(run),'updated':'2026-10-13','files':[k+'.md' for k in ACTIVE+'x']+['a-w.md'],
        'note':'MD预览按用户要求更新为最新人工分桶；此目录原实验模型及历史摘要保持原样。'})
    incoming=sum(before[cp]['primary']!='o' for cp in wedge)
    explanation=['# o纯楔笔桶与最新MD预览','',
        f'o共{len(wedge)}字；从其他桶或待分类移入{incoming}字，移出非楔笔{len(outgoing)}字。',
        f'其中{summary["wedgePendingGlyph"]}字已确定楔笔族但仍缺可靠渲染，标记为待补字形；不猜造字形。',
        '包含苏美尔-阿卡德楔形文字及数字标点、早期王朝扩展、乌加里特字和古波斯字。参考：[Unicode 17](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-11/)。',
        '所有非楔笔字符的o别名已清除，楔笔字符只保留o主归属；其他主归属仅调整原o中的非楔笔，x/y/z逐项不变。',
        '原o的非楔笔按照固定旧中心距离与各桶剩余容量，用最小费用流整体分配；其他桶没有全量重聚类。','',
        '已更新首次优化/运行/20261012-171242/全部字符预览下a～w.md，并新增x.md。每文件仅真实字符单行，不加标题、占位圈或说明。旧MD字节备份在本版更新前MD备份。历史实验模型和摘要不冒充本版分桶。',
        '正式码本和小狼毫未改动。','',
        '字体归属沿用锁定来源：Egyptology Extended by Land of Kemet，基于Rosmorduc与Thomas的JSesh字形，CeCILL v2.1。','']
    (run/'纯楔笔修正说明.md').write_text('\n'.join(explanation),encoding='utf-8')
    report={'ok':True,'identities':len(rows),'o':counts['o'],'oOnlyWedge':True,'wedgeMembers':len(wedge),
        'wedgePendingGlyph':summary['wedgePendingGlyph'],'incoming':incoming,'outgoing':len(outgoing),
        'x':counts['x'],'reservedXYZUnchanged':True,'otherPrimaryUnchanged':True,
        'minOrdinary':min(counts[k] for k in ACTIVE),'maxOrdinary':max(counts[k] for k in ACTIVE),'mdFiles':24,
        'previewDirectory':str(target)}
    for k in ACTIVE+'x':
        assert (target/(k+'.md')).read_bytes()==(preview/(k+'.md')).read_bytes()
        assert len((target/(k+'.md')).read_bytes().decode('utf-8'))==counts[k]
    assert summary['assigned']+summary['pending']==len(rows)
    save(run/'校验报告.json',report)
    save(ROOT/'现行人工约束.json',rules)
    save(ROOT/'最新人工核对.json',{'run':str(run),'source':str(source),'completed':True,'effectiveCodebooksChanged':False})
    (run/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(report,run=str(run)),ensure_ascii=False))

if __name__=='__main__':main()
