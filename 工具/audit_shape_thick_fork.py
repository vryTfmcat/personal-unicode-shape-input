"""Fresh fixed-cohort verification of the guarded thick-fork correction."""
from collections import Counter
import hashlib
from pathlib import Path

from audit_shape_historical_buckets import SOURCE, PROJECT, load, protect
from build_shape_keyboard_full import save
from shape_experiment_features import observe,render
from shape_experiment_rules import position
from shape_recovery_geometry import visible_fork

OUTPUT=SOURCE.parent/'20261022-thick-fork-repair-v1'
BASE=SOURCE.parent/'20261022-chvc-structure-trial-v1/chvc结构细分与优先级试验.json'
CENTRE=SOURCE.parent/'20261022-centre-position-trial-v1/中心属性交点试验.json'


def proofs(f):
    box=f['bbox'];span=max(box[2]-box[0],box[3]-box[1]);out=[]
    for i,j in enumerate(f['junctionObjects']):
        p=visible_fork(f,j,(3,4))
        if p:
            out.append({'index':i,'positionKey':position((j['x0']+j['x1']-box[0]-box[2])/(2*span),
                                                        (j['y0']+j['y1']-box[1]-box[3])/(2*span),0,0),**p})
    return out


def build():
    if (OUTPUT/'粗笔分叉误拒复核.json').exists():raise FileExistsError('不覆盖既有粗笔复核')
    before=protect();base=load(BASE);fingerprints={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE,CENTRE)}
    fonts={};records=[]
    for n,r in enumerate(base['records']):
        variants=[]
        for previous in r['checks']:
            size,weight=previous['size'],previous['weight']
            f=observe(*render(r['char'],r['font']['path'],r['font'].get('index',0),size=size,weight=weight,fonts=fonts))
            assert f['bbox']==previous['bodyBBox'],(r['cp'],size,weight,'原锁定主体发生变化')
            current=proofs(f)
            for old in previous['visibleForks']:
                assert any(all(p.get(k)==v for k,v in old.items()) for p in current),(r['cp'],size,weight,'丢失旧正证据')
            variants.append({'size':size,'weight':weight,'beforeSupported':bool(previous['visibleForks']),
                             'afterSupported':bool(current),'proofs':current,
                             'newThickProofs':sum('thickStrokeConcavityProof' in p for p in current)})
        old_count=sum(v['beforeSupported'] for v in variants);new_count=sum(v['afterSupported'] for v in variants)
        assert old_count==r['forkPositiveVariants'] and new_count>=old_count
        records.append({k:r[k] for k in ('cp','char','font','preview')} | {
            'beforePositiveVariants':old_count,'afterPositiveVariants':new_count,
            'newlyStable':old_count<9 and new_count==9,'improved':new_count>old_count,
            'variants':variants,'oldPreferencesChanged':False})
        if (n+1)%200==0:
            save(OUTPUT/'观测检查点.json',{'records':records,'sourceSHA256':fingerprints})
            print(f'粗笔复核 {n+1}/1562',flush=True)
    assert before==protect()
    assert fingerprints=={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE,CENTRE)}
    stats={'cohort':len(records),'stableBefore':sum(r['beforePositiveVariants']==9 for r in records),
           'stableAfter':sum(r['afterPositiveVariants']==9 for r in records),
           'newlyStable':sum(r['newlyStable'] for r in records),'improvedCharacters':sum(r['improved'] for r in records),
           'remainingUnstable':sum(r['afterPositiveVariants']<9 for r in records),
           'neverSupportedAfter':sum(r['afterPositiveVariants']==0 for r in records),
           'newlySupportedCharacterVariants':sum(r['afterPositiveVariants']-r['beforePositiveVariants'] for r in records)}
    assert len(records)==1562 and stats['stableBefore']==620
    t=next(r for r in records if r['char']=='T');assert t['afterPositiveVariants']==9
    report={'version':'thick-fork-concavity-repair-20261022-v1','date':'2026-10-22',
            'sourceIndexSHA256':before[str((SOURCE/'发布核对索引.json').relative_to(PROJECT))],
            'statistics':stats,'afterVariantDistribution':dict(Counter(str(r['afterPositiveVariants']) for r in records)),
            'records':records,'allOldPositiveEvidenceRetained':True,'protectedHashes':before,
            'sourceSHA256':fingerprints,'geometryCodeSHA256':hashlib.sha256((PROJECT/'工具/shape_recovery_geometry.py').read_bytes()).hexdigest(),
            'auditCodeSHA256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'fix':'保留原双环带出口条件；密度超过0.72时，另要求交点同一连通墨块的出口数量一致及局部凸包可见缺口至少6%。',
            'scope':'只修复粗笔正证据检验；未改字形主桶、全部已有路径、418及162字首选或中心码成员。',
            'runtimeDeployed':False,'candidateCodesChanged':False,'pictorialAllocationChanged':False,
            'limitations':['九扰动支持只证明局部交点，不等于整字主族经人工确认。',
                           '未解决的短支臂、半径选择、交点匹配及连体主体分离问题仍保留，不批量判错。',
                           '原始兼容chvc仍为1562候选；本次支持数增加不是重码人数减少。']}
    save(OUTPUT/'粗笔分叉误拒复核.json',report)
    save(OUTPUT/'验收.json',{'passed':True,'allOldPositiveEvidenceRetained':True,'fixedCohort':1562,
                           'TStableAfter':9,'protectedInputsUnchanged':True,'runtimeDeployed':False})
    print(stats,flush=True)
    return report


if __name__=='__main__':build()
