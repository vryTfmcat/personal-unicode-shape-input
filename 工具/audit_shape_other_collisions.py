"""Nine-view whole-glyph descriptors for every other current >=500 group.

No new code bindings. Compute overlapping characters once, preserve all queues.
"""
import json
import math
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from statistics import median

import numpy as np
from PIL import Image,ImageDraw

from build_shape_turn_classification import PROJECT,overview,PALETTE
from build_shape_turn_samples import sha
from audit_shape_historical_buckets import protect
from shape_stroke_topology_trial import analyze,render_locked
from shape_stroke_continuation_trial import analyze_continuation
from shape_recovery_geometry import angle_has_visible_gap
from shape_lab_features import components

OUTPUT=overview.RUNS/'20261024-other-large-collisions-v1'
CACHE=overview.RUNS/'20261024-stroke-continuation-trial-v1/分类数据.json'
THRESHOLD=500
FIELDS=('corners','forks','crosses','straightSegments','curveSegments','totalSegments','otherJunctions','uncertainSegments',
        'strokeCount','straightStrokes','curveStrokes','uncertainStrokes','straightThroughJunctions','curveThroughJunctions','noThroughForks','loops')
JOINT=('corners','forks','crosses','straightSegments','curveSegments','straightThroughJunctions','curveThroughJunctions','straightStrokes','curveStrokes','loops')
FEATURES=('corners','forks','crosses','straightSegments','curveSegments','totalSegments','straightThroughJunctions','curveThroughJunctions','strokeCount','straightStrokes','curveStrokes','loops')
STATUS_NAMES={'stable':'九扰动稳定','unstable':'计数不稳定','filled-face':'实心面，线模型待解释','no-line':'未提取可靠线段',
              'topology-pending':'闭孔与图环待核','pairing-pending':'贯通配对待核','error':'观测失败'}


def vector(s):return [s[k] for k in FIELDS]


def applicability(mask,base):
    if not base['statistics']['totalSegments']:return 'no-line'
    yy,xx=np.nonzero(mask);w=int(xx.max()-xx.min()+1);h=int(yy.max()-yy.min()+1)
    parts=[c for c in components(mask,8) if c['area']>=3]
    if len(parts)==1 and min(w,h)/max(w,h)>=.35 and mask.sum()/(w*h)>.55 and not angle_has_visible_gap({'body':mask}):
        return 'filled-face'
    return 'line-model'


def pictures(mask,base,new):
    plain=Image.fromarray(255-mask.astype('uint8')*255).convert('RGB')
    marked=Image.fromarray(255-mask.astype('uint8')*65).convert('RGB');d=ImageDraw.Draw(marked)
    for stroke in new['strokes']:
        if len(stroke['points'])>1:d.line([tuple(p) for p in stroke['points']],fill=PALETTE[stroke['id']%len(PALETTE)],width=3)
    for c in base['corners']:
        x,y=c['xy'];d.rectangle((x-4,y-4,x+4,y+4),outline='#1452e6',width=2)
    for j in base['junctions']:
        x,y=j['xy'];color='#a315a8' if j['arms']==4 else '#cf1930'
        d.ellipse((x-5,y-5,x+5,y+5),outline=color,width=2)
    for h in new['holes']:d.rectangle(tuple(h['bbox']),outline='#009590',width=2)
    return tuple(im.resize((80,80),Image.Resampling.LANCZOS).tobytes() for im in (plain,marked))


