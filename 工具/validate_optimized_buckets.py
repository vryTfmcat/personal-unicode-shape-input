"""Validate optimized output and unchanged reserved collections against its baseline."""
import json,gzip
from pathlib import Path
from collections import Counter
import numpy as np
from shape_quality_v2 import ROOT
from shape_bucket_scope import ACTIVE,full_scope
from shape_strategy_lab import save


def main():
    run=Path(json.loads((ROOT/'最新优化.json').read_text(encoding='utf-8'))['run'])
    summary=json.loads((run/'摘要.json').read_text(encoding='utf-8'));rows=json.loads((run/'全部收纳.json').read_text(encoding='utf-8'))['characters']
    ordinary=json.loads((run/'冻结分组.json').read_text(encoding='utf-8'))['characters'];counts=Counter(r['primary'] for r in rows if r['primary']);counts['x']=0
    identities={r['cp']:r['char'] for r in rows};expected,_=full_scope()
    assert len(identities)==len(rows)==len(expected)
    assert all(identities[r['cp']]==r['char'] for r in expected)
    assert dict(counts)==summary['counts'];assert counts['x']==0
    assert all(500<=counts[k]<=2000 for k in ACTIVE)
    old=json.loads((Path(summary['baseline'])/'全部收纳.json').read_text(encoding='utf-8'))['characters']
    assert [r for r in rows if r['primary'] in ('y','z')]==[r for r in old if r['primary'] in ('y','z')]
    for r in ordinary:
        assert r['primary'] is None or r['primary'] in ACTIVE
        assert all(k in ACTIVE for k in r['aliases']) and r['primary'] not in r['aliases']
    for key in ACTIVE:
        content=(run/'全部字符预览'/(key+'.md')).read_bytes().decode('utf-8')
        assert content==''.join(r['char'] for r in ordinary if r['primary']==key)
        assert not any(c in content for c in '\r\n\u2028\u2029')
        assert len(content)==counts[key];assert (run/'代表字形'/(key+'.png')).exists()
    model=json.loads((run/'模型.json').read_text(encoding='utf-8'))
    assert np.array(model['centres']).shape==(23,216)
    assert np.isfinite(np.array(model['centres'])).all()
    with gzip.open(model['qualityRecords'],'rt',encoding='utf-8') as stream:qa=list(map(json.loads,stream))
    assert [r['cp'] for r in qa]==[r['cp'] for r in ordinary if r['primary']]
    methods=Counter(r.get('method') for r in summary['comparisons'] if 'method' in r)
    assert all(n>=2 for n in methods.values()) and len(methods)==3
    for r in summary['comparisons']:
        if r.get('method'):assert 500<=r['metrics']['minBucket'] and r['metrics']['maxBucket']<=2000
    result={'ok':True,'characters':len(rows),'ordinaryAssigned':summary['ordinaryAssigned'],'pending':summary['pending'],
        'capacity':[500,2000],'minBucket':min(counts[k] for k in ACTIVE),'maxBucket':max(counts[k] for k in ACTIVE),
        'reservedUnchanged':True,'singleLinePreviews':23,'featureDimensions':216,'multipleSeeds':dict(methods)}
    save(run/'校验报告.json',result);print(json.dumps(dict(result,run=str(run)),ensure_ascii=False))


if __name__=='__main__':main()
