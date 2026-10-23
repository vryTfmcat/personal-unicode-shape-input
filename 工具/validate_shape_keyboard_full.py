"""Read back every generated shard and compare its index, evidence and baseline."""
import argparse
import collections
from pathlib import Path

from build_shape_keyboard_full import validate_row, save
from shape_keyboard_trial import load, fingerprint


def validate(run):
    index = load(run / '发布核对索引.json')
    report = load(run / '容量与差异报告.json')
    by_cp = {r['cp']: r for r in index['records']}
    assert len(by_cp) == len(index['records']) == 28223
    seen = set()
    counts = collections.Counter()
    for path in sorted((run / 'details').glob('*.json')):
        shard = load(path)
        assert shard['experimentId'] == index['id']
        for row in shard['records']:
            cp = row['cp']
            assert cp not in seen and row['char'] == chr(cp)
            seen.add(cp)
            slim = by_cp[cp]
            assert slim['codes'] == [p['code'] for p in row['paths']]
            assert slim['preferredCodes'] == [p['code'] for p in row['paths'] if p['preferred']]
            assert slim['familyRoutes'] == row['familyRoutes']
            assert slim['bucket'] == row['bucket'] and slim['familyKey'] == row['familyKey']
            assert slim.get('withheldDetailedPaths') == row.get('withheldDetailedPaths')
            assert slim.get('familyBoundaryReview') == row.get('familyBoundaryReview')
            counts['paths'] += len(row['paths'])
            counts['evidenceItems'] += validate_row(row, index['definitions'])
            for obj in row['objects']:
                if obj.get('fill'):
                    assert obj['kind'] == 'body'
                if 'memberCount' in obj:
                    assert obj['kind'] == 'part-group' and len(obj['memberCentres']) == obj['memberCount']
    assert seen == set(by_cp)
    assert counts['paths'] == report['paths'] and counts['evidenceItems'] == report['evidenceItems']
    source = load(run / '构建来源.json')
    assert fingerprint(Path(source['baseline'])) == source['baselineSHA256']
    baseline = load(Path(source['baseline']))
    old = {r['cp']: r for r in baseline['records']}
    assert set(old) == set(by_cp)
    withdrawn = [cp for cp in old if old[cp]['paths'] and not by_cp[cp]['codes']]
    for cp in withdrawn:
        row = by_cp[cp]
        assert index['definitions'].get('familyBoundaryPolicy', {}).get('withdrawInvalidLastRoute')
        assert row['withheldDetailedPaths']['baselineHadPaths']
        assert row['withheldDetailedPaths']['retainedFirstKey'] == old[cp]['bucket'] == row['bucket']
        assert row['familyBoundaryReview']['excluded']
        assert row['familyKey'] is None and not row['familyRoutes']
    assert baseline['collections'] == index['collections']
    assert baseline['unclassified'] == index['unclassified']
    all_cp = set(by_cp)
    for group in list(index['collections'].values()) + [index['unclassified']]:
        assert not all_cp.intersection(group)
        all_cp.update(group)
    assert len(all_cp) == 159345
    for group in index['bucketGroups']:
        assert group['count'] == sum(r['bucket'] == group['bucket'] and r['familyKey'] in group['families']
                                     for r in index['records'])
    protected = load(run / '保护基线.json')
    for name, expected in protected.items():
        assert fingerprint(Path(name)) == expected['sha256'], name
    result = {'passed': True, 'ordinary': len(by_cp), 'identities': len(all_cp), **counts,
              'indexMatchesEveryShard': True, 'objectsAndTypedAttributesValid': True,
              'noJunctionWindowSizePaths': True, 'noPreviouslyCodedCharacterLostAllPaths': not withdrawn,
              'explicitlyWithheldDetailedCharacters': len(withdrawn),
              'allWithheldCharactersRetainBaselineFirstKeyAndIdentity': True,
              'xyzAndUnclassifiedUnchanged': True, 'protectedFileHashesUnchanged': True}
    save(run / '全量回读校验.json', result)
    print(result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    validate(parser.parse_args().run)
