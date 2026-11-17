"""Reproduce the reviewed v10 migration; no image reconstruction or runtime writes."""
import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'原型/键位编辑器'),str(ROOT/'工具')]
FIELD='continuousTotalCountAcceptance20261027'
MODE='whole-continuous-total-v1'
COUNTS={1:'u',2:'b',3:'t',4:'y',5:'p'}


def load(rel,expected):
    p=(ROOT/rel).resolve()
    assert p.is_relative_to(ROOT.resolve()) and hashlib.sha256(p.read_bytes()).hexdigest()==expected,rel
    return json.loads(p.read_text(encoding='utf-8'))


def build(output_dir=None):
    import shape_structure_bindings as binding
    manual=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    a=manual[FIELD];g=a['generation']
    assert a['decision']=='accepted' and a['batchReviewed'] and a['countSemanticsVersion']==MODE
    baseline=load(g['baseReport'],g['baseReportSHA256'])
    seed=load(g['baseRuntime'],g['baseRuntimeSHA256'])
    rows=load(g['reviewedPaths'],g['reviewedPathsSHA256'])
    proofs=load(g['jointProofs'],g['jointProofsSHA256'])
    assert baseline['version']==seed['version']=='structure-count-bindings-v9'
    assert baseline['codeMembers']==seed['codeMembers'] and len(rows)==1930
    by=defaultdict(list);proofBy={p['cp']:p for p in proofs}
    for row in rows:by[row['cp']].append(row)
    restoration=manual['dStrokeCurveRestoreAcceptance20261027']
    assert restoration['decision']=='accepted' and restoration['restoredOnly']==['ikqu']
    additional={(restoration['cp'],restoration['canonical'])}
    d=copy.deepcopy(baseline);mapping={};inputPairs=[]
    for r in d['records']:
        rs=by.get(r['cp'],[])
        old=[x for x in r['assignments'] if x['code'][2] in 'jq']
        expected={(r['cp'],x['code']) for x in old}|{x for x in additional if x[0]==r['cp']}
        assert {(r['cp'],x['oldCode']) for x in rs}==expected,(r['cp'],'选择器范围不符')
        if not rs:continue
        stats=r['statistics'];pr=proofBy[r['cp']]
        assert r['eligible'] and r['status']=='stable' and not pr['baseReasons']
        assert stats==pr['statistics'] and stats['uncertainStrokes']==0
        assert len(pr['variants'])==9
        total=stats['straightStrokes']+stats['curveStrokes']
        for v in pr['variants']:
            assert (v['straight'],v['curve'],v['uncertain'])==(stats['straightStrokes'],stats['curveStrokes'],0)
            assert v['topologyAgrees'] is True and v['ambiguous'] is False
        assignments=[x for x in r['assignments'] if x['code'][2] not in 'jq']
        for row in rs:
            key=row['oldCode'][2];selector='straightStrokes' if key=='j' else 'curveStrokes'
            assert stats[selector]>0 and row['status']=='recomputable'
            code=row['oldCode'][:3]+COUNTS[min(total,5)]
            assert code==row['newCode'] and row['total']==total
            assignments.append(dict(code=code,feature='totalContinuousGroups',selectorFeature=selector,
                meaning='含'+('直' if key=='j' else '曲')+'的整字直曲连续组总集合',count=total,
                memberTypeCounts=dict(straight=stats['straightStrokes'],curve=stats['curveStrokes']),
                objectId='whole-glyph-collection:straight-and-curve-total',scope='整字直曲连续组总集合；非手写笔画、原始短段或主体数量',
                countSemanticsVersion=MODE,variants=9,humanScopeConfirmed=bool(r.get('acceptedBoundary')),humanCountConfirmed=False))
            mapping.setdefault(str(r['cp']),{})[row['oldCode']]=code
            inputPairs.append((r['cp'],row['oldCode']))
        r.update(assignments=assignments,codes=sorted(x['code'] for x in assignments),
                 countSemanticsVersion=MODE,legacyTypedCountCodes=sorted(x['oldCode'] for x in rs))
    assert len(inputPairs)==1930 and len(set(inputPairs))==1930
    members=defaultdict(set)
    for r in d['records']:
        for c in r['codes']:members[c].add(r['cp'])
    d.update(version='structure-count-bindings-v10',createdAt=a['date'],countSemanticsVersion=MODE,
        countRuleAcceptanceField=FIELD,countMigration=dict(codeMap=mapping,inputPaths=1930,movedRelations=791,
        unchangedStrings=1139,sourceRestorationField='dStrokeCurveRestoreAcceptance20261027',
        sourceReport=g['baseReport'],sourceReportSHA256=g['baseReportSHA256']),
        codeMembers={c:sorted(cps) for c,cps in sorted(members.items())})
    for key,selector in [('j','straightStrokes'),('q','curveStrokes')]:
        d['definitions']['third'][key]=dict(meaning='含'+('直' if key=='j' else '曲')+'的整字直曲总集合',
            feature='totalContinuousGroups',selectorFeature=selector,status='accepted-global-total-count',
            condition='仅保留既有入口且所选类型可靠正数；第四位统一数同一整字直曲总集合，≥5用p；缺测不当0。')
    for k,old in d['definitions']['fourth'].items():
        old['condition']='j/q数直曲连续组总数；a/b/g仍数各自角点/三叉/四叉集合。'
    st=d['statistics'];st.update(newCodes=len(members),newCharacterCodePairs=sum(len(r['codes']) for r in d['records']),
        totalCountReboundPaths=1930,totalCountMovedRelations=791,totalCountUnchangedStrings=1139,inputRestoredCountPairs=1)
    assert (st['assigned'],st['newCodes'],st['newCharacterCodePairs'],st['wholeScopePending'])==(1528,123,3259,2073)
    assert d['codeMembers']['ikjt']==d['codeMembers']['ikqt']==[272,7694]
    assert 'ikqu' not in members
    byRecord={r['cp']:r for r in d['records']}
    for group in d['groups']:
        cps=[x['cp'] for x in group['recommendations']];recs=[]
        for cp in cps:
            options=[c for c in byRecord[cp]['codes'] if c[:2]==group['code'][:2]]
            best=min(options,key=lambda c:(len(members[c]),c)) if options else None
            recs.append(dict(cp=cp,code=best if best and len(members[best])<len(cps) else group['code'],
                             burden=min(len(members[best]),len(cps)) if best else len(cps)))
        group.update(recommendations=recs,pending=sum(not any(c[:2]==group['code'][:2] for c in byRecord[cp]['codes']) for cp in cps),
            withBetterRoute=sum(x['code']!=group['code'] for x in recs),maxRecommendedBurden=max(x['burden'] for x in recs),
            medianRecommendedBurden=sorted(x['burden'] for x in recs)[len(cps)//2])
    runtime={k:d[k] for k in seed if k!='records'}
    for k in ('countSemanticsVersion','countRuleAcceptanceField','countMigration'):runtime[k]=d[k]
    runtime['records']=[{k:r[k] for k in ('cp','codes','assignments')} for r in d['records'] if r['codes']]
    if output_dir:
        out=Path(output_dir).resolve()
        if out==binding.PATH.parent.resolve() or (out/'大组结构键位分配.json').exists():raise ValueError('只允许新隔离输出')
        out.mkdir(parents=True,exist_ok=True)
        for n,obj in [('大组结构键位分配.json',d),('structure-count-bindings.json',runtime)]:
            (out/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        assert d==binding.review_report()
        assert runtime=={k:v for k,v in binding.data().items() if k!='byCp'}
    print(json.dumps(dict(passed=True,version=d['version'],countSemanticsVersion=MODE,paths=3259,movedRelations=791,runtimeWritten=False),ensure_ascii=False))
    return d,runtime


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir');build(p.parse_args().output_dir)
