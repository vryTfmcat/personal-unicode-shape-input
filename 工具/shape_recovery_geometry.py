"""Evidence for two-stroke angles and visible (not medial-axis-only) forks."""
import math

import numpy as np
from PIL import Image, ImageDraw

from shape_lab_features import components
from shape_quality_v2 import skeleton
from shape_experiment_features import component_mask


def angle_has_visible_gap(f):
    """A solid convex face's medial axis is not a visible two-stroke angle."""
    yy,xx = np.nonzero(f['body'])
    points = sorted(zip(xx.tolist(),yy.tolist()))
    def cross(o,a,b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves = []
    for seq in (points,points[::-1]):
        half = []
        for point in seq:
            while len(half)>=2 and cross(half[-2],half[-1],point)<=0:
                half.pop()
            half.append(point)
        halves.append(half[:-1])
    hull = halves[0]+halves[1]
    if len(hull)<3:
        return False
    im = Image.new('1',(f['body'].shape[1],f['body'].shape[0]))
    ImageDraw.Draw(im).polygon(hull,fill=1)
    hull_mask = np.array(im,dtype=bool)
    return bool((hull_mask & ~f['body']).sum() / hull_mask.sum() >= .06)


def endpoints(sk):
    p = np.pad(sk, 1)
    ns = [p[:-2, 1:-1], p[:-2, 2:], p[1:-1, 2:], p[2:, 2:],
          p[2:, 1:-1], p[2:, :-2], p[1:-1, :-2], p[:-2, :-2]]
    transitions = sum((~ns[i] & ns[(i + 1) % 8]).astype('uint8') for i in range(8))
    return np.argwhere(sk & (transitions == 1))[:, ::-1].astype(float)


def two_stroke_angle(f):
    if len(f['parts']) != 1 or f['holes'] or any(j['armCount'] >= 3 for j in f['junctionObjects']):
        return None
    sk = skeleton(f['body'])
    ends = endpoints(sk)
    if len(ends) != 2:
        return None
    points = np.argwhere(sk)[:, ::-1].astype(float)
    chord = ends[1] - ends[0]
    length2 = float(chord @ chord)
    if length2 < 16:
        return None
    t = np.clip((points-ends[0]) @ chord / length2, 0, 1)
    distance2 = ((points - ends[0] - t[:, None]*chord)**2).sum(axis=1)
    corner = points[distance2.argmax()]
    vectors = ends - corner
    lengths = np.linalg.norm(vectors, axis=1)
    span = max(f['bbox'][2]-f['bbox'][0], f['bbox'][3]-f['bbox'][1])
    if lengths.min() < max(7, .25*span):
        return None
    angle = math.degrees(math.acos(float(np.clip(vectors[0] @ vectors[1] / np.prod(lengths), -1, 1))))
    if not 25 <= angle <= 145:
        return None
    t = np.clip((points-corner) @ vectors.T / lengths**2, 0, 1)
    error = np.sqrt(((points[:, None, :]-corner-t[:, :, None]*vectors[None, :, :])**2).sum(axis=2).min(axis=1)).max()
    if error > 1.75 or not angle_has_visible_gap(f):
        return None
    return {'test': 'two-visible-stroke-angle', 'endpoints': ends.tolist(), 'corner': corner.tolist(),
            'angleDegrees': float(angle), 'maxSkeletonDeviationPixels': float(error),
            'minimumArmPixels': float(lengths.min())}


def converging_stroke_bands(f):
    """Fit two actual separated ink runs; solid triangles have only one run."""
    if len(f['parts']) != 1 or f['holes']:
        return None
    for turns in range(4):
        mask = np.rot90(f['body'], turns)
        yy, xx = np.nonzero(mask)
        y0, y1 = yy.min(), yy.max()+1
        height = y1-y0
        samples = []
        for y in range(y0+round(height*.08), y1-round(height*.08)):
            xs = np.flatnonzero(mask[y])
            runs = np.split(xs, np.flatnonzero(np.diff(xs)>1)+1)
            if len(runs) == 2 and min(len(r) for r in runs) >= 2:
                samples.append([y, runs[0].mean(), runs[1].mean(), len(runs[0]), len(runs[1])])
        if len(samples) < max(8, height*.40):
            continue
        points = np.array(samples)
        if np.ptp(points[:,0]) < .45*height:
            continue
        lines = [np.polyfit(points[:,0], points[:,i], 1) for i in (1,2)]
        errors = [float(np.max(np.abs(np.polyval(line,points[:,0])-points[:,i])))
                  for i,line in zip((1,2),lines)]
        difference = lines[0][0]-lines[1][0]
        if max(errors) > 1.5 or abs(difference) < .25:
            continue
        apex_y = (lines[1][1]-lines[0][1])/difference
        apex_x = np.polyval(lines[0],apex_y)
        # Thick joined strokes can end before their fitted centrelines meet.
        if not y0-height*.15 <= apex_y <= y1+height*.15 or not xx.min()-2 <= apex_x <= xx.max()+2:
            continue
        angle = abs(math.degrees(math.atan(lines[0][0])-math.atan(lines[1][0])))
        if not 25 <= angle <= 145:
            continue
        widths = np.median(points[:,3:5],axis=0)/2+2
        residuals = np.column_stack([np.abs(xx-np.polyval(line,yy))/width for line,width in zip(lines,widths)])
        explained = float((residuals.min(axis=1)<=1).mean())
        if explained < .97 or not angle_has_visible_gap(f):
            continue
        return {'test': 'two-converging-ink-bands', 'rotationQuarterTurns': turns,
                'sampledRows': len(samples), 'rowSpan': float(np.ptp(points[:,0])),
                'fittedLinesXFromY': [line.tolist() for line in lines],
                'maximumRunCentreErrors': errors, 'apexInRotatedMask': [float(apex_x),float(apex_y)],
                'angleDegrees': angle, 'fractionOfActualInkExplained': explained}
    return None


def visible_fork(f, junction, allowed_arms=(3,4)):
    if junction['armCount'] not in allowed_arms:
        return None
    box = junction['coreBbox']
    cx, cy = (box[0]+box[2]-1)/2, (box[1]+box[3]-1)/2
    if not f['mask'][round(cy), round(cx)]:
        return None
    yy, xx = np.indices(f['mask'].shape)
    radius2 = (xx-cx)**2 + (yy-cy)**2
    span = max(f['bbox'][2]-f['bbox'][0], f['bbox'][3]-f['bbox'][1])
    radius = max(8., min(12., span*.20))
    radii = [radius, radius+2]
    counts, occupancy, thick_evidence = [], [], []
    connected_ink = None
    for radius in radii:
        ring = (radius2 >= (radius-1.25)**2) & (radius2 <= (radius+1.25)**2)
        ports = [p for p in components(f['mask'] & ring, 8) if p['area'] >= 2]
        disk = radius2 <= radius**2
        density = float((f['mask'] & disk).sum() / disk.sum())
        if len(ports) != junction['armCount']:
            return None
        if density > .72:
            # Thick T/Y ink can fill most of the disk. Actual exits plus a
            # concave local ink hull distinguish it from a solid convex face.
            if connected_ink is None:
                for part in f['parts']:
                    if part['x0']<=cx<part['x1'] and part['y0']<=cy<part['y1']:
                        candidate=component_mask(f['mask'],part)
                        if candidate[round(cy),round(cx)]:
                            connected_ink=candidate
                            break
            if connected_ink is None:return None
            own_ports=[p for p in components(connected_ink & ring,8) if p['area']>=2]
            if len(own_ports)!=junction['armCount'] or not angle_has_visible_gap({'body': connected_ink & disk}):
                return None
            thick_evidence.append({'radius':radius,'density':density,
                                   'localConvexHullGapAtLeast':.06,'exitsFromSameConnectedInk':True})
        counts.append(len(ports))
        occupancy.append(density)
    result = {'test': 'visible-ink-fork-annuli', 'centre': [cx,cy], 'radii': radii,
            'visiblePortCounts': counts, 'diskInkDensities': occupancy,
            'armCount': junction['armCount'], 'source': 'actual-ink-not-filled-silhouette'}
    if thick_evidence:result['thickStrokeConcavityProof']=thick_evidence
    return result
