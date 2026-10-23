"""Audit recovery and withdrawals separately; recheck actual component ink."""
import argparse
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from build_shape_keyboard_full import save
from shape_experiment_features import render, observe, component_mask
from shape_keyboard_trial import load
from shape_reviewed_components import cycle_subject


def audit(before, after):
    previous = load(before / '发布核对索引.json')
    index = load(after / '发布核对索引.json')
    old = {r['cp']: r for r in previous['records']}
    current = {r['cp']: r for r in index['records']}
    assert set(old) == set(current)
    assert previous['collections'] == index['collections']
    assert previous['unclassified'] == index['unclassified']
    restored, newly_lost, remaining, repaired = [], [], [], []
    causes, methods = Counter(), Counter()
    verified = Counter()
    baseline = load(Path(load(after / '构建来源.json')['baseline']))
    original = {r['cp']: r for r in baseline['records']}
    prior_withheld = {cp for cp, row in old.items() if row.get('withheldDetailedPaths')}
    prior_families = Counter(original[cp]['familyKey'] for cp in prior_withheld)
    prior_structure = Counter()
    for cp in prior_withheld:
        f = original[cp].get('features') or {}
        prior_structure['多部件' if len(f.get('parts', [])) > 1 else '单连通部件'] += 1
    for url in sorted({r['detailUrl'] for r in index['records']}):
        for row in load(after / url)['records']:
            cp = row['cp']
            item = {'cp': cp, 'char': row['char'], 'oldReviewed': row.get('oldReviewed', False),
                    'codes': [p['code'] for p in row['paths']], 'amendments': row['routeAmendments']}
            if not old[cp]['codes'] and row['paths']:
                restored.append(item)
            if old[cp]['codes'] and not row['paths']:
                newly_lost.append(item)
            if row.get('withheldDetailedPaths'):
                f = row.get('features') or {}
                # These are program triage categories, not visual family judgments.
                category = ('分离部件需要进一步取对象' if len(f.get('parts', [])) > 1 else
                            '多闭孔连接结构' if len(f.get('holes', [])) > 1 else
                            '单闭孔与附件／异形轮廓' if f.get('holes') else
                            '无闭孔但当前开口／骨架边界未通过')
                causes[category] += 1
                item['triageCategory'] = category
                remaining.append(item)
            if any('补回' in s or '圆环与附笔' in s for s in row['routeAmendments']):
                repaired.append(item)
                methods.update(s for s in row['routeAmendments'] if '补回' in s or '圆环与附笔' in s)
            if any(r.get('componentEvidence') or r.get('componentPartitionProof') for r in row['familyRoutes']):
                font = row['font']
                f = observe(*render(row['char'], font['path'], font.get('index', 0)))
                for route in row['familyRoutes']:
                    if route.get('componentPartitionProof'):
                        rf, tail, proof = cycle_subject(f)
                        assert proof == route['componentPartitionProof']
                        assert np.array_equal(rf['mask'] | tail, f['body'])
                        assert not (rf['mask'] & tail).any()
                        verified['cycleTailPartitions'] += 1
                    if route.get('componentEvidence'):
                        proof = route['componentEvidence']
                        part = next(p for p in f['parts'] if [p[k] for k in ('x0', 'y0', 'x1', 'y1')] == proof['bbox']
                                    and p['area'] == proof['pixels'])
                        mask = component_mask(f['mask'], part)
                        assert int(mask.sum()) == proof['pixels']
                        # Local junction observation windows can extend beyond
                        # the ink bbox; only the selected body uses the full box.
                        assert all(fact['object']['bbox'] == proof['bbox']
                                   for fact in route['reviewedObjectFacts'] if fact['object']['kind'] == 'body')
                        verified['actualConnectedComponents'] += 1
    q = current[ord('Q')]
    assert q['familyKey'] == 'o' and 'iose' in q['codes']
    assert not any(r['familyKey'] == 'j' for r in current[ord('T')]['familyRoutes'])
    assert current[ord('T')]['familyKey'] == 'h'
    assert current[ord('L')]['familyKey'] == 'a'
    result = {'passed': True, 'before': previous['id'], 'after': index['id'],
              'identitiesCollectionsUnclassifiedUnchanged': True,
              'restoredDetailedCharacters': len(restored), 'newlyWithheldDetailedCharacters': len(newly_lost),
              'priorWithheldCohort': {'count': len(prior_withheld), 'originalPrimaryFamilies': dict(prior_families),
                                     'structure': dict(prior_structure),
                                     'restored': sum(item['cp'] in prior_withheld for item in restored)},
              'netDetailedCharacterChange': len(restored) - len(newly_lost),
              'remainingPreviouslyCodedFirstKeyOnly': len(remaining),
              'remainingTriageCategories': dict(causes), 'recoveryMethods': dict(methods),
              'actualInkVerified': dict(verified), 'QCircleRestored': True, 'THookRemovedForkRetained': True,
              'limitations': ['剩余字符未据旧入口自动恢复；分组仅为程序排查顺序，不等于人工判断。',
                              '撤回错误钩弯可能新增仅第一位字符；单列而不抵消隐藏。',
                              '保持独立试验，不部署、不改写人工确认。'],
              'restored': restored, 'newlyWithheld': newly_lost, 'remaining': remaining,
              'allRecoveryProposals': repaired}
    save(after / '程序修复与漏收审计.json', result)
    canvas = Image.new('RGB', (960, 340), 'white')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 19)
    # The immutable baseline source font is recorded on Q's detail row.
    qr = next(r for r in load(after / q['detailUrl'])['records'] if r['cp'] == ord('Q'))
    f = observe(*render('Q', qr['font']['path'], qr['font'].get('index', 0)))
    rf, tail, proof = cycle_subject(f)
    for n, (mask, title) in enumerate([(f['body'], '原始Q墨迹'), (rf['mask'], '圆环主体：尺寸只量这部分'),
                                        (tail, '附加尾笔：独立对象')]):
        pixels = np.full((*mask.shape, 3), 255, dtype='uint8')
        pixels[f['body']] = [218, 218, 218]
        pixels[mask] = [0, 0, 0] if n == 0 else [25, 110, 155] if n == 1 else [160, 65, 40]
        draw.text((n*320+12, 14), title, font=font, fill='black')
        canvas.paste(Image.fromarray(pixels).resize((256, 256), Image.Resampling.NEAREST), (n*320+24, 52))
    canvas.save(after / 'Q主体与尾笔分离.png')
    print({k: v for k, v in result.items() if k not in ('restored', 'newlyWithheld', 'remaining', 'allRecoveryProposals')})
    return result


if __name__ == '__main__':
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    audit(args.before, args.after)
