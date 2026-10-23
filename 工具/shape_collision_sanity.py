"""Negative geometry certificates, separate from weak positive evidence."""
import hashlib

from shape_experiment_features import observe, render
from shape_recovery_geometry import two_stroke_angle


VERSION = 'collision-negative-geometry-20261021-v1'


def contradiction(f, family):
    simple = len(f['parts']) == 1 and not f['holes'] and not f['junctionObjects'] and f['endpoints'] == 2
    if not simple:
        return None
    if family in ('h', 'x', 'r'):
        return {'kind': 'single-open-path-without-intersection',
                'parts': 1, 'holes': 0, 'endpoints': 2, 'junctions': 0}
    if family == 'j':
        angle = two_stroke_angle(f)
        if angle and angle['maxSkeletonDeviationPixels'] <= 1.0:
            span = max(f['bbox'][2]-f['bbox'][0], f['bbox'][3]-f['bbox'][1])
            if angle['minimumArmPixels'] >= .30 * span:
                return {'kind': 'two-long-straight-arms-not-curved-hook', 'angleProof': angle}
    return None


def certify(row, f, family):
    base = contradiction(f, family)
    if base is None:
        return None
    variants = []
    font = row['font']
    for size in (48, 96, 128):
        for weight in (-1, 0, 1):
            try:
                vf = observe(*render(row['char'], font['path'], font.get('index', 0), size=size, weight=weight))
            except (OSError, ValueError):
                return None
            proof = contradiction(vf, family)
            if proof is None or proof['kind'] != base['kind']:
                return None
            variants.append({'size': size, 'weight': weight, 'proof': proof,
                             'inkSHA256': hashlib.sha256(vf['body'].tobytes()).hexdigest()})
    return {'version': VERSION, 'familyKey': family, 'target': 'body', 'kind': base['kind'],
            'canonical': base, 'variants': variants, 'scope': 'negative-certificate-not-low-prototype-score'}
