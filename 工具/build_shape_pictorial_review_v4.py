"""Apply the explicit 24 floral / 4 rocket / 20 excluded ornamental partition."""
import copy
import json
from collections import Counter

from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_pictorial_review_v3 import OUT as V3
from build_shape_keyboard_full import save

VERSION='pictorial-intake-20261022-v4'
OUT=V3.parent/'20261022-pictorial-intake-review-v4'
SNAPSHOT=V3/'人工审核保存/网页审核原始结果-f0e17886e5206393423b117f1a5ec89fbfe8076b67f1805b3298ce6927035aa0.json'
FLORAL=set(range(0x1F650,0x1F668))
ROCKETS=set(range(0x1F66C,0x1F670))
EXCLUDED=set(range(0x1F668,0x1F66C))|set(range(0x1F670,0x1F680))


def build():
    if OUT.exists():raise FileExistsError('不覆盖已有v4核对稿')
    before=protect();previous=read(V3/'拟物收入全量初稿.json')
    assert sha(SNAPSHOT)=='f0e17886e5206393423b117f1a5ec89fbfe8076b67f1805b3298ce6927035aa0'
    snapshot=read(SNAPSHOT);result=copy.deepcopy(previous)
    result.update(version=VERSION,predecessorVersion=previous['version'],
        lineageVersions=previous['lineageVersions']+[VERSION],
        predecessorReportSHA256=sha(V3/'拟物收入全量初稿.json'),
        sourceReviewSnapshot=str(SNAPSHOT),sourceReviewSHA256=sha(SNAPSHOT),protectedHashes=before)
    rows={r['cp']:r for r in result['records']}
    decisions={str(r['cp']):dict(r) for r in snapshot['decisions']};confirmations={}
    for cps,decision,category,basis in (
        (FLORAL,'include','装饰','本人确认U+1F650—1F667花饰、叶饰、芽饰收入装饰'),
        (ROCKETS,'include','物品／火箭','本人确认四向火箭是物品火箭，不归装饰'),
        (EXCLUDED,'exclude','文字标点／抽象纹样','本人确认拼布方块、符号连字、标点及棋盘纹样等不属于t')):
        for cp in cps:
            old=decisions.get(str(cp),{})
            confirmations[str(cp)]={'decision':decision,'category':category,'basis':basis,
                'beforeDecision':old.get('decision','pending'),'beforeCategory':rows[cp]['category']}
            decisions[str(cp)]={'cp':cp,'char':chr(cp),'decision':decision,
                **({'note':old['note']} if 'note' in old else {})}
            rows[cp].update(category=category,decisionSource=basis,classificationStatus='本人按完整码段确认',
                confirmationKind='本轮48字明确分段确认',correctionReason=basis)
    q=result['reviewQueues'];q['decoration']={'label':'花饰／叶饰／芽饰','cps':sorted(FLORAL)}
    q['rockets']={'label':'物品／四向火箭','cps':sorted(ROCKETS)}
    q['ornamentalPartition']={'label':'花饰区块48字确认对照','cps':sorted(FLORAL|ROCKETS|EXCLUDED)}
    for r in rows.values():r['similarityTopics']=[k for k,v in q.items() if r['cp'] in v['cps']]
    result['reviewDecisions']=decisions;result['latestConfirmations']=confirmations
    result['latestChanges']=[{'cp':int(cp),'char':chr(int(cp)),**d} for cp,d in confirmations.items()]
    result['ornamentalBlockAcceptance']={'floralIncluded':sorted(FLORAL),'objectRocketsIncluded':sorted(ROCKETS),
        'excludedFromT':sorted(EXCLUDED),'completeBlockPartition':True,'all48IndividuallyCoveredByExplicitRanges':True}
    result['categoryReviewAcceptance']['ornamentalBlockPartition']=result['ornamentalBlockAcceptance']
    result['reviewSummary']['currentKnownCounts']=dict(Counter(d['decision'] for d in decisions.values()))
    result['reviewSummary']['latestDecisionChanges']=sum(d['beforeDecision']!=d['decision'] for d in confirmations.values())
    result['uiNotice']='v4已确认花饰区块48字：24字装饰、4字物品火箭、20字不收入t。其余专题仅确认范围者，仍保留未逐字审核状态。'
    assert len(FLORAL)==24 and len(ROCKETS)==4 and len(EXCLUDED)==20
    assert FLORAL|ROCKETS|EXCLUDED==set(range(0x1F650,0x1F680))
    assert all(decisions[str(d['cp'])]==d for d in snapshot['decisions'] if str(d['cp']) not in confirmations)
    assert all((r['oldBucket'],r['oldCodes'])==(o['oldBucket'],o['oldCodes']) for r,o in zip(result['records'],previous['records']))
    assert protect()==before
    save(OUT/'拟物收入全量初稿.json',result)
    save(OUT/'花饰区块48字确认.json',{'partition':result['ornamentalBlockAcceptance'],'confirmations':confirmations})
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in result.items() if k!='protectedHashes'})
    save(OUT/'验收.json',{'passed':True,'all48Accounted':True,'unrelatedDecisionsUnchanged':True,
        'protectedInputsUnchanged':protect()==before,'allocationChanged':False,'runtimeDeployed':False})
    print(json.dumps({'version':VERSION,'partition':{'floral':24,'rockets':4,'excluded':20},
        'knownDecisions':result['reviewSummary']['currentKnownCounts']},ensure_ascii=False))
    return result


if __name__=='__main__':build()
