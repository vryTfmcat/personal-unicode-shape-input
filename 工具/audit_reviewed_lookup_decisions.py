"""Verify reviewed entry points and visualize actual D component masks."""
import argparse
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from build_shape_keyboard_full import save
from shape_experiment_features import render, observe
from shape_keyboard_trial import load


def audit(run):
    index = load(run / '发布核对索引.json')
    rows = {r['cp']: r for r in index['records']}
    selected = {}
    wanted = {ord(c) for c in '[]⊔+×DTY'}
    for url in {rows[cp]['detailUrl'] for cp in wanted}:
        selected.update({r['cp']: r for r in load(run / url)['records'] if r['cp'] in wanted})
    for char in '[ ]⊔'.replace(' ', ''):
        assert any(r['familyKey'] == 'u' for r in selected[ord(char)]['familyRoutes'])
    for char in '+×':
        assert selected[ord(char)]['familyKey'] == 'x'
        assert any(r['familyKey'] == 'h' for r in selected[ord(char)]['familyRoutes'])
    assert not index['definitions']['lookupBoundaryDecisions']['splitTY']
    d = selected[ord('D')]
    assert {'alli', 'fcpd'} <= {p['code'] for p in d['paths']}
    assert any(r['familyKey'] == 'o' for r in d['familyRoutes'])
    proof = next(r['objectPartitionProof'] for r in d['familyRoutes'] if r.get('objectPartitionProof'))
    source = d['font']
    f = observe(*render('D', source['path'], source.get('index', 0)))
    assert hashlib.sha256(f['body'].tobytes()).hexdigest() == proof['sourceInkSHA256']
    x = np.indices(f['body'].shape)[1]
    masks = [f['body'], f['body'] & (x < proof['cutX']), f['body'] & (x >= proof['cutX'])]
    assert not (masks[1] & masks[2]).any()
    assert np.array_equal(masks[1] | masks[2], masks[0])
    canvas = Image.new('RGB', (1040, 360), 'white')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
    labels = [('圆形入口：整字', 'iosc 等圆形路径'), ('线条入口：左侧竖线', 'alli：单一直线 → 纵向'),
              ('曲弧入口：右侧半弧', 'fcpd：半轮廓 → 右侧')]
    for i, (mask, (title, subtitle)) in enumerate(zip(masks, labels)):
        pixels = np.full((*mask.shape, 3), 255, dtype='uint8')
        pixels[f['body']] = [218, 218, 218]
        pixels[mask] = [0, 0, 0] if i == 0 else [20, 95, 160] if i == 1 else [25, 125, 85]
        glyph = Image.fromarray(pixels).resize((224, 224), Image.Resampling.NEAREST)
        left = 12 + i * 344
        draw.text((left, 10), title, font=font, fill='black')
        draw.text((left, 42), subtitle, font=font, fill='black')
        canvas.paste(glyph, (left + 30, 82))
    draw.text((12, 326), '着色为该路径选中的实际墨迹；灰色仅作整字位置参照。', font=font, fill='black')
    canvas.save(run / 'D三种对象查法.png')
    result = {'run': index['id'], 'passed': True, 'squareUEntries': True, 'crossPriorityAndExistingForkSupplement': True,
              'noTYSubtypeOrNewBinding': True, 'DHasRoundSpineAndHalfArc': True,
              'DPartitionMatchesFreshFontPixels': True, 'DSourceFont': source,
              'DComponentPathsAreImplementationProposals': True,
              'samples': [{'char': chr(cp), 'cp': cp, 'primaryFamily': r['familyKey'],
                           'routes': [{'familyKey': a['familyKey'], 'target': a['target']} for a in r['familyRoutes']],
                           'codes': [p['code'] for p in r['paths']]} for cp, r in sorted(selected.items())]}
    save(run / '查法决定验收.json', result)
    print({k: v for k, v in result.items() if k != 'samples'})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    audit(parser.parse_args().run)
