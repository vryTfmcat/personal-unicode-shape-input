"""Rebuild immutable keyboard proposals from versioned observations and new facts."""
from __future__ import annotations

import argparse
import collections
import copy
import json
import time
from pathlib import Path

import numpy as np

from build_shape_experiment import protected_inputs
from shape_experiment_features import observe, render
from shape_keyboard_trial import (PROJECT, DATA, ROOT, OUTLINES, SIZE_KEYS, load,
                                  fingerprint, trial_definitions, outline_anchors,
                                  line_group, extension_facts, trial_facts,
                                  make_paths, trial_properties)
from shape_reviewed_routes import amend, calibrate, references, frame_lookup_decisions
from shape_family_boundaries import VERSION as BOUNDARY_VERSION, LIMITS, retained_legacy_characters, lookup_boundary_decisions
from shape_stroke_groups import stable_stroke_group, VERSION as STROKE_GROUP_VERSION

VERSION = 'keyboard-full-20261021-v14'


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    temp.replace(path)


def refresh_metadata(output):
    """Recount primary memberships after line-group repairs; keep old exemplars scoped."""
    path = output / '发布核对索引.json'
    index = load(path)
    for group in index['bucketGroups']:
        if group['coarse'] == '闭环' and 'b' in index['definitions']['families'] and 'b' not in group['families']:
            group['families'].append('b')
        group['count'] = sum(r['bucket'] == group['bucket'] and r['familyKey'] in group['families']
                             for r in index['records'])
    if 'representatives' in index:
        index['baselineRepresentatives'] = index.pop('representatives')
    index['metadataScope'] = 'bucketGroups counts are current primary memberships; baselineRepresentatives are historical'
    save(path, index)
    provenance_path = output / '构建来源.json'
    if provenance_path.exists():
        provenance = load(provenance_path)
        provenance['metadataFinalizerSHA256'] = fingerprint(Path(__file__))
        save(provenance_path, provenance)


def legacy_facts(row, route):
    objects = {o['id']: o for o in row['objects']}
    unique = {}
    for path in row['paths']:
        if path['code'][:2] != route['bucket'] + route['familyKey']:
            continue
        for e in path['evidence']:
            if e['familyTarget'] != route['target']:
                continue
            key = (e['third'], e['rule'], e['objectId'], e['condition'])
            unique[key] = {'third': e['third'], 'function': e['rule'],
                           'object': copy.deepcopy(objects[e['objectId']]),
                           'reason': e['condition'], 'status': e['status']}
    return list(unique.values())


def line_bucket(groups, ratio):
    proportion = 'tall' if ratio < .8 else 'wide' if ratio > 1.25 else 'balanced'
    return next(g['bucket'] for g in groups if g['coarse'] == '线与转折' and g['proportion'] == proportion)


def expand(route, observations, definitions, output, objects):
    normalized = []
    for fact in observations:
        fact = copy.deepcopy(fact)
        o = fact['object']
        # Family interpretations can share geometry but carry different cohort
        # metadata. Keep their object identities separate instead of overwriting.
        o['id'] = route['target'] + ':' + route['familyKey'] + ':' + o['id'].split(':')[-1]
        if o['id'] in objects:
            assert objects[o['id']] == o, 'Conflicting object definitions'
        objects[o['id']] = o
        normalized.append(fact)
    for path in make_paths(route['bucket'], route['familyKey'], normalized, definitions):
        item = output.setdefault(path['code'], {'code': path['code'], 'evidence': [], 'preferred': False})
        item['preferred'] |= path['preferred']
        for e in path['evidence']:
            evidence = {'rule': e['rule'], 'third': path['code'][2],
                        'objectId': e['object']['id'], 'fourthObjectId': e['fourthObjectId'],
                        'familyTarget': route['target'], 'familyId': route['familyId'],
                        'attribute': e['attribute'], 'status': 'machine-proposal'}
            if evidence not in item['evidence']:
                item['evidence'].append(evidence)


