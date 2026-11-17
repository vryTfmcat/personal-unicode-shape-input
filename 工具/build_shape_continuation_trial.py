"""Refine current chvc classifications by continuous strokes and actual rings."""
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont

from build_shape_turn_classification import PROJECT, PAGE, CSS, JS, FIELDS, overview
from build_shape_turn_samples import sha, PALETTE
from audit_shape_historical_buckets import protect
from shape_stroke_topology_trial import analyze,render_locked
from shape_stroke_continuation_trial import analyze_continuation,VERSION

SOURCE=overview.RUNS/'20261024-chvc-turn-classification-v1'
OUTPUT=overview.RUNS/'20261024-stroke-continuation-trial-v1'
NEW_FIELDS=('straightThroughJunctions','curveThroughJunctions','noThroughForks','straightStrokes','curveStrokes','loops')


def marked_tile(mask,result):
    im=Image.fromarray(255-mask.astype('uint8')*65).convert('RGB');d=ImageDraw.Draw(im)
    for stroke in result['strokes']:
        d.line([tuple(p) for p in stroke['points']],fill=PALETTE[stroke['id']%len(PALETTE)],width=4)
    for hole in result['holes']:
        d.rectangle(tuple(hole['bbox']),outline='#009590',width=2)
    for j in result['junctionContinuations']:
        x,y=j['xy'];d.ellipse((x-5,y-5,x+5,y+5),outline='#dc2035',width=2)
    return im.resize((96,96),Image.Resampling.LANCZOS).tobytes()


def worker(old):
    variants=[];baseline=None;mask0=None;errors=[]
    for v in old['variants']:
        try:
            m=render_locked(old['char'],old['font'],size=v['size'],weight=v['weight'])
            base=analyze(m)
            assert base['statistics']==v['statistics'],(old['cp'],'original segment observations changed')
            new=analyze_continuation(m,base)
            variants.append(dict(size=v['size'],weight=v['weight'],statistics=dict(v['statistics'],**new['statistics']),
                                 topologyAgrees=new['topologyAgrees'],ambiguous=bool(new['ambiguities'])))
            if (v['size'],v['weight'])==(192,0):baseline=new;mask0=m
        except (ValueError,KeyError,IndexError) as error:
            errors.append(dict(size=v['size'],weight=v['weight'],error=str(error)))
    if baseline is None:raise ValueError(f'no baseline {old["cp"]}')
    full=dict(old['statistics'],**baseline['statistics'])
    new_stable=not errors and all(all(v['statistics'][k]==full[k] for k in baseline['statistics'])
                                 and v['topologyAgrees'] and not v['ambiguous'] for v in variants)
    combined=old['stableAcrossNineVariants'] and new_stable and not baseline['statistics']['uncertainStrokes']
    r=dict(old)
    r.update(previousGroupId=old['groupId'],previousStable=old['stableAcrossNineVariants'],
             statistics=full,stableAcrossNineVariants=combined,newFeaturesStableNine=new_stable,
             variants=variants,variantsAgreeWithBaseline=sum(v['statistics']==full and v['topologyAgrees'] and not v['ambiguous'] for v in variants),
             errors=errors,continuation=dict(statistics=baseline['statistics'],pairings=baseline['pairings'],
                                            topologyAgrees=baseline['topologyAgrees'],graphCycleCount=baseline['graphCycleCount'],
                                            holes=baseline['holes'],ambiguities=baseline['ambiguities']))
    return r,marked_tile(mask0,baseline)


def group_rows(rows):
    groups=defaultdict(list)
    for r in rows:
        key=tuple(r['statistics'][k] for k in (*FIELDS,*NEW_FIELDS)) if r['stableAcrossNineVariants'] else None
        groups[key].append(r)
    result=[]
    for number,key in enumerate(sorted((k for k in groups if k is not None),key=lambda k:(-len(groups[k]),k)),1):
        s=groups[key][0]['statistics']
        label=f'折{s["corners"]}·叉{s["forks"]}·交{s["crosses"]}｜段{s["straightSegments"]}直{s["curveSegments"]}曲｜贯通直{s["straightThroughJunctions"]}曲{s["curveThroughJunctions"]}｜笔{s["straightStrokes"]}直{s["curveStrokes"]}曲｜环{s["loops"]}'
        g=dict(id=f'class-{number:03}',label=label,count=len(groups[key]),status='stable',signature=list(key));result.append(g)
        for r in groups[key]:r.update(groupId=g['id'],status='stable')
    if None in groups:
        result.append(dict(id='pending-unstable',label='原结构或连续线／环待核',count=len(groups[None]),status='pending-unstable'))
        for r in groups[None]:r.update(groupId='pending-unstable',status='pending-unstable')
    return result


