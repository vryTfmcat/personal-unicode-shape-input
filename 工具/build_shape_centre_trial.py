"""Add an isolated centre property to existing fork/junction objects only."""
from collections import Counter, defaultdict
import ast
import copy
import hashlib
from pathlib import Path

from audit_shape_historical_buckets import SOURCE, PROJECT, ROOT, load, protect
from audit_shape_collision_groups import feature_for
from build_shape_keyboard_full import save
from shape_experiment_features import observe, render, component_mask
from shape_experiment_rules import obj, position
from shape_recovery_geometry import visible_fork

OUTPUT=SOURCE.parent/'20261022-centre-position-trial-v1'
CHVC=SOURCE.parent/'20261022-chvc-structure-trial-v1/chvc结构细分与优先级试验.json'
REVIEW_KEY='centralPositionAcceptance20261022'
VERSION='centre-fork-junction-overlay-20261022-v1'


def observation_source(text):
    tree=ast.parse(text)
    names={'is_centre','facts_for','parent_feature','matching_junction','make_path','tier_for'}
    functions=[ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    build=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build')
    loop=next(n for n in build.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple)
              and isinstance(n.target.elts[0],ast.Name) and n.target.elts[0].id=='number')
    return functions,ast.dump(loop,include_attributes=False)


def is_centre(relative, threshold=.12):
    return max(abs(v) for v in relative)<threshold


def facts_for(row):
    objects={o['id']:o for o in row['objects']}
    routes={(r['bucket']+r['familyKey'],r['target']):r for r in row['familyRoutes']}
    selected={}
    for p in row['paths']:
        for e in p['evidence']:
            if p['code'][1]!='h' or e['rule']!='skeleton.branch':continue
            o=objects[e['objectId']]
            if o['kind']=='junction' and is_centre(o['relativePosition']):
                key=(p['code'][:2],e['familyTarget'],o['id'])
                selected[key]={'object':o,'route':routes[key[:2]],'existingEvidence':e}
    return list(selected.values())


def parent_feature(row, route, f):
    if route.get('localBranchProof'):
        return f
    parent=feature_for(row,route,f)
    if parent is not None:return parent
    boxes=[o['bbox'] for o in row['objects'] if o['kind']=='body' and
           o['id'].startswith(route['target']+':'+route['familyKey']+':')]
    matches=[]
    for part in f['parts']:
        box=[part[k] for k in ('x0','y0','x1','y1')]
        delta=min((max(abs(a-b) for a,b in zip(box,old)) for old in boxes),default=999)
        if delta<=5:matches.append((delta,part,box))
    matches.sort(key=lambda x:x[0])
    if not matches or (len(matches)>1 and matches[0][0]==matches[1][0]):return None
    delta,part,box=matches[0]
    span=max(f['bbox'][2]-f['bbox'][0],f['bbox'][3]-f['bbox'][1])
    parent=observe(component_mask(f['mask'],part),f['extent']*max(box[2]-box[0],box[3]-box[1])/span)
    parent['parentRestorationProof']={'kind':'unique-nearest-original-connected-component',
                                      'sourceBoxes':boxes,'actualBBox':box,'maxBboxDelta':delta,
                                      'source':'actual-connected-ink-not-bbox-crop'}
    return parent


def matching_junction(parent, original):
    if parent is None:return {'passed':False,'reason':'参考主体尚不能从原墨迹独立复原'}
    candidates=[]
    for j in parent['junctionObjects']:
        box=[j[k] for k in ('x0','y0','x1','y1')]
        distance=max(abs(a-b) for a,b in zip(box,original['bbox']))
        if distance<=5:candidates.append((distance,j,box))
    candidates.sort(key=lambda x:x[0])
    if not candidates:return {'passed':False,'reason':'交点未复原或位置偏离'}
    if len(candidates)>1 and candidates[0][0]==candidates[1][0]:
        return {'passed':False,'reason':'多个交点距离相同，未唯一匹配对象'}
    _,j,box=candidates[0]
    current=obj('centre-junction','junction',box,parent['bbox'],parent['extent'])
    proof=visible_fork(parent,j,(3,4))
    central=is_centre(current['relativePosition'])
    return {'passed':bool(proof and central),'reason':'通过' if proof and central else
            '中心边界跨越' if proof else '未通过实际墨迹出口检验',
            'bbox':box,'referenceBBox':parent['bbox'],'relativePosition':current['relativePosition'],
            'distanceToCentreBoundary':.12-max(map(abs,current['relativePosition'])),
            'parentRestorationProof':parent.get('parentRestorationProof'),
            'positionKey':position(*current['relativePosition'],0,0),'visibleProof':proof}