def validate_row(row, definitions):
    for proof in row.get('collisionSanityExclusions', []):
        assert proof['scope'] == 'negative-certificate-not-low-prototype-score'
        assert len(proof['variants']) == 9
        assert {(v['size'],v['weight']) for v in proof['variants']} == {(s,w) for s in (48,96,128) for w in (-1,0,1)}
        assert not any(r['target']=='body' and r['familyKey']==proof['familyKey'] for r in row['familyRoutes'])
    objects = {o['id']: o for o in row['objects']}
    partitions = {}
    for route in row['familyRoutes']:
        if route.get('connectedStrokeGroupEvidence'):
            evidence=route['connectedStrokeGroupEvidence']
            proof=evidence['proof']
            assert route['target']=='body' and route['familyKey']=='h'
            assert proof['memberCount'] in (2,3) and proof['memberOrientation']=='h'
            assert proof['groupArrangement']=='i' and proof['overlapPixels']==0
            assert sum(proof['memberPixels'])==proof['groupPixels']
            assert proof['groupPixels']+proof['remainderPixels']==proof['parentPixels']
            assert len(evidence['stabilityProof']['variants'])==9
            assert all(v['proof']['memberCount']==proof['memberCount'] for v in evidence['stabilityProof']['variants'])
        if route.get('reviewedLoopEvidence'):
            proof = route['reviewedLoopEvidence']
            decision = frame_lookup_decisions()['irregularLoopSupplement']
            assert row['char'] == decision['char'] and route['familyKey'] == decision['familyKey']
            assert route['supplementOnly'] and proof['familyKey'] is None
            assert proof['kind'] == 'visible-connected-frame' and proof['overlapPixels'] == 0
            assert proof['framePixels'] + proof['remainderPixels'] == proof['parentPixels']
        if route.get('frameEvidence'):
            proof = route['frameEvidence']
            assert proof['kind']=='visible-connected-frame' and proof['overlapPixels']==0
            assert proof['framePixels']+proof['remainderPixels']==proof['parentPixels']
            assert proof['familyKey']==route['familyKey'] and route['supplementOnly']
            if proof['polygonFace']:
                assert proof['polygonFace']['beyondOnePixelBoundaryFraction']<=.015
            else:
                assert proof['prototypeError']<={'o':.035,'s':.045,'t':.05}[route['familyKey']]
        if route.get('spineEvidence'):
            proof=route['spineEvidence']
            assert proof['kind']=='visible-border-spine' and proof['overlapPixels']==0
            assert proof['spinePixels']+proof['remainderPixels']==proof['parentPixels']
            assert proof['minimumColumnOrRowOccupancy']>=.92
        if route.get('localBranchProof'):
            proof = route['localBranchProof']
            assert proof['test'] == 'visible-ink-fork-annuli'
            assert proof['visiblePortCounts'] == [proof['armCount']]*2
            assert proof['armCount'] in (3, 4) and max(proof['diskInkDensities']) <= .72
            assert any(s.get('target') == route['target'] and s.get('key') == 'h'
                       for s in row.get('semantic', {}).get('routes', []))
            assert all(fact['third'] == 'm' and fact['object']['kind'] == 'junction'
                       for fact in route['reviewedObjectFacts'])
        if route.get('componentPartitionProof'):
            proof = route['componentPartitionProof']
            assert proof['kind'] == 'cycle-tail' and proof['overlapPixels'] == 0
            assert proof['ringPixels'] + proof['tailPixels'] == proof['parentPixels']
            assert route['target'] == 'cycle-subject'
            assert any(fact['third'] == 'y' for fact in route['reviewedObjectFacts'])
        if route.get('objectPartitionProof'):
            proof = route['objectPartitionProof']
            assert proof['overlapPixels'] == 0
            assert proof['spinePixels'] + proof['arcPixels'] == proof['parentPixels']
            partitions.setdefault(proof['sourceInkSHA256'], set()).add(route['target'])
    assert all(targets == {'reviewed-spine', 'reviewed-half-arc'} for targets in partitions.values())
    seen = set()
    actual = collections.defaultdict(set)
    for p in row['paths']:
        code = p['code']
        assert code not in seen and len(code) in (3, 4)
        seen.add(code)
        for e in p['evidence']:
            o = objects[e['objectId']]
            assert e['objectId'] == e['fourthObjectId']
            assert code[2] == e['third'] and code[2] in definitions['third']
            assert e['rule'] == definitions['third'][code[2]]['function']
            assert any(code[:2] == r['bucket'] + r['familyKey'] and e['familyTarget'] == r['target']
                       for r in row['familyRoutes'])
            key = (code[:3], e['objectId'], e['rule'], e['familyTarget'])
            actual[key].add(code[3:])
            if len(code) == 4:
                assert code[-1] in definitions['fourth']
                assert (code[-1], e['attribute']) in trial_properties(o, code[1], definitions.get('sizePolicy'))
                assert not (o['kind'] == 'junction' and code[-1] in SIZE_KEYS)
                if code[-1] in 'ef':
                    assert o['kind'] == 'body' and o.get('fill') == ('hollow' if code[-1] == 'e' else 'solid')
                if code[-1] in 'bt':
                    assert o['kind'] == 'part-group'
                    assert o['memberCount'] == len(o['memberCentres']) == (2 if code[-1] == 'b' else 3)
                if '排列轴' in e['attribute']:
                    points = np.array(o['memberCentres'])
                    dx, dy = np.ptp(points, axis=0)
                    assert (code[-1] == 'h' and dx > 4 * max(dy, .1)) or (code[-1] == 'i' and dy > 4 * max(dx, .1))
                if '整体尖端' in e['attribute']:
                    assert o['kind'] == 'part-group' and o['memberCount'] == 3
                    points = sorted(o['memberCentres'], key=lambda p: p[1])
                    lo, hi = points[1][1] - points[0][1], points[2][1] - points[1][1]
                    assert (code[-1] == 'w' and lo > hi) or (code[-1] == 's' and hi > lo)
    for (prefix, oid, _, _), suffixes in actual.items():
        expected = {k for k, _ in trial_properties(objects[oid], prefix[1], definitions.get('sizePolicy'))} or {''}
        assert suffixes == expected, (row['cp'], prefix, oid, 'Missing property paths')
    return sum(len(p['evidence']) for p in row['paths'])


