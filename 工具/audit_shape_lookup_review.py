"""Rebuild only reviewed examples; never label this as a full codebook."""
import argparse
import json
from collections import defaultdict
from statistics import median
from pathlib import Path

from build_shape_keyboard_full import rebuild_row, validate_row, save, VERSION
from shape_candidate_layers import CandidateLayers, LAYERS
from shape_keyboard_trial import DATA, PROJECT, ROOT, load, fingerprint, trial_definitions, outline_anchors
from shape_reviewed_routes import frame_lookup_decisions


def audit(output):
    manifest = load(DATA / '全形核对版.json')
    index_path = PROJECT / manifest['indexPath']
    baseline = load(index_path.parent / 'shape-experiment.json')
    index = load(index_path)
    definitions = trial_definitions(index)
    anchors = outline_anchors(Path('C:/Windows/Fonts/seguisym.ttf'))
    chars = '𒌒𒌷𒀖ﻄﻈᕣTᵏ○●'
    rows = [rebuild_row(r, definitions, index['bucketGroups'], anchors, {})[0]
            for r in baseline['records'] if r['char'] in chars]
    by_char = {r['char']: r for r in rows}
    assert set(by_char) == set(chars)
    for row in rows:
        validate_row(row, definitions)
    assert not any(r.get('spineEvidence', {}).get('orientation') == 0 for r in by_char['ﻄ']['familyRoutes'])
    assert any(r.get('spineEvidence', {}).get('orientation') == 0 for r in by_char['ﻈ']['familyRoutes'])
    loop = next(r for r in by_char['ᕣ']['familyRoutes'] if r.get('reviewedLoopEvidence'))
    assert loop['familyKey'] == 'p' and loop['supplementOnly']
    view = CandidateLayers(rows)
    assert view.suggestions(ord('T'))[0]['code'] == 'chmw'
    assert ord('ᵏ') in view.query('qhm')['candidates']
    for prefix, entries in view.entries.items():
        result = view.query(prefix)
        assert result['mode'] == 'all' and set(result['candidates']) == set(entries)
        assert list(result['groups']) == list(LAYERS)
    previous = ROOT / '键位试验/20261021-connected-frames-v1'
    old = {r['char']:r for p in sorted((previous/'details').glob('*.json')) for r in load(p)['records'] if r['char'] in chars}
    changes = []
    for row in rows:
        before, after = {p['code'] for p in old[row['char']]['paths']}, {p['code'] for p in row['paths']}
        removed, added = sorted(before-after), sorted(after-before)
        assert not removed or (row['char']=='ﻄ' and all(c.startswith('wll') for c in removed))
        assert row['bucket'] == old[row['char']]['bucket']
        changes.append({'char':row['char'], 'removed':removed, 'added':added,
                        'preferred':[p['code'] for p in row['paths'] if p['preferred']],
                        'firstKeyOnly':not row['paths']})
    report = {'passed':True, 'version':VERSION, 'scope':'targeted-reviewed-examples-only-not-full-build',
              'decisions':frame_lookup_decisions(), 'ordinaryCharactersRebuilt':len(rows),
              'onlyExplicitlyRejectedPathsRemoved':True, 'allModePreservesEveryCandidate':True,
              'runtimeDeployed':False, 'fullBuildPending':True, 'changes':changes,
              'reviewSHA256':fingerprint(ROOT/'人工审议.json')}
    details = {'status':'targeted-not-release-index','records':rows}
    if output.exists():
        assert load(output/'查法答复定点验收.json') == report, 'Existing audit differs; choose a new output'
        assert load(output/'已核字详情.json') == json.loads(json.dumps(details)), 'Existing details differ'
    else:
        save(output/'查法答复定点验收.json',report)
        save(output/'已核字详情.json',details)
    print(json.dumps(report, ensure_ascii=True))


