"""Unbound stroke graph experiment: endpoints/junctions/turns, never codes.

No character, Unicode name, script or expected answer enters analyze(). Coordinates
are in the supplied ink mask; all reported segments retain their original paths.
"""
import math
from collections import defaultdict

import numpy as np
from PIL import Image, ImageFont
from shape_quality_v2 import skeleton
from shape_lab_features import components

VERSION = 'stroke-graph-turns-unbound-v2'


def render_locked(char, font, size=192, weight=0, canvas_size=192):
    face = ImageFont.truetype(font['path'], size, index=font.get('index', 0))
    core = face.getmask(char, mode='L')
    box = core.getbbox()
    if not box:
        raise ValueError('empty glyph')
    im = Image.frombytes('L', core.size, bytes(core)).crop(box)
    scale = (canvas_size - 12) / max(im.size)
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.Resampling.LANCZOS)
    canvas = Image.new('L', (canvas_size, canvas_size))
    canvas.paste(im, ((canvas_size - im.width) // 2, (canvas_size - im.height) // 2))
    ink = np.asarray(canvas) > 255 * .35
    if weight:
        for _ in range(max(1, round(canvas_size / 64))):
            p = np.pad(ink, 1)
            h, w = ink.shape
            views = [p[1+dy:1+dy+h,1+dx:1+dx+w] for dy, dx in ((0,0),(1,0),(-1,0),(0,1),(0,-1))]
            ink = np.logical_or.reduce(views) if weight > 0 else np.logical_and.reduce(views)
    return ink


def adjacency(sk):
    points = {(int(x), int(y)) for y, x in np.argwhere(sk)}
    graph = {}
    for x, y in points:
        neighbors = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if not (dx or dy) or (x+dx, y+dy) not in points:
                    continue
                # Avoid a spurious triangle where a diagonal shortcuts an L.
                if dx and dy and ((x+dx, y) in points or (x, y+dy) in points):
                    continue
                neighbors.append((x+dx, y+dy))
        graph[(x,y)] = sorted(neighbors)
    return graph


def path_length(points):
    p = np.asarray(points, dtype=float)
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) if len(p) > 1 else 0.


def graph_edges(sk):
    graph = adjacency(sk)
    junction_pixels = {p for p, ns in graph.items() if len(ns) >= 3}
    # Contract only small contiguous digital junction cores, not whole branches.
    groups = []
    remaining = set(junction_pixels)
    while remaining:
        seed = min(remaining); group = {seed}; queue = [seed]; remaining.remove(seed)
        while queue:
            p = queue.pop()
            for q in list(remaining):
                if max(abs(p[0]-q[0]), abs(p[1]-q[1])) <= 2:
                    remaining.remove(q); group.add(q); queue.append(q)
        groups.append(group)
    nodes = []
    ownership = {}
    for group in groups:
        # Include connecting degree-two pixels in the tiny core bounding box.
        a = np.asarray(list(group)); lo = a.min(axis=0); hi = a.max(axis=0)
        zone = {p for p in graph if lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1]}
        i = len(nodes)
        nodes.append(dict(id=i, xy=a.mean(axis=0).tolist(), pixels=sorted(zone)))
        ownership.update({p:i for p in zone})
    for p, ns in sorted(graph.items()):
        if len(ns) <= 1 and p not in ownership:
            i = len(nodes); nodes.append(dict(id=i, xy=list(p), pixels=[p])); ownership[p] = i
    seen = set(); edges = []
    for p, start in sorted(ownership.items()):
        for q in graph[p]:
            if ownership.get(q) == start:
                seen.add(frozenset((p,q))); continue
            key = frozenset((p,q))
            if key in seen:
                continue
            path = [p,q]; seen.add(key); prev, current = p,q
            while current not in ownership:
                nexts = [n for n in graph[current] if n != prev]
                if len(nexts) != 1:
                    raise ValueError('uncontracted digital graph node')
                n = nexts[0]; seen.add(frozenset((current,n))); path.append(n); prev,current=current,n
            edges.append(dict(start=start, end=ownership[current], points=path, length=path_length(path)))
    # Closed paths have no endpoints and must not silently disappear.
    for p, ns in sorted(graph.items()):
        for q in ns:
            if frozenset((p,q)) in seen:
                continue
            path=[p,q]; seen.add(frozenset((p,q))); prev,current=p,q
            while current != p:
                nexts=[n for n in graph[current] if n!=prev and frozenset((current,n)) not in seen]
                if not nexts:
                    break
                n=nexts[0];seen.add(frozenset((current,n)));path.append(n);prev,current=current,n
            if path_length(path) > 3:
                i=len(nodes);nodes.append(dict(id=i,xy=list(p),pixels=[p],cycle=True))
                edges.append(dict(start=i,end=i,points=path,length=path_length(path),cycle=True))
    return nodes, edges


