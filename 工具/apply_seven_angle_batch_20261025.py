"""Reproduce the single accepted 7/corners binding from pinned v7 and proof.

Default is comparison only; --output-dir writes a new isolated report/runtime.
No source, authority, service, or deployed dictionary is modified here.
"""
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
    a=manual['sevenAngleScopeAcceptance20261025'];g=a['generation']
    assert a['decision']=='accepted' and a['cp']==55 and a['addedCode']=='aaau'
    assert set(a['decisions'])=={'55'} and a['oldPathsRetained'] and a['preferredUnchanged']
    for rel,h in [(g['baseReport'],g['baseSHA256']),(a['proofReport'],a['proofSHA256']),(a['candidateReport'],a['candidateSHA256'])]:
        p=(ROOT/rel).resolve();assert p.is_relative_to(ROOT.resolve())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==h,(rel,'冻结输入不符')
    original=json.loads((ROOT/g['baseReport']).read_text(encoding='utf-8'))
    assert original['version']=='structure-count-bindings-v7'
    proof=json.loads((ROOT/a['proofReport']).read_text(encoding='utf-8'));seven=next(r for r in proof if r['cp']==55)
    assert seven['allNineWholeStable'] and len(seven['variants'])==9
    assert all(v['topologyAgrees'] and not v['ambiguities'] and v['signature']['corners']==1 for v in seven['variants'])
    d=copy.deepcopy(original);by={r['cp']:r for r in d['records']};r=by[55];decision=copy.deepcopy(a['decisions']['55'])
    assert r['eligible'] and r['status']=='stable' and not r['codes']
    assert all(r['statistics']==v['statistics'] for v in seven['variants'])
    assert decision['selectedFeatures']==['corners'] and decision['selectedCodes']==['aaau']
    assert (decision['bucket'],decision['familyKey'],decision['scope'])==('a','a','whole-glyph')
    r.update(acceptedBoundary=decision,previousScopeRejections=copy.deepcopy(r['scopeRejections']),
        codes=['aaau'],assignments=[dict(code='aaau',feature='corners',meaning='整字角点集',count=1,
            objectId='whole-glyph-collection:corners',scope='本人仅确认7整字角折主体；本批只接入整字角点集',
            variants=9,humanScopeConfirmed=True,humanCountConfirmed=False)],scopeRejections=[],
        reviewResolution='confirmed-seven-whole-angle-selected-corners')
    d['acceptedBoundary']['55']=decision
    members=defaultdict(set)
    for row in d['records']:
        for code in row['codes']:members[code].add(row['cp'])
    d.update(version=g['targetVersion'],createdAt=g['createdAt'],baseReportSHA256=g['baseSHA256'],
             authorization=a['originalAnswer'],sevenAngleScopeAcceptance=copy.deepcopy(a),
             codeMembers={code:sorted(cps) for code,cps in sorted(members.items())})
    st=d['statistics'];st.update(assigned=sum(bool(row['codes']) for row in d['records']),
        pending=sum(not row['codes'] for row in d['records']),
        wholeScopePending=sum(row['eligible'] and not row['codes'] and not row.get('reviewResolution') for row in d['records']),
        newCharacterCodePairs=sum(len(row['codes']) for row in d['records']),newCodes=len(members),
        scopeAcceptedCharacters=original['statistics']['scopeAcceptedCharacters']+1,
        scopeNewlyAssignedCharacters=original['statistics']['scopeNewlyAssignedCharacters']+1,
        scopeAddedPaths=original['statistics']['scopeAddedPaths']+1,
        sevenAngleAssigned=1,sevenAngleAddedPaths=1)
    assert (st['assigned'],st['newCodes'],st['newCharacterCodePairs'],st['wholeScopePending'])==(1527,125,3255,2074)
    assert set(d['codeMembers']['aaau'])==set(original['codeMembers']['aaau'])|{55}
    assert d['codeMembers']['aajb']==original['codeMembers']['aajb']
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
    old={x['cp']:x for x in original['records']}
    assert all(row==old[row['cp']] for row in d['records'] if row['cp']!=55)
    keys=set(binding.data())-{'byCp','records','dStrokeKScopeAcceptance'}
    keys.add('sevenAngleScopeAcceptance')
    runtime={key:d[key] for key in keys}
    runtime['records']=[{key:row[key] for key in ('cp','codes','assignments')} for row in d['records'] if row['codes']]
    if output_dir:
        out=Path(output_dir).resolve()
        if out==binding.PATH.parent.resolve() or (out/'大组结构键位分配.json').exists():
            raise ValueError('仅向新的独立目录输出，不覆盖runtime或冻结报告')
        out.mkdir(parents=True,exist_ok=True)
        for name,obj in [('大组结构键位分配.json',d),('structure-count-bindings.json',runtime)]:
            (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        if binding.data()['version']==d['version']:
            assert d==binding.review_report()
            assert runtime=={k:v for k,v in binding.data().items() if k!='byCp'}
        else:
            frozen=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v8'
            assert d==json.loads((frozen/'大组结构键位分配.json').read_text(encoding='utf-8'))
            assert runtime==json.loads((frozen/'structure-count-bindings.json').read_text(encoding='utf-8'))
    print(json.dumps(dict(passed=True,version=d['version'],scopeAccepted=1,addedPaths=1,runtimeWritten=False),ensure_ascii=False))
    return d,runtime


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir');args=p.parse_args();build(args.output_dir)
