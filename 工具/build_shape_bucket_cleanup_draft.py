"""Clear retained primary buckets in an isolated overlay, keeping legacy lookup intact."""
import argparse
from collections import Counter,defaultdict
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from audit_shape_historical_buckets import SOURCE,DEFAULT_OUTPUT as PILOT,protect,load
from build_shape_keyboard_full import expand,save,legacy_facts
from shape_experiment_features import observe,render
from shape_keyboard_trial import outline_anchors,trial_facts,group_object
from shape_reviewed_routes import amend,references

OUTPUT=SOURCE.parent/'20261022-historical-buckets-cleanup-draft-v1'
KEYS='tujvbg'
VERSION='historical-bucket-cleanup-overlay-20261022-v1'


def observations(row,f,index,anchors,templates):
    routes,_,_,changes=amend(copy.deepcopy(row),f,index['bucketGroups'],anchors,templates)
    paths,objects={},{}
    for route in routes:
        route=copy.deepcopy(route)
        facts=route.get('reviewedObjectFacts')
        if facts is None:
            facts=trial_facts(f,route['familyKey'],anchors) if route.get('newGeometryBasis') else legacy_facts(row,route)
        route['target']='cleanup-'+route['target']
        route['draftOnly']=True
        expand(route,facts,index['definitions'],paths,objects)
    return list(paths.values()),list(objects.values()),[dict(r,target='cleanup-'+r['target'],draftOnly=True) for r in routes],changes


def evidence_keys(paths,objects):
    lookup={o['id']:o for o in objects}; result={}
    for path in paths:
        for e in path['evidence']:
            obj=lookup.get(e['objectId'],{})
            result[(path['code'],e['rule'],e['familyTarget'],e['objectId'])]=obj.get('bbox')
    return result


def recover(row,index,anchors,templates,fonts,pilot):
    def view(size=96,weight=0):
        return observe(*render(row['char'],row['font']['path'],row['font'].get('index',0),size=size,weight=weight,fonts=fonts))
    f=view(); paths,objects,routes,changes=observations(row,f,index,anchors,templates)
    # Independently verified whole triangles must not depend on an old primary-family gate.
    whole=pilot['existingFamilyProbe']
    if whole and whole['stable']:
        route={'bucket':whole['proposedBucket'],'familyKey':whole['family'],
               'familyId':index['definitions']['families'][whole['family']]['id'],
               'target':'cleanup-recovered-whole','draftOnly':True}
        out={p['code']:p for p in paths};obj={o['id']:o for o in objects}
        expand(route,trial_facts(f,whole['family'],anchors),index['definitions'],out,obj)
        paths,objects=list(out.values()),list(obj.values());routes.append(route)
    base=evidence_keys(paths,objects); survivors=set(base); checks=[]
    if base:
        for size in (48,96,128):
            for weight in (-1,0,1):
                try:
                    vf=view(size,weight); vp,vo,_,_=observations(row,vf,index,anchors,templates)
                    if whole and whole['stable']:
                        out={p['code']:p for p in vp};obj={o['id']:o for o in vo}
                        expand(route,trial_facts(vf,whole['family'],anchors),index['definitions'],out,obj)
                        vp,vo=list(out.values()),list(obj.values())
                    current=evidence_keys(vp,vo)
                    good=set()
                    for key,box in base.items():
                        if key not in current:continue
                        other=current[key]
                        if box is None or other is None:
                            if box==other:good.add(key)
                        elif max(abs(a-b) for a,b in zip(box,other))<=5:
                            good.add(key)
                    survivors &= good
                    checks.append({'size':size,'weight':weight,'matchingEvidence':len(good)})
                except (OSError,ValueError) as error:
                    survivors.clear();checks.append({'size':size,'weight':weight,'error':str(error)})
    stable=[]
    for p in paths:
        e=[e for e in p['evidence'] if (p['code'],e['rule'],e['familyTarget'],e['objectId']) in survivors]
        if e:stable.append(dict(p,evidence=e,preferred=False,draftOnly=True))
    used={e['objectId'] for p in stable for e in p['evidence']}
    objects=[o for o in objects if o['id'] in used]
    used_targets={e['familyTarget'] for p in stable for e in p['evidence']}
    routes=[r for r in routes if r['target'] in used_targets]
    if pilot['cp'] in load_pilot()['trials']['u']['cps']:
        # The count is ink pieces, not the six layer count; no invented fourth-key 'six'.
        obj=group_object(f);obj['arrangement']='i';obj['memberOrientation']='h'
        route={'bucket':'u','familyKey':'l','familyId':'family.line','target':'cleanup-layer-group',
               'draftOnly':True,'supplementOnly':False,'componentEvidence':{'source':'all-original-separated-line-ink'}}
        facts=[{'third':'k','function':'topology.separated','object':obj,
                'reason':'原墨迹分离线层组；六层不虚构新的数量字母','status':'independent-draft'}]
        out={p['code']:p for p in stable};objs={o['id']:o for o in objects}
        expand(route,facts,index['definitions'],out,objs)
        stable=[p for code,p in out.items() if not code.startswith('ulk') or code=='ulki']
        objects=list(objs.values());routes.append(route)
    return {'paths':stable,'objects':objects,'familyRoutes':routes,'recoveryChanges':changes,
            'stabilityChecks':checks,'baseProposedPaths':len(paths),'retainedStablePaths':len(stable)}


_PILOT=None
def load_pilot():
    global _PILOT
    if _PILOT is None:_PILOT=load(PILOT/'历史桶整理与新用途试验.json')
    return _PILOT