def merge_crossing_cores(nodes, edges, stroke_width, mask):
    """A thick X can have two nearby medial forks; validate four actual exits."""
    nodes=[dict(n) for n in nodes]
    edges=[dict(e) for e in edges]
    merged=[]
    while True:
        degree=defaultdict(int)
        for e in edges:
            degree[e['start']]+=1;degree[e['end']]+=1
        chosen=None
        for edge in edges:
            a,b=edge['start'],edge['end']
            if a==b or degree[a]!=3 or degree[b]!=3 or edge['length']>.9*stroke_width:
                continue
            center=(np.asarray(nodes[a]['xy'])+nodes[b]['xy'])/2
            yy,xx=np.indices(mask.shape);d2=(xx-center[0])**2+(yy-center[1])**2
            ports=[];radii=[]
            for radius in (stroke_width*k for k in (.9,1.05,1.2,1.35,1.5)):
                ring=mask & (d2>(radius-1.5)**2)&(d2<(radius+1.5)**2)
                ports.append(len([c for c in components(ring,8) if c['area']>=2]))
                radii.append(radius)
            adjacent=next((i for i in range(len(ports)-1) if ports[i:i+2]==[4,4]),None)
            if adjacent is not None:
                chosen=(edge,a,b,center,ports,radii,adjacent);break
        if chosen is None:
            break
        edge,a,b,center,ports,radii,adjacent=chosen
        nodes[a]['xy']=center.tolist();nodes[a]['pixels']+=nodes[b]['pixels']
        merged.append(dict(nodeIds=[a,b],xy=center.tolist(),portCounts=ports,
                           radii=radii,acceptedAdjacentRadii=radii[adjacent:adjacent+2],
                           connectingLength=edge['length'],test='four-actual-ink-exits-at-two-radii'))
        edges=[e for e in edges if e is not edge]
        for e in edges:
            if e['start']==b:e['start']=a
            if e['end']==b:e['end']=a
    return nodes,edges,merged


def simplify_graph(nodes, edges, stroke_width):
    edges = [dict(e) for e in edges]
    pruned = []
    for _ in range(8):
        degree = defaultdict(int)
        for e in edges:
            degree[e['start']] += 1; degree[e['end']] += 1
        short=[]
        for e in edges:
            if min(degree[e['start']],degree[e['end']])!=1:
                continue
            joint=e['end'] if degree[e['start']]==1 else e['start']
            tiny=e['length']<.65*stroke_width
            others=[v for v in edges if v is not e and joint in (v['start'],v['end'])]
            curved_terminal=(degree[joint]==3 and len(others)==2 and e['length']<1.5*stroke_width
                             and all(v['length']>2*e['length'] and
                                     segment_kind(v['points'],max(1,stroke_width/7))[0]=='curve' for v in others))
            if tiny or curved_terminal:
                e['pruneReason']='short medial spur at curved terminal' if curved_terminal else 'sub-stroke-width terminal spur'
                short.append(e)
        if not short:
            break
        pruned += short; edges = [e for e in edges if e not in short]
    # Restore a single path after removing a tiny medial-axis spur.
    while True:
        incident=defaultdict(list)
        for i,e in enumerate(edges):
            incident[e['start']].append(i);incident[e['end']].append(i)
        joint=next((n for n,ids in incident.items() if len(ids)==2 and ids[0]!=ids[1]),None)
        if joint is None:
            break
        i,j=incident[joint];a,b=edges[i],edges[j]
        pa=a['points'] if a['end']==joint else a['points'][::-1]
        pb=b['points'] if b['start']==joint else b['points'][::-1]
        points=pa+pb
        merged=dict(start=a['start'] if a['end']==joint else a['end'],
                    end=b['end'] if b['start']==joint else b['start'],points=points,length=path_length(points))
        edges=[e for k,e in enumerate(edges) if k not in (i,j)]+[merged]
    return nodes,edges,pruned


