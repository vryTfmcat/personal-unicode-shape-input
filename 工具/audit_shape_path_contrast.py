"""Find contrast-review candidates; measurements are not automatic pruning rules."""
import argparse
import collections
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from build_shape_keyboard_full import save
from shape_experiment_features import render, bounds
from shape_keyboard_trial import load


REVIEW = [
    ('A1', '𐎊'), ('A2', '𝍫'), ('A3', '﹦'), ('A4', '𝌆'),
    ('B1', '⬤'), ('B2', '•'), ('B3', '▪'), ('B4', '▫'), ('B5', '◽'), ('B6', '◾'),
    ('C1', 'I'), ('C2', '4'), ('C3', 'B'),
]


def audit(run):
    index = load(run / '发布核对索引.json')
    rows = {r['cp']: r for r in index['records']}
    prefixes = collections.defaultdict(set)
    for row in rows.values():
        for route in row['familyRoutes']:
            prefixes[route['bucket'] + route['familyKey']].add(row['cp'])
        for code in row['codes']:
            for length in (2, 3, 4):
                if length <= len(code):
                    prefixes[code[:length]].add(row['cp'])
    no_reduction = []
    for code, values in prefixes.items():
        if len(code) in (3, 4) and len(values) >= 100 and values == prefixes[code[:-1]]:
            no_reduction.append({'code': code, 'count': len(values), 'parent': code[:-1]})
    no_reduction.sort(key=lambda x: (-x['count'], x['code']))
    equivalent = collections.defaultdict(list)
    for code, values in prefixes.items():
        if len(code) == 4 and len(values) >= 100:
            equivalent[(code[:3], frozenset(values))].append(code)
    duplicate_sets = [{'codes': sorted(codes), 'count': len(key[1])}
                      for key, codes in equivalent.items() if len(codes) > 1]
    duplicate_sets.sort(key=lambda x: (-x['count'], x['codes']))
    path_metrics = []
    for code, values in sorted(prefixes.items()):
        if len(code) != 4:
            continue
        parent_count = len(prefixes[code[:-1]])
        basis = '规则成立的机器候选；区分价值待核对'
        if code[-1] in 'ef':
            basis = '已确认空心／实心对照入口；具体成员仍待核对'
        elif code[1] in 'os' and code[-1] in 'zxcv':
            basis = '圆方尺寸对照系列候选；需区分主体尺寸与内部构件尺寸'
        elif code[2] == 'k' and code[-1] in 'bt':
            basis = '构件组数量候选；同数量未必能区分字形'
        path_metrics.append({'code': code, 'candidates': len(values), 'parentCandidates': parent_count,
                             'reduction': parent_count - len(values), 'selectionBasis': basis})
    shards = {}

    def detail(char):
        row = rows[ord(char)]
        url = row['detailUrl']
        if url not in shards:
            shards[url] = load(run / url)
        return next(r for r in shards[url]['records'] if r['cp'] == ord(char))

    series = {}
    for family, chars in [('o', '◯○o◦⬤●•∙'), ('s', '□■◻◼▫▪◽◾'), ('r', '☆★')]:
        series[family] = []
        for char in chars:
            r = detail(char)
            objects = {o['id']: o for o in r['objects']}
            body_sizes = []
            for path in r['paths']:
                if len(path['code']) != 4 or path['code'][-1] not in 'zxcv' or path['code'][1] != family:
                    continue
                if any(objects[e['objectId']]['kind'] == 'body' for e in path['evidence']):
                    body_sizes.append(path['code'])
            series[family].append({'char': char, 'cp': ord(char), 'primaryFamily': r['familyKey'],
                                   'bodySizeCodes': body_sizes})
    canvas = Image.new('RGB', (1040, 640), 'white')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 18)
    review_rows = []
    for i, (identity, char) in enumerate(REVIEW):
        r = detail(char)
        font_source = r['font']
        mask, _ = render(char, font_source['path'], font_source.get('index', 0))
        x, y = (i % 4) * 260, (i // 4) * 160
        draw.text((x + 12, y + 8), f'{identity}  U+{ord(char):04X}', fill='black', font=font)
        image = Image.fromarray(255 - mask.astype('uint8') * 255).resize((96, 96), Image.Resampling.NEAREST)
        canvas.paste(image, (x + 12, y + 36))
        review_rows.append({'id': identity, 'char': char, 'cp': ord(char), 'font': font_source,
                            'primaryFamily': r['familyKey'], 'baselineFamily': r.get('baselineFamilyKey'),
                            'oldReviewed': r.get('oldReviewed', False), 'routes': r['familyRoutes']})
    canvas.save(run / '具体核对字形.png')
    size_canvas = Image.new('RGB', (1040, 640), 'white')
    size_draw = ImageDraw.Draw(size_canvas)
    for i, char in enumerate('◯○o◦⬤●•∙□◻◽▫■◼◾▪'):
        r = detail(char)
        font_source = r['font']
        mask, extent = render(char, font_source['path'], font_source.get('index', 0))
        x, y = (i % 4) * 260, (i // 4) * 160
        sizes = next(entry['bodySizeCodes'] for family in ('o', 's') for entry in series[family] if entry['char'] == char)
        tiers = '/'.join(sorted({code[-1] for code in sizes})) or '-'
        size_draw.text((x + 12, y + 8), f'U+{ord(char):04X} em={extent:.3f} {tiers}', fill='black', font=font)
        x0, y0, x1, y1 = bounds(mask)
        crop = mask[y0:y1, x0:x1]
        scale = extent * 96 / max(crop.shape)
        image = Image.fromarray(255 - crop.astype('uint8') * 255).resize(
            (max(1, round(crop.shape[1] * scale)), max(1, round(crop.shape[0] * scale))), Image.Resampling.NEAREST)
        size_canvas.paste(image, (x + 12, y + 42))
    size_canvas.save(run / '圆方同字号尺寸对照.png')
    report = {'run': index['id'], 'status': 'review-candidates-not-decisions',
              'noReductionPathCount': len(no_reduction), 'noReductionExamples': no_reduction[:20],
              'equivalentSuffixGroupCount': len(duplicate_sets), 'equivalentSuffixExamples': duplicate_sets[:20],
              'pathMetrics': path_metrics,
              'sizeSeries': series, 'specificReview': review_rows,
              'interpretation': '集合相同和候选未缩减只标出待审项；自然别名仍可能有价值，不据此自动删码。'}
    save(run / '路径区分与具体核对.json', report)
    print({'noReductionPathCount': len(no_reduction), 'equivalentSuffixGroupCount': len(duplicate_sets),
           'specificReviewGlyphs': len(review_rows), 'output': str(run)})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    audit(parser.parse_args().run)
