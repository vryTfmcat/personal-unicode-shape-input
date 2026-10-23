"""Extract connected comb-like horizontal strokes without counting components."""
import hashlib

import numpy as np

from shape_experiment_features import bounds, observe, render
from shape_keyboard_trial import obj


VERSION = 'connected-horizontal-stroke-group-20261021-v1'


def runs(values):
    indices=np.flatnonzero(values)
    return [r for r in np.split(indices,np.flatnonzero(np.diff(indices)>1)+1) if len(r)]


def horizontal_stroke_group(f):
    if len(f['parts'])!=1 or f['holes']:
        return None
    x0,y0,x1,y1=f['bbox']; w,h=x1-x0,y1-y0
    if h<30 or w<12 or not .25<=w/h<=1.5:
        return None
    body=f['body']; crop=body[y0:y1,x0:x1]
    for stem in runs(crop.mean(axis=0)>=.90):
        if len(stem)<2 or len(stem)>w*.35:
            continue
        if w*.22<float(stem.mean())<w*.78:
            continue
        rows=[]
        for y in range(h):
            row=runs(crop[y])
            rows.append(len(row)==1 and len(row[0])>=w*.55)
        bands=runs(rows)
        bands=[b for b in bands if max(2,round(h*.045))<=len(b)<=h*.20]
        if len(bands) not in (2,3):
            continue
        centres=np.array([float(b.mean()) for b in bands])
        if np.diff(centres).min()<h*.20:
            continue
        members=[]
        for band in bands:
            mask=np.zeros_like(body)
            mask[y0+band[0]:y0+band[-1]+1]=body[y0+band[0]:y0+band[-1]+1]
            members.append(mask)
        union=np.logical_or.reduce(members)
        stem_mask=np.zeros_like(body)
        stem_mask[y0:y1,x0+stem[0]:x0+stem[-1]+1]=crop[:,stem[0]:stem[-1]+1]
        explained=float((union|stem_mask).sum()/body.sum())
        if explained<.97:
            continue
        remainder=body&~union
        boxes=[bounds(mask) for mask in members]
        centres=[[(b[0]+b[2])/2,(b[1]+b[3])/2] for b in boxes]
        group=obj('connected-horizontal-stroke-group','part-group',bounds(union),f['bbox'],f['extent'])
        group.update(memberCount=len(members),memberCentres=centres,memberBBoxes=boxes,
                     memberOrientation='h',arrangement='i',groupType='connected-stroke-group')
        proof={'kind':'connected-horizontal-stroke-group','memberCount':len(members),
               'memberBBoxes':boxes,'memberPixels':[int(mask.sum()) for mask in members],
               'memberInkSHA256':[hashlib.sha256(mask.tobytes()).hexdigest() for mask in members],
               'sourceInkSHA256':hashlib.sha256(body.tobytes()).hexdigest(),
               'remainderInkSHA256':hashlib.sha256(remainder.tobytes()).hexdigest(),
               'parentPixels':int(body.sum()),'groupPixels':int(union.sum()),
               'remainderPixels':int(remainder.sum()),'overlapPixels':0,
               'stemBBox':bounds(stem_mask),'fractionExplainedByBarsAndStem':explained,
               'memberOrientation':'h','groupArrangement':'i',
               'partition':'existing ink in disjoint horizontal bands; no artificial stroke completion'}
        return {'object':group,'members':members,'mask':union,'remainder':remainder,'proof':proof}
    return None


def stable_stroke_group(row, f=None):
    font=row['font']
    f=f or observe(*render(row['char'],font['path'],font.get('index',0)))
    result=horizontal_stroke_group(f)
    if result is None:
        return None
    count=result['object']['memberCount']
    variants=[]
    for size in (48,96,128):
        for weight in (-1,0,1):
            try:
                vf=observe(*render(row['char'],font['path'],font.get('index',0),size=size,weight=weight))
                candidate=horizontal_stroke_group(vf)
            except (OSError,ValueError):
                return None
            if candidate is None or candidate['object']['memberCount']!=count:
                return None
            variants.append({'size':size,'weight':weight,'proof':candidate['proof']})
    result['stabilityProof']={'version':VERSION,'variants':variants,'memberCountStable':count}
    return result
