"""Explainable soft-capacity allocation; family identity is not a bucket letter."""
import collections,sys
import numpy as np
from external_paths import shape_dependency_dir
from shape_experiment_rules import FAMILIES

LETTERS='abcdefghijklmnopqrstuvw'
COARSE={'o':'闭环','p':'闭环','s':'角形闭合','t':'角形闭合','r':'辐射骨架','x':'辐射骨架','h':'辐射骨架',
        'l':'线与转折','a':'线与转折','j':'线与转折','c':'开放曲线','u':'开放曲线','w':'开放曲线','d':'点群','m':'复合'}


def proportion(ratio):return 'tall' if ratio<.8 else 'wide' if ratio>1.25 else 'balanced'


def allocate(records):
    primary=collections.defaultdict(list)
    for r in records:
        if r['familyKey']:primary[COARSE[r['familyKey']]].append(r)
    units=[{'id':coarse,'families':[k for k in FAMILIES if COARSE[k]==coarse],
            'proportion':None,'members':members,'coarse':coarse} for coarse,members in primary.items()]
    splits=[];merges=[]
    # Large families may split only at declared geometric boundaries, never by row count.
    candidates=[]
    for u in units:
        children=collections.defaultdict(list)
        for r in u['members']:children[proportion(r['features']['ratio'])].append(r)
        overflow=max(0,len(u['members'])-2000)
        gain=overflow-sum(max(0,len(v)-2000) for v in children.values())
        if overflow and len(children)>1 and gain>0:candidates.append((gain,u,children))
    for gain,u,children in sorted(candidates,key=lambda t:(-t[0],t[1]['id'])):
        if len(units)+len(children)-1>23:continue
        units.remove(u)
        for shape,members in sorted(children.items()):units.append({'id':u['id']+'.'+shape,'families':u['families'],
            'proportion':shape,'members':members,'coarse':u['coarse']})
        splits.append({'families':['family.'+FAMILIES[k][0] for k in u['families']],'reason':'相近形族大组超出软目标且具有可解释的宽高比子族',
                       'children':{k:len(v) for k,v in children.items()},'thresholds':[.8,1.25]})
    # Small, visually related whole families can share an entry. Do not merge proportion
    # slices or force an unrelated character into a small bucket to reach a quota.
    for small in sorted(list(units),key=lambda u:(len(u['members']),u['id'])):
        if small not in units or len(small['members'])>=500 or small['proportion']:continue
        compatible=[u for u in units if u is not small and not u['proportion'] and u['coarse']==small['coarse'] and len(u['members'])+len(small['members'])<=2000]
        if not compatible:continue
        target=min(compatible,key=lambda u:(abs(1250-len(u['members'])-len(small['members'])),u['id']))
        merges.append({'families':small['families']+target['families'],'reason':'相近基础形族共享主桶','coarse':small['coarse']})
        target['families']+=small['families'];target['members']+=small['members'];target['id']+='+'+small['id'];units.remove(small)
    units.sort(key=lambda u:u['id']);n=len(units)
    sys.path.insert(0,str(shape_dependency_dir()));from ortools.graph.python import min_cost_flow
    flow=min_cost_flow.SimpleMinCostFlow();maximum=len(records)
    for i,u in enumerate(units):
        overlap=collections.Counter(r['oldBucket'] for r in u['members'])
        for j,a in enumerate(LETTERS):flow.add_arc_with_capacity_and_unit_cost(i,n+j,1,(maximum-overlap[a])*100+j)
        flow.set_node_supply(i,1)
    sink=n+23
    for j in range(23):flow.add_arc_with_capacity_and_unit_cost(n+j,sink,1,0)
    flow.set_node_supply(sink,-n)
    if flow.solve()!=flow.OPTIMAL:raise ValueError('Soft family allocation failed')
    for a in range(flow.num_arcs()):
        if flow.tail(a)<n and flow.flow(a):units[flow.tail(a)]['bucket']=LETTERS[flow.head(a)-n]
    groups=[{k:v for k,v in u.items() if k!='members'}|{'count':len(u['members'])} for u in units]
    def bucket_for(family,ratio):
        candidates=[u for u in units if family in u['families'] and (u['proportion'] is None or u['proportion']==proportion(ratio))]
        if not candidates:raise ValueError('Missing family sub-group')
        return candidates[0]['bucket']
    for r in records:
        r['bucket']=bucket_for(r['familyKey'],r['features']['ratio']) if r['familyKey'] else r['oldBucket']
        target_buckets={}
        for route in r['familyRoutes']:
            ratio=r['features']['ratio']
            if route['target'].startswith('inner-negative-'):
                measured=next((s for s in r.get('semantic',{}).get('routes',[]) if s['target']==route['target'] and s.get('bbox')),None)
                if measured is None:raise ValueError('Negative-space route requires its own measured bounds')
                x0,y0,x1,y1=measured['bbox'];ratio=(x1-x0)/(y1-y0)
            elif route['target'].startswith('inner-'):
                g=r['features']['parts'][int(route['target'].split('-')[1])];ratio=(g['x1']-g['x0'])/(g['y1']-g['y0'])
            route['bucket']=bucket_for(route['familyKey'],ratio)
            target_buckets[(route['familyKey'],route['target'])]=route['bucket']
        paths={}
        for path in r['paths']:
            for evidence in path['evidence']:
                code=target_buckets[(path['code'][1],evidence['familyTarget'])]+path['code'][1:]
                entry=paths.setdefault(code,{'code':code,'evidence':[]})
                if evidence not in entry['evidence']:entry['evidence'].append(evidence)
        r['paths']=sorted(paths.values(),key=lambda p:p['code'])
    return groups,{'method':'相近形族先聚合为闭环／角形闭合／辐射骨架／线与转折／开放曲线／点群／复合大组；大组按明确比例分支，第二位再区分形族；字母按旧归属最大重合匹配',
                   'capacityTarget':[500,2000],'splits':splits,'merges':merges,'hardCapacity':False}
