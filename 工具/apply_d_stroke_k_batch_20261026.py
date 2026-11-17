"""Reproduce only Đ's three accepted whole-glyph routes; never infer a q route."""
import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'原型/键位编辑器'),str(ROOT/'工具')]

def build(output_dir=None):
    import shape_structure_bindings as binding
    manual=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    a=manual['dStrokeKScopeAcceptance20261026'];g=a['generation']
    assert a['decision']=='accepted' and set(a['decisions'])=={'272'}
    for rel,h in [(g['baseReport'],g['baseSHA256']),(a['candidateReport'],a['candidateSHA256'])]:
        p=(ROOT/rel).resolve();assert p.is_relative_to(ROOT.resolve())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==h,rel
    original=json.loads((ROOT/g['baseReport']).read_text(encoding='utf-8'))
    proposal=json.loads((ROOT/a['candidateReport']).read_text(encoding='utf-8'))
    assert original['version']=='structure-count-bindings-v8'
    d=copy.deepcopy(original);by={r['cp']:r for r in d['records']};r=by[272]
    decision=copy.deepcopy(a['decisions']['272'])
    assert r['eligible'] and r['status']=='stable' and not r['codes']
    assert r['statistics']==proposal['wholeStatistics'] and r['statistics']['curveStrokes']==1
    assert (decision['bucket'],decision['familyKey'],decision['scope'])==('i','k','whole-glyph')
    assert decision['selectedFeatures']==['corners','crosses','straightStrokes']
    assert decision['selectedCodes']==decision['newCodes']==['ikab','ikgu','ikjb']
    assert decision['rejectedCodes']==['ikqu'] and decision['retainedCompatibility']==['ioma']
    assert decision['withdrawnCurrentCodes']==['iocv','iosc']
    fields={'ikab':('corners',2,'整字角点集'),'ikgu':('crosses',1,'整字四叉点集'),'ikjb':('straightStrokes',2,'整字直连续笔集')}
    assignments=[]
    for code,(field,n,meaning) in fields.items():
        assert r['statistics'][field]==n
        assignments.append(dict(code=code,feature=field,meaning=meaning,count=n,
            objectId='whole-glyph-collection:'+field,scope='Đ整字有孔复合；仅本人逐码接受的三路，不生成本字已拒绝q路',
            variants=9,humanScopeConfirmed=True,humanCountConfirmed=False))
    r.update(acceptedBoundary=decision,previousScopeRejections=copy.deepcopy(r['scopeRejections']),
        codes=sorted(fields),assignments=assignments,scopeRejections=[],reviewResolution='confirmed-d-stroke-k-three-selected-routes')
    d['acceptedBoundary']['272']=decision
    members=defaultdict(set)
    for row in d['records']:
        for code in row['codes']:members[code].add(row['cp'])
    d.update(version=g['targetVersion'],createdAt=g['createdAt'],baseReportSHA256=g['baseSHA256'],
        authorization=a['originalAnswer'],dStrokeKScopeAcceptance=copy.deepcopy(a),codeMembers={c:sorted(cps) for c,cps in sorted(members.items())})
    st=d['statistics'];st.update(assigned=sum(bool(row['codes']) for row in d['records']),pending=sum(not row['codes'] for row in d['records']),
        wholeScopePending=sum(row['eligible'] and not row['codes'] and not row.get('reviewResolution') for row in d['records']),
        newCodes=len(members),newCharacterCodePairs=sum(len(row['codes']) for row in d['records']),
        scopeAcceptedCharacters=original['statistics']['scopeAcceptedCharacters']+1,
        scopeNewlyAssignedCharacters=original['statistics']['scopeNewlyAssignedCharacters']+1,
        scopeAddedPaths=original['statistics']['scopeAddedPaths']+3,dStrokeKAssigned=1,dStrokeKAddedPaths=3)
    assert (st['assigned'],st['newCodes'],st['newCharacterCodePairs'],st['wholeScopePending'])==(1528,126,3258,2073)
    assert d['codeMembers']['ikqu']==original['codeMembers']['ikqu']
    for group in d['groups']:
        cps=[x['cp'] for x in group['recommendations']];recs=[]
        for cp in cps:
            options=[c for c in by[cp]['codes'] if c[:2]==group['code'][:2]]
            best=min(options,key=lambda c:(len(members[c]),c)) if options else None
            recs.append(dict(cp=cp,code=best if best and len(members[best])<len(cps) else group['code'],
                burden=min(len(members[best]),len(cps)) if best else len(cps)))
        group.update(recommendations=recs,pending=sum(not any(c[:2]==group['code'][:2] for c in by[cp]['codes']) for cp in cps),
            withBetterRoute=sum(x['code']!=group['code'] for x in recs),maxRecommendedBurden=max(x['burden'] for x in recs),
            medianRecommendedBurden=sorted(x['burden'] for x in recs)[len(cps)//2])
    previous={row['cp']:row for row in original['records']}
    assert all(row==previous[row['cp']] for row in d['records'] if row['cp']!=272)
    keys=set(json.loads(binding.PATH.read_text(encoding='utf-8')))-{'records'}
    keys.add('dStrokeKScopeAcceptance')
    runtime={k:d[k] for k in keys}
    runtime['records']=[{k:row[k] for k in ('cp','codes','assignments')} for row in d['records'] if row['codes']]
    if output_dir:
        out=Path(output_dir).resolve()
        if out==binding.PATH.parent.resolve() or (out/'大组结构键位分配.json').exists():
            raise ValueError('只写新独立输出，不覆盖runtime或冻结报告')
        out.mkdir(parents=True,exist_ok=True)
        for name,obj in [('大组结构键位分配.json',d),('structure-count-bindings.json',runtime)]:
            (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        assert d==binding.review_report()
        assert runtime=={k:v for k,v in binding.data().items() if k!='byCp'}
    print(json.dumps(dict(passed=True,version=d['version'],addedPaths=3,rejectedCodes=['ikqu'],runtimeWritten=False),ensure_ascii=False))
    return d,runtime

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir');args=p.parse_args();build(args.output_dir)
