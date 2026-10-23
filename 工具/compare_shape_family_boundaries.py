"""Record boundary withdrawals, retained identities and collision changes."""
import argparse
import collections
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from shape_keyboard_trial import load, fingerprint
from shape_experiment_features import render, bounds
from build_shape_keyboard_full import save


def compare(before, after):
    previous, current = (load(p / '发布核对索引.json') for p in (before, after))
    old = {r['cp']: r for r in previous['records']}
    new = {r['cp']: r for r in current['records']}
    assert set(old) == set(new)
    assert previous['collections'] == current['collections'] and previous['unclassified'] == current['unclassified']
    provenance=load(after/'构建来源.json')
    original={r['cp']:r for r in load(Path(provenance['baseline']))['records']}
    changes, withdrawn = [], []
    counts = collections.Counter()
    for cp, row in new.items():
        a = old[cp]
        old_routes = {(r['bucket'], r['familyKey'], r['target']) for r in a['familyRoutes']}
        new_routes = {(r['bucket'], r['familyKey'], r['target']) for r in row['familyRoutes']}
        if old_routes != new_routes or set(a['codes']) != set(row['codes']) or a['familyKey'] != row['familyKey']:
            change = {'cp': cp, 'char': row['char'], 'oldReviewed': row['oldReviewed'],
                      'beforeFamily': a['familyKey'], 'afterFamily': row['familyKey'],
                      'removedRoutes': sorted(old_routes - new_routes), 'addedRoutes': sorted(new_routes - old_routes),
                      'removedCodes': sorted(set(a['codes']) - set(row['codes'])),
                      'addedCodes': sorted(set(row['codes']) - set(a['codes'])),
                      'review': row['familyBoundaryReview']}
            changes.append(change)
            for _, family, target in change['removedRoutes']:
                counts['removed.' + family + '.' + target.split('-')[0]] += 1
        if a['codes'] and not row['codes']:
            assert row['withheldDetailedPaths'] and row['bucket'] == original[cp]['bucket']
            assert row['withheldDetailedPaths']['retainedFirstKey'] == original[cp]['bucket']
            withdrawn.append({'cp': cp, 'char': row['char'], 'firstKey': row['bucket'],
                              'review': row['familyBoundaryReview'], 'oldReviewed': row['oldReviewed']})
    for char, code in [('○', 'iose'), ('●', 'iosf'), ('□', 'dswe'), ('■', 'dswf'),
                       ('☆', 'qrwe'), ('★', 'qrwf'), ('∥', 'alkh'), ('=', 'wlki'),
                       ('∴', 'mdkw'), ('∵', 'mdks')]:
        assert code in new[ord(char)]['preferredCodes']
    for char in '◯○o◦⬤●•∙□◻◽▫■◼◾▪☆★∥=∴∵𐎊𝍫﹦𝌆I4∞8':
        assert set(old[ord(char)]['codes']) == set(new[ord(char)]['codes']), char
    assert new[ord('B')]['familyKey'] != 'b'
    assert any(r['familyKey'] == 'b' for r in new[ord('B')]['familyRoutes'])

    old_report, report = (load(p / '容量与差异报告.json') for p in (before, after))
    prefixes = []
    for data in (old, new):
        mapping = collections.defaultdict(set)
        for cp, row in data.items():
            for code in row['codes']:
                if len(code) == 4:
                    mapping[code].add(cp)
        prefixes.append(mapping)
    cohort = {cp for cp in new if old[cp]['codes'] and new[cp]['codes']}
    cohort_distributions = []
    for mapping in prefixes:
        sizes = [len(values & cohort) for values in mapping.values() if values & cohort]
        cohort_distributions.append({'characters': len(cohort), 'occupiedFourCodes': len(sizes),
                                     'maximumCandidates': max(sizes, default=0),
                                     'medianCandidates': statistics.median(sizes) if sizes else 0})
    family_seen, codes = set(), []
    for entry in old_report['topCollisions']:
        if entry['code'][1] not in family_seen:
            family_seen.add(entry['code'][1])
            codes.append(entry['code'])
    largest_new = report['topCollisions'][0]['code']
    if largest_new not in codes:
        codes.append(largest_new)
    groups, wanted = [], set()
    hints = 'UCS235?EHL[]()YΨFTKX+Baɽ○●□■◇◆△▲O0DΩ©@⊙◎▣'
    for number, code in enumerate(codes):
        a, b = prefixes[0][code], prefixes[1][code]
        selected = [ord(c) for c in hints if ord(c) in a | b][:12]
        for cp in sorted(a | b):
            if len(selected) >= 12:
                break
            if cp not in selected:
                selected.append(cp)
        wanted.update(selected)
        groups.append({'id': f'C{number + 1}', 'code': code, 'beforeCount': len(a), 'afterCount': len(b),
                       'removed': len(a - b), 'added': len(b - a), 'selected': selected})
    details = {}
    for url in {new[cp]['detailUrl'] for cp in wanted}:
        details.update({r['cp']: r for r in load(after / url)['records'] if r['cp'] in wanted})
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 18)
    for group in groups:
        canvas = Image.new('RGB', (1040, 480), 'white')
        draw = ImageDraw.Draw(canvas)
        samples = []
        for i, cp in enumerate(group['selected']):
            source = details[cp]['font']
            mask, _ = render(chr(cp), source['path'], source.get('index', 0))
            x0, y0, x1, y1 = bounds(mask)
            crop = mask[y0:y1, x0:x1]
            scale = min(90 / crop.shape[0], 180 / crop.shape[1])
            glyph = Image.fromarray(255 - crop.astype('uint8') * 255).resize(
                (max(1, round(crop.shape[1] * scale)), max(1, round(crop.shape[0] * scale))), Image.Resampling.NEAREST)
            x, y = i % 4 * 260, i // 4 * 160
            identity = f"{group['id']}-{i + 1}"
            status = 'KEEP' if cp in prefixes[1][group['code']] else 'WITHDRAW'
            draw.text((x + 10, y + 6), f'{identity} U+{cp:04X}', font=font, fill='black')
            draw.text((x + 140, y + 35), status, font=font, fill='black')
            canvas.paste(glyph, (x + 10, y + 43))
            samples.append({'id': identity, 'cp': cp, 'char': chr(cp), 'font': source,
                            'keptInThisCode': cp in prefixes[1][group['code']],
                            'beforeFamily': old[cp]['familyKey'], 'afterFamily': new[cp]['familyKey'],
                            'withheldDetailedPaths': new[cp].get('withheldDetailedPaths')})
        group['samples'] = samples
        canvas.save(after / f"重码边界样本-{group['id']}.png")
    result = {'before': previous['id'], 'after': current['id'], 'beforeIndexSHA256': fingerprint(before / '发布核对索引.json'),
              'afterIndexSHA256': fingerprint(after / '发布核对索引.json'),
              'status': 'trial-boundary-refinement-not-deployed', 'identitiesAndCollectionsPreserved': True,
              'confirmedSampleCodeSetsUnchangedExceptExplicitBBodyCorrection': True,
              'changedCharacters': len(changes), 'withdrawnDetailedFromPreviousTrial': len(withdrawn),
              'beforeDistribution': old_report['prefixDistribution'], 'afterDistribution': report['prefixDistribution'],
              'sameDetailedCharacterCohort': {'before': cohort_distributions[0], 'after': cohort_distributions[1]},
              'removedRouteCounts': dict(counts), 'collisionGroups': groups, 'changes': changes,
              'withdrawnCharacters': withdrawn}
    save(after / '形族边界与重码差异.json', result)
    print({k: v for k, v in result.items() if k not in ('changes', 'withdrawnCharacters', 'collisionGroups')})
    print([(g['id'], g['code'], g['beforeCount'], g['afterCount']) for g in groups])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    compare(args.before, args.after)
