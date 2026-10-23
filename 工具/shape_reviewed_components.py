"""Object-backed supplementary entries for explicitly reviewed lookups."""
import hashlib

import numpy as np

from shape_experiment_features import observe, bounds, crossing_topology
from shape_keyboard_trial import obj, RULES


def cycle_subject(f):
    """Prune skeletal tails, then partition only existing ink by nearest branch."""
    if len(f['holes']) != 1:
        return None
    sk = crossing_topology(f['body'])['skeleton']
    cycle = sk.copy()
    while True:
        p = np.pad(cycle, 1)
        neighbours = [p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]]
        degree = sum(n.astype('uint8') for n in neighbours)
        # Do not count a diagonal shortcut when an orthogonal connection exists.
        for dy, dx, a, b in ((0, 0, 0, 2), (0, 2, 0, 3), (2, 0, 1, 2), (2, 2, 1, 3)):
            degree += (p[dy:dy+sk.shape[0], dx:dx+sk.shape[1]] & ~neighbours[a] & ~neighbours[b]).astype('uint8')
        leaves = cycle & (degree <= 1)
        if not leaves.any():
            break
        cycle[leaves] = False
    tail = sk & ~cycle
    if not cycle.any() or not tail.any():
        return None
    pixels = np.argwhere(f['body'])
    def distance(mask):
        points = np.argwhere(mask)
        return ((pixels[:, None, :] - points[None, :, :]) ** 2).sum(axis=2).min(axis=1)
    selected = distance(cycle) <= distance(tail)
    ring = np.zeros_like(sk)
    ring[tuple(pixels[selected].T)] = True
    remainder = f['body'] & ~ring
    rf = observe(ring, f['extent'])
    if len(rf['holes']) != 1 or len(rf['parts']) != 1 or ring.sum() < .65 * f['body'].sum():
        return None
    box = bounds(ring)
    whole_box = bounds(f['mask'])
    rf['extent'] = f['extent'] * max(box[2]-box[0], box[3]-box[1]) / max(
        whole_box[2]-whole_box[0], whole_box[3]-whole_box[1])
    proof = {'kind': 'cycle-tail', 'sourceInkSHA256': hashlib.sha256(f['body'].tobytes()).hexdigest(),
             'parentPixels': int(f['body'].sum()), 'ringPixels': int(ring.sum()),
             'tailPixels': int(remainder.sum()), 'overlapPixels': int((ring & remainder).sum()),
             'ringBBox': box, 'tailBBox': bounds(remainder),
             'ringInkSHA256': hashlib.sha256(ring.tobytes()).hexdigest(),
             'partition': 'nearest pruned skeletal cycle/tail; existing ink only'}
    return rf, remainder, proof


def closed_spine_arc(f):
    if len(f['parts']) != 1 or len(f['holes']) != 1:
        return []
    x0, y0, x1, y1 = f['bbox']
    body = f['body']
    candidates = [x for x in range(x0, x0 + max(1, (x1 - x0) // 3))
                  if body[y0:y1, x].mean() >= .88]
    if not candidates:
        return []
    cut = max(candidates) + 1
    spine, arc = body.copy(), body.copy()
    spine[:, cut:] = False
    arc[:, :cut] = False
    if not spine.any() or not arc.any():
        return []
    sf, af = observe(spine, f['extent']), observe(arc, f['extent'])
    if len(sf['parts']) != 1 or len(af['parts']) != 1 or af['holes'] or af['endpoints'] != 2:
        return []
    sx0, sy0, sx1, sy1 = bounds(spine)
    if (sy1 - sy0) < .85 * (y1 - y0) or (sy1 - sy0) / (sx1 - sx0) < 4:
        return []
    ax0, ay0, ax1, ay1 = bounds(arc)
    # The two arc ends lie on the cut side; its outer bulge lies to their right.
    if af['junctions'] or ax1 - ax0 < .4 * (x1 - x0):
        return []
    proof = {'sourceInkSHA256': hashlib.sha256(body.tobytes()).hexdigest(),
             'parentPixels': int(body.sum()), 'spinePixels': int(spine.sum()), 'arcPixels': int(arc.sum()),
             'overlapPixels': int((spine & arc).sum()), 'cutX': cut,
             'partition': 'visible ink left/right of a full-height spine; no synthetic ink'}
    line = obj('visible-spine', 'part', [sx0, sy0, sx1, sy1], f['bbox'], f['extent'],
               area=int(spine.sum()), orientation=90)
    virtual_ellipse = [2 * ax0 - ax1, ay0, ax1, ay1]
    curve = obj('visible-half-arc', 'contour-section', [ax0, ay0, ax1, ay1], virtual_ellipse, f['extent'],
                area=int(arc.sum()))
    curve['referenceFrame'] = '按可见右半弧拟合的完整椭圆；非整字中心'
    curve['sourceSubjectBBox'] = f['bbox']
    return [
        {'familyKey': 'l', 'familyId': 'family.line', 'target': 'reviewed-spine', 'ratio': sf['ratio'],
         'proof': proof, 'facts': [{'third': 'l', 'function': RULES['l'][0], 'object': line,
                                  'reason': '从闭合轮廓实际墨迹中分出的完整竖直主干', 'status': 'proposal'}]},
        {'familyKey': 'c', 'familyId': 'family.open-arc', 'target': 'reviewed-half-arc', 'ratio': af['ratio'],
         'proof': proof, 'facts': [{'third': 'p', 'function': RULES['p'][0], 'object': curve,
                                  'reason': '去除实际竖干后连通的右侧半弧；位置相对拟合完整椭圆', 'status': 'proposal'}]},
    ]