def rebuild_row(row, definitions, groups, anchors, fonts, templates=None):
    row = copy.deepcopy(row)
    old_codes = {p['code'] for p in row['paths']}
    old_family, old_bucket = row['familyKey'], row['bucket']
    old_routes = {(r['familyKey'], r['target']) for r in row['familyRoutes']}
    f = row.get('features')
    rendered = None

    def fresh():
        nonlocal rendered
        if rendered is None:
            font = row['font']
            mask, extent = render(row['char'], font['path'], font.get('index', 0), fonts=fonts)
            rendered = observe(mask, extent)
        return rendered

    semantic = row.get('semantic', {})
    bind_double = semantic.get('primaryFamilyId') == 'family.double-loop'
    amendments = []
    if f and (old_family or bind_double):
        templates = templates or references(Path('C:/Windows/Fonts/seguisym.ttf'))
        routes, family, bucket, amendments = amend(row, fresh(), groups, anchors, templates)
        row['familyRoutes'], row['familyKey'], row['bucket'] = routes, family, bucket
        if family:
            row['familyId'] = definitions['families'][family]['id']
        else:
            row['familyId'] = None
    output, objects = {}, {}
    for route in row['familyRoutes']:
        if route.get('reviewedObjectFacts'):
            obs = route['reviewedObjectFacts']
        elif route.get('newGeometryBasis'):
            obs = trial_facts(fresh(), route['familyKey'], anchors)
        else:
            obs = legacy_facts(row, route)
            if route['target'] == 'body' and f:
                # Only body routes acquire new whole-subject/group facts. Inner
                # interpretations remain bound to their original observed object.
                if route['familyKey'] in OUTLINES or len(f['parts']) > 1:
                    obs += extension_facts(fresh(), route['familyKey'], anchors)
        if route['target'] == 'body' and route['familyKey'] in ('o', 's'):
            calibrate(obs, fresh(), route['familyKey'], anchors)
        if route['target']=='body' and route['familyKey']=='h':
            group=stable_stroke_group(row,fresh())
            if group is not None:
                route['connectedStrokeGroupEvidence']={'proof':group['proof'],'stabilityProof':group['stabilityProof']}
                obs=obs+[{'third':'z','function':definitions['third']['z']['function'],'object':group['object'],
                          'reason':'原墨迹中的连接横笔组；不同于分离部件数，成员横向而整组纵向排列',
                          'status':'accepted-trial-object-proposal'}]
        expand(route, obs, definitions, output, objects)
    preferred = frame_lookup_decisions()['preferredPaths'].get(row['char'])
    if preferred:
        assert preferred in output, (row['char'], 'Reviewed preferred path disappeared')
        output[preferred]['preferred'] = True
        output[preferred]['reviewedPreference'] = 'frameLookupAcceptance20261021'
    row['paths'] = sorted(output.values(), key=lambda p: (not p['preferred'], p['code']))
    row['objects'] = list(objects.values())
    row['baselineFamilyKey'] = old_family
    row['baselineBucket'] = old_bucket
    row['routeAmendments'] = amendments
    new_codes = {p['code'] for p in row['paths']}
    exclusions = [reason for reason in amendments if reason.startswith('主体形族边界排除：')]
    row['familyBoundaryReview'] = {'excluded': exclusions, 'primaryUnresolved': row['familyKey'] is None}
    if row['familyKey'] is None and exclusions:
        row['status'] = 'main-family-unresolved-after-boundary-review'
    if old_codes and not new_codes:
        assert exclusions and not row['familyRoutes'] and row['familyKey'] is None
        row['bucket'] = old_bucket
        row['withheldDetailedPaths'] = {'reason': '所有主体候选均未通过形族边界；保留第一位和字符身份，等待可靠入口',
                                        'retainedFirstKey': row['bucket'], 'baselineHadPaths': True}
    delta = {'removed': len(old_codes - new_codes), 'added': len(new_codes - old_codes),
             'lostAll': bool(old_codes) and not new_codes,
             'lineRepair': row['familyKey'] == 'l' and old_family != 'l',
             'addedLineRoute': ('l', 'body') not in old_routes and any(r['familyKey'] == 'l' and r['target'] == 'body' for r in row['familyRoutes']),
             'newlyBoundFamily': old_family is None and row['familyKey'] is not None,
             'addedRoutes': sorted({(r['familyKey'], r['target']) for r in row['familyRoutes']} - old_routes),
             'removedRoutes': sorted(old_routes - {(r['familyKey'], r['target']) for r in row['familyRoutes']}),
             'rerendered': rendered is not None}
    return row, delta