def observe(job):
    row,cached=job;cp=row['cp'];observations=[];errors=[];base0=new0=mask0=None
    if cached:
        observations=[dict(size=v['size'],weight=v['weight'],values=vector(v['statistics']),
                           topologyAgrees=v['topologyAgrees'],ambiguous=v['ambiguous']) for v in cached['variants']]
        mask0=render_locked(row['char'],row['font']);base0=analyze(mask0);new0=analyze_continuation(mask0,base0)
        assert dict(base0['statistics'],**new0['statistics'])==cached['statistics']
        errors=list(cached.get('errors',[]))
    else:
        for size in (96,192,256):
            for weight in (-1,0,1):
                try:
                    mask=render_locked(row['char'],row['font'],size=size,weight=weight);base=analyze(mask);new=analyze_continuation(mask,base)
                    observations.append(dict(size=size,weight=weight,values=vector(dict(base['statistics'],**new['statistics'])),
                                             topologyAgrees=new['topologyAgrees'],ambiguous=bool(new['ambiguities'])))
                    if (size,weight)==(192,0):mask0,base0,new0=mask,base,new
                except (ValueError,IndexError,KeyError) as e:
                    observations.append(dict(size=size,weight=weight,values=None,topologyAgrees=False,ambiguous=False))
                    errors.append(dict(size=size,weight=weight,message=str(e)))
    r={k:row[k] for k in ('cp','char','font','codes','preferredCodes','collisionGroups','detailUrl')}
    r.update(fromCache=bool(cached),observations=observations,errors=errors)
    if base0 is None:
        r.update(statistics=None,status='error',numericallyStable=False,repeatableFields=[],applicability='unobserved',proof={})
        im=Image.new('RGB',(80,80),'white');ImageDraw.Draw(im).text((4,30),'unobserved',fill='black')
        return r,im.tobytes(),im.tobytes()
    stats=dict(base0['statistics'],**new0['statistics']);values=vector(stats)
    repeat=[k for i,k in enumerate(FIELDS) if not errors and all(v['values'] and v['values'][i]==values[i] for v in observations)]
    numeric=len(repeat)==len(FIELDS) and not errors
    domain=applicability(mask0,base0)
    if errors:status='error'
    elif domain!='line-model':status=domain
    elif not all(v['topologyAgrees'] for v in observations):status='topology-pending'
    elif any(v['ambiguous'] for v in observations):status='pairing-pending'
    elif numeric and not (stats['otherJunctions'] or stats['uncertainSegments'] or stats['uncertainStrokes']):status='stable'
    else:status='unstable'
    r.update(statistics=stats,status=status,numericallyStable=numeric,repeatableFields=repeat,applicability=domain,
             proof=dict(pairings=new0['pairings'],holes=new0['holes'],graphCycles=new0['graphCycleCount'],
                        topologyAgrees=new0['topologyAgrees'],ambiguities=new0['ambiguities'],
                        prunedSpurs=base0['prunedSpurCount'],corners=base0['corners'],junctions=base0['junctions']))
    return (r,*pictures(mask0,base0,new0))


def partition(rows,fields):
    groups=Counter(tuple(r['statistics'][k] for k in fields) if r['status']=='stable' else None for r in rows)
    burdens=sorted(n for n in groups.values() for _ in range(n))
    stable_sizes=[n for k,n in groups.items() if k is not None]
    return dict(stableClasses=len(stable_sizes),largestStableClass=max(stable_sizes,default=0),
                pending=groups.get(None,0),maximumIncludingPending=max(burdens),medianCharacterGroup=median(burdens),
                p90CharacterGroup=burdens[math.ceil(.9*len(burdens))-1],charactersInGroupsAtMost20=sum(x<=20 for x in burdens))


def feature_partition(rows,key):
    counts=Counter()
    for r in rows:
        allowed=(r['statistics'] is not None and key in r['repeatableFields'] and not r['errors'])
        if key!='loops':allowed=allowed and r['applicability']=='line-model'
        else:allowed=allowed and all(v['topologyAgrees'] for v in r['observations'])
        counts[r['statistics'][key] if allowed else None]+=1
    return dict(repeatable=len(rows)-counts.get(None,0),pending=counts.get(None,0),
                valueCounts={str(k):v for k,v in counts.items() if k is not None},maximumIncludingPending=max(counts.values()))


