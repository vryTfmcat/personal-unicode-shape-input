"""Reproduce the scoped p-boundary revision from the unique manual acceptance.

Default only compares. --output-dir emits an isolated candidate, never switches
the active runtime. No new family membership or counts are inferred.
"""
import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'原型/键位编辑器'))
import shape_structure_bindings as binding


def build(output_dir=None):
    manual=json.loads((PROJECT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    acceptance=manual['pFamilyBoundaryAcceptance20261025Batch1']
    config=acceptance['generation'];base=PROJECT/config['baseReport']
    assert base.resolve().is_relative_to(PROJECT.resolve())
    assert hashlib.sha256(base.read_bytes()).hexdigest()==config['baseSHA256']
    original=json.loads(base.read_text(encoding='utf-8'));d=copy.deepcopy(original)
    index={r['cp']:r for r in d['records']}
    withdrawals={int(cp):a for cp,a in acceptance['decisions'].items() if a['action']=='withdraw-p-whole-counts'}
    assert set(withdrawals)=={ord(ch) for ch in config['withdrawWholePCharacters']}=={ord('ρ'),ord('ộ')}
    diff=[]
    for cp,a in withdrawals.items():
        row=index[cp];removed=[c for c in row['codes'] if c[1]=='p']
        assert removed and row['eligible']
        row['codes']=[c for c in row['codes'] if c not in removed]
        row['assignments']=[item for item in row['assignments'] if item['code'] not in removed]
        row['withdrawnPWholeCodes']=removed
        row['reviewResolution']='confirmed-subject-separate-from-whole-p-counts'
        row['pFamilyBoundaryReview']=copy.deepcopy(a)
        row['scopeRejections'].append(dict(prefix='ep',reasons=[a['note']]))
        diff.append(dict(cp=cp,char=chr(cp),removedStructuralCodes=removed,oldCodes=row['oldCodes'],oldPreferredCodes=row['oldPreferredCodes']))
    assert sum(len(r['removedStructuralCodes']) for r in diff)==5
    members=defaultdict(set)
    for row in d['records']:
        for code in row['codes']:members[code].add(row['cp'])
    d.update(version=config['targetVersion'],createdAt=config['createdAt'],
        baseReportSHA256=config['baseSHA256'],authorization=acceptance['userResponseRaw'],
        pFamilyBoundaryReview=copy.deepcopy(acceptance),
        codeMembers={c:sorted(cps) for c,cps in sorted(members.items())})
    s=d['statistics'];s.update(assigned=sum(bool(r['codes']) for r in d['records']),pending=sum(not r['codes'] for r in d['records']),
        reviewedRetained=sum(not r['codes'] and bool(r.get('reviewResolution')) for r in d['records']),
        wholeScopePending=sum(r['eligible'] and not r['codes'] and not r.get('reviewResolution') for r in d['records']),
        newCodes=len(members),newCharacterCodePairs=sum(len(r['codes']) for r in d['records']),
        pBoundaryReviewedCharacters=8,pBoundaryDeferredCharacters=3,pBoundaryWithdrawnPaths=5)
    assert (s['assigned'],s['reviewedRetained'],s['wholeScopePending'],s['newCodes'],s['newCharacterCodePairs'])==(1518,3,2083,122,3230)
    for group in d['groups']:
        cps=[r['cp'] for r in group['recommendations']];recommendations=[]
        for cp in cps:
            options=[c for c in index[cp]['codes'] if c[:2]==group['code'][:2]]
            best=min(options,key=lambda c:(len(members[c]),c)) if options else None
            recommendations.append(dict(cp=cp,code=best if best and len(members[best])<len(cps) else group['code'],
                burden=min(len(members[best]),len(cps)) if best else len(cps)))
        group.update(recommendations=recommendations,pending=sum(not any(c[:2]==group['code'][:2] for c in index[cp]['codes']) for cp in cps),
            withBetterRoute=sum(r['code']!=group['code'] for r in recommendations),
            maxRecommendedBurden=max(r['burden'] for r in recommendations),
            medianRecommendedBurden=sorted(r['burden'] for r in recommendations)[len(cps)//2])
    old_index={r['cp']:r for r in original['records']}
    assert all(r==old_index[r['cp']] for r in d['records'] if r['cp'] not in withdrawals)
    assert d['codeMembers']['ajqu']==original['codeMembers']['ajqu']
    runtime={k:d[k] for k in ('version','active','runtimeDeployed','sourceIndexSHA256','definitions','statistics','codeMembers','acceptedBoundary','pFamilyBoundaryReview')}
    runtime['records']=[{k:r[k] for k in ('cp','codes','assignments')} for r in d['records'] if r['codes']]
    if output_dir:
        out=Path(output_dir).resolve()
        if out in (binding.PATH.parent.resolve(),binding.active_report_path().parent.resolve()) or (out/'大组结构键位分配.json').exists():
            raise ValueError('候选不能覆盖当前运行目录或现行报告')
        out.mkdir(parents=True,exist_ok=True)
        for name,value in [('大组结构键位分配.json',d),('structure-count-bindings.json',runtime),
                           ('p族首批确认与差异.json',dict(acceptance=acceptance,diff=diff,addedCodes=[],membershipsNotExpanded=True))]:
            (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        audit=json.loads((base.parent/'p族86字边界核查.json').read_text(encoding='utf-8'))
        scope=json.loads((base.parent/'范围待核2083字续查分流.json').read_text(encoding='utf-8'))
        payload=dict(audit=audit,scope={k:v for k,v in scope.items() if k not in ('records','protectedHashes')},
                     acceptance=acceptance,currentVersion=d['version'])
        template=Path(__file__).with_name('p_family_scope_review_template.html').read_text(encoding='utf-8')
        (out/'p-family-scope-review.html').write_text(template.replace('__DATA__',json.dumps(payload,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
    else:
        historical=d['version']!=binding.data()['version']
        if historical:
            frozen=list((PROJECT/'数据/三模式/规则库/四键实验/键位试验').glob('*-'+d['version']+'/大组结构键位分配.json'))
            assert len(frozen)==1 and d==json.loads(frozen[0].read_text(encoding='utf-8')),'历史v5报告不可复现'
        else:
            assert d==binding.review_report(),'当前报告不可从确认源复现'
            assert runtime=={k:v for k,v in binding.data().items() if k!='byCp'},'运行数据不可复现'
    print(json.dumps(dict(passed=True,version=d['version'],historicalBaseline=d['version']!=binding.data()['version'],removedPaths=5,addedPaths=0,source='人工审议.json',runtimeWritten=False),ensure_ascii=False))
    return d,runtime


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir')
    args=parser.parse_args();build(args.output_dir)