def write_page(report):
    slim={k:report[k] for k in ('statistics','groups','limitations','sampleAcceptance')}
    slim['records']=[{k:r[k] for k in ('cp','char','statistics','status','groupId','preview','variantsAgreeWithBaseline','stableAcrossNineVariants',
                                     'prunedSpurCount','variants','originalPreferredCodes','originalCodes','corners','junctions','continuation')} for r in report['records']]
    page=PAGE.replace('chvc 全字符结构分类试验','chvc 连续笔与闭环试验').replace('chvc：按折角、分叉、交叉与直曲段分类','chvc：连续笔、贯通关系与闭环')
    page=page.replace('蓝方框＝折角 · 红圆＝三线分叉 · 紫菱形＝四线交叉。折角和交点均分段；同处重合只分一次。',
                      '红圈＝连接点；绿色框标出闭孔范围。旧线段数保留，同色表示接续后的同一连续笔。')
    page=page.replace('不同颜色表示不同线段。','同一颜色表示接续后的同一连续笔；绿色框为闭环内区。近180°暂用155°下限，两种观察距离均须成立。')
    page=page.replace('<th>直／曲／总段</th>','<th>直／曲／总段</th><th>贯通直／曲</th><th>连续笔／环</th>')
    js=JS.replace("fields=['corners','forks','crosses','straightSegments','curveSegments'], names=['折角','分叉','交叉','直线段','曲线段']", "fields=['corners','forks','crosses','straightSegments','curveSegments','straightThroughJunctions','curveThroughJunctions','strokeCount','loops'], names=['折角','分叉','交叉','直线段','曲线段','直贯通','曲贯通','连续笔数','环数']")
    js=js.replace('url("atlas/', 'url("${state.view===\'plain\'?\'../20261024-chvc-turn-classification-v1/atlas\':\'atlas\'}/')
    js=js.replace('直${s.straightSegments} · 曲${s.curveSegments} · 共${s.totalSegments}段', '直${s.straightSegments} · 曲${s.curveSegments} · 共${s.totalSegments}段<br>连续${s.strokeCount}笔：直${s.straightStrokes}／曲${s.curveStrokes}<br>贯通直${s.straightThroughJunctions}／曲${s.curveThroughJunctions} · 环${s.loops}')
    old="${t?`${t.straightSegments}／${t.curveSegments}／${t.totalSegments}`:'待核'}</td></tr>"
    new="${t?`${t.straightSegments}／${t.curveSegments}／${t.totalSegments}`:'待核'}</td><td>${t?`${t.straightThroughJunctions}／${t.curveThroughJunctions}`:'待核'}</td><td>${t?`${t.strokeCount}／${t.loops}`:'待核'}</td></tr>"
    assert old in js;js=js.replace(old,new)
    marker="\n $('variantRows').innerHTML="
    injection="\n $('detailText').insertAdjacentHTML('beforeend',`<p>连续笔 ${s.strokeCount}：直${s.straightStrokes}／曲${s.curveStrokes}；环 ${s.loops}。墨迹闭孔与图环核对：${r.continuation.topologyAgrees?'一致':'不一致，待核'}。</p><p>贯通配对角度（两种观察距离）：${r.continuation.pairings.map(p=>p.angles.map(a=>a.toFixed(1)+'°').join('／')).join('；')||'无近180°配对'}。</p>`);"
    assert marker in js;js=js.replace(marker,injection+marker)
    data=json.dumps(slim,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (OUTPUT/'分类审阅.html').write_text(page.replace('/*DATA*/',f'window.REVIEW_DATA={data};'),encoding='utf-8')
    (OUTPUT/'review.js').write_text(js,encoding='utf-8');(OUTPUT/'review.css').write_text(CSS,encoding='utf-8')


def build():
    target=OUTPUT/'分类数据.json'
    if target.exists():raise FileExistsError('不覆盖既有连续笔试验')
    source=SOURCE/'分类数据.json';old=json.loads(source.read_text(encoding='utf-8'))
    before=protect();o=overview.Overview();cohort=set(o.allocation_members('chvc'))
    assert cohort=={r['cp'] for r in old['records']} and not cohort&set(overview.exclusive_intake())
    assert sha(PROJECT/'工具/shape_stroke_topology_trial.py')==old['sourceHashes'][str(Path('工具/shape_stroke_topology_trial.py'))]
    files=[source,Path(__file__),PROJECT/'工具/shape_stroke_continuation_trial.py',PROJECT/'工具/shape_stroke_topology_trial.py']
    files+=[PROJECT/'原型/键位编辑器'/n for n in ('shape_overview.py','shape-key-overview.js','shape-key-overview.html','data/pictorial-exclusive-allocation.json')]
    fingerprints={str(p.relative_to(PROJECT)):sha(p) for p in files}
    OUTPUT.mkdir(exist_ok=True);(OUTPUT/'atlas').mkdir(exist_ok=True)
    records=[];canvas=Image.new('RGB',(1536,1536),'white')
    with ProcessPoolExecutor(max_workers=4) as executor:
        for n,(r,raw) in enumerate(executor.map(worker,old['records'])):
            p=r['preview'];canvas.paste(Image.frombytes('RGB',(96,96),raw),(p['x'],p['y']));records.append(r)
            if n%256==255 or n==len(old['records'])-1:
                canvas.save(OUTPUT/f'atlas/{p["atlas"]:03}-annotated.png');canvas=Image.new('RGB',(1536,1536),'white')
            if (n+1)%150==0:print(f'贯通与闭环九扰动 {n+1}/{len(cohort)}',flush=True)
    groups=group_rows(records)
    assert before==protect() and fingerprints=={str(p.relative_to(PROJECT)):sha(p) for p in files}
    assert {r['cp'] for r in records}==cohort
    assert all(o.brief(r['cp'],True)['codes']==r['originalCodes'] and o.brief(r['cp'],True)['preferredCodes']==r['originalPreferredCodes'] for r in records)
    stats=dict(cohort=len(records),stableNineVariants=sum(r['stableAcrossNineVariants'] for r in records),
               classifiedStable=sum(r['stableAcrossNineVariants'] for r in records),
               unstableNineVariants=sum(not r['stableAcrossNineVariants'] for r in records),
               stableClassCount=sum(g['status']=='stable' for g in groups),largestStableClass=max(g['count'] for g in groups if g['status']=='stable'),
               previousStable=old['statistics']['classifiedStable'],newFeaturesStable=sum(r['newFeaturesStableNine'] for r in records))
    old_largest=[r for r in records if r['previousGroupId']=='class-001']
    split=defaultdict(list)
    for r in old_largest:
        key='待核' if not r['stableAcrossNineVariants'] else f'直贯通{r["statistics"]["straightThroughJunctions"]}／曲贯通{r["statistics"]["curveThroughJunctions"]}／连续{r["statistics"]["strokeCount"]}笔／环{r["statistics"]["loops"]}'
        split[key].append(r['cp'])
    report=dict(version=VERSION,statistics=stats,groups=groups,records=records,
                runTime=datetime.now().astimezone().isoformat(),sourceHashes=fingerprints,protectedHashes=before,
                sampleAcceptance=old['sampleAcceptance'],userDirection='初步检查没有问题；按近180°连续贯通区分T和ꓬ，曲线Ꚕ可看作两笔，4含一个环。',
                largestPreviousClassSplit=[dict(label=k,count=len(v),cps=v) for k,v in split.items()],
                limitations=['连续笔是几何接续，不推断实际书写笔顺。155°与两观察距离均为独立实验参数，未冻结。',
                             '线段数与连续笔数同时保留；环用原墨迹闭孔与骨架图独立环数交叉核对。',
                             '原753稳定字仅在新特征也九扰动稳定且拓扑一致时进入新稳定类，其余完整保留。',
                             '新类别尚未绑定字母或四码；chvc实际仍1554候选。'],
                currentChvcBefore=1554,currentChvcAfter=1554,newCodes=0,removedPaths=0,tBReentry=0,publicIntegration=False)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    write_page(report)
    print(json.dumps(dict(statistics=stats,old143Split=[{k:v for k,v in x.items() if k!='cps'} for x in report['largestPreviousClassSplit']]),ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':build()
