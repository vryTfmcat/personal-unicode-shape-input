"""Validate a human-accepted 7 route in memory, without editing shared runtime.

The coordinator owns manual/source/version/service integration. This adapter is
an executable isolated candidate, never imported by the live server.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
OUT=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/第一位分桶专项-20261025/1与7对象补验'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    target=OUT/'已确认7的隔离接入模拟'
    if target.exists():raise SystemExit('拒绝覆盖模拟现场')
    target.mkdir()
    import shape_overview as so
    base=so.get_overview()
    proof=json.loads((OUT/'对象与九扰动证据.json').read_text(encoding='utf-8'))
    seven=next(r for r in proof if r['cp']==55)
    assert seven['allNineWholeStable'] and all(r['signature']['corners']==1 for r in seven['variants'])
    assert not next(r for r in proof if r['cp']==49)['allNineWholeStable']
    protected={ROOT/'数据/三模式/规则库/四键实验/人工审议.json',so.structure.PATH,
        so.structure.active_report_path(),ROOT/'工具/audit_shape_new_key_rules.py',ROOT/'工具/verify_shape_release.py'}
    protected|=set((ROOT/'原型/键位编辑器').glob('*.py'))
    protected|=set((ROOT/'原型/键位编辑器').glob('*.js'))
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    assert so.structure.data()['version']=='structure-count-bindings-v6','先按当前实际版本重新核对'

    class Candidate(so.Overview):
        def __init__(self):self.__dict__.update(base.__dict__)

        def brief(self,cp,allocation=False):
            r=super().brief(cp,allocation)
            if allocation and cp==55:
                r=dict(r,familyKey='a',legacyAngleFamilyKey=r['familyKey'],
                    codes=sorted(set(r['codes'])|{'aaau'}),scopedAngleCodes=['aaau'],
                    angleScopeNote='7整字角折已获本轮答复接受；本实例仅为隔离候选。a桶不变，原12路与首选状态保留。')
            return r

        def allocation_members(self,prefix):
            result=super().allocation_members(prefix)
            if prefix and 'aaau'.startswith(prefix):result[55]=min(result.get(55,4),1)
            return result

        def key_members(self,position,key,allocation=False):
            result=set(super().key_members(position,key,allocation))
            if allocation and 'aaau'[position-1]==key:result.add(55)
            return sorted(result)

        def detail(self,cp,allocation=False):
            result=copy.deepcopy(super().detail(cp,allocation))
            if not allocation:return result
            if cp==55:
                result.update(familyKey='a',legacyAngleFamilyKey=result['familyKey'])
                oid='accepted-7-whole-glyph-corners'
                result['objects'].append(dict(id=oid,type='whole-glyph-collection',feature='corners',count=1,scope='whole-glyph'))
                result['familyRoutes'].append(dict(bucket='a',familyKey='a',familyId='family.angle',target='whole-glyph',
                    lookupEvidence=dict(verified=True,scope='single-character-human-angle-acceptance')))
                result['paths'].append(dict(code='aaau',preferred=False,scopedAngleCollection=True,
                    evidence=[dict(rule='whole-glyph-collection-nine-variant-count',objectId=oid,fourthObjectId=oid,
                                   familyTarget='whole-glyph',attribute='整字角点集：1个',status='accepted-scope-machine-count',variants=9)]))
            # Frozen v6 stores 79 for its own aaau group; live candidate must show
            # 80 for every affected detail, including existing members such as Γ.
            result['codeCounts']={p['code']:len(self.allocation_members(p['code'])) for p in result.get('paths',[])}
            return result

    c=Candidate()
    assert len(base.allocation_members('aaau'))==79 and len(c.allocation_members('aaau'))==80
    assert set(c.allocation_members('aaau'))==set(base.allocation_members('aaau'))|{55}
    assert 55 not in c.allocation_members('aajb')
    old=base.brief(55,True);new=c.brief(55,True)
    assert old['bucket']==new['bucket']=='a' and new['familyKey']=='a'
    assert set(new['codes'])==set(old['codes'])|{'aaau'} and len(new['codes'])==13
    assert new['preferredCodes']==old['preferredCodes']==[]
    assert c.brief(49,True)==base.brief(49,True)
    assert c.brief(55,False)==base.brief(55,False)
    assert c.detail(55,False)==base.detail(55,False)
    d=c.detail(55,True);path=next(p for p in d['paths'] if p['code']=='aaau')
    assert path['evidence'][0]['objectId']==path['evidence'][0]['fourthObjectId']
    assert c.detail(ord('Γ'),True)['codeCounts']['aaau']==80
    assert c.query(dict(allocation=['1'],prefix=['aaau']))['total']==80
    assert c.query(dict(allocation=['1'],prefix=['aaua'],order=['back']))['total']==80
    assert [r['cp'] for r in c.query(dict(allocation=['1'],prefix=['aaau']))['rows']]==[
        r['cp'] for r in c.query(dict(allocation=['1'],prefix=['aaua'],order=['back']))['rows']]
    memberships=[]
    allcodes={code for cp in base.rows for code in base.brief(cp,True)['codes']}
    prefixes={code[:n] for code in allcodes|{'aaau'} for n in range(1,len(code)+1)}
    for prefix in sorted(prefixes):
        a=set(base.allocation_members(prefix));b=set(c.allocation_members(prefix))
        if a!=b:memberships.append(dict(prefix=prefix,added=sorted(b-a),removed=sorted(a-b)))
    assert {r['prefix'] for r in memberships}=={'aa','aaa','aaau'}
    assert all(r['added']==[55] and not r['removed'] for r in memberships)
    assert all(not set(so.exclusive_intake())&set(c.allocation_members(code)) for code in ('aa','aaa','aaau'))
    differences=[]
    for cp in base.rows:
        a=base.brief(cp,True);b=c.brief(cp,True)
        if a!=b:differences.append(cp)
    assert differences==[55]
    after={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    assert hashes==after,'共享版本在模拟期间变化，不能认定当前基线有效'
    proposedAuthority=dict(key='sevenAngleScopeAcceptance20261025',status='仅为待追加唯一人工审议的字段候选；不是另一确认库',
        value=dict(id='seven-angle-scope-20261025',decision='accepted',date='2026-10-25',cp=55,char='7',bucket='a',familyKey='a',scope='whole-glyph',addedCode='aaau',
            originalAnswer='接受角折主体及aaau入口',originalQuestion='对锁定原图中的7（顶部横笔接向下弯斜干），是否接受整字作为“角折”主体？建议保留第一位a，主形族改为角折a，并按现有计数规则新增aaau：a线与转折·纵长／a角折／a整字角点集／u一个。模拟为80候选，原12路和首选状态保留；不扩展其它字。',
            proofReport=(OUT/'对象与九扰动证据.json').relative_to(ROOT).as_posix(),proofSHA256=sha(OUT/'对象与九扰动证据.json'),
            candidateReport=(OUT/'7字最小接入候选.json').relative_to(ROOT).as_posix(),candidateSHA256=sha(OUT/'7字最小接入候选.json'),
            oldPathsRetained=True,preferredUnchanged=True,excluded=['1','aajb','aaec','aavc']))
    receipt=dict(passed=True,baselineVersion=so.structure.data()['version'],sourceHashes=hashes,
        status='用户已接受7；隔离模拟通过；共享人工审议/源码/运行尚未改动',
        changedCharacterCPs=differences,prefixDifferences=memberships,
        aaauBefore=79,aaauAfter=80,oldBest=644,newBest=80,pathsBefore=12,pathsAfter=13,
        coverageAdded=0,oldPathsRetained=True,preferredUnchanged=True,oneUntouched=True,
        frontBackCandidatesAndOrderSame=True,legacyIsolated=True,existingMembersDetailCountRefreshed=True,
        fullPrefixesChecked=len(prefixes),wholeOldCodeTableChecked=True,runtimeWritten=False,serviceRestarted=False)
    for name,obj in [('模拟验证.json',receipt),('人工审议待追加字段.json',proposedAuthority),('7的候选详情.json',d)]:
        (target/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='sourceHashes'},ensure_ascii=False))


if __name__=='__main__':main()
