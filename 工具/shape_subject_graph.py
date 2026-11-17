"""Object-local graph corrections. Never enabled by a default/global analyzer."""
import copy
from collections import defaultdict
import numpy as np
from shape_lab_features import components
from shape_stroke_continuation_trial import graph_cycles
from shape_stroke_topology_trial import segment_kind

VERSION='object-local-cycle-and-core-v1'


def cycle_object(base):
    """Select an inherited cycle graph, instead of skeletonizing an artificial cut."""
    kept=list(enumerate(base['edges']));removed=[]
    while True:
        degree=defaultdict(int)
        for _,e in kept:degree[e['start']]+=1;degree[e['end']]+=1
        leaves=[(i,e) for i,e in kept if min(degree[e['start']],degree[e['end']])==1]
        if not leaves:break
        removed.extend(i for i,_ in leaves);ids={i for i,_ in leaves};kept=[(i,e) for i,e in kept if i not in ids]
    degree=defaultdict(int)
    for _,e in kept:degree[e['start']]+=1;degree[e['end']]+=1
    if not kept or any(d!=2 for d in degree.values()) or graph_cycles([e for _,e in kept])!=1:
        return dict(verified=False,reason='not-a-single-degree-two-inherited-cycle')
    # A single closed edge needs no fabricated seam or connecting line.
    if len(kept)!=1 or kept[0][1]['start']!=kept[0][1]['end']:
        return dict(verified=False,reason='multi-edge-cycle-needs-explicit-port-order')
    eid,edge=kept[0];kind,metrics=segment_kind(edge['points'],max(base['maskShape'])/64,base['estimatedStrokeWidth'])
    corners=[c for c in base['corners'] if c['edgeId']==eid]
    return dict(verified=kind=='curve' and not corners,sourceEdgeIds=[eid],removedTailEdgeIds=removed,
        statistics=dict(corners=len(corners),forks=0,crosses=0,straightStrokes=int(kind=='straight'),curveStrokes=int(kind=='curve'),loops=1),
        sourcePoints=edge['points'],metrics=metrics,
        method='inherit original closed centreline; cut boundaries never become strokes',version=VERSION)


def contract_closed_core(nodes,edges,width,mask):
    """Contract a sub-two-width bridge only with four ink exits in a tight core.

    Closed topology is required. Open H/T/X controls cannot enter this rule.
    All deleted graph points survive in the recorded core, and no ink is edited.
    """
    nodes=copy.deepcopy(nodes);edges=copy.deepcopy(edges);old_cycles=graph_cycles(edges);proof=[];examined=[]
    if old_cycles<1:return nodes,edges,dict(version=VERSION,accepted=[],reason='no-closed-cycle')
    lookup={n['id']:n for n in nodes};degree=defaultdict(int)
    for e in edges:degree[e['start']]+=1;degree[e['end']]+=1
    for e in sorted(edges,key=lambda e:e['length']):
        a,b=e['start'],e['end']
        if a==b or degree[a]!=3 or degree[b]!=3:continue
        center=(np.asarray(lookup[a]['xy'])+np.asarray(lookup[b]['xy']))/2
        yy,xx=np.indices(mask.shape);d2=(xx-center[0])**2+(yy-center[1])**2
        # The inspection envelope must contain both endpoints plus one pen
        # width; fixed radii otherwise inspect the middle of a thin connector.
        span=float(np.linalg.norm(np.asarray(lookup[a]['xy'])-lookup[b]['xy']))
        radii=[span/2+width,span/2+1.25*width];ports=[]
        for radius in radii:
            ring=mask&(d2>(radius-1.5)**2)&(d2<(radius+1.5)**2)
            ports.append(len([c for c in components(ring,8) if c['area']>=2]))
        check=dict(nodeIds=[a,b],bridgeLength=e['length'],width=width,lengthOverWidth=e['length']/width,
                   radii=radii,actualInkPorts=ports)
        examined.append(check)
        if e['length']>2*width or ports!=[4,4]:continue
        lookup[a]['xy']=center.tolist();lookup[a]['pixels']+=lookup[b]['pixels']+[tuple(p) for p in e['points']]
        updated=[v for v in edges if v is not e]
        for v in updated:
            if v['start']==b:v['start']=a
            if v['end']==b:v['end']=a
        assert graph_cycles(updated)==old_cycles
        check.update(coreInternalPath=e['points'],cycleRankBefore=old_cycles,cycleRankAfter=graph_cycles(updated))
        proof.append(check);edges=updated;break
    return nodes,edges,dict(version=VERSION,accepted=proof,examined=examined,
                            scope='object-local candidate; no global detector or original observation rewritten')