def summarize(rows,scopes):
    indexed={r['cp']:r for r in rows};reports=[]
    for scope in scopes:
        members=[indexed[cp] for cp in scope['cps']]
        joint=partition(members,JOINT)
        reports.append(dict(code=scope['code'],count=len(members),membershipFamily=scope['membershipFamily'],
                            identicalMembershipCodes=scope['identicalMembershipCodes'],
                            statusCounts=dict(Counter(r['status'] for r in members)),joint=joint,
                            featureMetrics={key:feature_partition(members,key) for key in FEATURES},
                            cps=scope['cps']))
    return reports


def write_review(report):
    assets={suffix:PROJECT/f'工具/other_collisions_review.{suffix}' for suffix in ('html','css','js')}
    slim=dict(statistics=report['statistics'],groups=report['groups'],statusNames=STATUS_NAMES,fields=list(FIELDS),featureFields=list(FEATURES))
    slim['rows']=[{k:r[k] for k in ('cp','char','collisionGroups','statistics','status','numericallyStable','repeatableFields',
                                   'applicability','observations','proof','preview','preferredCodes')} for r in report['records']]
    data=json.dumps(slim,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    html=assets['html'].read_text(encoding='utf-8').replace('/*DATA*/','window.REVIEW_DATA='+data+';')
    (OUTPUT/'大组结构审阅.html').write_text(html,encoding='utf-8')
    for suffix in ('css','js'):(OUTPUT/f'review.{suffix}').write_bytes(assets[suffix].read_bytes())
    return {str(p.relative_to(PROJECT)):sha(p) for p in assets.values()}


def build():
    if (OUTPUT/'其他大组分析.json').exists():raise FileExistsError('不覆盖既有大组分析')
    o=overview.Overview();intake=set(overview.exclusive_intake());before=protect()
    selected=[g for g in o.collision_groups(4,True) if g['count']>=THRESHOLD and g['code']!='chvc']
    families=defaultdict(list);scopes=[]
    for g in selected:families[tuple(sorted(o.allocation_members(g['code'])))].append(g['code'])
    family_names={cps:f'family-{i+1:03}' for i,cps in enumerate(families)}
    for g in selected:
        cps=tuple(sorted(o.allocation_members(g['code'])))
        scopes.append(dict(code=g['code'],cps=list(cps),membershipFamily=family_names[cps],identicalMembershipCodes=families[cps]))
    union=set().union(*(set(g['cps']) for g in scopes));assert not union&intake
    cached_data=json.loads(CACHE.read_text(encoding='utf-8'));cache={r['cp']:r for r in cached_data['records']}
    model_files=[PROJECT/f'工具/{n}.py' for n in ('shape_stroke_topology_trial','shape_stroke_continuation_trial')]
    for p in model_files:assert sha(p)==cached_data['sourceHashes'][str(p.relative_to(PROJECT))]
    inputs=[Path(__file__),CACHE,*model_files]+[PROJECT/'原型/键位编辑器'/n for n in ('shape_overview.py','shape-key-overview.js','shape-key-overview.html','data/pictorial-exclusive-allocation.json')]
    hashes={str(p.relative_to(PROJECT)):sha(p) for p in inputs}
    membership=defaultdict(list)
    for s in scopes:
        for cp in s['cps']:membership[cp].append(s['code'])
    jobs=[]
    for cp in sorted(union):
        brief=o.brief(cp,True);detail=o.detail(cp,True)
        row=dict(cp=cp,char=chr(cp),font=detail['font'],codes=brief['codes'],preferredCodes=brief['preferredCodes'],
                 collisionGroups=membership[cp],detailUrl=o.rows[cp]['detailUrl'])
        if cp in cache:assert row['codes']==cache[cp]['originalCodes'] and row['preferredCodes']==cache[cp]['originalPreferredCodes']
        jobs.append((row,cache.get(cp)))
    OUTPUT.mkdir(exist_ok=True);(OUTPUT/'atlas').mkdir(exist_ok=True)
    rows=[];raw=Image.new('RGB',(1280,1280),'white');marked=raw.copy()
    # Keep partial results recoverable without rerunning observations.
    checkpoint=OUTPUT/'观测记录.jsonl';completed={}
    if checkpoint.exists():
        manifest=json.loads((OUTPUT/'观测来源.json').read_text(encoding='utf-8'))
        assert manifest['sourceHashes']==hashes
        for line in checkpoint.read_text(encoding='utf-8').splitlines():
            r=json.loads(line);completed[r['cp']]=r
    else:(OUTPUT/'观测来源.json').write_text(json.dumps(dict(sourceHashes=hashes,scopes=scopes),ensure_ascii=False,indent=2),encoding='utf-8')
    # Atlas fragments and JSONL are written only by this parent process.
    with checkpoint.open('a',encoding='utf-8') as stream,ProcessPoolExecutor(max_workers=4) as executor:
        for n,(r,plain_tile,mark_tile) in enumerate(executor.map(observe,jobs)):
            x=n%16*80;y=(n%256)//16*80;atlas=n//256
            r['preview']=dict(atlas=atlas,x=x,y=y,cell=80)
            raw.paste(Image.frombytes('RGB',(80,80),plain_tile),(x,y));marked.paste(Image.frombytes('RGB',(80,80),mark_tile),(x,y));rows.append(r)
            stream.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
            if n%256==255 or n==len(jobs)-1:
                raw.save(OUTPUT/f'atlas/{atlas:03}-plain.png');marked.save(OUTPUT/f'atlas/{atlas:03}-annotated.png')
                raw=Image.new('RGB',(1280,1280),'white');marked=raw.copy();stream.flush()
            if (n+1)%300==0:print(f'其他大组九扰动 {n+1}/{len(jobs)}',flush=True)
    assert before==protect() and hashes=={str(p.relative_to(PROJECT)):sha(p) for p in inputs}
    for g in scopes:assert set(g['cps'])==set(o.allocation_members(g['code']))
    assert all(o.brief(r['cp'],True)['codes']==r['codes'] and o.brief(r['cp'],True)['preferredCodes']==r['preferredCodes'] for r in rows)
    reports=summarize(rows,scopes)
    stats=dict(threshold=THRESHOLD,codeGroups=len(scopes),distinctMembershipFamilies=len(families),uniqueCharacters=len(rows),
               membershipSum=sum(g['count'] for g in selected),cachedCharacters=sum(r['fromCache'] for r in rows),
               freshlyObservedCharacters=sum(not r['fromCache'] for r in rows),nineViewObservations=len(rows)*9,
               newlyComputedNineViewObservations=sum(not r['fromCache'] for r in rows)*9,
               statusCounts=dict(Counter(r['status'] for r in rows)))
    report=dict(version='other-large-groups-v1',runTime=datetime.now().astimezone().isoformat(),statistics=stats,
                groups=reports,records=rows,fields=list(FIELDS),jointFields=list(JOINT),sourceHashes=hashes,protectedHashes=before,
                featureObject='整字原墨迹；不是原码所选局部对象的正确性认证',
                scope='所有现行>=500候选的其他四码组；字符去重观测，逐码保持原集合比较',
                limitations=['完整联合特征分组尚未表达为四键内规则，不能当成实际降重。',
                             '数值稳定不等于人工正确；实心面／无可靠线段／拓扑冲突等保留待解释。',
                             '凸实心面适用性门槛是保守试验，原数值和图仍完整展示，不删除任何候选。',
                             '相同候选集合的多个码均列出，但不重复叠加收益。'],
                newCodes=0,removedPaths=0,tBReentry=0,publicIntegration=False)
    report['uiSourceHashes']=write_review(report)
    (OUTPUT/'其他大组分析.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':build()
