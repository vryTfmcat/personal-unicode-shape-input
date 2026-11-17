"""Verify the isolated four-character candidate against the current accepted view."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]


def verify(out):
    import shape_overview as so
    p=out/'第1项-逐图判断与首批四字差异.json'
    d=json.loads(p.read_text(encoding='utf-8'));o=so.get_overview()
    for rel,h in d['runtimeAndManualSHA256'].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,('现场已变，候选需重核',rel)
    assert len(d['judgments'])==37
    assert len({r['cp'] for r in d['judgments']})==37
    assert sum(r['judgment']=='非圆主体候选' for r in d['judgments'])==17
    assert sum(r['judgment']=='主体与局部圆范围待核' for r in d['judgments'])==2
    assert {r['char'] for r in d['batch']}==set('ĎḊḎḒ')
    assert sum(len(r['withdrawProposal']) for r in d['batch'])==24
    assert sum(len(r['kWholeGlyphProposal']) for r in d['batch'])==12
    for r in d['batch']:
        b=o.brief(r['cp'],True)
        assert b['preferredCodes']==r['preferred']==['ioki']
        assert set(b['codes'])==set(r['beforeCodes'])
        assert set(r['keepCompatibility'])|set(r['withdrawProposal'])==set(r['beforeCodes'])
        assert not set(r['keepCompatibility'])&set(r['withdrawProposal'])
        assert all(len(c)==4 and c.startswith('ik') for c in r['kWholeGlyphProposal'])
    for impact in d['candidateImpacts']:
        current=set(o.allocation_members(impact['code']))
        assert len(current)==impact['before']
        assert len(current-set(impact['removed']))==impact['after']
    for r in d['batch']:
        for c,count in r['kCandidateCounts'].items():
            members=set(o.allocation_members(c))|{x['cp'] for x in d['batch'] if c in x['kWholeGlyphProposal']}
            assert len(members)==count
    result=dict(passed=True,currentRuntimeUnchanged=True,visualSubset=37,nonroundCandidates=17,
                objectScopePending=2,batch=4,withdrawProposal=24,addProposal=12,
                humanDecisionRecorded=False,scopePending=2083,historicalMissing=84,
                scope='只验证独立候选身份/人数/原首选；不是新运行版或几何重算')
    (out/'第1项-独立候选验收.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);verify(p.parse_args().output_dir)
