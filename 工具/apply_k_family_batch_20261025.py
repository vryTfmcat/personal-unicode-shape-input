"""Reproduce only the four accepted k-family additions from frozen v5 evidence."""
import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'原型/键位编辑器'),str(ROOT/'工具')]
FIELDS={'a':('corners','整字角点集'),'b':('forks','整字三叉点集'),'g':('crosses','整字四叉点集'),
        'j':('straightStrokes','整字直连续笔集'),'q':('curveStrokes','整字曲连续笔集')}
VALUES={1:'u',2:'b',3:'t',4:'y',5:'p'}


def build(output_dir=None,batch=None):
    import shape_structure_bindings as binding
    manual=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    batch=batch or (2 if binding.data()['version'] in ('structure-count-bindings-v7','structure-count-bindings-v8') else 1)
    assert batch in (1,2)
    acceptance=manual['kFamilyScopeAcceptance20261025Batch'+str(batch)];g=acceptance['generation']
    base=ROOT/g['baseReport'];candidate=ROOT/g['candidateReport']
    for p,h in [(base,g['baseSHA256']),(candidate,g['candidateSHA256'])]:
        assert p.resolve().is_relative_to(ROOT.resolve())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==h
    original=json.loads(base.read_text(encoding='utf-8'));d=copy.deepcopy(original)
    proposal=json.loads(candidate.read_text(encoding='utf-8'));by={r['cp']:r for r in d['records']}
    decisions=acceptance['decisions'];assert set(decisions)=={str(ord(ch)) for ch in ('ĎḊḎḒ' if batch==1 else 'ᴰⅮＤ𝗗')}
    for cp,a in decisions.items():
        r=by[int(cp)];p=next(x for x in proposal['batch'] if x['cp']==int(cp))
        assert a['humanConfirmed'] and a['scope']=='whole-glyph' and a['prefix']=='ik'
        assert r['eligible'] and r['status']=='stable' and not r['codes'] and r['statistics']['loops']>0
        assert r['statistics']==p.get('wholeStatistics',p.get('statistics'))
        assignments=[]
        for key,(field,meaning) in FIELDS.items():
            n=r['statistics'][field]
            if n:assignments.append(dict(code='ik'+key+VALUES[min(n,5)],feature=field,meaning=meaning,count=n,
                objectId='whole-glyph-collection:'+field,scope='本人确认的整字有孔复合形族；计数复用v5九扰动整字观测',
                variants=9,humanScopeConfirmed=True,humanCountConfirmed=False))
        assert {x['code'] for x in assignments}==set(p.get('kWholeGlyphProposal',p.get('newCodes')))
        r.update(acceptedBoundary=copy.deepcopy(a),previousScopeRejections=copy.deepcopy(r['scopeRejections']),
            codes=sorted(x['code'] for x in assignments),assignments=assignments,scopeRejections=[],
            reviewResolution='confirmed-whole-glyph-k-family')
        d['acceptedBoundary'][cp]=copy.deepcopy(a)
    members=defaultdict(set)
    for r in d['records']:
        for c in r['codes']:members[c].add(r['cp'])
    d.update(version=g['targetVersion'],createdAt=g['createdAt'],baseReportSHA256=g['baseSHA256'],
             authorization=acceptance['userResponseRaw'],
             codeMembers={c:sorted(cps) for c,cps in sorted(members.items())})
    d['kFamilyScopeAcceptance' if batch==1 else 'kFamilyScopeAcceptanceBatch2']=copy.deepcopy(acceptance)
    s=d['statistics'];s.update(assigned=sum(bool(r['codes']) for r in d['records']),
        pending=sum(not r['codes'] for r in d['records']),
        wholeScopePending=sum(r['eligible'] and not r['codes'] and not r.get('reviewResolution') for r in d['records']),
        newCodes=len(members),newCharacterCodePairs=sum(len(r['codes']) for r in d['records']),
        scopeAcceptedCharacters=7+4*batch,scopeNewlyAssignedCharacters=6+4*batch,scopeAddedPaths=18+12*batch,kBatchAssigned=4,kBatchAddedPaths=12)
    assert (s['assigned'],s['wholeScopePending'],s['newCodes'],s['newCharacterCodePairs'])==(1518+4*batch,2083-4*batch,125,3230+12*batch)
    for group in d['groups']:
        cps=[r['cp'] for r in group['recommendations']];recs=[]
        for cp in cps:
            options=[c for c in by[cp]['codes'] if c[:2]==group['code'][:2]]
            best=min(options,key=lambda c:(len(members[c]),c)) if options else None
            recs.append(dict(cp=cp,code=best if best and len(members[best])<len(cps) else group['code'],
                             burden=min(len(members[best]),len(cps)) if best else len(cps)))
        group.update(recommendations=recs,pending=sum(not any(c[:2]==group['code'][:2] for c in by[cp]['codes']) for cp in cps),
            withBetterRoute=sum(x['code']!=group['code'] for x in recs),maxRecommendedBurden=max(x['burden'] for x in recs),
            medianRecommendedBurden=sorted(x['burden'] for x in recs)[len(cps)//2])
    previous={r['cp']:r for r in original['records']}
    assert all(r==previous[r['cp']] for r in d['records'] if str(r['cp']) not in decisions)
    runtime={k:d[k] for k in ('version','active','runtimeDeployed','sourceIndexSHA256','definitions','statistics',
                            'codeMembers','acceptedBoundary','pFamilyBoundaryReview','kFamilyScopeAcceptance')}
    if batch==2:runtime['kFamilyScopeAcceptanceBatch2']=d['kFamilyScopeAcceptanceBatch2']
    runtime['records']=[{k:r[k] for k in ('cp','codes','assignments')} for r in d['records'] if r['codes']]
    if output_dir:
        out=Path(output_dir).resolve()
        if out==binding.PATH.parent.resolve() or (out/'大组结构键位分配.json').exists():
            raise ValueError('仅向新的独立目录输出，不覆盖运行数据或冻结报告')
        out.mkdir(parents=True,exist_ok=True)
        for name,obj in [('大组结构键位分配.json',d),('structure-count-bindings.json',runtime)]:
            (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        if d['version']==binding.data()['version']:
            assert d==binding.review_report()
            assert runtime=={k:v for k,v in binding.data().items() if k!='byCp'}
        else:
            frozen=list((ROOT/'数据/三模式/规则库/四键实验/键位试验').glob('*-'+d['version']+'/大组结构键位分配.json'))
            assert len(frozen)==1 and d==json.loads(frozen[0].read_text(encoding='utf-8'))
    print(json.dumps(dict(passed=True,version=d['version'],historicalBaseline=d['version']!=binding.data()['version'],newScope=4,addedPaths=12,runtimeWritten=False),ensure_ascii=False))
    return d,runtime


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir');p.add_argument('--batch',type=int,choices=[1,2]);args=p.parse_args();build(args.output_dir,args.batch)
