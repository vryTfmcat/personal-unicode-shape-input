"""Extract a visible face boundary from existing ink, never from a hole alone."""
import hashlib
from itertools import combinations

import numpy as np
from PIL import Image, ImageDraw

from shape_experiment_features import observe, bounds, component_mask, dilate, normalized
from shape_lab_features import components
from shape_quality_v2 import skeleton


def distance_to(points, mask):
    targets = np.argwhere(mask)
    return ((points[:,None,:]-targets[None,:,:])**2).sum(axis=2).min(axis=1)


def polygon_face(mask, diagnostics=None):
    yy,xx = np.nonzero(mask)
    if min(np.ptp(xx)+1,np.ptp(yy)+1)<18:
        return None
    points = sorted((int(x),int(y)) for y,x in np.argwhere(mask))
    def cross(o,a,b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves = []
    for seq in (points,points[::-1]):
        half = []
        for p in seq:
            while len(half)>=2 and cross(half[-2],half[-1],p)<=0:
                half.pop()
            half.append(p)
        halves.append(half[:-1])
    hull = halves[0]+halves[1]
    if len(hull)<3:
        return None
    def raster(vertices):
        im = Image.new('1',(mask.shape[1],mask.shape[0]))
        ImageDraw.Draw(im).polygon(vertices,fill=1)
        return np.array(im,dtype=bool)
    hull_mask = raster(hull)
    if diagnostics is not None:
        diagnostics.append({'hullMissing':float((hull_mask&~mask).sum()/hull_mask.sum()),'hull':hull})
    if (hull_mask & ~mask).sum()/hull_mask.sum()>.22:
        return None
    for count in (3,4):
        if len(hull)<count:
            continue
        choices = np.array(list(combinations(range(len(hull)),count)))
        polygons = np.array(hull)[choices]
        areas = abs((polygons[:,:,0]*np.roll(polygons[:,:,1],-1,axis=1)
                     -polygons[:,:,1]*np.roll(polygons[:,:,0],-1,axis=1)).sum(axis=1))
        vertices = [tuple(int(x) for x in p) for p in polygons[int(areas.argmax())]]
        poly = raster(vertices)
        mismatch = float(np.logical_xor(poly,hull_mask).sum()/hull_mask.sum())
        boundary = poly & dilate(~poly,1)
        unexplained = float((np.logical_xor(poly,hull_mask)&~dilate(boundary,1)).sum()/hull_mask.sum())
        sides = np.linalg.norm(np.roll(np.array(vertices),-1,axis=0)-vertices,axis=1)
        if diagnostics is not None:
            diagnostics.append({'count':count,'vertices':vertices,'mismatch':mismatch,'sides':sides.tolist()})
        if mismatch<=.20 and unexplained<=.015 and sides.min()/sides.max()>=.25:
            return {'familyKey':'t' if count==3 else 's','vertices':vertices,
                    'faceMismatchFraction':mismatch,'beyondOnePixelBoundaryFraction':unexplained,
                    'faceHullMissingFraction':float((hull_mask&~mask).sum()/hull_mask.sum())}
    return None


def connected_frames(f, views, include_unclassified=False):
    if not f['holes']:
        return []
    body = f['body']
    width,height = f['bbox'][2]-f['bbox'][0],f['bbox'][3]-f['bbox'][1]
    eligible = [h for h in f['holes'] if h['x1']-h['x0']>=width*.25
                and h['y1']-h['y0']>=height*.25 and h['area']>=max(20,width*height*.04)]
    if not eligible:
        return []
    sk = skeleton(body)
    voids = ~np.pad(sk,1)
    faces = [component_mask(voids,h,4)[1:-1,1:-1] for h in components(voids,4)
             if not h['edge'] and h['area']>=20]
    if not faces:
        return []
    source_voids = ~np.pad(body,1)
    ink_points = np.argwhere(body)
    whole_box = bounds(f['mask'])
    output = []
    for number,hole in enumerate(sorted(eligible,key=lambda h:-h['area'])[:3]):
        padded = dict(hole)
        for key in ('x0','x1','y0','y1','cx','cy'):
            padded[key] += 1
        hole_mask = component_mask(source_voids,padded,4)[1:-1,1:-1]
        face = max(faces,key=lambda a:int((a&hole_mask).sum()))
        if (face&hole_mask).sum()<hole['area']*.95:
            continue
        cycle = sk & dilate(face,1)
        if not cycle.any():
            continue
        other = sk & ~cycle
        selected = (distance_to(ink_points,cycle)<=distance_to(ink_points,other)) if other.any() else np.ones(len(ink_points),dtype=bool)
        frame = np.zeros_like(body)
        frame[tuple(ink_points[selected].T)] = True
        remainder = body & ~frame
        if not frame.any():
            continue
        box = bounds(frame)
        if box[2]-box[0]<width*.35 or box[3]-box[1]<height*.35:
            continue
        extent = f['extent'] * max(box[2]-box[0],box[3]-box[1])/max(whole_box[2]-whole_box[0],whole_box[3]-whole_box[1])
        ff = observe(frame,extent)
        if len(ff['parts'])!=1 or len(ff['holes'])!=1 or not .35<=ff['ratio']<=2.8:
            continue
        if ff['holes'][0]['area']<hole['area']*.9 or hole['area']/ff['silhouette'].sum()<.15:
            continue
        errors = {key:float(np.min(np.mean((views[key]-normalized(ff['silhouette']))**2,axis=(1,2)))) for key in 'ost'}
        family = min(errors,key=errors.get)
        best_family=family
        runner_up = min(v for k,v in errors.items() if k!=family)
        polygon = None
        if errors[family]>{'o':.035,'s':.045,'t':.05}[family] or runner_up-errors[family]<.015:
            polygon = polygon_face(hole_mask)
            if polygon is None:
                if not include_unclassified:
                    continue
                family=None
            else:
                family = polygon['familyKey']
        proof = {'kind':'visible-connected-frame','sourceInkSHA256':hashlib.sha256(body.tobytes()).hexdigest(),
                 'parentPixels':int(body.sum()),'framePixels':int(frame.sum()),'remainderPixels':int(remainder.sum()),
                 'overlapPixels':int((frame&remainder).sum()),'frameBBox':box,
                 'sourceHoleBBox':[hole[k] for k in ('x0','y0','x1','y1')],'sourceHoleArea':hole['area'],
                 'frameInkSHA256':hashlib.sha256(frame.tobytes()).hexdigest(),
                 'remainderInkSHA256':hashlib.sha256(remainder.tobytes()).hexdigest(),
                 'partition':'nearest actual skeletal face boundary vs other actual skeleton; no synthetic ink',
                 'familyKey':family,'prototypeError':errors[family or best_family],'runnerUpError':runner_up}
        proof['polygonFace'] = polygon
        output.append({'familyKey':family,'target':'connected-frame-'+str(number),'feature':ff,
                       'remainder':remainder,'proof':proof})
    return output


def border_spines(f):
    if not f['holes']:
        return []
    output = []
    body = f['body']
    x0,y0,x1,y1 = f['bbox']
    for axis in (0,1):
        oriented = body if axis==0 else body.T
        low,high,start,end = (x0,x1,y0,y1) if axis==0 else (y0,y1,x0,x1)
        span = end-start
        if span<24:
            continue
        occupancy = oriented[start:end,low:high].mean(axis=0)
        indices = np.flatnonzero(occupancy>=.92)+low
        groups = np.split(indices,np.flatnonzero(np.diff(indices)>1)+1)
        for group in groups:
            if len(group)<2 or span/len(group)<5:
                continue
            if not (group[-1]<low+(high-low)*.25 or group[0]>=high-(high-low)*.25):
                continue
            selected = np.zeros_like(oriented)
            selected[start:end,group[0]:group[-1]+1] = oriented[start:end,group[0]:group[-1]+1]
            spine = selected if axis==0 else selected.T
            share = float(spine.sum()/body.sum())
            if not .15<=share<=.5:
                continue
            sf = observe(spine,f['extent'])
            if len(sf['parts'])!=1 or sf['holes'] or sf['endpoints']!=2 or sf['junctions']:
                continue
            remainder = body&~spine
            proof = {'kind':'visible-border-spine','sourceInkSHA256':hashlib.sha256(body.tobytes()).hexdigest(),
                     'parentPixels':int(body.sum()),'spinePixels':int(spine.sum()),'remainderPixels':int(remainder.sum()),
                     'overlapPixels':0,'spineBBox':sf['bbox'],'orientation':90 if axis==0 else 0,
                     'minimumColumnOrRowOccupancy':float(occupancy[group-low].min()),
                     'spineInkSHA256':hashlib.sha256(spine.tobytes()).hexdigest(),
                     'partition':'complete observed border band, existing ink only'}
            output.append({'feature':sf,'mask':spine,'proof':proof,'target':'border-spine-'+str(len(output))})
    return sorted(output,key=lambda x:-x['proof']['spinePixels'])[:2]
