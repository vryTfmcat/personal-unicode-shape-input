"""One effective count semantics version; historical decisions stay immutable."""
import copy
import functools
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MODE='whole-continuous-total-v1'
FIELD='continuousTotalCountAcceptance20261027'


def active():
    import shape_structure_bindings as binding
    return binding.data().get('countSemanticsVersion')==MODE


@functools.lru_cache(maxsize=1)
def authority():
    a=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))[FIELD]
    assert a['decision']=='accepted' and a['batchReviewed'] and a['countSemanticsVersion']==MODE
    for key in ('baseReport','baseRuntime','reviewedPaths','jointProofs'):
        p=(ROOT/a['generation'][key]).resolve()
        assert p.is_relative_to(ROOT.resolve()) and hashlib.sha256(p.read_bytes()).hexdigest()==a['generation'][key+'SHA256']
    return a


def policy():
    return authority() if active() else None


def resolve_codes(cp,codes):
    if not active():return list(codes)
    import shape_structure_bindings as binding
    mapping=binding.data()['countMigration']['codeMap'].get(str(cp),{})
    return list(dict.fromkeys(mapping.get(c,c) for c in codes))


def effective_boundary(cp,source):
    if not active():return source
    import shape_structure_bindings as binding
    current=binding.record(cp)
    if not current:return source
    result=copy.deepcopy(source)
    result.update(countSelectionHistory={k:source.get(k) for k in ('selectedCodes','selectedFeatures','rejectedCodes','newCodes','basis')},
                  countSemanticsVersion=MODE,currentCodes=current['codes'])
    for key in ('selectedCodes','newCodes'):
        if key in result:result[key]=current['codes']
    result.pop('selectedFeatures',None)
    result['entryKeys']=sorted({c[2] for c in current['codes']})
    result['rejectedCodes']=[]
    result['basis']='整字形族/范围沿用原确认；当前j/q数量依全局直曲总数规则。原数量接受/拒绝见countSelectionHistory。'
    return result


def expected_code(key,prefix,stats):
    fields=dict(a='corners',b='forks',g='crosses',j='straightStrokes',q='curveStrokes')
    n=stats[fields[key]]
    if not n:return None
    if active() and key in 'jq':
        assert all(type(stats.get(k)) is int and stats[k]>=0 for k in ('straightStrokes','curveStrokes'))
        assert stats.get('uncertainStrokes')==0
        n=stats['straightStrokes']+stats['curveStrokes']
    return prefix+key+{1:'u',2:'b',3:'t',4:'y',5:'p'}[min(n,5)]


def note():
    return 'j为含直入口、q为含曲入口；仅保留既有选择条件。两者第四位统一数同一个整字直曲连续组总集合，≥5用p；不是手写笔画或原始短段。a/b/g仍数角点/三叉/四叉，O的ioqc等非计数例外不变。'
