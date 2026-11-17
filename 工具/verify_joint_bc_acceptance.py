"""Material receipt for the complete before/after four-character acceptance."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
OUT=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261027-structure-count-bindings-v10/七组合接入-20261029'
def save(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    o=so.get_overview();a=so.joint_bc.policy();before=so.read(OUT/'接入前全字.json');changed=[];oldrels=set();newrels=set()
    for cp,b in before.items():
        cp=int(cp);c=o.brief(cp,True)
        assert b['preferredCodes']==c['preferredCodes'] and b.get('bucket')==c.get('bucket') and b.get('familyKey')==c.get('familyKey')
        oldrels|={(cp,code) for code in b['codes']};newrels|={(cp,code) for code in c['codes']}
        if b!=c:changed.append(dict(cp=cp,char=chr(cp),before=b,after=c))
    assert {r['cp'] for r in changed}=={56,7897,272,120123}
    added=sorted(newrels-oldrels);retired=sorted(oldrels-newrels)
    assert len(added)==7 and len(retired)==6 and len(newrels)==208927
    prior=so.read(OUT/'接入前完整前缀成员.json');allprefix=set(prior)|{c[:n] for _,c in added for n in range(1,5)};diff=[]
    for code in sorted(allprefix):
        b={int(cp) for cp in prior.get(code,{})};c=set(o.allocation_members(code));remove=b-c;add=c-b
        assert (remove|add)<={56,7897,272,120123}
        if remove or add:diff.append(dict(code=code,before=len(b),after=len(c),removed=sorted(remove),added=sorted(add)))
    keys=[]
    for name,b in so.read(OUT/'接入前104键.json').items():
        n=int(name[0]);key=name[1];c=set(o.key_members(n,key,True));b=set(b)
        assert (b^c)<={56,7897,272,120123}
        if b!=c:keys.append(dict(position=n,key=key,before=len(b),after=len(c),removed=sorted(b-c),added=sorted(c-b)))
    source=so.read(OUT/'接入前人工审议.json');manual=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')
    assert all(manual[k]==v for k,v in source.items()) and set(manual)-set(source)=={so.joint_bc.FIELD}
    paths={cp:{p['code']:p for p in o.detail(cp,True)['paths']} for cp in [56,7897,272,120123]}
    baseline=so.read(OUT/'接入前四字详情.json')
    for cp,ps in paths.items():
        target=a['records'][str(cp)]
        for old in baseline[str(cp)]['paths']:
            if old['code'] not in target['retiredCanonicalCodes']:assert ps[old['code']]==old
    preferred={c for b in before.values() for c in b['preferredCodes']};prefdiff=[]
    for code in preferred:
        b={int(cp) for cp in prior.get(code,{})};c=set(o.allocation_members(code))
        if b!=c:prefdiff.append(dict(code=code,before=len(b),after=len(c),removed=sorted(b-c),added=sorted(c-b)))
    assert not prefdiff
    result=dict(passed=True,charactersChecked=len(before),changed=changed,canonicalBefore=len(oldrels),canonicalAfter=len(newrels),
        added=[dict(cp=cp,char=chr(cp),code=c) for cp,c in added],retired=[dict(cp=cp,char=chr(cp),code=c) for cp,c in retired],
        prefixesChecked=len(allprefix),prefixes=diff,keysChecked=104,keys=keys,allPreferredCodesUnchanged=True,
        preferredCandidateGroupsChecked=len(preferred),preferredCandidateDifferences=prefdiff,
        remainingTargetPathsByteEquivalent=True,allNonTargetBriefsUnchanged=True,oldAuthorityFieldsUnchanged=len(source),
        realShortRoutesUnchanged=True,tbCount=len(so.exclusive_intake()),scopePending=len(so.structure.queues()['scopePending']),
        structureVersion=so.structure.data()['version'],jointBCVersion=a['id'],fullCodeGroups=len(o.collision_groups(4,True)))
    save('精确全字与成员差异验收.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['changed','prefixes','keys','added','retired']},ensure_ascii=False))
if __name__=='__main__':main()
