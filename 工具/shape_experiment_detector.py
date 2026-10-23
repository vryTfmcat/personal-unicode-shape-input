"""Reviewed semantic boundaries, independent of experimental keyboard letters.

This module does not read character identities. Font-rendered prototypes are
examples, not codepoint overrides. Unknown family letters remain unassigned.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from shape_lab_features import components
from shape_experiment_features import observe, signature, component_mask, filled, dilate

VERSION='reviewed-boundaries-20261017-v1'
DOUBLE_LOOP='family.double-loop'


def distance(f, anchor):
    return float(((f['signature']-anchor['signature'])**2).sum())+.025*min(1,abs(math.log(f['ratio']/anchor['ratio'])))


def dot_group(f):
    """Compact solid components, without a six-dot upper bound."""
    parts=f['parts']
    if not parts:return False
    areas=[p['area'] for p in parts]
    if max(areas)>min(areas)*3:return False
    for p in parts:
        w,h=p['x1']-p['x0'],p['y1']-p['y0']
        if not .5<=w/h<=2 or p['area']/(w*h)<.50:return False
        ink=component_mask(f['mask'],p)
        if int(filled(ink).sum())>int(ink.sum())*1.08:return False
    # A single large solid square or circle is a body, not automatically a dot.
    return len(parts)>1 or f['extent']<=.35


def hull_mask(f):
    points=sorted(set((p['cx'],p['cy']) for p in f['parts']))
    if len(points)<3:return None
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for seq,out in ((points,lower),(points[::-1],upper)):
        for p in seq:
            while len(out)>=2 and cross(out[-2],out[-1],p)<=0:out.pop()
            out.append(p)
    hull=lower[:-1]+upper[:-1]
    if len(hull)<3:return None
    im=Image.new('1',(f['mask'].shape[1],f['mask'].shape[0]));ImageDraw.Draw(im).polygon(hull,fill=1)
    return np.array(im,dtype=bool)


def shape_routes(f, anchors, loop_anchors=()):
    """Return semantic proposals and measured objects, with no invented codes.

    Main detector handles existing families; these additions enforce reviewed
    boundaries or provide independent object-specific alternate entries.
    """
    routes=[]
    def add(identity,key,target,why,priority=False,score=None,box=None):
        routes.append({'familyId':identity,'key':key,'target':target,'basis':why,
                       'priority':priority,'distance':score,'bbox':box or f['bbox'],
                       'status':'machine-proposal'})
    holes=f['holes']
    if len(holes)==2:
        a,b=holes
        if min(a['area'],b['area'])/max(a['area'],b['area'])>=.20:
            positive=[a for a in loop_anchors if a['role']=='positive']
            negative=[a for a in loop_anchors if a['role']=='boundary']
            dp=min((distance(f,a) for a in positive),default=1.)
            dn=min((distance(f,a) for a in negative),default=1.)
            add(DOUBLE_LOOP,None,'body','两个可观测闭环；正例形状距离与边界反例共同判断',dp<.07 and dp+.008<dn,dp)
    # Explicit compound examples outrank a mere crossing at their shared centre.
    compound=[a for a in anchors if a['key']=='m']
    dm=min((distance(f,a) for a in compound),default=1.)
    if dm<.018:
        add('family.compound','m','body','复合部件原型强匹配；不凭低置信度兜底',True,dm)
    # Rotation-invariant U matching uses a common normalized geometry view.
    us=[a for a in anchors if a['key']=='u']
    du=min((distance(f,a) for a in us),default=1.)
    dc=min((distance(f,a) for a in anchors if a['key']=='c'),default=1.)
    if du<.055 and du+.008<dc and not holes and f['junctions']==0:
        add('family.u-shape','u','body','旋转U形原型匹配；方向不改变形族',True,du)
    if not holes:
        for i,j in enumerate(f['junctionObjects']):
            arms=j['armCount']
            if arms>=3:
                key,identity=('r','radial') if arms>=5 else ('h','fork')
                # Radial/branch semantic is local, not a condition on all endpoints.
                add('family.'+identity,key,'junction-'+str(i),f'同一局部交点{arms}支；局部出口计数',
                    len(f['junctionObjects'])==1 and len(f['parts'])==1,0.,j['coreBbox'])
    if dot_group(f):
        add('family.dots','d','point-array',f"{len(f['parts'])}个紧凑实心点；点阵入口不设六点上限",True,0.)
        if len(f['parts'])>=3:
            centres=np.array([[p['cx'],p['cy']] for p in f['parts']])
            eigen=np.linalg.eigvalsh(np.cov(centres.T))
            if eigen[-1]/max(.001,eigen[0])>=25:
                add('family.line','l','point-array-outline','点中心近共线；保留整体线状排列入口',False,0.)
        hull=hull_mask(f)
        if hull is not None:
            # Hull supports only the outer arrangement; never infer internal ink.
            hf=observe(hull,f['extent']);view=hf['signature'][:256]
            ranked=[]
            for key in ('o','s','t'):
                aa=[a for a in anchors if a['key']==key]
                score=min((float(((view-a['signature'][:256])**2).sum()) for a in aa),default=1.)
                ranked.append((score,key))
            score,key=min(ranked)
            if score<.075:
                # A triangle of three dots cannot establish a circular outline.
                if key!='o' or len(f['parts'])>=6:
                    identity={'o':'round-outline','s':'quadrilateral','t':'triangle'}[key]
                    add('family.'+identity,key,'point-array-outline','点中心凸包与外轮廓原型匹配；不是单个点的轮廓',False,score)
    return routes


def inner_star_routes(f, anchors):
    """Independent enclosed ink, bound to its own bbox; no Cartesian products."""
    result=[]
    if not f['holes']:return result
    b=f['bbox']
    for i,p in enumerate(f['parts']):
        box=[p['x0'],p['y0'],p['x1'],p['y1']]
        if p['area']<12 or not (b[0]<box[0] and b[1]<box[1] and box[2]<b[2] and box[3]<b[3]):continue
        sub=observe(component_mask(f['mask'],p),f['extent']*max(box[2]-box[0],box[3]-box[1])/max(b[2]-b[0],b[3]-b[1]))
        score=min((distance(sub,a) for a in anchors if a['key']=='r'),default=1.)
        other=min((distance(sub,a) for a in anchors if a['key'] in ('o','s','t')),default=1.)
        if score<.10 and score+.008<other:
            result.append({'familyId':'family.radial','key':'r','target':'inner-'+str(i),
                           'basis':'独立内部星形构件与星芒原型匹配','priority':False,
                           'distance':score,'bbox':box,'status':'machine-proposal','feature':sub})
    # A white star in a solid circle is an observed negative-space object.
    # It must not be confused with the whole character or a plain round hole.
    holes=components(~np.pad(f['body'],1),4)
    for i,hole in enumerate(holes):
        if hole['edge'] or hole['area']<max(12,f['body'].sum()*.06):continue
        ink=component_mask(~np.pad(f['body'],1),hole,4)[1:-1,1:-1]
        sub=observe(ink,f['extent'])
        sb=sub['bbox'];sub['extent']=f['extent']*max(sb[2]-sb[0],sb[3]-sb[1])/max(b[2]-b[0],b[3]-b[1])
        score=min((distance(sub,a) for a in anchors if a['key']=='r'),default=1.)
        other=min((distance(sub,a) for a in anchors if a['key'] in ('o','s','t')),default=1.)
        if score<.10 and score+.008<other:
            result.append({'familyId':'family.radial','key':'r','target':'inner-negative-'+str(i),
                           'basis':'闭合空区的可见星形轮廓；不是外围圆主体','priority':False,
                           'distance':score,'bbox':sub['bbox'],'status':'machine-proposal','feature':sub})
    return result


def detect(f, anchors):
    """Semantic entry point. Keyboard assignment is explicitly optional."""
    from build_shape_experiment import classify
    extra=shape_routes(f,anchors,[a for a in anchors if a['key'] is None])
    compatible=classify(f,anchors)
    loop=next((r for r in extra if r['familyId']==DOUBLE_LOOP and r['priority']),None)
    primary=DOUBLE_LOOP if loop else compatible[0]['familyId'] if compatible else None
    routes=[]
    for r in compatible:
        routes.append(dict(r,target='body',bbox=f['bbox']))
    for r in extra+inner_star_routes(f,anchors):
        if not any(q['familyId']==r['familyId'] and q['target']==r['target'] for q in routes):routes.append(r)
    return {'primaryFamilyId':primary,'primaryKey':compatible[0]['key'] if compatible and not loop else None,
            'routes':routes,'pendingKeyboardFamilyIds':[r['familyId'] for r in routes if r['key'] is None],
            'featureVersion':VERSION}
