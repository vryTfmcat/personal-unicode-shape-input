"""Conservative whole-family gates; local structures never imply a whole subject."""
import numpy as np
from functools import lru_cache

from shape_experiment_features import normalized, observe, render
from shape_quality_v2 import skeleton
from shape_hook_geometry import straight_armed_junction


VERSION = 'whole-family-boundaries-20261021-v4'
LIMITS = {'u': .18, 'c': .18, 'o': .11, 's': .055, 't': .08}


@lru_cache(maxsize=1)
def retained_legacy_characters():
    from shape_keyboard_trial import ROOT, load
    review = load(ROOT / '人工审议.json')['keyboardConsultation20261020']['comparisonAcceptance20261021']
    assert review['decision'] == 'accepted'
    return frozenset(char for group in review['compoundAndLines'] for char in group.split('／'))


@lru_cache(maxsize=1)
def lookup_boundary_decisions():
    from shape_keyboard_trial import ROOT, load
    decision = load(ROOT / '人工审议.json')['keyboardConsultation20261020']['lookupBoundaryAcceptance20261021']
    assert decision['decision'] == 'accepted'
    return decision


@lru_cache(maxsize=4)
def reference_views(font):
    views = {}
    for family, chars in [('u', 'U∪∩⊂⊃⊔[]'), ('c', 'C(⌒◡◜◝◟◞'),
                          ('o', '○●0O'), ('s', '□■◇◆'), ('t', '△▲▷')]:
        views[family] = []
        for char in chars:
            for size in (48, 96, 128):
                for weight in (-1, 0, 1):
                    mask, extent = render(char, font, size=size, weight=weight)
                    for turns in range(4) if family in 'uct' else (0,):
                        rotated = np.rot90(mask, turns).copy()
                        view = observe(rotated, extent)['silhouette'] if family in 'ost' else rotated
                        views[family].append(normalized(view))
        views[family] = np.array(views[family])
    return views


def fits(f, family, views):
    if family == 'j' and straight_armed_junction(f):
        return False, '各支均为直线的交点结构不构成钩弯；不据分叉数量删除真实弯钩'
    if family in ('h', 'r') and not f['holes'] and len(f['parts']) == 1:
        view = normalized(f['silhouette'])
        if min(float(np.min(np.mean((views[k] - view) ** 2, axis=(1, 2)))) for k in 'ost') <= .015:
            return False, '实心几何面的细化骨架不等于可见分叉／放射墨迹'
    if family not in LIMITS:
        return True, None
    if family in 'uc' and (f['holes'] or len(f['parts']) != 1 or f['junctions'] or f['endpoints'] != 2):
        return False, '开口单曲线不能由闭孔、分离部件或分叉主体代替'
    if family == 'u' and not same_side_mouth(f):
        return False, 'U形开口的两个端部应处于主体同侧；单角折不满足'
    view = normalized(f['silhouette'] if family in 'ost' else f['body'])
    error = float(np.min(np.mean((views[family] - view) ** 2, axis=(1, 2))))
    if error > LIMITS[family]:
        return False, f'整体轮廓／墨迹误差{error:.4f}超过{LIMITS[family]:.3f}'
    return True, None


def same_side_mouth(f):
    sk = skeleton(f['body'])
    p = np.pad(sk, 1)
    neighbours = [p[:-2, 1:-1], p[:-2, 2:], p[1:-1, 2:], p[2:, 2:],
                  p[2:, 1:-1], p[2:, :-2], p[1:-1, :-2], p[:-2, :-2]]
    crossing = sum((~neighbours[i] & neighbours[(i + 1) % 8]).astype('uint8') for i in range(8))
    yy, xx = np.nonzero(sk & (crossing == 1))
    if len(xx) != 2:
        return False
    ends = np.column_stack((xx, yy))
    box = f['bbox']
    for axis in (0, 1):
        low, high = box[axis], box[axis + 2] - 1
        span = max(1, high - low)
        across = max(1, box[3 - axis] - box[1 - axis] - 1)
        same_face = max(ends[:, axis]) <= low + .25 * span or min(ends[:, axis]) >= high - .25 * span
        if same_face and np.ptp(ends[:, axis]) <= .2 * span and np.ptp(ends[:, 1 - axis]) >= .4 * across:
            return True
    return False


def refine(routes, primary, bucket, f, views, groups):
    kept, exclusions = [], []
    for route in routes:
        family = route['familyKey']
        valid, reason = fits(f, family, views) if route['target'] == 'body' and not route.get('reviewedRetain') else (True, None)
        if valid:
            kept.append(route)
        else:
            exclusions.append({'familyKey': family, 'target': route['target'], 'reason': reason})
    eligible = [r for r in kept if r['target'] == 'body' and not r.get('supplementOnly')]
    if primary and not any(r['familyKey'] == primary for r in eligible):
        replacement = next((r for r in eligible if r['familyKey'] not in ('h', 'r')), None)
        replacement = replacement or next(iter(eligible), None)
        primary = replacement['familyKey'] if replacement else None
        bucket = replacement['bucket'] if replacement else bucket
    return kept, primary, bucket, exclusions