def resample(points, spacing=1.):
    p=np.asarray(points,dtype=float)
    lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    keep=np.r_[True,np.diff(lengths)>1e-8];p=p[keep];lengths=lengths[keep]
    if len(p)<2:
        return p
    ticks=np.linspace(0,lengths[-1],max(2,round(lengths[-1]/spacing)+1))
    return np.column_stack([np.interp(ticks,lengths,p[:,i]) for i in (0,1)])


def angle(a,b):
    size=float(np.linalg.norm(a)*np.linalg.norm(b))
    return math.degrees(math.acos(float(np.clip(np.dot(a,b)/size,-1,1)))) if size else 0.


def turn_candidates(points, scale=1., stroke_width=0.):
    p=resample(points)
    # Tangents on both sides of a bend: a sustained smooth arc is not an apex.
    small=max(3,round(3.2*scale),round(.8*stroke_width));large=max(small+2,round(1.8*small))
    candidates=[]
    for i in range(small,len(p)-small):
        # Require visible support beyond the rounded endpoint cap on both arms.
        # Shorter turns remain unresolved rather than counting a terminal serif.
        if min(i,len(p)-1-i)<max(small,1.5*stroke_width):
            continue
        a=p[i]-p[i-small];b=p[i+small]-p[i]
        local=angle(a,b)
        j=max(0,i-large);k=min(len(p)-1,i+large)
        broad=angle(p[i]-p[j],p[k]-p[i])
        if local>=48 and broad>=48 and local>=.68*broad:
            candidates.append(dict(index=i,xy=p[i].tolist(),localAngle=local,broadAngle=broad,
                                   score=local,kind='corner',source='two-sided-centreline-tangents'))
    selected=[]
    for c in sorted(candidates,key=lambda c:-c['score']):
        if all(abs(c['index']-v['index']) > large for v in selected):
            selected.append(c)
    return p,sorted(selected,key=lambda c:c['index'])


