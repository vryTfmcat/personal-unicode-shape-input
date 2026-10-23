"""Compare two independent keyboard runs without editing either index."""
import argparse
import collections
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from build_shape_keyboard_full import save
from shape_keyboard_trial import load, fingerprint
from shape_experiment_features import render, bounds


def compare(before, after):
    old_index, index = (load(p / '发布核对索引.json') for p in (before, after))
    old = {r['cp']: r for r in old_index['records']}
    new = {r['cp']: r for r in index['records']}
    source = load(after / '构建来源.json')
    baseline_index = load(Path(source['baseline']).parent / '发布核对索引.json')
    baseline = {r['cp']: r for r in baseline_index['records']}
    assert set(old) == set(new)
    assert old_index['collections'] == index['collections']
    assert old_index['unclassified'] == index['unclassified']
    changes = []
    counts = collections.Counter()
    for cp, row in new.items():
        previous = old[cp]
        previous_routes = {(r['bucket'], r['familyKey'], r['target']) for r in previous['familyRoutes']}
        routes = {(r['bucket'], r['familyKey'], r['target']) for r in row['familyRoutes']}
        if previous_routes == routes and previous['codes'] == row['codes'] and previous['familyKey'] == row['familyKey']:
            continue
        removed, added = previous_routes - routes, routes - previous_routes
        item = {'cp': cp, 'char': row['char'], 'oldReviewed': row['oldReviewed'],
                'beforeFamily': previous['familyKey'], 'afterFamily': row['familyKey'],
                'removedRoutes': sorted(removed), 'addedRoutes': sorted(added),
                'removedCodes': sorted(set(previous['codes']) - set(row['codes'])),
                'addedCodes': sorted(set(row['codes']) - set(previous['codes']))}
        changes.append(item)
        counts['changedCharacters'] += 1
        counts['changedPreviouslyReviewed'] += bool(row['oldReviewed'])
        counts['retractedLineBodyCharacters'] += any(f == 'l' and t == 'body' for _, f, t in removed)
        counts['retractedDoubleLoopBodyCharacters'] += any(f == 'b' and t == 'body' for _, f, t in removed)
        counts['restoredRoutes'] += len(added)
        counts['primaryChangedBetweenTrials'] += previous['familyKey'] != row['familyKey']
        if previous['codes'] and not row['codes']:
            assert not baseline[cp]['codes'], chr(cp)
            item['withdrawnTrialOnlyBinding'] = True
            counts['withdrawnTrialOnlyBindings'] += 1

    for char in '（[⌠⎧⏠⁀𐎃':
        row = new[ord(char)]
        assert not any(r['familyKey'] == 'l' and r['target'] == 'body' for r in row['familyRoutes']), char
    for char in '🕶🛩⥈༔៖ⴻ':
        assert not any(r['familyKey'] == 'b' and r['target'] == 'body' for r in new[ord(char)]['familyRoutes']), char
    for char in 'B8∞⧟':
        assert any(r['familyKey'] == 'b' for r in new[ord(char)]['familyRoutes']), char
    for char in '◯○o◦⬤●•∙□◻◽▫■◼◾▪☆★∥=∴∵𐎊𝍫﹦𝌆BI4∞8':
        assert set(new[ord(char)]['codes']) == set(old[ord(char)]['codes']), char

    details = {}
    selected = {}
    for family in ('l', 'b'):
        selected[family] = sorted([r for r in changes if any(f == family and t == 'body' for _, f, t in r['removedRoutes'])],
                                  key=lambda r: (not r['oldReviewed'], r['cp']))[:32]
    wanted = {r['cp'] for values in selected.values() for r in values}
    for url in {new[cp]['detailUrl'] for cp in wanted}:
        details.update({r['cp']: r for r in load(after / url)['records'] if r['cp'] in wanted})
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)
    for family, values in selected.items():
        image = Image.new('RGB', (1280, max(1, (len(values) + 7) // 8) * 140), 'white')
        draw = ImageDraw.Draw(image)
        for i, row in enumerate(values):
            source = details[row['cp']]['font']
            mask, _ = render(row['char'], source['path'], source.get('index', 0))
            x0, y0, x1, y1 = bounds(mask)
            crop = mask[y0:y1, x0:x1]
            scale = min(80 / crop.shape[0], 110 / crop.shape[1])
            glyph = Image.fromarray(255 - crop.astype('uint8') * 255).resize(
                (max(1, round(crop.shape[1] * scale)), max(1, round(crop.shape[0] * scale))), Image.Resampling.NEAREST)
            x, y = i % 8 * 160, i // 8 * 140
            draw.text((x + 4, y + 4), f"{i + 1} U+{row['cp']:04X}", font=font, fill='black')
            image.paste(glyph, (x + 4, y + 35))
        image.save(after / f'收紧排除样本-{family}.png')
    report = {'before': old_index['id'], 'after': index['id'],
              'beforeIndexSHA256': fingerprint(before / '发布核对索引.json'),
              'afterIndexSHA256': fingerprint(after / '发布核对索引.json'),
              'scope': 'trial-comparison-not-human-accuracy-or-deployment',
              'identitiesPreserved': True, 'confirmedSampleCodeSetsUnchanged': True,
              'specifiedFalsePositiveExamplesExcluded': True, **counts,
              'changes': changes, 'renderedSamples': selected}
    save(after / '规则收紧前后差异.json', report)
    print({k: v for k, v in report.items() if k not in ('changes', 'renderedSamples')})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    compare(args.before, args.after)
