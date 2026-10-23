"""Narrow, identity-blind probes for unbound first-key group/face proposals."""
import hashlib

import numpy as np

from shape_experiment_features import bounds, render
from shape_lab_features import components

VERSION = 'historical-bucket-semantic-pilot-20261022-v1'


def ink_info(mask):
    parts = [p for p in components(mask, 8) if p['area'] >= 3]
    box = bounds(mask)
    holes = [p for p in components(~np.pad(mask, 1), 4) if not p['edge'] and p['area'] >= 5]
    return {'mask': mask, 'parts': parts, 'bbox': box, 'holes': holes}


def parallel_layers(info):
    """Account for all ink as aligned rows of one/two rectangular line pieces."""
    parts, mask = info['parts'], info['mask']
    if len(parts) < 2 or sum(p['area'] for p in parts) < mask.sum() * .995:
        return None
    for axis in (0, 1):
        along, across = ('x', 'y') if axis == 0 else ('y', 'x')
        lengths = np.array([p[along+'1']-p[along+'0'] for p in parts])
        widths = np.array([p[across+'1']-p[across+'0'] for p in parts])
        if (lengths / widths < 2.5).any() or widths.max() > widths.min() * 1.5:
            continue
        def rectangular(p, length, width):
            fraction = p['area'] / (length * width)
            core = mask[p['y0']+1:p['y1']-1,p['x0']+1:p['x1']-1]
            return fraction>=.88 or (fraction>=.80 and core.size>0 and core.mean()>=.98)
        if not all(rectangular(p,length,width) for p,length,width in zip(parts,lengths,widths)):
            continue
        bands = []
        for p in sorted(parts, key=lambda p: p['c'+across]):
            if not bands or abs(p['c'+across] - np.mean([b['c'+across] for b in bands[-1]])) > widths.mean() * .7:
                bands.append([])
            bands[-1].append(p)
        if len(bands) < 2 or any(len(b) not in (1, 2) for b in bands):
            continue
        spans = [max(p[along+'1'] for p in b)-min(p[along+'0'] for p in b) for b in bands]
        centres = [(max(p[along+'1'] for p in b)+min(p[along+'0'] for p in b))/2 for b in bands]
        if max(spans)/min(spans) > 1.15 or np.ptp(centres) > max(spans)*.08:
            continue
        if any(len(b)==2 and max(p['area'] for p in b)/min(p['area'] for p in b)>1.3 for b in bands):
            continue
        positions = [np.mean([p['c'+across] for p in b]) for b in bands]
        gaps = np.diff(positions)
        if gaps.min() < widths.mean()*1.15 or gaps.max()/gaps.min()>1.25:
            continue
        rows = [[p['x0'],p['y0'],p['x1'],p['y1']] for b in bands for p in b]
        return {'kind':'parallel-layer-group', 'memberDirection':'h' if axis==0 else 'i',
                'arrangement':'i' if axis==0 else 'h', 'layerCount':len(bands),
                'pieceCount':len(parts), 'piecesPerLayer':[len(b) for b in bands],
                'memberBBoxes':rows, 'bbox':info['bbox'],
                'explainedInkFraction':float(sum(p['area'] for p in parts)/mask.sum()),
                'sourceInkSHA256':hashlib.sha256(mask.tobytes()).hexdigest()}
    return None


def stepped_face(info):
    """A conservative 2x3/3x2 solid-cell pilot, not every irregular polygon."""
    if len(info['parts']) != 1 or info['holes']:
        return None
    x0,y0,x1,y1 = info['bbox']
    mask = info['mask'][y0:y1,x0:x1]
    h,w = mask.shape
    density = float(mask.mean())
    if min(w,h)<20 or not .40<=density<=.90:
        return None
    for rows,cols in ((3,2),(2,3)):
        ys = np.rint(np.linspace(0,h,rows+1)).astype(int)
        xs = np.rint(np.linspace(0,w,cols+1)).astype(int)
        cells = np.array([[mask[ys[y]:ys[y+1],xs[x]:xs[x+1]].mean()
                           for x in range(cols)] for y in range(rows)])
        if np.minimum(cells,1-cells).max()>.10:
            continue
        pattern = cells>=.5
        if not 3<=pattern.sum()<=5:
            continue
        model = np.zeros_like(mask)
        for y,x in np.argwhere(pattern):
            model[ys[y]:ys[y+1],xs[x]:xs[x+1]] = True
        mismatch = float((model != mask).mean())
        if mismatch>.025:
            continue
        return {'kind':'stepped-solid-face', 'bbox':info['bbox'], 'grid':[rows,cols],
                'filledCells':int(pattern.sum()), 'cellPattern':pattern.astype(int).tolist(),
                'cellDensities':cells.tolist(), 'modelMismatchFraction':mismatch,
                'sourceInkSHA256':hashlib.sha256(info['mask'].tobytes()).hexdigest(),
                'scope':'2x3-or-3x2-stepped-solid-cells-only; not generic-solid-or-all-cut-polygons'}
    return None


def stable_probe(row, detector, fonts=None):
    """Keep every failed perturbation; base success never implies stability."""
    font = row['font']
    results = []
    for size in (48,96,128):
        for weight in (-1,0,1):
            try:
                mask,_ = render(row['char'],font['path'],font.get('index',0),size=size,weight=weight,fonts=fonts)
                result = detector(ink_info(mask))
            except (ValueError,OSError) as error:
                results.append({'size':size,'weight':weight,'passed':False,'error':str(error)})
                continue
            results.append({'size':size,'weight':weight,'passed':result is not None,'object':result})
    signatures = set()
    for result in results:
        obj = result.get('object') or {}
        if detector is parallel_layers:
            signatures.add((obj.get('memberDirection'),obj.get('layerCount'),tuple(obj.get('piecesPerLayer',[]))))
        else:
            # Grid geometry may transpose under aspect ratio quantization; compare actual pattern too.
            signatures.add((tuple(obj.get('grid',[])),str(obj.get('cellPattern'))))
    return {'passed':all(r['passed'] for r in results) and len(signatures)==1,
            'variants':results,'variantCount':len(results), 'scope':'locked-font-only; not cross-font agreement'}
