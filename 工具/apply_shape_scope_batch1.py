"""Apply the seven explicit human scope decisions; preserve v3 and all old routes."""
import argparse
import copy
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
EDITOR=PROJECT/'原型/键位编辑器'
RUNS=PROJECT/'数据/三模式/规则库/四键实验/键位试验'
MANUAL=PROJECT/'数据/三模式/规则库/四键实验/人工审议.json'
FIELDS={'a':('corners','整字角点集'),'b':('forks','整字三叉点集'),'g':('crosses','整字四叉点集'),'j':('straightStrokes','整字直连续笔集'),'q':('curveStrokes','整字曲连续笔集')}
COUNTS={1:'u',2:'b',3:'t',4:'y',5:'p'}


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def build(output_dir=None):
    acceptance=json.loads(MANUAL.read_text(encoding='utf-8'))['scopeBoundaryAcceptance20261024Batch1']
    config=acceptance['generation']
    BASE=PROJECT/config['baseReport']
    if not BASE.resolve().is_relative_to(PROJECT.resolve()):
        raise ValueError('基线必须位于本工程')
    OUT=Path(output_dir).resolve() if output_dir else None
    d=json.loads(BASE.read_text(encoding='utf-8'));original=copy.deepcopy(d)
    index={r['cp']:r for r in d['records']}
    decisions=acceptance['decisions']
    mapping={a['char']:(a['bucket'],a['familyKey']) for a in decisions.values()}
    text=acceptance['userResponse']
    accepted={}
    for ch,(bucket,family) in mapping.items():
        r=index[ord(ch)];assert r['eligible'] and not r['codes']
        accepted[str(ord(ch))]=copy.deepcopy(decisions[str(ord(ch))])
        if not accepted[str(ord(ch))]['humanConfirmed']:
            raise ValueError('未确认的条目不能生成')
        r['acceptedBoundary']=accepted[str(ord(ch))]
        r['previousScopeRejections']=r['scopeRejections']
        if not accepted[str(ord(ch))]['generateWholeCounts']:
            r['reviewResolution']='confirmed-circle-subject-retain-existing-routes'
            r['scopeRejections']=[dict(prefix='io',reasons=['圆形主体查法已确认保留；原九扰动统计为整字，不将含尾笔的整字计数套到圆主体。'])]
            continue
        st=r['statistics']
        if family=='k': assert st['loops']>0
        if family=='x': assert st['crosses']==1
        if family=='w': assert st['forks']==st['crosses']==0 and st['curveStrokes']>0
        assignments=[]
        for key,(field,meaning) in FIELDS.items():
            n=st[field]
            if n:assignments.append(dict(code=bucket+family+key+COUNTS[min(n,5)],feature=field,meaning=meaning,count=n,
                objectId='whole-glyph-collection:'+field,scope='本人确认的整字形族；计数来自原九扰动整字观测',variants=9,humanScopeConfirmed=True))
        r.update(codes=sorted(a['code'] for a in assignments),assignments=assignments,scopeRejections=[],
                 reviewResolution='confirmed-whole-glyph-family')
    members=defaultdict(set)
    for r in d['records']:
        for code in r['codes']:members[code].add(r['cp'])
    d['version']=config['targetVersion']
    d['createdAt']=config['createdAt']
    d['acceptedBoundary']=accepted
    d['baseReportSHA256']=hashlib.sha256(BASE.read_bytes()).hexdigest()
    d['authorization']=text
    d['definitions']['second']=copy.deepcopy(config['secondDefinitions'])
    d['codeMembers']={c:sorted(v) for c,v in sorted(members.items())}
    s=d['statistics'];s.update(assigned=sum(bool(r['codes']) for r in d['records']),pending=sum(not r['codes'] for r in d['records']),
      wholeScopePending=sum(r['eligible'] and not r['codes'] and not r.get('reviewResolution') for r in d['records']),
      reviewedRetained=sum(not r['codes'] and bool(r.get('reviewResolution')) for r in d['records']),
      newCodes=len(members),newCharacterCodePairs=sum(len(r['codes']) for r in d['records']),
      scopeAcceptedCharacters=7,scopeNewlyAssignedCharacters=6,scopeAddedPaths=sum(len(index[ord(ch)]['codes']) for ch in mapping))
    assert s['assigned']==1520 and s['wholeScopePending']==2083 and s['reviewedRetained']==1
    assert s['pending']==s['observationPending']+s['wholeScopePending']+s['reviewedRetained']
    for g in d['groups']:
        cps=[r['cp'] for r in g['recommendations']]
        recommendations=[]
        for cp in cps:
            options=[c for c in index[cp]['codes'] if c[:2]==g['code'][:2]]
            best=min(options,key=lambda c:(len(members[c]),c)) if options else None
            recommendations.append(dict(cp=cp,code=best if best and len(members[best])<len(cps) else g['code'],burden=min(len(members[best]),len(cps)) if best else len(cps)))
        g.update(recommendations=recommendations,pending=sum(not any(c[:2]==g['code'][:2] for c in index[cp]['codes']) for cp in cps),
          withBetterRoute=sum(r['code']!=g['code'] for r in recommendations),maxRecommendedBurden=max(r['burden'] for r in recommendations),
          medianRecommendedBurden=sorted(r['burden'] for r in recommendations)[len(cps)//2])
    unchanged=[r for r in d['records'] if str(r['cp']) not in accepted]
    oldindex={r['cp']:r for r in original['records']}
    assert all(r==oldindex[r['cp']] for r in unchanged)
    assert d['codeMembers']['ajqu']==original['codeMembers']['ajqu']
    runtime={k:d[k] for k in ('version','active','runtimeDeployed','sourceIndexSHA256','definitions','statistics','codeMembers','acceptedBoundary')}
    runtime['records']=[{k:r[k] for k in ('cp','codes','assignments')} for r in d['records'] if r['codes']]
    # Use the existing public-review generator with the new report and output directory.
    import build_shape_structure_bindings as generator
    overview=generator.so.get_overview()
    for cp,a in accepted.items():
        assert int(cp) in overview.allocation_members(a['bucket']), '第一位不应新增或改动'
    observed=set(index)
    d['prefixScope']=[dict(prefix=prefix,currentMembers=len(overview.allocation_members(prefix)),
       observed=len(set(overview.allocation_members(prefix)) & observed),
       outsideObservedScope=len(set(overview.allocation_members(prefix))-observed)) for prefix in sorted({c[:2] for c in members})]
    import shape_structure_bindings as binding
    live=binding.review_report()
    historical=d['version']!=live['version']
    frozen=list(RUNS.glob('*-'+d['version']+'/大组结构键位分配.json'))
    assert len(frozen)==1
    target=json.loads(frozen[0].read_text(encoding='utf-8')) if historical else live
    if d != target or (not historical and runtime != {k:v for k,v in binding.data().items() if k!='byCp'}):
        raise ValueError('确认源重生成结果与现行版本不同；停止，不覆盖当前数据')
    if OUT:
        if OUT in (binding.active_report_path().parent,frozen[0].parent,EDITOR/'data'):
            raise ValueError('候选输出不得覆盖当前版本或运行数据目录')
        OUT.mkdir(parents=True,exist_ok=True)
        write(OUT/'大组结构键位分配.json',d)
        write(OUT/'structure-count-bindings.json',runtime)
        generator.OUT=OUT
        generator.write_review(d,publish=False)
    print(json.dumps(dict(passed=True,source='人工审议.json',activeVersion=d['version'],
        reportMatches=True,runtimeMatches=not historical,historicalBaseline=historical,activeFilesWritten=False,output=str(OUT) if OUT else None),ensure_ascii=False))
    return d, runtime


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='从唯一确认源核验v4；默认只检查，不修改运行数据')
    parser.add_argument('--output-dir',help='可选的候选目录，禁止覆盖现行报告及运行数据')
    args=parser.parse_args()
    build(args.output_dir)
