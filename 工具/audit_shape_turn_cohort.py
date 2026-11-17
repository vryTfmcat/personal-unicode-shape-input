"""Same-current-chvc cohort diagnostic; graph signatures are NOT input codes."""
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from audit_shape_historical_buckets import protect
from build_shape_turn_samples import PROJECT, sha
from shape_stroke_topology_trial import analyze, render_locked, VERSION

sys.path.insert(0,str(PROJECT/'原型/键位编辑器'))
import shape_overview as overview

OUTPUT=overview.RUNS/'20261024-turn-junction-samples-v2'
FEATURES=('corners','forks','crosses','straightSegments','curveSegments')


def partition(records,fields):
    groups=defaultdict(list)
    for r in records:
        # Preserve every uncertain/unobservable character in one explicit fallback.
        signature=tuple(r['statistics'][k] for k in fields) if r['stableAcrossThreeSizes'] else ('未稳定／保留原入口',)
        groups[signature].append(r['cp'])
    sizes=sorted(len(members) for members in groups.values() for _ in members)
    return dict(fields=list(fields),cohort=len(records),groups=len(groups),
                medianCharacterGroup=median(sizes),p90CharacterGroup=sizes[math.ceil(.9*len(sizes))-1],
                maximumGroup=max(sizes),inGroupsAtMost20=sum(v<=20 for v in sizes),
                largestGroups=[dict(signature=list(k),count=len(v),cps=v) for k,v in sorted(groups.items(),key=lambda kv:-len(kv[1]))[:12]],
                scope='联合结构特征诊断；尚非可输入的四码候选，不能计作正式降重')


def observe_character(job):
    cp,font,codes=job
    variants=[];baseline=None;errors=[]
    for size in (96,192,256):
        try:
            result=analyze(render_locked(chr(cp),font,size=size))
            variants.append(dict(size=size,statistics=result['statistics']))
            if size==192:baseline=result
        except (ValueError,IndexError,KeyError) as error:
            errors.append(dict(size=size,error=str(error)));variants.append(dict(size=size,statistics=None))
    stable=not errors and len({json.dumps(v['statistics'],sort_keys=True) for v in variants})==1
    return dict(cp=cp,char=chr(cp),font=font,variants=variants,
                statistics=baseline['statistics'] if baseline else None,
                stableAcrossThreeSizes=stable,errors=errors,originalCodes=codes,
                corners=baseline['corners'] if baseline else [],
                junctions=baseline['junctions'] if baseline else [],
                prunedSpurCount=baseline['prunedSpurCount'] if baseline else None)


def build():
    target=OUTPUT/'当前chvc全组结构比较.json'
    if target.exists():raise FileExistsError('禁止覆盖既有全组比较')
    before=protect()
    files=[PROJECT/'原型/键位编辑器'/name for name in
           ('shape_overview.py','shape-key-overview.js','shape-key-overview.html','data/pictorial-exclusive-allocation.json')]
    files += [Path(__file__),PROJECT/'工具/shape_stroke_topology_trial.py']
    fingerprints={str(p.relative_to(PROJECT)):sha(p) for p in files}
    o=overview.Overview();cohort=set(o.allocation_members('chvc'));intake=set(overview.exclusive_intake())
    assert not cohort&intake
    assert len(cohort)==1554, '现行集合变化，先核对新基线'
    baseline_members={cp:list(o.brief(cp,True)['codes']) for cp in cohort}
    records=[]
    jobs=[(cp,o.detail(cp,True)['font'],baseline_members[cp]) for cp in sorted(cohort)]
    with ProcessPoolExecutor(max_workers=4) as executor:
        for number,record in enumerate(executor.map(observe_character,jobs),1):
            records.append(record)
            if number%150==0:
                print(f'同集合结构比较 {number}/{len(cohort)}',flush=True)
                (OUTPUT/'全组比较检查点.json').write_text(json.dumps(dict(records=records,sourceHashes=fingerprints),ensure_ascii=False),encoding='utf-8')
    assert before==protect()
    assert fingerprints=={str(p.relative_to(PROJECT)):sha(p) for p in files}
    assert cohort==set(o.allocation_members('chvc'))
    assert baseline_members=={cp:list(o.brief(cp,True)['codes']) for cp in cohort}
    assert not {r['cp'] for r in records}&intake
    stats=dict(cohort=len(cohort),stableThreeSizes=sum(r['stableAcrossThreeSizes'] for r in records),
               unstableThreeSizes=sum(not r['stableAcrossThreeSizes'] for r in records),
               charactersWithError=sum(bool(r['errors']) for r in records),
               baselineWithCorners=sum(bool(r['statistics'] and r['statistics']['corners']) for r in records),
               baselineWithCross=sum(bool(r['statistics'] and r['statistics']['crosses']) for r in records),
               baselineWithCurves=sum(bool(r['statistics'] and r['statistics']['curveSegments']) for r in records))
    comparisons={k:partition(records,[k]) for k in FEATURES}
    comparisons['joint']=partition(records,FEATURES)
    report=dict(version=VERSION,runTime=datetime.now().astimezone().isoformat(),statistics=stats,
                records=records,comparisons=comparisons,protectedHashes=before,sourceHashes=fingerprints,
                currentCandidateCountBefore=1554,currentCandidateCountAfter=1554,
                codesAdded=0,codesRemoved=0,tBReentry=0,newBindings=False,runtimeIntegrated=False,
                scope='现行排他集合的三字号观测比较；稳定是机器重复性，不代表结构正确或人工确认',
                limitations=['七例是参与开发的校准样本，不能用其通过率估计1554字准确率。',
                             '曲端修剪可能误伤真实短支，本轮只作观测而不撤销任何原有码。',
                             '复合字的分叉数、交叉数、折角数和直曲段数的组合尚未落实为四键内规则。'])
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(statistics=stats,joint={k:v for k,v in comparisons['joint'].items() if k!='largestGroups'}),ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':build()