def build(output=OUTPUT):
    if output.exists():raise FileExistsError('不覆盖已有独立草案，请选择新的输出目录')
    before=protect();index=load(SOURCE/'发布核对索引.json');pilot=load_pilot()
    selected={r['cp']:r for r in pilot['records']};lookup={}
    for file in sorted((SOURCE/'details').glob('*.json')):
        for row in load(file)['records']:
            if row['cp'] in selected:lookup[row['cp']]=row
    anchors=outline_anchors(Path('C:/Windows/Fonts/seguisym.ttf'))
    templates=references(Path('C:/Windows/Fonts/seguisym.ttf'));fonts={};records=[]
    for n,(cp,row) in enumerate(lookup.items()):
        p=selected[cp]; result=recover(row,index,anchors,templates,fonts,p)
        new_bucket=None;family=None;basis='证据不足，进入待定主桶队列；旧码在兼容视图保留'
        if cp in pilot['trials']['u']['cps']:
            new_bucket,family,basis='u','l','独立试用：完整规则线群／层列'
        elif cp in pilot['trials']['v']['cps']:
            new_bucket,basis='v','独立试用：九扰动稳定的台阶块面；第二位未定，不猜造后续键'
        elif p['existingFamilyProbe'] and p['existingFamilyProbe']['stable']:
            whole=p['existingFamilyProbe'];new_bucket,family,basis=whole['proposedBucket'],whole['family'],'九扰动一致的完整主体原型'
        old_codes={q['code'] for q in row['paths']}
        new_codes={q['code'] for q in result['paths']}-old_codes
        records.append(dict(result,cp=cp,char=row['char'],oldBucket=row['bucket'],
                            draftBucket=new_bucket,draftFamily=family,allocationBasis=basis,
                            historicalFirstKeyConfirmed=bool(row.get('oldReviewed')),
                            historicalConfirmationMigrated=False,legacyFirstAlias=row['bucket'],
                            oldCodes=sorted(old_codes),newCodes=sorted(new_codes),
                            primaryPending=new_bucket is None,originalPathsPreserved=True))
        if (n+1)%40==0:print(f'对象与路径复核 {n+1}/443',flush=True)
    assert before==protect()
    active=Counter();old=Counter();pending=0
    for row in index['records']:
        old[row['bucket']]+=1
    for r in records:
        if r['draftBucket']:active[r['draftBucket']]+=1
        else:pending+=1
    assert len(records)==443 and sum(active.values())+pending==443
    assert not any(r['draftBucket'] in set('bgjt') for r in records)
    report={'version':VERSION,'date':'2026-10-22','source':index['id'],
            'sourceIndexSHA256':hashlib.sha256((SOURCE/'发布核对索引.json').read_bytes()).hexdigest(),
            'status':'independent-primary-allocation-and-supplement-overlay-not-full-rebuild',
            'authorization':{'userStatement':'好的，你继续核对吧，把旧桶清空看看怎么分配新键位',
                             'priorCandidateAcceptance':'其他都可以；按已展示42线群、1稳定块面、4三角形候选查找方向处理',
                             'scope':'只在独立草案清空历史分桶；未授权部署或迁移人工确认'},
            'total':443,'legacyBuckets':dict(Counter(r['oldBucket'] for r in records)),
            'allocated':dict(active),'pendingPrimary':pending,'releasedFirstKeys':list('bgjt'),
            'firstKeyProposals':{'u':{'meaning':'线群／层列','count':active['u'],'status':'independent-draft'},
                                 'v':{'meaning':'台阶实心块面','count':active['v'],'status':'narrow-independent-draft'}},
            'recoveredCharacters':sum(bool(r['newCodes']) for r in records),
            'newCharacterCodePairs':sum(len(r['newCodes']) for r in records),
            'withAnyPathsAfter':sum(bool(r['oldCodes'] or r['newCodes']) for r in records),
            'withAnyPathsBefore':sum(bool(r['oldCodes']) for r in records),
            'historicalFirstConfirmationsPreserved':sum(r['historicalFirstKeyConfirmed'] for r in records),
            'pendingWithReliableSupplement':sum(r['primaryPending'] and bool(r['oldCodes'] or r['newCodes']) for r in records),
            'protectedInputsUnchanged':True,'protectedHashes':before,'records':records,
            'runtimeDeployed':False,'activeIndexChanged':False,'fullGeneratorChanged':False,
            'limitations':['清空仅指独立草案的旧第一位归属；原v14与部署版不改动。',
                           '待定主桶不等于所有路径丢失，有可靠局部入口的仍可查找。',
                           'u仅推广本次42字，不把所有平行线现有入口自动迁移。',
                           'v只保留本轮1个稳定块面，第二位与四码未定，不把7个不稳定样本收进来。',
                           '尚未覆盖所有Unicode形族或全量重建。']}
    save(output/'旧桶清空与新键位草案.json',report)
    save(output/'验收.json',{'passed':True,'oldBucketsClearedInDraft':True,'identitiesPreserved':443,
                           'legacyFirstAliasesPreserved':443,'historicalConfirmationsPreserved':10,
                           'originalSourceUnchanged':True,'runtimeDeployed':False})
    print(json.dumps({k:report[k] for k in ('total','allocated','pendingPrimary','releasedFirstKeys','recoveredCharacters',
                                          'newCharacterCodePairs','withAnyPathsAfter','pendingWithReliableSupplement')},ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUTPUT)
    build(parser.parse_args().output)
