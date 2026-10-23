"""Isolated keyboard proposal; never publishes or changes the legacy rules."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from shape_experiment_features import component_mask, filled, normalized, observe, render
from shape_experiment_rules import RULES, facts, obj, properties, position
from shape_experiment_detector import dot_group

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / '数据/三模式'
ROOT = DATA / '规则库/四键实验'
VERSION = 'keyboard-object-trial-20261021-v3'
SIZE_KEYS = set('zxcv')
OUTLINES = {'o': '○●', 's': '□■', 'r': '☆★', 't': '△▲'}
SIZE_REFERENCES = {'o': {'hollow': '◯○o◦', 'solid': '⬤●•∙'},
                   's': {'hollow': '□◻◽▫', 'solid': '■◼◾▪'}}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trial_definitions(baseline):
    fourth = {k: dict(v) for k, v in baseline['definitions']['fourth'].items()}
    fourth['g'] = fourth.pop('e')
    fourth.update({
        'e': {'function': 'fill.hollow', 'meaning': '空心'},
        'f': {'function': 'fill.solid', 'meaning': '实心'},
        'b': {'function': 'count.two', 'meaning': '两个'},
        't': {'function': 'count.three', 'meaning': '三个'},
    })
    third = {k: dict(v) for k, v in baseline['definitions']['third'].items()}
    third['w'] = {'function': 'subject.outline', 'meaning': '主体轮廓', 'status': 'proposal'}
    third['z'] = {'function': 'component.connected_horizontal_group', 'meaning': '连接横笔组',
                  'status': 'accepted-independent-trial',
                  'condition': '共享侧边竖干且可由原墨迹分出的两或三条横笔；数量经字号粗细扰动复核'}
    families = {k: dict(v) for k, v in baseline['definitions']['families'].items()}
    families['b'] = {'id': 'family.double-loop', 'meaning': '双环', 'anchors': ['∞', '8'],
                     'status': 'trial-binding', 'boundary': '沿用已审边界；B为补充入口，不强制同主族'}
    font = Path('C:/Windows/Fonts/seguisym.ttf')
    reference_sizes = {family: {style: {key: render(ch, font)[1] for key, ch in zip('vcxz', chars)}
                                for style, chars in styles.items()} for family, styles in SIZE_REFERENCES.items()}
    return {
        'version': VERSION, 'status': 'candidate-bindings-only',
        'families': families,
        'third': third, 'fourth': fourth,
        'secondKeyBindings': {'b': '双环，沿用此前空键候选用于独立试验'},
        'typedExtensions': {
            'h/i': '成员对象表示单线方向；构件组表示中心排列轴',
            'w/s': '位置属性保留；三点组新增整体尖端朝上／下候选属性',
        },
        'sizePolicy': {
            'o': {'subjectSize': 'retain', 'references': reference_sizes['o'], 'reason': '已确认圆形大小系列'},
            's': {'subjectSize': 'retain', 'references': reference_sizes['s'], 'reason': '已确认方形大小系列'},
            'r': {'excludedKinds': ['body', 'hole', 'contour-section'],
                  'reason': '当前星形组不以主体及随主体变化的孔洞尺寸区分；独立附件另审'},
        },
        'sizeReferenceSource': {'characters': SIZE_REFERENCES, 'font': str(font), 'fontSHA256': fingerprint(font),
                                'method': '按已确认参考字形的em中心取对数距离最近档，不按码位覆盖归类'},
        'thresholds': {'outlineMSE': .065, 'hollowInkMSE': .15, 'solidOccupancy': .98,
                       'hollowOccupancyMax': .85, 'groupAxisRatio': 4.0},
    }


def trial_properties(o, family=None, size_policy=None):
    excluded = (size_policy or {}).get(family, {}).get('excludedKinds', [])
    attrs = [('g' if k == 'e' else k, why) for k, why in properties(o)
             if not (k in SIZE_KEYS and (o['kind'] == 'junction' or o['kind'] in excluded))]
    references = (size_policy or {}).get(family, {}).get('references', {}).get(o.get('sizeReferenceFill'))
    if o['kind'] == 'body' and references and o['extentEm'] > 0:
        attrs = [(k, why) for k, why in attrs if k not in SIZE_KEYS]
        key = min(references, key=lambda k: abs(np.log(o['extentEm'] / references[k])))
        attrs.append((key, '同族同填充参考系列的相对主体尺寸'))
    if o.get('fill'):
        attrs.append(('e' if o['fill'] == 'hollow' else 'f', '选定主体的填充状态'))
    if o.get('memberCount') in (2, 3):
        attrs.append(('b' if o['memberCount'] == 2 else 't', '选定构件组的成员数量'))
    if o.get('arrangement'):
        attrs.append((o['arrangement'], '选定构件组的成员中心排列轴'))
    if o.get('triangleDirection'):
        attrs.append((o['triangleDirection'], '选定三点组的整体尖端朝向'))
    if o['kind']=='body' and o.get('positionReference')=='parent-subject':
        key = position(*o['relativePosition'],0,0)
        if key:
            attrs.append((key,'选定边框中心相对原字主体中心'))
    return list(dict.fromkeys(attrs))


def line_group(f):
    parts = f['parts']
    if len(parts) < 2:
        return False
    directions = []
    lengths = []
    for p in parts:
        w, h = p['x1'] - p['x0'], p['y1'] - p['y0']
        if max(w / h, h / w) < 3 or p['area'] / (w * h) < .55:
            return False
        directions.append('h' if w > h else 'i')
        lengths.append(max(w, h))
    return len(set(directions)) == 1 and max(lengths) / min(lengths) <= 1.25


def group_object(f):
    parts = f['parts']
    box = [min(p['x0'] for p in parts), min(p['y0'] for p in parts),
           max(p['x1'] for p in parts), max(p['y1'] for p in parts)]
    o = obj('visible-part-group', 'part-group', box, f['bbox'], f['extent'])
    o['memberCount'] = len(parts)
    o['memberCentres'] = [[p['cx'], p['cy']] for p in parts]
    points = np.array(o['memberCentres'])
    delta = np.ptp(points, axis=0)
    if delta[0] > 4 * max(delta[1], .1):
        o['arrangement'] = 'h'
    elif delta[1] > 4 * max(delta[0], .1):
        o['arrangement'] = 'i'
    if len(parts) == 3 and dot_group(f):
        # A stable pair at one height and a separated apex, not any three dots.
        scale = max(box[2] - box[0], box[3] - box[1])
        order = np.argsort(points[:, 1])
        a, b, c = points[order]
        up = abs(b[1] - c[1]) <= .12 * scale and b[1] - a[1] >= .3 * scale
        down = abs(a[1] - b[1]) <= .12 * scale and c[1] - b[1] >= .3 * scale
        if up and min(b[0], c[0]) < a[0] < max(b[0], c[0]):
            o['triangleDirection'] = 'w'
        elif down and min(a[0], b[0]) < c[0] < max(a[0], b[0]):
            o['triangleDirection'] = 's'
    return o


def outline_anchors(font_path):
    anchors = {}
    for family, chars in OUTLINES.items():
        anchors[family] = {
            'contours': [normalized(filled(render(ch, font_path)[0])) for ch in chars],
            'hollowInk': normalized(render(chars[0], font_path)[0]),
        }
    return anchors


def fill_state(f, family, anchors):
    if family not in anchors or len(f['parts']) != 1:
        return None
    view = normalized(f['silhouette'])
    if min(float(((view - a) ** 2).mean()) for a in anchors[family]['contours']) > .065:
        return None
    occupancy = float(f['body'].sum() / f['silhouette'].sum())
    ink_distance = float(((normalized(f['body']) - anchors[family]['hollowInk']) ** 2).mean())
    if family in ('o', 's') and len(f['holes']) == 1:
        ink = normalized(f['body'])
        symmetry = max(float(abs(ink - np.flip(ink, axis=0)).mean()),
                       float(abs(ink - np.flip(ink, axis=1)).mean()))
        hole = f['holes'][0]
        x0, y0, x1, y1 = f['bbox']
        offset = max(abs(hole['cx'] - (x0 + x1) / 2), abs(hole['cy'] - (y0 + y1) / 2)) / max(x1 - x0, y1 - y0)
        if symmetry <= .08 and offset <= .08:
            return 'hollow'
    if len(f['holes']) == 1 and occupancy <= .85 and ink_distance <= .15:
        return 'hollow'
    if not f['holes'] and occupancy >= .98:
        return 'solid'
    return None


def extension_facts(f, family, anchors):
    result = []
    if len(f['parts']) > 1:
        group = group_object(f)
        result.append({'third': 'k', 'function': RULES['k'][0], 'object': group,
                       'reason': '多个分离墨部件；本条绑定整个构件组', 'status': 'proposal'})
    fill = fill_state(f, family, anchors)
    square_size_series = (family == 's' and .8 <= f['ratio'] <= 1.25
                          and min(float(((normalized(f['silhouette']) - a) ** 2).mean())
                                  for a in anchors['s']['contours']) <= .065)
    if fill or square_size_series:
        body = obj('visible-body', 'body', f['bbox'], f['bbox'], f['extent'])
        if fill:
            body['fill'] = fill
            body['sizeReferenceFill'] = fill
        third = 's' if family == 'o' and .8 <= f['ratio'] <= 1.25 else 'w'
        result.append({'third': third, 'function': RULES[third][0] if third in RULES else 'subject.outline',
                       'object': body, 'reason': '完整主体轮廓；填充及有对照系列的尺寸，不使用孔洞对象',
                       'status': 'proposal'})
    return result


def trial_facts(f, family, anchors):
    return facts(f, family) + extension_facts(f, family, anchors)


def make_paths(bucket, family, observations, definitions):
    output = {}
    for fact in observations:
        prefix = bucket + family + fact['third']
        attrs = trial_properties(fact['object'], family, definitions.get('sizePolicy'))
        for key, why in attrs or [('', '缺少可用第四位，停在三码')]:
            assert not key or key in definitions['fourth']
            code = prefix + key
            evidence = {'rule': fact['function'], 'object': fact['object'],
                        'attribute': why, 'fourthObjectId': fact['object']['id']}
            p = output.setdefault(code, {'code': code, 'evidence': [], 'preferred': False})
            if evidence not in p['evidence']:
                p['evidence'].append(evidence)
            if key in ('e', 'f') and fact['object'].get('fill'):
                p['preferred'] = True
            if why in ('选定构件组的成员中心排列轴', '选定三点组的整体尖端朝向'):
                if fact['object'].get('groupType') != 'connected-stroke-group':
                    p['preferred'] = True
            if why == '选定构件组的成员数量' and fact['object'].get('groupType') == 'connected-stroke-group':
                p['preferred'] = True
    return sorted(output.values(), key=lambda p: (not p['preferred'], p['code']))


def historical_transition(data):
    stats = collections.Counter()
    for row in data['records']:
        objects = {o['id']: o for o in row['objects']}
        before = {p['code'] for p in row['paths']}
        after = set()
        groups = {}
        for p in row['paths']:
            for e in p['evidence']:
                o = objects[e['objectId']]
                identity = (p['code'][:3], e['objectId'], e['rule'], e.get('familyTarget'))
                g = groups.setdefault(identity, {'prefix': p['code'][:3], 'drop': False, 'keep': False})
                drop = len(p['code']) == 4 and p['code'][-1] in SIZE_KEYS and o['kind'] == 'junction'
                g['drop' if drop else 'keep'] = True
                if not drop:
                    after.add(p['code'])
        for g in groups.values():
            if g['drop'] and not g['keep']:
                after.add(g['prefix'])
        stats['oldPaths'] += len(before)
        stats['removedJunctionSizePairs'] += len(before - after)
        stats['addedThreeKeyPairs'] += len(after - before)
        stats['afterJunctionFix'] += len(after)
        stats['charactersLosingAllPaths'] += bool(before) and not after
        stats['alignmentPairsToRebind'] += sum(len(c) == 4 and c[-1] == 'e' for c in after)
    return dict(stats)


def build(output):
    manifest_path = DATA / '全形核对版.json'
    manifest = load(manifest_path)
    source_index = PROJECT / manifest['indexPath']
    assert fingerprint(source_index) == manifest['indexSHA256']
    baseline = load(source_index)
    protected = [manifest_path, source_index, DATA / '全形第四位-当前布局.json',
                 DATA / 'codebooks.json', DATA / 'shape-stage.json', ROOT / '最新实验.json']
    before = {str(p): fingerprint(p) for p in protected}
    definitions = trial_definitions(baseline)
    font = Path('C:/Windows/Fonts/seguisym.ttf')
    anchors = outline_anchors(font)
    samples = []
    glyphs = []
    for ch in '○●□■☆★∥=∴∵':
        row = next(r for r in baseline['records'] if r['char'] == ch)
        mask, extent = render(ch, font)
        f = observe(mask, extent)
        family = 'l' if line_group(f) else row['familyKey']
        coarse = '线与转折' if family == 'l' else None
        bucket = row['bucket']
        if coarse:
            proportion = 'tall' if f['ratio'] < .8 else 'wide' if f['ratio'] > 1.25 else 'balanced'
            bucket = next(g['bucket'] for g in baseline['bucketGroups']
                          if g['coarse'] == coarse and g['proportion'] == proportion)
        obs = trial_facts(f, family, anchors)
        paths = make_paths(bucket, family, obs, definitions)
        preferred = [p['code'] for p in paths if p['preferred']]
        glyphs.append((ch, mask, preferred))
        samples.append({'char': ch, 'cp': ord(ch), 'bucket': bucket, 'family': family,
                        'baselineFamily': row['familyKey'], 'paths': paths,
                        'group': group_object(f) if len(f['parts']) > 1 else None})
    transition = historical_transition(load(source_index.parent / 'shape-experiment.json'))
    assert before == {str(p): fingerprint(p) for p in protected}
    output.mkdir(parents=True, exist_ok=False)
    result = {'version': VERSION, 'status': 'sample-trial-only', 'baseline': baseline['id'],
              'definitions': definitions, 'samples': samples, 'historicalTransition': transition,
              'protectedFiles': before, 'protectedUnchanged': True,
              'font': str(font), 'fontSHA256': fingerprint(font),
              'limitations': ['绑定为试验候选，未改编辑器或Rime。',
                              '完整新路径仅对十个代表字符生成；全量统计仅模拟交点尺寸排除及正置迁键影响。',
                              '未对28223字运行新填充与构件组检测；不声称达到全量覆盖。']}
    (output / '样本试验.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    canvas = Image.new('RGB', (880, 760), 'white')
    draw = ImageDraw.Draw(canvas)
    label_font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 23)
    for i, (ch, mask, preferred) in enumerate(glyphs):
        x, y = (i % 2) * 440, (i // 2) * 150
        draw.text((x + 14, y + 8), f'P{i // 2 + 1}  U+{ord(ch):04X}', fill='black', font=label_font)
        glyph = Image.fromarray((255 - mask.astype('uint8') * 255)).resize((96, 96), Image.Resampling.NEAREST)
        canvas.paste(glyph, (x + 14, y + 43))
        draw.text((x + 128, y + 70), ', '.join(preferred), fill='black', font=label_font)
    canvas.save(output / '五组试验.png')
    print(json.dumps({'output': str(output), 'sampleCount': len(samples), 'transition': transition,
                      'protectedUnchanged': True}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / '键位试验' / datetime.now().strftime('%Y%m%d-%H%M%S'))
    build(parser.parse_args().output)