def build(output):
    started = time.monotonic()
    manifest_path = DATA / '全形核对版.json'
    manifest = load(manifest_path)
    index_path = PROJECT / manifest['indexPath']
    assert fingerprint(index_path) == manifest['indexSHA256']
    index = load(index_path)
    stage = load(DATA / 'shape-stage.json')
    protected = protected_inputs(PROJECT / stage['source'])
    protected.update({str(p): {'sha256': fingerprint(p)} for p in (manifest_path, index_path, ROOT / '最新实验.json')})
    baseline_path = index_path.parent / 'shape-experiment.json'
    baseline_sha = fingerprint(baseline_path)
    baseline = load(baseline_path)
    output.mkdir(parents=True, exist_ok=False)
    definitions = trial_definitions(index)
    definitions['familyBoundaryPolicy'] = {'version': BOUNDARY_VERSION, 'limits': LIMITS,
        'withdrawInvalidLastRoute': True, 'fallback': 'retain-first-key-and-identity-no-invented-family',
        'reviewedRetainedCharacters': sorted(retained_legacy_characters()),
        'scope': '主体边界仅作用于body；既有内部目标保留独立语义'}
    definitions['status'] = 'accepted-for-independent-trial'
    definitions['lookupBoundaryDecisions'] = lookup_boundary_decisions()
    definitions['frameLookupDecisions'] = frame_lookup_decisions()
    definitions['connectedStrokeGroupPolicy']={'version':STROKE_GROUP_VERSION,'thirdKey':'z',
        'scope':'shared side spine and two/three horizontal ink bands; no general connected-stroke grouping',
        'legacyKMeaningUnchanged':True,'quantityPreferred':True,'runtimeDeployed':False}
    definitions['candidatePresentationProposal'] = {'status':'lookup-preference-accepted-not-deployed', 'defaultMode':'all',
        'modes':['all','focused'],'layers':['primary','component','supplement','pending'],
        'allModeRetainsEveryCandidate':True,'noKeyboardBindingsChanged':True}
    anchors = outline_anchors(Path('C:/Windows/Fonts/seguisym.ttf'))
    templates = references(Path('C:/Windows/Fonts/seguisym.ttf'))
    fonts, chunk, slim, deltas, route_deltas = {}, [], [], [], []
    prefixes = collections.defaultdict(set)
    statistics = collections.Counter()
    samples = {}
    generation_id = VERSION + '-' + output.name
    for number, old in enumerate(baseline['records']):
        row, delta = rebuild_row(old, definitions, index['bucketGroups'], anchors, fonts, templates)
        evidence_count = validate_row(row, definitions)
        statistics['ordinary'] += 1
        statistics['paths'] += len(row['paths'])
        statistics['evidenceItems'] += evidence_count
        statistics['preferredPaths'] += sum(p['preferred'] for p in row['paths'])
        statistics['withPaths'] += bool(row['paths'])
        statistics['lostAll'] += delta['lostAll']
        statistics['withheldDetailedCharacters'] += bool(row.get('withheldDetailedPaths'))
        statistics['pendingMainFamily'] += row['familyKey'] is None
        statistics['boundaryExcludedRoutes'] += len(row['familyBoundaryReview']['excluded'])
        statistics['lineRepairs'] += delta['lineRepair']
        statistics['addedLineRoutes'] += delta['addedLineRoute']
        statistics['newlyBoundFamilies'] += delta['newlyBoundFamily']
        statistics['addedFamilyRoutes'] += len(delta['addedRoutes'])
        statistics['removedFamilyRoutes'] += len(delta['removedRoutes'])
        statistics['rerendered'] += delta['rerendered']
        statistics['removedOldCharacterCodePairs'] += delta['removed']
        statistics['addedCharacterCodePairs'] += delta['added']
        for route in row['familyRoutes']:
            prefixes[route['bucket'] + route['familyKey']].add(row['cp'])
        prefixes[row['bucket']].add(row['cp'])
        for path in row['paths']:
            for n in range(1, len(path['code']) + 1):
                prefixes[path['code'][:n]].add(row['cp'])
        if row['char'] in '○●□■☆★∥=∴∵':
            samples[row['char']] = [p['code'] for p in row['paths'] if p['preferred']]
        if row['familyKey'] != old['familyKey'] or row['bucket'] != old['bucket']:
            deltas.append({'cp': row['cp'], 'char': row['char'], 'beforeFamily': old['familyKey'],
                           'afterFamily': row['familyKey'], 'beforeBucket': old['bucket'], 'afterBucket': row['bucket'],
                           'oldReviewed': old.get('oldReviewed', False)})
        if delta['addedRoutes'] or delta['removedRoutes']:
            route_deltas.append({'cp': row['cp'], 'char': row['char'], 'added': delta['addedRoutes'],
                                 'removed': delta['removedRoutes'], 'basis': row['routeAmendments'],
                                 'oldReviewed': old.get('oldReviewed', False)})
        chunk.append(row)
        detail_name = f'details/{number // 128:03d}.json'
        record = {k: row[k] for k in ('cp', 'char', 'bucket', 'oldBucket', 'oldReviewed', 'familyKey', 'familyId', 'familyRoutes')}
        record.update({'codes': [p['code'] for p in row['paths']], 'detailUrl': detail_name,
                       'preferredCodes': [p['code'] for p in row['paths'] if p['preferred']],
                       'pendingKeyboardFamilyIds': [key for key in old.get('semantic', {}).get('pendingKeyboardFamilyIds', [])
                                                    if not (key == 'family.double-loop' and any(r['familyKey'] == 'b' for r in row['familyRoutes']))]})
        record['familyBoundaryReview'] = row['familyBoundaryReview']
        if 'withheldDetailedPaths' in row:
            record['withheldDetailedPaths'] = row['withheldDetailedPaths']
        if 'preview' in row:
            record['preview'] = row['preview']
        slim.append(record)
        if len(chunk) == 128 or number + 1 == len(baseline['records']):
            save(output / detail_name, {'experimentId': generation_id, 'records': chunk})
            chunk = []
        if (number + 1) % 1000 == 0:
            print(json.dumps({'processed': number + 1, 'total': len(baseline['records']),
                              'elapsedSeconds': round(time.monotonic() - started, 1)}, ensure_ascii=False), flush=True)
    assert statistics['ordinary'] == 28223
    assert statistics['lostAll'] == statistics['withheldDetailedCharacters']
    identities = {r['cp'] for r in slim}
    for values in index['collections'].values():
        assert not identities.intersection(values)
        identities.update(values)
    assert not identities.intersection(index['unclassified'])
    identities.update(index['unclassified'])
    assert len(identities) == 159345
    expected_samples = {'○': 'iose', '●': 'iosf', '□': 'dswe', '■': 'dswf', '☆': 'qrwe',
                        '★': 'qrwf', '∥': 'alkh', '=': 'wlki', '∴': 'mdkw', '∵': 'mdks'}
    assert all(code in samples[ch] for ch, code in expected_samples.items())
    current = protected_inputs(PROJECT / stage['source'])
    current.update({str(p): {'sha256': fingerprint(p)} for p in (manifest_path, index_path, ROOT / '最新实验.json')})
    assert current == protected and fingerprint(baseline_path) == baseline_sha
    distribution = {str(n): {'occupied': len(values := [len(v) for k, v in prefixes.items() if len(k) == n]),
                             'maximumCandidates': max(values, default=0),
                             'medianCandidates': float(np.median(values)) if values else 0}
                    for n in range(1, 5)}
    top = sorted(((code, values) for code, values in prefixes.items() if len(code) == 4), key=lambda x: (-len(x[1]), x[0]))[:20]
    report = {'id': generation_id, 'status': 'independent-trial-not-deployed', 'baseline': index['id'],
              **statistics, 'identities': len(identities), 'unclassified': len(index['unclassified']),
              'prefixDistribution': distribution,
              'topCollisions': [{'code': c, 'count': len(v), 'sample': [chr(cp) for cp in sorted(v)[:12]]} for c, v in top],
              'samples': samples, 'protectedUnchanged': True,
              'elapsedSeconds': round(time.monotonic() - started, 2),
              'limitations': ['主体／双入口修正采用新几何规则，内部备选对象沿用旧观测。',
                              '无可靠主体形族时明确待定；允许撤回旧试验错误长码，仍保留第一位入口和完整身份。',
                              '新增属性不是全量人工准确率；部分形族归属仍为机器候选。',
                              '双环b为独立试验绑定；未判定的其余项不猜码。',
                              '尚未发布至编辑器或Rime。']}
    result_index = {k: v for k, v in index.items() if k not in ('records', 'id', 'definitions', 'definitionsSHA256')}
    result_index.update({'id': generation_id, 'active': False, 'status': 'independent-keyboard-trial',
                         'definitions': definitions, 'records': slim})
    save(output / '发布核对索引.json', result_index)
    save(output / '定义快照.json', definitions)
    save(output / '容量与差异报告.json', report)
    save(output / '主族修正提案.json', deltas)
    save(output / '线组修正提案.json', [d for d in deltas if d['afterFamily'] == 'l' and d['beforeFamily'] != 'l'])
    save(output / '补充入口与排除清单.json', route_deltas)
    save(output / '保护基线.json', protected)
    save(output / '构建来源.json', {'baseline': str(baseline_path), 'baselineSHA256': baseline_sha,
                                  'reviewSHA256': fingerprint(ROOT / '人工审议.json'),
                                  'codeHashes': {name: fingerprint(PROJECT / '工具' / name) for name in
                                                 ('shape_keyboard_trial.py', 'shape_reviewed_routes.py',
                                                  'shape_family_boundaries.py', 'shape_reviewed_components.py',
                                                  'shape_hook_geometry.py',
                                                  'shape_recovery_geometry.py',
                                                  'shape_connected_frames.py',
                                                  'shape_collision_sanity.py',
                                                  'shape_stroke_groups.py',
                                                  'shape_candidate_layers.py',
                                                  'build_shape_keyboard_full.py')}})
    refresh_metadata(output)
    print(json.dumps({'output': str(output), **report}, ensure_ascii=False), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--metadata-only', action='store_true')
    args = parser.parse_args()
    refresh_metadata(args.output) if args.metadata_only else build(args.output)
