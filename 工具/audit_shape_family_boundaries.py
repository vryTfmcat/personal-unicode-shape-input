"""Diagnose collision membership and object scope without editing a trial."""
import argparse
import collections
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from shape_keyboard_trial import load
from build_shape_keyboard_full import save
from shape_experiment_features import render, observe, normalized, bounds


def prototypes():
    font = 'C:/Windows/Fonts/seguisym.ttf'
    views = {}
    for family, chars in [('u', 'U∪∩⊂⊃⊔'), ('c', 'C(⌒◡◜◝◟◞'),
                          ('o', '○●0O'), ('s', '□■◇◆'), ('t', '△▲▷')]:
        views[family] = [normalized(observe(*render(ch, font))['silhouette'] if family in 'ost'
                                    else render(ch, font)[0]) for ch in chars]
    return views


def audit(run):
    index = load(run / '发布核对索引.json')
    rows = {r['cp']: r for r in index['records']}
    report = load(run / '容量与差异报告.json')
    details = {}
    for path in sorted((run / 'details').glob('*.json')):
        details.update({r['cp']: r for r in load(path)['records']})
    refs = prototypes()
    collisions = []
    entries = list(report['topCollisions'][:20])
    for code in ('fuvc', 'rsvg', 'fcvc', 'iosc'):
        if code not in {r['code'] for r in entries}:
            members = [r for r in rows.values() if code in r['codes']]
            entries.append({'code': code, 'count': len(members), 'sample': [r['char'] for r in members[:12]]})
    for entry in entries:
        code = entry['code']
        selected = [r for r in rows.values() if code in r['codes']]
        targets, kinds, primary, arms, holes = (collections.Counter() for _ in range(5))
        for slim in selected:
            row = details[slim['cp']]
            objects = {o['id']: o for o in row['objects']}
            path = next(p for p in row['paths'] if p['code'] == code)
            for target in {e['familyTarget'] for e in path['evidence']}:
                targets[target.split('-')[0]] += 1
            for kind in {objects[e['objectId']]['kind'] for e in path['evidence']}:
                kinds[kind] += 1
            primary['primary' if row['familyKey'] == code[1] else 'alternate'] += 1
            if any(e['familyTarget'] == 'body' for e in path['evidence']):
                f = row.get('features', {})
                pattern = '+'.join(str(j['armCount']) for j in f.get('junctionObjects', [])) or 'none'
                arms[pattern] += 1
                holes[str(len(f.get('holes', [])))] += 1
        collisions.append(dict(entry, targets=dict(targets), objectKinds=dict(kinds), roles=dict(primary),
                               recordedBodyArmPatterns=dict(arms), recordedBodyHoleCounts=dict(holes)))
    samples = []
    chars = 'U∪∩⊂⊃⊔CS235?EHL[]()YΨFTKX+Baɽ○●□■◇◆△▲O0DΩ©@⊙◎▣'
    for char in dict.fromkeys(chars):
        if ord(char) not in details:
            continue
        row = details[ord(char)]
        source = row['font']
        f = observe(*render(char, source['path'], source.get('index', 0)))
        scores = {family: round(min(float(((normalized(f['silhouette'] if family in 'ost' else f['body']) - a) ** 2).mean())
                                   for a in anchors), 4) for family, anchors in refs.items()}
        samples.append({'cp': ord(char), 'char': char, 'primary': row['familyKey'], 'routes': row['familyRoutes'],
                        'contourOrInkMSE': scores, 'holes': len(f['holes']), 'parts': len(f['parts']),
                        'junctionArms': [j['armCount'] for j in f['junctionObjects']], 'endpoints': f['endpoints'],
                        'font': source})
    result = {'run': index['id'], 'collisions': collisions, 'diagnosticSamples': samples,
              'scope': 'measurements-not-user-decisions'}
    save(run / '形族边界诊断.json', result)
    print({'output': str(run / '形族边界诊断.json'), 'sampleCount': len(samples), 'collisionCount': len(collisions)})
    for row in samples:
        print(ascii(row['char']), row['primary'], [(r['familyKey'], r['target']) for r in row['routes']],
              row['contourOrInkMSE'], row['holes'], row['junctionArms'], row['endpoints'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    audit(parser.parse_args().run)