def verify_full(before, after):
    old_index, new_index = [load(p/'发布核对索引.json') for p in (before,after)]
    old, new = [{r['cp']:r for r in index['records']} for index in (old_index,new_index)]
    assert set(old)==set(new)
    assert old_index['collections']==new_index['collections']
    assert old_index['unclassified']==new_index['unclassified']
    changes, recovered, lost, preferred_changes = [], [], [], []
    for cp, row in new.items():
        previous=old[cp]
        assert row['bucket']==previous['bucket'] and row['familyKey']==previous['familyKey']
        a,b=set(previous['codes']),set(row['codes'])
        if a!=b:
            assert row['char'] in 'ﻄᕣ', row['char']
            changes.append({'char':row['char'],'added':sorted(b-a),'removed':sorted(a-b)})
        if not a and b:
            recovered.append(row['char'])
        if a and not b:
            lost.append(row['char'])
        if set(previous['preferredCodes'])!=set(row['preferredCodes']):
            assert row['char'] in 'ﻄᕣT'
            preferred_changes.append({'char':row['char'],'before':previous['preferredCodes'],'after':row['preferredCodes']})
    by_char={r['char']:r for r in new.values()}
    assert next(c for c in changes if c['char']=='ﻄ')['removed']==['wllg','wllh','wlls','wllv']
    assert next(c for c in changes if c['char']=='ᕣ')['added']==['ipwe','ipwm','ipwx']
    assert by_char['T']['preferredCodes']==['chmw'] and 'chvc' in by_char['T']['codes']
    for char in '𒌒𒌷𒀖':
        frames=[r for r in by_char[char]['familyRoutes'] if r.get('frameEvidence')]
        assert frames and all(r['familyKey']=='s' and r['supplementOnly'] and r.get('reviewedRetain') for r in frames)
    policy=new_index['definitions']['candidatePresentationProposal']
    assert policy['defaultMode']=='all' and policy['allModeRetainsEveryCandidate']
    cohort={cp for cp in new if old[cp]['codes'] and new[cp]['codes']}
    distributions=[]
    for records in (old,new):
        prefixes=defaultdict(set)
        for cp in cohort:
            row=records[cp]
            prefixes[row['bucket']].add(cp)
            for route in row['familyRoutes']:
                prefixes[route['bucket']+route['familyKey']].add(cp)
            for code in row['codes']:
                for n in range(1,len(code)+1):
                    prefixes[code[:n]].add(cp)
        dist={}
        for n in range(1,5):
            counts=[len(v) for k,v in prefixes.items() if len(k)==n]
            dist[str(n)]={'occupied':len(counts),'maximumCandidates':max(counts,default=0),
                          'medianCandidates':median(counts) if counts else 0,
                          'totalCandidateAssociations':sum(counts)}
        distributions.append(dist)
    assert distributions[0]==distributions[1], 'Unexpected same-cohort path change'
    provenance=load(after/'构建来源.json')
    assert all(fingerprint(PROJECT/'工具'/name)==value for name,value in provenance['codeHashes'].items())
    report={'passed':True,'before':old_index['id'],'after':new_index['id'],
            'ordinary':len(new),'allFirstBucketsAndMainFamiliesUnchanged':True,
            'onlyApprovedCodeChanges':True,'changes':changes,'recoveredDetailed':recovered,
            'newlyFirstKeyOnly':lost,'preferredChanges':preferred_changes,
            'sameDetailedCohort':{'characters':len(cohort),'before':distributions[0],'after':distributions[1]},
            'sameCohortCollisionReductionAchieved':False,'allGroupedDefaultVerified':True,
            'sourceCodeHashesMatch':True,'runtimeDeployed':False,'status':'full-independent-rebuild-not-deployed'}
    save(after/'已确认查法全量验收.json',report)
    print(json.dumps(report,ensure_ascii=True))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    parser.add_argument('--before',type=Path)
    parser.add_argument('--after',type=Path)
    args=parser.parse_args()
    if args.before and args.after:
        verify_full(args.before,args.after)
    else:
        assert args.output
        audit(args.output)
