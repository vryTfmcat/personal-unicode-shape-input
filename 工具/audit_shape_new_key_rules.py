"""Audit the active structure version, including explicit human scope decisions."""
import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'原型/键位编辑器'),str(PROJECT/'工具')]
import shape_overview as so
import shape_structure_bindings as binding
from shape_structure_scope import check_scope,load_facts
from build_shape_structure_bindings import whole_curve_scope

FIELDS=dict(a='corners',b='forks',g='crosses',j='straightStrokes',q='curveStrokes')
COUNTS={1:'u',2:'b',3:'t',4:'y',5:'p'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(offline=False,output_dir=None,base_url='http://127.0.0.1:8765'):
    report=binding.review_report();active=binding.active_report_path()
    out=Path(output_dir) if output_dir else active.parent
    sources=[so.RUNS/'20261024-other-large-collisions-v1/其他大组分析.json',
             so.RUNS/'20261024-stroke-continuation-trial-v1/分类数据.json']
    manual=PROJECT/'数据/三模式/规则库/四键实验/人工审议.json'
    protected=sources+[active,binding.PATH,manual,so.RUN/'发布核对索引.json',
        PROJECT/'原型/键位编辑器/data/pictorial-exclusive-allocation.json',
        PROJECT/'数据/三模式/全形核对版.json',PROJECT/'原型/键位编辑器/shape_overview.py']
    before={str(p.relative_to(PROJECT)):sha(p) for p in protected}
    observations={}
    for source in sources:
        for row in so.read(source)['records']:
            observations.setdefault(row['cp'],row)
    overview=so.get_overview()
    facts=load_facts(overview,{r['cp'] for r in report['records'] if r['eligible']})
    decisions=so.read(manual).get('scopeBoundaryAcceptance20261024Batch1',{}).get('decisions',{})
    decisions=dict(decisions)
    decisions.update(so.read(manual).get('kFamilyScopeAcceptance20261025Batch1',{}).get('decisions',{}))
    decisions.update(so.read(manual).get('kFamilyScopeAcceptance20261025Batch2',{}).get('decisions',{}))
    decisions.update(so.read(manual).get('sevenAngleScopeAcceptance20261025',{}).get('decisions',{}))
    decisions.update(so.read(manual).get('dStrokeKScopeAcceptance20261026',{}).get('decisions',{}))
    accepted=report.get('acceptedBoundary',{})
    assert all(decisions.get(cp)==a for cp,a in accepted.items()), '报告与人工确认源不同'
    cache={}
    def burden(code):
        if code not in cache:cache[code]=len(overview.allocation_members(code))
        return cache[code]
    issues=[];entries=[];pending=[];union=defaultdict(set);reasons=Counter()
    for r in report['records']:
        cp=r['cp'];obs=observations[cp];expected=set();a=accepted.get(str(cp))
        if obs['status']=='stable':
            if a:
                assert a['humanConfirmed']
                prefixes=[a['prefix']] if a['generateWholeCounts'] else []
            else:prefixes=sorted({c[:2] for c in r['oldCodes'] if len(c)==4})
            for prefix in prefixes:
                if not a:
                    passed,rejected=(whole_curve_scope(obs) if prefix[1]=='j' else check_scope(prefix,obs,facts[cp]))
                    if not passed:reasons.update(rejected);continue
                for key,field in FIELDS.items():
                    if a and 'selectedFeatures' in a and field not in a['selectedFeatures']:
                        continue
                    n=obs['statistics'][field]
                    if n:expected.add(binding.totals.expected_code(key,prefix,obs['statistics']))
        p_decision=binding.p_family_decision(cp)
        if p_decision and p_decision['action']=='withdraw-p-whole-counts':
            assert p_decision==so.read(manual)['pFamilyBoundaryAcceptance20261025Batch1']['decisions'][str(cp)]
            expected={c for c in expected if c[1]!='p'}
        restore=so.external_groups.curve_restore_policy()
        if binding.totals.active() and restore and cp==restore['cp']:
            expected.add(binding.totals.expected_code('q',restore['canonical'][:2],obs['statistics']))
        frozen_expected=set(expected)
        expected=so.joint_bc.migrate_structure(cp,expected)
        live=overview.brief(cp,True);actual=set(live.get('structuralCodes',[]))
        if expected!=actual:issues.append(dict(cp=cp,missing=sorted(expected-actual),unexpected=sorted(actual-expected)))
        for code in frozen_expected:union[code].add(cp)
        refinement=so.round_refinement.policy() or {}
        withdrawn=set(refinement.get('withdrawnCurrentCodes',{}).get(str(cp),[]))
        assert withdrawn<=set(r['oldCodes']),('撤路不在冻结旧路内',cp)
        assert not withdrawn & set(live['codes']),('确认撤路仍残留',cp)
        assert set(r['oldCodes'])-withdrawn-set(so.accepted_bc_records().get(str(cp),{}).get('retiredCanonicalCodes',[]))<=set(live['codes']),('未授权旧入口丢失',cp)
        assert r['oldPreferredCodes']==live['preferredCodes'],('原首选改变',cp)
        assert not actual or cp not in so.exclusive_intake()
        old4=[c for c in r['oldCodes'] if len(c)==4 and c not in withdrawn]
        old_best=min(old4,key=lambda c:(burden(c),c)) if old4 else None
        new_best=min(actual,key=lambda c:(burden(c),c)) if actual else None
        item=dict(cp=cp,char=chr(cp),oldBest=old_best,oldBurden=burden(old_best) if old_best else None,
            newBest=new_best,newBurden=burden(new_best) if new_best else None,newCodes=sorted(actual),
            oldPreferredCodes=r['oldPreferredCodes'],status=r['status'],reviewResolution=r.get('reviewResolution'))
        if actual:
            item['improvesBestOld']=old_best is not None and burden(new_best)<burden(old_best)
            entries.append(item)
        else:
            item.update(scopeRejections=r['scopeRejections'],statistics=obs['statistics']);pending.append(item)
    current_union={code:cps|so.external_groups.count_members(code) for code,cps in union.items()}
    if so.joint_bc.policy():
        migrated=defaultdict(set)
        for code,cps in current_union.items():
            for cp in cps:
                for target in so.joint_bc.migrate_structure(cp,{code}):migrated[target].add(cp)
        current_union=dict(migrated)
    union_issues=[code for code,cps in current_union.items() if cps!=set(overview.allocation_members(code))]
    checks=[]
    if not offline:
        for code,cps in sorted(current_union.items()):
            with urlopen(base_url.rstrip('/')+'/api/shape-overview/query?allocation=1&prefix='+code,timeout=60) as f:live=json.load(f)
            assert live['total']==len(cps),('在线人数不符',code)
            checks.append(dict(code=code,total=live['total']))
    if issues or union_issues:
        raise AssertionError(json.dumps(dict(ruleMismatches=issues[:8],unionMismatches=union_issues[:8]),ensure_ascii=False))
    assert len(entries)==report['statistics']['assigned']
    assert sum(map(len,union.values()))==report['statistics']['newCharacterCodePairs']
    assert before=={str(p.relative_to(PROJECT)):sha(p) for p in protected}
    summary=dict(version=report['version'],observed=len(observations),assigned=len(entries),newCodes=len(union),
        paths=sum(map(len,union.values())),currentUnionPaths=sum(map(len,current_union.values())),
        acceptedCountOverlayPairs=sum(len(so.external_groups.count_members(c)) for c in union),ruleMismatchCharacters=len(issues),unionMismatches=union_issues,
        improvesBestOld=sum(r['improvesBestOld'] for r in entries),
        equalBestOld=sum(r['oldBurden']==r['newBurden'] for r in entries),
        worseThanBestOld=sum(r['oldBurden'] is not None and r['newBurden']>r['oldBurden'] for r in entries),
        withoutNewCode=len(pending),queueCounts=binding.summary()['queueCounts'],
        humanScopeConfirmed=len(accepted),allGlyphSemanticsHumanConfirmed=False,
        liveCodesVerified=len(checks),offline=offline,protectedInputsUnchanged=True,
        closedFamilyPolicyID=(binding.closed_family_policy() or {}).get('id'),
        frozenAllocationAudit=True,closedFamilyMembersSemanticallyRevalidated=False,
        countSemanticsVersion=binding.data().get('countSemanticsVersion','separate-straight-or-curve'))
    summary['pBoundaryReviewedCharacters']=len(binding.data().get('pFamilyBoundaryReview',{}).get('decisions',{}))
    summary['pBoundaryCountsHumanConfirmed']=False
    result=dict(passed=True,createdAt=datetime.now().astimezone().isoformat(),summary=summary,
        issues=issues,assigned=entries,pending=pending,liveChecks=checks,protectedHashes=before)
    out.mkdir(parents=True,exist_ok=True)
    (out/'新键规则审计.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 当前新键规则审计','',json.dumps(summary,ensure_ascii=False),'',
      '从运行数据中的唯一当前版本读取报告；人工确认源驱动已接受范围，其余沿用观测和必要条件。',
      '本次只读复算，未改变候选、首选或规则。稳定检测、形族接受与逐字几何确认分别记录。',
      'Q已确认保留圆主体原查法，不属于仍待人工审核；没有新增整字计数。',
      '闭合形族一般边界已接受时，本审计仍只验证冻结分配与计数，不证明现有全部成员已按新语义逐字复核。','',
      '在线核查：'+('未执行（离线恢复验收）' if offline else f'{len(checks)}码候选人数一致。')]
    (out/'新键规则审计.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=['# 当前新旧查法比较','','| 字符 | 码位 | 旧最佳（人数） | 新最佳（人数） | 全部新增查法 |','| --- | --- | --- | --- | --- |']
    for r in sorted(entries,key=lambda r:r['cp']):
        ch=r['char'].replace('|','&#124;').replace('<','&lt;').replace('>','&gt;')
        lines.append(f"| {ch} | U+{r['cp']:04X} | {r['oldBest']}（{r['oldBurden']}） | {r['newBest']}（{r['newBurden']}） | {' '.join(r['newCodes'])} |")
    (out/'符号新旧查法清单.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='只读审计当前结构计数版本')
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--output-dir')
    parser.add_argument('--base-url',default='http://127.0.0.1:8765')
    args=parser.parse_args();run(args.offline,args.output_dir,args.base_url)
