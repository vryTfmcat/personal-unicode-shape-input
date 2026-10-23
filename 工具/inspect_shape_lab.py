"""Inspect or validate isolated rule experiments without editing effective codebooks."""
import argparse
import gzip
import json
import hashlib
from contextlib import ExitStack
from pathlib import Path
from shape_strategy_lab import LAB, corpus


def load_run(run=None):
    if run is None:run=Path(json.loads((LAB/'最新实验.json').read_text(encoding='utf-8'))['run'])
    return run,json.loads((run/'summary.json').read_text(encoding='utf-8'))


def validate(run,summary):
    expected,_=corpus(None if summary['scope']['allNonHan'] else summary['scope']['characters'])
    counts={r['id']:0 for r in summary['strategies']}
    observed=0
    with ExitStack() as stack:
        streams=[stack.enter_context(gzip.open(run/'编码'/(r['id']+'.jsonl.gz'),'rt',encoding='utf-8')) for r in summary['strategies']]
        shared=stack.enter_context(gzip.open(run/'观测视图.jsonl.gz','rt',encoding='utf-8'))
        for identity in expected:
            view=json.loads(next(shared))
            assert (view['cp'],view['char'])==(identity['cp'],identity['char'])
            observed+=bool(view['observed'])
            suffixes={v['suffix'] for v in view['views'] if v['suffix'] is not None}
            for spec,stream in zip(summary['strategies'],streams):
                row=json.loads(next(stream));counts[spec['id']]+=1
                assert (row['cp'],row['char'])==(identity['cp'],identity['char'])
                assert bool(row['codes'])==view['observed']
                assert {c['code'][-1] for c in row['codes']}==suffixes
                assert len({c['code'] for c in row['codes']})==len(row['codes'])
                for code in row['codes']:
                    assert len(code['code'])==4 and code['code'].isascii() and code['code'].islower()
                    assert code['views'] and all(0<=i<len(view['views']) for i in code['views'])
                    assert all(view['views'][i]['suffix']==code['code'][-1] for i in code['views'])
                    assert all(k in spec['dictionary'][i] for i,k in enumerate(code['code'][:3]))
                    assert code['code'][-1] in summary['fourth']
        assert not shared.readline()
        assert all(not stream.readline() for stream in streams)
    for name,digest in summary['sourceHashes'].items():
        assert hashlib.sha256((run/'来源快照'/name).read_bytes()).hexdigest()==digest
    for spec in summary['strategies']:
        assert spec['metrics']['fourCodeGlyphs']==observed
        assert spec['metrics']['coverageRecords']==len(expected)
        assert all(abs(sum(d.values())-observed)<.00001 for d in spec['metrics']['distribution'])
    result={'ok':True,'charactersPerStrategy':len(expected),'strategies':len(counts),
            'recordsChecked':sum(counts.values()),'observed':observed,'frozenFourthViews':True,'sourceHashes':True}
    (run/'校验报告.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def inspect(run,summary,chars,strategy=None):
    selected=next(r for r in summary['strategies'] if r['id']==(strategy or summary['selected']['id']))
    wanted={ord(c) for c in chars};found={}
    with gzip.open(run/'观测视图.jsonl.gz','rt',encoding='utf-8') as vf,gzip.open(run/'编码'/(selected['id']+'.jsonl.gz'),'rt',encoding='utf-8') as cf:
        for v,c in zip(vf,cf):
            row=json.loads(c)
            if row['cp'] not in wanted:continue
            view=json.loads(v)
            for code in row['codes']:
                code['meanings']=[selected['dictionary'][i][key] for i,key in enumerate(code['code'][:3])]+[summary['fourth'][code['code'][-1]]['meaning']]
                code['fourthTargets']=[view['views'][i]['target'] for i in code['views']]
            found[row['char']]={**row,'font':view['font']}
    return {'strategy':selected['id'],'characters':[found.get(c,{'char':c,'status':'outside-experiment-scope'}) for c in dict.fromkeys(chars)]}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path)
    parser.add_argument('--validate',action='store_true');parser.add_argument('--chars',default='○◯Oo〇0CϹJj')
    parser.add_argument('--strategy');args=parser.parse_args();run,summary=load_run(args.run)
    print(json.dumps(validate(run,summary) if args.validate else inspect(run,summary,args.chars,args.strategy),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
