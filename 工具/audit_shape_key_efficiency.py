"""Read-only canonical ABCD audit. Writes isolated evidence, never runtime bindings."""
import argparse
import collections
import functools
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'工具'), str(ROOT/'原型/键位编辑器')]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


def review_sheet(out):
    """Enlarge locked glyph atlas cells; do not infer size classes from this sheet."""
    from PIL import Image, ImageDraw, ImageFont
    base = 'http://127.0.0.1:8765/api/shape-overview/'
    q = json.load(urlopen(base+'query?allocation=1&prefix=iots',timeout=60))
    cps = [r['cp'] for r in q['rows']] + list(map(ord, ['D','O','Q','◎','◉']))
    assert q['total'] == 7, 'This review sheet is pinned to the seven-candidate audit'
    canvas = Image.new('RGB', (960, math.ceil(len(cps)/6)*200), 'white')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',17)
    sources = []
    for i, cp in enumerate(cps):
        d = json.load(urlopen(base+'detail?allocation=1&cp='+str(cp),timeout=60))
        p = d['preview']; src = ROOT/'原型/键位编辑器'/p['url']
        x, y = (i%6)*160, (i//6)*200
        with Image.open(src) as im:
            crop = im.crop((p['x'],p['y'],p['x']+64,p['y']+64)).convert('RGB').resize((128,128),Image.Resampling.NEAREST)
        canvas.paste(crop,(x+16,y+35))
        draw.text((x+10,y+7),'U+%04X'%cp,font=font,fill='black')
        draw.text((x+10,y+170),'iots' if i<7 else 'control',font=font,fill='black')
        sources.append(dict(cp=cp, preview=p, sourceSHA256=sha(src)))
    canvas.save(out/'iots七字与圆主体对照.png')
    save(out/'原图来源与审核边界.json',dict(sources=sources,method='64px locked atlas, 2x nearest-neighbour; shape only, not size',
         humanDecision=False, outputSHA256=sha(out/'iots七字与圆主体对照.png')))


def verify_output(out):
    """Replay saved representative ranks against live API and summarize lookup cost."""
    from urllib.parse import urlencode
    import shape_overview as so
    def api(endpoint, **params):
        return json.load(urlopen('http://127.0.0.1:8765/api/shape-overview/'+endpoint+'?'+urlencode(params), timeout=60))
    reps = json.loads((out/'代表字实际候选顺序与对象.json').read_text(encoding='utf-8'))
    checks = 0
    for r in reps:
        for a in r['paths']:
            d = api('query', allocation=1, prefix=a['code'], offset=(a['page60']-1)*60)
            assert d['total'] == a['candidates']
            assert d['rows'][(a['rank']-1)%60]['cp'] == r['cp']
            checks += 1
    codes = json.loads((out/'逐码候选与前缀缩减.json').read_text(encoding='utf-8'))
    chars = json.loads((out/'逐字形族与规范路径负担.json').read_text(encoding='utf-8'))
    full = [r for r in codes if len(r['code']) == 4]
    bins = {label: sum(lo <= r['candidates'] <= hi for r in full) for label, lo, hi in
            [('1',1,1),('2—10',2,10),('11—60',11,60),('61—120',61,120),('121—500',121,500),('501及以上',501,10**9)]}
    overview = so.get_overview()
    r2, r3 = (set(overview.key_members(n, 'r', True)) for n in (2,3))
    summary = json.loads((out/'验收与统计摘要.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/p) == h for p,h in summary['protectedHashes'].items())
    live = api('bootstrap')
    receipt = dict(rankAndPageLiveChecks=checks, allPassed=True, fullCodeCandidateBins=bins,
        fourCodePairs=sum(r['registeredHolders'] for r in full),
        registeredShortCodePairs=sum(r['registeredHolders'] for r in codes if len(r['code'])==3),
        fullCodeHolders=sum(r['fullCodes']>0 for r in chars),
        shortOnlyHolders=sum(r['totalCodes']>0 and r['fullCodes']==0 for r in chars),
        oldBestCandidateDistribution=distribution(r['oldBestCandidates'] for r in chars if r.get('oldBest')),
        allBestCandidateDistribution=distribution(min(v for v in [r.get('oldBestCandidates'),r.get('newBestCandidates')] if v is not None)
                                                for r in chars if r.get('oldBest') or r.get('newBest')),
        radialMembership=dict(second=len(r2),third=len(r3),intersection=len(r2&r3),secondOnly=len(r2-r3),thirdOnly=len(r3-r2)),
        scopeQueueUnchanged=live['structureBindings']['statistics']['wholeScopePending'],
        historicalMissing=live['allocationQueueCounts']['historical'],protectedHashesStillMatch=True)
    save(out/'线上候选顺序分页验收.json', receipt)
    print(json.dumps(receipt,ensure_ascii=False))


def distribution(values):
    a = sorted(values)
    if not a:
        return {'n': 0}
    return dict(n=len(a), min=a[0], median=a[(len(a)-1)//2],
                p90=a[math.ceil(len(a)*.9)-1], p95=a[math.ceil(len(a)*.95)-1],
                p99=a[math.ceil(len(a)*.99)-1], max=a[-1], mean=sum(a)/len(a))


def run(out):
    import shape_overview as so
    if (out/'验收与统计摘要.json').exists() or (out/'圆主体两字独立候选差异.json').exists():
        raise FileExistsError('已有冻结核查材料可能被人工审议引用；请使用新的独立输出目录')
    out.mkdir(parents=True, exist_ok=True)
    protected = [ROOT/p for p in [
        '数据/三模式/规则库/四键实验/人工审议.json',
        '原型/键位编辑器/data/structure-count-bindings.json',
        '原型/键位编辑器/data/pictorial-exclusive-allocation.json',
        '原型/键位编辑器/shape_overview.py', '原型/键位编辑器/shape-key-overview.js',
        '原型/键位编辑器/shape-key-overview.html', '原型/键位编辑器/subject_scope_bindings.py',
        '原型/键位编辑器/shape_structure_bindings.py', '原型/键位编辑器/bucket_order_query.py',
        '原型/键位编辑器/round_subject_refinement.py',
        '数据/三模式/全形核对版.json']]
    protected += [so.structure.active_report_path(), so.PROJECT/so.subject.policy()['proofReport']]
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    (out/'git-status-before.txt').write_bytes(subprocess.check_output(
        ['git', '-c', 'core.quotePath=false', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=ROOT))
    overview = so.get_overview()
    # Audit-local cache of the existing backend, no source/runtime mutations.
    overview.allocation_members = functools.lru_cache(None)(overview.allocation_members)
    overview.chunk = functools.lru_cache(None)(overview.chunk)
    rows = {cp: overview.brief(cp, True) for cp in overview.rows if cp not in so.exclusive_intake()}
    actual = collections.defaultdict(set)
    for cp, r in rows.items():
        for code in set(r['codes']):
            actual[code].add(cp)
    for code, cps in actual.items():
        assert cps <= set(overview.allocation_members(code)), ('unreachable', code)
        if len(code) == 4:
            assert cps == set(overview.allocation_members(code)), ('full-code-mismatch', code)
    full = {c: s for c, s in actual.items() if len(c) == 4}
    short = {c: s for c, s in actual.items() if len(c) == 3}
    code_counts = {c: len(overview.allocation_members(c)) for c in actual}
    # Exact registered three-letter codes differ from their query-prefix union.
    metrics = [dict(code=c, candidates=code_counts[c], registeredHolders=len(cps),
                    parentCandidates=len(overview.allocation_members(c[:-1])),
                    reduction=len(overview.allocation_members(c[:-1]))-code_counts[c])
               for c, cps in sorted(actual.items())]
    save(out/'逐码候选与前缀缩减.json', metrics)
    keys = []
    for pos in range(1, 5):
        for k in so.LETTERS:
            route_cps = {cp for c, cps in actual.items() if len(c) >= pos and c[pos-1] == k for cp in cps}
            browse = set(overview.key_members(pos, k, True))
            keys.append(dict(position=pos, key=k, routeHolders=len(route_cps), browseMembers=len(browse),
                             routeOnly=sorted(route_cps-browse), browseOnly=sorted(browse-route_cps)))
    save(out/'逐位逐键去重人数.json', keys)
    chars, anomalies, size_issues, fill_repeats, duplicates = [], [], [], [], []
    scope_errors = []
    details = {}
    targets = set(map(ord, ['O','Q','ρ','ộ','D','8','ᛒ','ȣ','𞥕','*','☆','★','⁂','Ḍ','Ḑ','◎','◉']))
    for i, (cp, brief) in enumerate(sorted(rows.items())):
        if not brief['codes']:
            chars.append(dict(cp=cp, char=chr(cp), primaryFamily=brief['familyKey'], alternateFamilies=[],
                              fullCodes=0, shortCodes=0, totalCodes=0, objectSignatures=0))
            continue
        d = overview.detail(cp, True)
        if cp in targets:
            details[cp] = d
        paths = d['paths']
        assert set(p['code'] for p in paths) == set(brief['codes']), ('brief/detail', cp)
        old = [p['code'] for p in paths if not p.get('structuralCollection') and not p.get('subjectAttachment') and not p.get('roundSubjectRefinement')]
        new = [p['code'] for p in paths if p.get('structuralCollection') or p.get('subjectAttachment') or p.get('roundSubjectRefinement')]
        def best(cs, length=4):
            cs = [c for c in cs if len(c) == length]
            return min(cs, key=lambda c: (code_counts[c], c)) if cs else None
        signatures = collections.defaultdict(list)
        objects = {x['id']: x for x in d['objects']}
        for p in paths:
            for e in p.get('evidence', []):
                third, fourth = e.get('objectId'), e.get('fourthObjectId')
                if third != fourth:
                    anomalies.append(dict(cp=cp, code=p['code'], evidence=e))
                if p.get('structuralCollection') and (e.get('familyTarget') != 'whole-glyph' or
                        objects.get(third, {}).get('type') != 'whole-glyph-collection'):
                    scope_errors.append(dict(cp=cp, code=p['code'], evidence=e))
                obj = objects.get(third, {})
                # Signature describes the recorded object + rule, not independent human lookup ideas.
                sig = (p['code'][:3], e.get('rule'), obj.get('kind', obj.get('type')),
                       tuple(obj.get('bbox', [])), e.get('familyTarget'))
                signatures[sig].append(p['code'])
                if len(p['code']) == 4 and p['code'][-1] in 'zxcv':
                    attr = e.get('attribute', '')
                    if '字号' in attr and obj.get('kind') not in ('body',):
                        size_issues.append(dict(cp=cp, char=chr(cp), code=p['code'], objectId=third,
                                                kind=obj.get('kind'), attribute=attr))
                if len(p['code']) == 4 and p['code'][-1] in 'ef' and e.get('rule') == 'topology.no_hole':
                    fill_repeats.append(dict(cp=cp, code=p['code'], evidence=e))
        for sig, cs in signatures.items():
            cs = sorted(set(cs))
            if len(cs) > 1:
                duplicates.append(dict(cp=cp, codes=cs, signature=list(sig),
                                       identicalCandidates=len({frozenset(actual[c]) for c in cs}) == 1))
        routes = sorted({r['familyKey'] for r in d['familyRoutes'] if not r.get('compatibilityOnly')})
        ob, nb = best(old), best(new)
        chars.append(dict(cp=cp, char=chr(cp), primaryFamily=d['familyKey'],
            primaryBrowseMember=cp in set(overview.key_members(2, d['familyKey'], True)) if cp in targets else None,
            alternateFamilies=[f for f in routes if f != d['familyKey']],
            reachableFamilies=sorted({c[1] for c in brief['codes']}),
            fullCodes=sum(len(c)==4 for c in brief['codes']), shortCodes=sum(len(c)==3 for c in brief['codes']),
            totalCodes=len(set(brief['codes'])), compatibilityCodes=[p['code'] for p in paths if p.get('compatibilityOnly')],
            wholeCountCodes=[p['code'] for p in paths if p.get('structuralCollection')],
            subjectAttachmentCodes=[p['code'] for p in paths if p.get('subjectAttachment')],
            objectSignatures=len(signatures), oldBest=ob, newBest=nb,
            oldBestCandidates=code_counts.get(ob), newBestCandidates=code_counts.get(nb),
            preferred=brief['preferredCodes']))
        if i % 4000 == 0:
            print('audited', i, flush=True)
    save(out/'逐字形族与规范路径负担.json', chars)
    save(out/'对象一致性与冗余线索.json', dict(objectMismatch=anomalies, wholeCountScopeErrors=scope_errors,
        wholeEmOnNonBody=size_issues, noHoleAndFillSamePath=fill_repeats, sameObjectRuleMultipleCodes=duplicates))
    same = collections.defaultdict(list)
    for c, cps in full.items():
        same[(c[:3], frozenset(cps))].append(c)
    equivalent = [dict(codes=sorted(cs), candidates=len(s[1])) for s, cs in same.items() if len(cs)>1]
    save(out/'候选集合相同的末位组.json', equivalent)
    report = so.structure.review_report()
    triage = so.read(so.RUNS/'20261024-structure-count-bindings-v4/范围待核2083字续查分流.json')
    assert collections.Counter(r['group'] for r in triage['records']) == {'local':1307,'proof':443,'shape':333}
    assert set(r['cp'] for r in triage['records']) == set(so.structure.queues()['scopePending'])
    save(out/'2083本批相关身份交叉.json', [r for r in triage['records'] if r['cp'] in targets])
    reps = []
    for cp in sorted(targets):
        d = details[cp]
        record = next(r for r in chars if r['cp'] == cp)
        paths = []
        for p in d['paths']:
            c = p['code']; members = overview.allocation_members(c)
            ordered = [n for t in range(4) for n, tier in members.items() if tier == t]
            rank = ordered.index(cp)+1
            paths.append(dict(p, candidates=len(members), rank=rank, page60=(rank-1)//60+1,
                              nextClicks60=(rank-1)//60, rotated=c[1:]+c[0],
                              kind='整字计数路' if p.get('structuralCollection') else '主体附件路' if p.get('subjectAttachment') else '圆主体单字入口' if p.get('roundSubjectRefinement') else '旧路'))
        reps.append(dict(record, paths=paths, objects=d['objects'], familyRoutes=d['familyRoutes'], preview=d.get('preview')))
    save(out/'代表字实际候选顺序与对象.json', reps)
    ots = sorted(overview.allocation_members('iots'))
    # Independent review candidate: mark only two non-round subjects compatible, preserve every query path.
    candidate = dict(status='AI-isolated-proposal-not-integrated', characters=['Ḍ','Ḑ'],
        action='o形族浏览排除；全部旧码保留并标兼容；不自动派k或新附件码',
        beforeRound=len(overview.key_members(2,'o',True)),
        proposedRound=len(set(overview.key_members(2,'o',True))-{ord('Ḍ'),ord('Ḑ')}),
        iotsBefore=ots, iotsAfterPreservingCompatibility=ots,
        optionalFilteredCurrentRoundIots=sorted(set(ots)-{ord('Ḍ'),ord('Ḑ')}),
        pathDelta=0, coverageDelta=0, preferredDelta=0,
        warning='过滤视图5人不等于现行完整码候选7人变成5人；不能把兼容查询删除伪装为成员清理')
    if so.round_refinement.policy():
        candidate.update(status='accepted-refinement-already-integrated-current-snapshot',
                         action='两字各保留ioki，其余13条已撤；O的ioqc已接入',
                         pathDelta=0,warning='当前快照；原确认前候选继续按冻结SHA追溯，不覆盖原件。')
    save(out/'圆主体两字独立候选差异.json', candidate)
    after = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    assert before == after
    assert not anomalies and not scope_errors
    totals = dict(characters=len(rows), withPaths=sum(bool(r['codes']) for r in rows.values()),
        firstOnly=sum(not r['codes'] for r in rows.values()), paths=sum(len(r['codes']) for r in rows.values()),
        completeCodes=len(full), registeredShortCodes=len(short),
        fullCodeCandidates=distribution(len(v) for v in full.values()),
        fullPathsPerCharacter=distribution(r['fullCodes'] for r in chars if r['totalCodes']),
        shortPathsPerCharacter=distribution(r['shortCodes'] for r in chars if r['totalCodes']),
        alternateFamiliesPerCharacter=distribution(len(r['alternateFamilies']) for r in chars if r['totalCodes']),
        noReductionFullCodes=sum(m['reduction']==0 for m in metrics if len(m['code'])==4),
        equivalentSuffixGroups=len(equivalent), objectMismatch=len(anomalies), wholeCountScopeErrors=len(scope_errors),
        noHoleAndFillSamePath=len(fill_repeats), wholeEmOnNonBody=len(size_issues))
    comparisons=collections.Counter()
    for r in chars:
        if r.get('newBest'):
            a,b=r['oldBestCandidates'],r['newBestCandidates']
            comparisons['new-only' if a is None else 'better' if b<a else 'equal' if b==a else 'worse']+=1
    live = json.load(urlopen('http://127.0.0.1:8765/api/shape-overview/bootstrap', timeout=60))
    assert live['structureBindings']['version']==so.structure.data()['version']
    assert live['exclusiveIntake']['geometryPaths']==totals['paths']
    assert live['exclusiveIntake']['geometryWithPaths']==totals['withPaths']==19840
    save(out/'验收与统计摘要.json', dict(version=so.structure.data()['version'], totals=totals,
        newVsOldBest=dict(comparisons), protectedUnchanged=True, protectedHashes=before,
        pending={'local':1307,'proof':443,'shape':333,'historical':84},
        runtimeChanged=False, naturalKeyHumanTest='未取得新答复，候选排序/页数是机器实测，不是人的自然程度或耗时',
        liveIntake=live['exclusiveIntake']))
    print(json.dumps(dict(totals=totals, newVsOldBest=dict(comparisons)),ensure_ascii=False),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--verify-output', action='store_true')
    p.add_argument('--review-sheet', action='store_true')
    args = p.parse_args()
    if args.verify_output and args.review_sheet:
        p.error('Choose one audit mode')
    (review_sheet if args.review_sheet else verify_output if args.verify_output else run)(args.output_dir)
