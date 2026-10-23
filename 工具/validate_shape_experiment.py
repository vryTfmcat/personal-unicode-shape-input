"""Independently audit all evidence shards and supported property combinations."""
import collections,json
from pathlib import Path
from build_shape_experiment import DATA,ROOT,EDITOR,read,save,protected_inputs
from shape_experiment_rules import properties,RULES,TRIAL_KEYS


def validate():
    run=Path(read(ROOT/'最新实验.json')['run']);index=read(EDITOR/'data/shape-experiment.json');report=read(run/'容量与重码报告.json')
    assert index['active'] is False and index['id']==report['experimentId']
    lookup={r['cp']:r for r in index['records']};assert len(lookup)==28223
    seen=set();associations=0;evidence_count=0
    for url in sorted({r['detailUrl'] for r in index['records']}):
        shard=read(EDITOR/url);assert shard['experimentId']==index['id']
        for r in shard['records']:
            cp=r['cp'];assert cp not in seen;seen.add(cp);assert r['char']==chr(cp)
            assert lookup[cp]['codes']==[p['code'] for p in r['paths']]
            assert lookup[cp]['bucket']==r['bucket'] and lookup[cp]['familyRoutes']==r['familyRoutes']
            objects={o['id']:o for o in r['objects']};assert len(objects)==len(r['objects'])
            actual=collections.defaultdict(set);expected={}
            for p in r['paths']:
                associations+=1;assert len(p['code']) in (3,4)
                assert any(route['bucket']==p['code'][0] and route['familyKey']==p['code'][1] for route in r['familyRoutes'])
                for e in p['evidence']:
                    evidence_count+=1;assert e['third']==p['code'][2] and e['third'] not in TRIAL_KEYS
                    assert e['rule']==RULES[e['third']][0]
                    assert e['objectId']==e['fourthObjectId'] and e['objectId'] in objects
                    assert any(route['bucket']==p['code'][0] and route['familyKey']==p['code'][1] and route['target']==e['familyTarget'] for route in r['familyRoutes'])
                    o=objects[e['objectId']];key=(p['code'][:3],e['objectId'],e['familyTarget'],e['rule'],e['condition'])
                    attrs=properties(o);expected[key]={k for k,_ in attrs} or {''}
                    actual[key].add(p['code'][3:] if len(p['code'])==4 else '')
                    if len(p['code'])==4:
                        assert p['code'][3] in index['definitions']['fourth']
                        assert (p['code'][3],e['attribute']) in attrs
            assert dict(actual)==expected,'Missing or unsupported property path'
    assert seen==set(lookup);assert associations==report['pathCount']
    stage=read(DATA/'shape-stage.json')
    for key in 'xyz':assert index['collections'][key]==stage['buckets'][key]
    assert index['unclassified']==stage['unclassified']
    assert seen=={cp for a in 'abcdefghijklmnopqrstuvw' for cp in stage['buckets'][a]}
    assert index['definitions']==read(run/'定义快照.json')
    source=DATA.parents[1]/stage['source'];assert protected_inputs(source)==read(run/'保护基线.json')
    result={'passed':True,'ordinary':len(seen),'codeAssociations':associations,'evidenceItems':evidence_count,
        'allObjectBindingsValid':True,'allObservedPropertiesEnumerated':True,'noUnsupportedProperties':True,
        'sourceStageUnchanged':True,'xyzUnchanged':True,'effectiveBooksAndRimeUnchanged':True}
    save(run/'全路径独立校验.json',result)
    report['fullEvidenceAudit']=result;save(run/'容量与重码报告.json',report);save(EDITOR/'data/shape-experiment-report.json',report)
    print(json.dumps(result,ensure_ascii=False));return result


if __name__=='__main__':validate()