def segment_kind(points,scale=1.,stroke_width=0.):
    p=resample(points)
    # Skeleton cores/rounded joints distort the short ends of otherwise straight arms.
    trim=min(round(.45*stroke_width),max(0,(len(p)-6)//4))
    if trim:p=p[trim:-trim]
    if len(p)<3:
        return 'uncertain',dict(reason='insufficient centreline samples')
    # Orthogonal TLS residual is rotation independent.
    centered=p-p.mean(axis=0);_,_,v=np.linalg.svd(centered,full_matrices=False)
    residual=np.abs(centered@v[-1]);length=path_length(p)
    rms=float(np.sqrt(np.mean(residual**2)));maximum=float(residual.max())
    chord=float(np.linalg.norm(p[-1]-p[0]));ratio=length/max(chord,1e-6)
    straight=rms <= max(.6*scale,.012*length) and maximum <= max(1.35*scale,.035*length) and ratio <= 1.18
    return ('straight' if straight else 'curve'),dict(rmsDistance=rms,maxDistance=maximum,
                                                      pathLength=length,chordLength=chord,lengthOverChord=ratio,
                                                      tangentEndTrimPixels=trim)


def analyze(mask, graph_transform=None):
    scale=max(mask.shape)/64
    sk=skeleton(mask)
    width=float(mask.sum()/max(1,sk.sum()))
    yy,xx=np.nonzero(mask);span=max(float(xx.max()-xx.min()+1),float(yy.max()-yy.min()+1))
    # Keep semantic support windows tied to glyph span: ink weight must not turn
    # the same terminal spur into a branch or a smooth terminal arc into a kink.
    support_width=float(np.clip(width,.10*span,.12*span))
    nodes,edges=graph_edges(sk)
    nodes,edges,merged=merge_crossing_cores(nodes,edges,width,mask)
    nodes,edges,pruned=simplify_graph(nodes,edges,support_width)
    correction=None
    if graph_transform is not None:
        nodes,edges,correction=graph_transform(nodes,edges,width,mask)
    degree=defaultdict(int)
    for e in edges:
        degree[e['start']]+=1;degree[e['end']]+=1
    junctions=[]
    for n in nodes:
        d=degree[n['id']]
        if d>=3:
            junctions.append(dict(id=n['id'],xy=n['xy'],arms=d,
                                  kind='fork' if d==3 else 'cross' if d==4 else 'multi-junction',
                                  source='contracted-centreline-graph-exits'))
    corners=[];segments=[]
    for eid,e in enumerate(edges):
        points,turns=turn_candidates(e['points'],scale,support_width)
        for turn in turns:
            turn.update(edgeId=eid,id=f'corner-{len(corners)}');corners.append(turn)
        split=[0]+[c['index'] for c in turns]+[len(points)-1]
        for a,b in zip(split,split[1:]):
            piece=points[a:b+1]
            kind,metrics=segment_kind(piece,scale,width)
            segments.append(dict(id=f'segment-{len(segments)}',edgeId=eid,kind=kind,
                                 points=piece.tolist(),metrics=metrics))
    # A curved side can join a continuing stem at a visible bend. The corner
    # and the three-way junction share a place; splitting there is counted once.
    for j in junctions:
        if j['arms']!=3:
            continue
        arms=[]
        for eid,e in enumerate(edges):
            if j['id'] not in (e['start'],e['end']):
                continue
            p=resample(e['points'] if e['start']==j['id'] else e['points'][::-1])
            dist=min(len(p)-1,max(3,round(1.6*width)))
            arms.append((eid,p[dist]-p[0]))
        pairs=[(angle(a[1],b[1]),i,k) for i,a in enumerate(arms) for k,b in enumerate(arms) if i<k]
        opposite=max(pairs,default=(0,0,0))
        if opposite[0]<155:
            continue
        side=next((i for i in range(len(arms)) if i not in opposite[1:]),None)
        if side is None:
            continue
        eid=arms[side][0]
        parts=[s for s in segments if s['edgeId']==eid]
        if len(parts)!=1 or parts[0]['kind']!='curve':
            continue
        small_angle=min(angle(arms[side][1],arms[i][1]) for i in opposite[1:])
        if small_angle>=48:
            corners.append(dict(id=f'corner-{len(corners)}',xy=j['xy'],edgeId=eid,
                                junctionId=j['id'],kind='corner',localAngle=180-small_angle,
                                source='curved-side-attachment-to-continuing-stem',
                                splitsAlreadyAtJunction=True))
    stats=dict(corners=len(corners),forks=sum(j['arms']==3 for j in junctions),
               crosses=sum(j['arms']==4 for j in junctions),otherJunctions=sum(j['arms']>4 for j in junctions),
               straightSegments=sum(s['kind']=='straight' for s in segments),
               curveSegments=sum(s['kind']=='curve' for s in segments),
               uncertainSegments=sum(s['kind']=='uncertain' for s in segments),totalSegments=len(segments))
    result=dict(version=VERSION,statistics=stats,junctions=junctions,corners=corners,segments=segments,
                edges=[dict(e,points=[list(p) for p in e['points']]) for e in edges],
                prunedSpurCount=len(pruned),prunedSpurs=[dict(e,points=[list(p) for p in e['points']]) for e in pruned],
                estimatedStrokeWidth=width,maskShape=list(mask.shape),
                semanticSupportWidth=support_width,
                mergedCrossingCores=merged,
                scope='experimental geometric graph; no character identity or desired counts used')
    if graph_transform is not None:
        result['objectGraphCorrection']=correction
    return result