def make_path(item,check):
    route=item['route'];original=item['object'];e=item['existingEvidence']
    evidence={k:e[k] for k in ('rule','third','objectId','fourthObjectId','familyTarget','familyId','status')}
    evidence.update(attribute='该对象中心相对本路径主体中心；中心试验区 max(|dx|,|dy|)<0.12',
                    centreTrial=True,referenceBBox=check['referenceBBox'])
    return {'code':route['bucket']+'hmo','evidence':[evidence],'preferred':False,'draftOnly':True}


def tier_for(row,route):
    q=route.get('lookupEvidence',{})
    if route['target']=='body' and row['familyKey']=='h' and q.get('verified') and q.get('dominantSubject'):
        return 0
    # A real local fork does not prove the whole glyph belongs to the fork family.
    return 2


def build():
    if (OUTPUT/'中心属性交点试验.json').exists():raise FileExistsError('不覆盖既有中心试验结果')
    before=protect();review=load(ROOT/'人工审议.json')
    decision=review['keyboardConsultation20261020'][REVIEW_KEY]
    assert decision['meaning']=='中心' and decision['meaningAccepted'] is True
    index=load(SOURCE/'发布核对索引.json');assert 'o' not in index['definitions']['fourth']
    chvc=load(CHVC);frozen={r['cp']:r['preferredCodes'] for r in chvc['records'] if r['preferredCodes']}
    original_counts=Counter(c for r in index['records'] for c in set(r['codes']))
    central_gap={r['cp'] for r in chvc['records'] if not r['preferredCodes'] and
                 all(len(o['visibleForks'])==1 and o['visibleForks'][0]['positionKey'] is None for o in r['checks'])}
    rows=[];scanned=0;related=0;other_central=set()
    for p in sorted((SOURCE/'details').glob('*.json')):
        for row in load(p)['records']:
            scanned+=1
            if any(r['familyKey']=='h' for r in row['familyRoutes']):related+=1
            selected=facts_for(row)
            if selected:rows.append((row,selected))
            for path in row['paths']:
                if path['code'][1]=='h':continue
                ids={e['objectId'] for e in path['evidence'] if e['rule']=='skeleton.branch'}
                if any(o['id'] in ids and is_centre(o['relativePosition']) for o in row['objects']):other_central.add(row['cp'])
    fonts={};records=[];centre_members=defaultdict(set)
    checkpoint=OUTPUT/'中心对象观测检查点.json'
    recipe=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if checkpoint.is_file():
        saved=load(checkpoint)
        producer=OUTPUT/'中心观测生成器快照.py'
        same_observation_recipe=(producer.is_file() and hashlib.sha256(producer.read_bytes()).hexdigest()==saved['recipe']
                                 and observation_source(producer.read_text(encoding='utf-8'))==observation_source(Path(__file__).read_text(encoding='utf-8')))
        if (saved['recipe']==recipe or same_observation_recipe) and saved['protectedHashes']==before:records=saved['records']
    completed={r['cp'] for r in records}
    for r in records:
        for p in r['paths']:centre_members[p['code']].add(r['cp'])
    for number,(row,selected) in enumerate(rows):
        if row['cp'] in completed:continue
        variants=[]
        for size in (48,96,128):
            for weight in (-1,0,1):
                try:
                    f=observe(*render(row['char'],row['font']['path'],row['font'].get('index',0),size=size,weight=weight,fonts=fonts))
                    parents={}
                    for item in selected:
                        key=item['route']['target']
                        if key not in parents:parents[key]=parent_feature(row,item['route'],f)
                    checks=[matching_junction(parents[item['route']['target']],item['object']) for item in selected]
                except (OSError,ValueError) as error:
                    checks=[{'passed':False,'reason':str(error)} for item in selected]
                variants.append({'size':size,'weight':weight,'checks':checks})
        paths={};added_objects={};routes={};tiers={};details=[]
        for i,item in enumerate(selected):
            checks=[v['checks'][i] for v in variants];passed=all(c['passed'] for c in checks)
            details.append({'objectId':item['object']['id'],'target':item['route']['target'],
                            'prefix':item['route']['bucket']+'h','passed':passed,'checks':checks})
            if not passed:continue
            path=make_path(item,checks[4]);code=path['code']
            if code in paths:paths[code]['evidence']+=path['evidence']
            else:paths[code]=path
            added_objects[item['object']['id']]=copy.deepcopy(item['object'])
            routes[(item['route']['bucket']+'h',item['route']['target'])]=item['route']
            tiers[code]=min(tiers.get(code,3),tier_for(row,item['route']))
            centre_members[code].add(row['cp'])
        records.append({k:row.get(k) for k in ('cp','char','bucket','familyKey','font','preview','oldReviewed')} |
                       {'paths':list(paths.values()),'objects':list(added_objects.values()),'familyRoutes':list(routes.values()),
                        'pathTiers':tiers,'objectsChecked':details,'stable':bool(paths),
                        'oldPreferredCodes':[p['code'] for p in row['paths'] if p.get('preferred')],
                        'chvcCohort':any(p['code']=='chvc' for p in row['paths']),
                        'inPrevious101':row['cp'] in central_gap,'frozenPreference':frozen.get(row['cp']),
                        'originalCodes':[p['code'] for p in row['paths']]})
        if (number+1)%100==0:print(f'中心 {number+1}/{len(rows)} 字九扰动复核完成',flush=True)
        if (number+1)%250==0 or number+1==len(rows):
            save(checkpoint,{'recipe':recipe,'protectedHashes':before,'records':records})
    counts={c:len(cps) for c,cps in centre_members.items()}
    for r in records:
        # Preserve all 418 prior choices. Promote only the targeted gap or an existing fork primary.
        choices=[p['code'] for p in r['paths'] if r['pathTiers'][p['code']]<=0]
        choices.sort(key=lambda c:(counts[c],c))
        old=r['oldPreferredCodes']
        generic=not old or all(len(c)<4 or c[2] in 'hveci' for c in old)
        eligible=not r['frozenPreference'] and choices and generic
        if eligible:
            best=choices[0]
            if old and min(original_counts[c] for c in old)<=counts[best]:eligible=False
        r['preferredCodes']=[choices[0]] if eligible else []
        for p in r['paths']:p['preferred']=p['code'] in r['preferredCodes']
    assert scanned==28223 and related==5041 and before==protect()
    kept_gap={r['cp'] for r in records if r['inPrevious101'] and r['stable']}
    assert central_gap <= {r['cp'] for r in records}, '原101字必须全部记入结果，包括未复原者'
    assert kept_gap <= central_gap
    assert not any(r['preferredCodes'] and r['frozenPreference'] for r in records)
    # New fourth keys extend existing three-key memberships, not new broad prefixes.
    ix={r['cp']:r for r in index['records']}
    assert all(any(c.startswith(p['code'][:3]) for c in ix[r['cp']]['codes']) for r in records for p in r['paths'])
    report={'version':VERSION,'date':'2026-10-22','sourceIndexSHA256':before[str((SOURCE/'发布核对索引.json').relative_to(PROJECT))],
            'definition':{'key':'o','position':4,'meaning':'中心','status':'independent-draft',
                          'function':'position.centre','condition':'第二位h分叉形族、第三位m单个真实交点；相对本路径主体中心，max(|dx|,|dy|)<0.12',
                          'meaningHumanAccepted':True,'letterHumanFrozen':False,'thresholdHumanFrozen':False,
                          'positive':'Y','negative':'T'},
            'ordinaryScanned':scanned,'forkRelatedCharacters':related,'baseCentreCharacters':len(rows),
            'stableCharacters':sum(r['stable'] for r in records),'unstableCharacters':sum(not r['stable'] for r in records),
            'newCharacterCodePairs':sum(len(r['paths']) for r in records),'codeCounts':counts,
            'newPreferredCharacters':sum(bool(r['preferredCodes']) for r in records),
            'previous101Stable':len(kept_gap),'previous101NewPreferred':sum(bool(r['preferredCodes']) and r['inPrevious101'] for r in records),
            'previous101Unresolved':[{'cp':r['cp'],'char':r['char'],'reason':'本路径主体或交点未通过完整九扰动恢复'}
                                     for r in records if r['inPrevious101'] and not r['stable']],
            'frozen418Preserved':True,'noExistingCodesRemoved':True,'oneToThreePrefixMembershipsUnchanged':True,
            'otherFamiliesCentralMeasuredOnly':len(other_central),'records':records,'protectedHashes':before,
            'priorChvcSHA256':hashlib.sha256(CHVC.read_bytes()).hexdigest(),'runtimeDeployed':False,
            'scope':'independent additive overlay; only family h + object m; all other centre objects not bound',
            'limitations':['阈值0.12与o字母均为独立试验；九扰动仅限同一锁定字体。',
                           '正证据证明局部交点，不自动确认整字主形族；局部入口不升级成整字主族。',
                           '仅检查原已记录的分叉交点对象；未提取交点者仍待程序排查。',
                           '101字只是旧chvc子集；实际候选量按全体普通字符内本试验的完整新码统计。'],
            'sourceCodeSHA256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    save(OUTPUT/'中心属性交点试验.json',report)
    save(OUTPUT/'验收.json',{'passed':True,'frozen418Preserved':True,'all101AccountedFor':True,
                           'previous101Stable':len(kept_gap),'previous101Unresolved':len(central_gap-kept_gap),
                           'sourceProtected':True,'oneToThreePrefixesUnchanged':True,'runtimeDeployed':False})
    print({k:v for k,v in report.items() if k not in ('records','protectedHashes','definition','limitations')},flush=True)
    return report


if __name__=='__main__':build()
