"""Full identity/capacity/freeze validation for a completed single-level draft."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter
from balanced_shape_buckets import ROOT,LETTERS
from shape_strategy_lab import corpus,save


def validate(previous=None):
    run=Path(json.loads((ROOT/'最新分桶.json').read_text(encoding='utf-8'))['run'])
    book=json.loads((run/'冻结分组.json').read_text(encoding='utf-8'));rows=book['characters'];capacity=book['capacity']
    expected,_=corpus();identity={r['cp']:r['char'] for r in rows};counts=Counter(r['primary'] for r in rows if r['primary'])
    assert len(identity)==len(rows)
    assert all(identity.get(r['cp'])==r['char'] for r in expected)
    assert set(counts)==set(LETTERS)
    for row in rows:
        assert ord(row['char'])==row['cp']
        assert row['primary'] is None or row['primary'] in LETTERS
        assert row['primary'] not in row['aliases']
        assert len(row['aliases'])==len(set(row['aliases']))<=2
        assert all(k in LETTERS for k in row['aliases'])
        if row['primary'] is None:assert not row['aliases']
    assert all(capacity['plannedLower']<=n<=capacity['plannedUpper'] for n in counts.values())
    assert all((run/'代表字形'/(k+'.png')).exists() for k in LETTERS)
    preserved=0
    if previous:
        before=json.loads((previous/'冻结分组.json').read_text(encoding='utf-8'));after={r['cp']:r for r in rows}
        for old in before['characters']:
            if old['primary'] is not None:assert after[old['cp']]==old;preserved+=1
        assert (previous/'模型.json').read_bytes()==(run/'模型.json').read_bytes()
    summary=json.loads((run/'摘要.json').read_text(encoding='utf-8'))
    assert summary['assigned']==sum(counts.values());assert summary['pending']==len(rows)-sum(counts.values())
    assert summary['counts']==dict(counts);assert summary['layers']==1
    result={'ok':True,'characters':len(rows),'assigned':sum(counts.values()),'pending':summary['pending'],
        'buckets':26,'layers':1,'minBucket':min(counts.values()),'maxBucket':max(counts.values()),
        'aliasesExcludedFromCapacity':True,'frozenAssignmentsVerified':preserved}
    save(run/'校验报告.json',result);return run,result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--previous',type=Path);args=parser.parse_args()
    run,result=validate(args.previous);print(json.dumps(dict(result,run=str(run)),ensure_ascii=False,indent=2))
