"""Geometry-only continuation and cycles on top of immutable segment graphs."""
from collections import defaultdict
import numpy as np

from shape_stroke_topology_trial import angle, resample, segment_kind
from shape_lab_features import components

VERSION='continuous-lines-and-loops-unbound-v1'
MIN_OPPOSITE_ANGLE=155.


def graph_cycles(edges):
    parent={}
    def find(v):
        parent.setdefault(v,v)
        if parent[v]!=v:parent[v]=find(parent[v])
        return parent[v]
    for e in edges:
        a,b=find(e['start']),find(e['end'])
        if a!=b:parent[a]=b
    return len(edges)-len(parent)+len({find(v) for v in parent})


def ink_loops(mask,width):
    holes=[]
    threshold=max(5.,.10*width*width)
    for h in components(~np.pad(mask,1),4):
        if h['edge'] or h['area']<threshold:continue
        holes.append(dict(area=h['area'],bbox=[h['x0']-1,h['y0']-1,h['x1']-1,h['y1']-1]))
    return holes


def best_pairing(arms):
    candidates=[]
    for i,a in enumerate(arms):
        for b in arms[i+1:]:
            angles=[angle(x,y) for x,y in zip(a['tangents'],b['tangents'])]
            if min(angles)>=MIN_OPPOSITE_ANGLE:
                candidates.append(dict(ports=[a['port'],b['port']],angles=angles,score=sum(angles)/len(angles)))
    matchings=[[]]
    for c in candidates:
        for chosen in list(matchings):
            used={tuple(p) for v in chosen for p in v['ports']}
            if not used & {tuple(p) for p in c['ports']}:matchings.append(chosen+[c])
    matchings.sort(key=lambda a:(len(a),sum(v['score'] for v in a)),reverse=True)
    best=matchings[0]
    alternatives=[m for m in matchings[1:] if len(m)==len(best)]
    ambiguous=bool(best and alternatives and sum(v['score'] for v in best)-sum(v['score'] for v in alternatives[0])<5.)
    return ([] if ambiguous else best),ambiguous


def analyze_continuation(mask,base):
    width=base['estimatedStrokeWidth'];scale=max(mask.shape)/64
    segments=base['segments'];by_edge=defaultdict(list)
    for i,s in enumerate(segments):by_edge[s['edgeId']].append(i)
    ports=defaultdict(list)
    for eid,e in enumerate(base['edges']):
        pieces=by_edge[eid]
        if not pieces:continue
        for node,sid,end in [(e['start'],pieces[0],0),(e['end'],pieces[-1],1)]:
            p=resample(segments[sid]['points'] if end==0 else segments[sid]['points'][::-1])
            tangents=[]
            for radius in (1.2*width,2.*width):
                n=min(len(p)-1,max(2,round(radius)))
                tangents.append((p[n]-p[0]).tolist())
            ports[node].append(dict(port=[sid,end],tangents=tangents))
    joins=[];junctions=[];ambiguities=[]
    for j in base['junctions']:
        arms=ports[j['id']]
        if len(arms)>4:
            ambiguities.append(dict(node=j['id'],reason='more-than-four-exits'));continue
        pairs,ambiguous=best_pairing(arms)
        if ambiguous:ambiguities.append(dict(node=j['id'],reason='non-unique-near-opposite-pairing'))
        types=[]
        for pair in pairs:
            ids=[p[0] for p in pair['ports']]
            kind='straight' if all(segments[i]['kind']=='straight' for i in ids) else 'curve'
            pair.update(node=j['id'],xy=j['xy'],kind=kind)
            joins.append(pair);types.append(kind)
        junctions.append(dict(node=j['id'],xy=j['xy'],arms=j['arms'],pairs=pairs,
                              kind='straight-through' if types and all(t=='straight' for t in types)
                              else 'curve-through' if types else 'no-through',ambiguous=ambiguous))
    links={}
    for join in joins:
        a,b=map(tuple,join['ports']);links[a]=b;links[b]=a
    strokes=[];seen=set()
    for seed in range(len(segments)):
        if seed in seen:continue
        # Find an unmatched end in this chain; closed components have none.
        available=[(seed,0),(seed,1)];component=set();stack=[seed]
        while stack:
            s=stack.pop()
            if s in component:continue
            component.add(s)
            for e in (0,1):
                if (s,e) in links:stack.append(links[(s,e)][0])
        starts=[(s,e) for s in component for e in (0,1) if (s,e) not in links]
        current=min(starts) if starts else (seed,0)
        points=[];members=[]
        while current[0] not in seen:
            sid,end=current;seen.add(sid);members.append(sid)
            points+=segments[sid]['points'] if end==0 else segments[sid]['points'][::-1]
            exit_port=(sid,1-end)
            if exit_port not in links:break
            current=links[exit_port]
        kind,metrics=segment_kind(points,scale,width)
        strokes.append(dict(id=len(strokes),segmentIds=members,kind=kind,points=points,metrics=metrics))
    holes=ink_loops(mask,width);cycle_count=graph_cycles(base['edges'])
    stats=dict(strokeCount=len(strokes),straightStrokes=sum(s['kind']=='straight' for s in strokes),
               curveStrokes=sum(s['kind']=='curve' for s in strokes),
               uncertainStrokes=sum(s['kind']=='uncertain' for s in strokes),
               straightThroughJunctions=sum(j['kind']=='straight-through' for j in junctions),
               curveThroughJunctions=sum(j['kind']=='curve-through' for j in junctions),
               noThroughForks=sum(j['arms']==3 and j['kind']=='no-through' for j in junctions),
               loops=len(holes))
    return dict(version=VERSION,statistics=stats,strokes=strokes,junctionContinuations=junctions,
                pairings=joins,holes=holes,graphCycleCount=cycle_count,
                topologyAgrees=cycle_count==len(holes),ambiguities=ambiguities,
                minimumOppositeAngle=MIN_OPPOSITE_ANGLE,
                scope='geometric continuous lines, not handwriting order; turns retain original segmentation')
