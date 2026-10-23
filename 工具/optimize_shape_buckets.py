"""First optimization experiment; comparison baseline stays immutable."""
import sys,argparse,gzip,hashlib,json,re,time
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np
from external_paths import shape_dependency_dir
sys.path.insert(0, str(shape_dependency_dir()))
from ortools.graph.python import min_cost_flow
import ortools
from shape_quality_v2 import ROOT,build
from shape_bucket_scope import full_scope,ACTIVE
from balanced_shape_buckets import distances,balanced_assign,features,boundary_aliases,publish_report
from reserved_shape_buckets import ROOT as BASE_ROOT
from shape_strategy_lab import save
from inspect_shape_lab import load_run

LOWER=500;UPPER=2000;COST_SCALE=100000


def flow_assign(cost,lower=LOWER,upper=UPPER):
    n,k=cost.shape
    if not k*lower<=n<=k*upper:raise ValueError('容量不可行')
    if not np.isfinite(cost).all():raise ValueError('距离非有限')
    solver=min_cost_flow.SimpleMinCostFlow();point=np.repeat(np.arange(n,dtype='int32'),k);bucket=n+np.tile(np.arange(k,dtype='int32'),n)
    integer=np.rint(np.maximum(0,cost).flatten()*COST_SCALE).astype('int64')
    arcs=solver.add_arcs_with_capacity_and_unit_cost(point,bucket,np.ones(n*k,dtype='int64'),integer)
    sink=n+k
    solver.add_arcs_with_capacity_and_unit_cost(np.arange(n,n+k,dtype='int32'),np.full(k,sink,dtype='int32'),np.full(k,upper-lower,dtype='int64'),np.zeros(k,dtype='int64'))
    nodes=np.arange(sink+1,dtype='int32');supply=np.r_[np.ones(n,dtype='int64'),np.full(k,-lower,dtype='int64'),-(n-k*lower)]
    solver.set_nodes_supplies(nodes,supply)
    status=solver.solve()
    if status!=solver.OPTIMAL:raise RuntimeError(f'最小费用流未得到最优解：{status}')
    flows=solver.flows(arcs).reshape(n,k);assert np.all(flows.sum(1)==1)
    labels=flows.argmax(1);counts=np.bincount(labels,minlength=k)
    assert np.all(counts>=lower) and np.all(counts<=upper)
    return labels


def train(x,seed,solver,iterations=8):
    rng=np.random.default_rng(seed);centres=[x[rng.integers(len(x))]];d=np.full(len(x),np.inf)
    for _ in range(1,len(ACTIVE)):
        d=np.minimum(d,((x-centres[-1])**2).sum(1));centres.append(x[rng.choice(len(x),p=d/d.sum() if d.sum() else None)])
    centres=np.array(centres,dtype='float32');best=None;history=[];previous=None
    for iteration in range(iterations):
        labels=solver(distances(x,centres),LOWER,UPPER)
        new=np.array([x[labels==j].mean(0) for j in range(len(ACTIVE))],dtype='float32')
        loss=float(((x-new[labels])**2).sum(1).mean());history.append(loss)
        print(f'{solver.__name__} seed={seed} {iteration+1}/{iterations} loss={loss:.6f}',flush=True)
        if best is None or loss<best[0]:best=(loss,labels.copy(),new.copy())
        if previous is not None and np.array_equal(labels,previous):break
        previous=labels.copy();centres=new
    return best[1],best[2],history


def neighbor_sample(x,count=512):
    indices=np.random.default_rng(20261012).choice(len(x),min(count,len(x)),replace=False);neighbors=[]
    for begin in range(0,len(indices),64):
        sample=indices[begin:begin+64];cost=distances(x[sample],x);cost[np.arange(len(sample)),sample]=np.inf
        neighbors.extend(np.argpartition(cost,5,axis=1)[:,:5])
    return indices,np.array(neighbors)


def metrics(x,labels,indices,neighbors):
    centres=np.array([x[labels==j].mean(0) for j in range(len(ACTIVE))]);counts=np.bincount(labels,minlength=len(ACTIVE))
    distance=((x-centres[labels])**2).sum(1)
    return {'commonFeatureMSE':float(distance.mean()),'p95Distance':float(np.quantile(distance,.95)),
        'sampleNeighborSamePrimary':float((labels[neighbors]==labels[indices,None]).mean()),
        'sampleCharacters':len(indices),'neighborsPerCharacter':5,'minBucket':int(counts.min()),'maxBucket':int(counts.max()),'counts':counts.tolist()}


def align(labels,baseline):
    overlap=np.zeros((len(ACTIVE),len(ACTIVE)),dtype='int64');np.add.at(overlap,(labels,baseline),1)
    mapping=flow_assign((overlap.max()-overlap).astype('float64'),1,1)
    return mapping[labels],mapping


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seeds',type=int,default=4);parser.add_argument('--iterations',type=int,default=8);args=parser.parse_args()
    if args.seeds<2:raise ValueError('多次初始化至少两个种子')
    started=time.monotonic();_,source=load_run();scope,policy=full_scope()
    base=Path(json.loads((BASE_ROOT/'最新分桶.json').read_text(encoding='utf-8'))['run'])
    baseline=json.loads((base/'冻结分组.json').read_text(encoding='utf-8'));base_map={r['cp']:r for r in baseline['characters']}
    with gzip.open(source['featureCache'],'rt',encoding='utf-8') as stream:cached={r['cp']:r for r in map(json.loads,stream)}
    records=[dict(r,feature=cached[r['cp']]['feature']) for r in scope if r['collection'] is None]
    for f in source['featureManifest']['fonts']:
        if hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()!=f['sha256']:raise ValueError('参考字体变更')
    observed,x,model=build(records,source)
    old_labels=np.array([ACTIVE.index(base_map[r['cp']]['primary']) for r in observed]);indices,neighbors=neighbor_sample(x)
    source_old=dict(source,featureCache=source['featureCache']+'#'+hashlib.sha256(','.join(str(r['cp']) for r in records).encode()).hexdigest())
    old_observed,old_x,_=features(records,source_old);assert [r['cp'] for r in observed]==[r['cp'] for r in old_observed]
    run=ROOT/'运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    results=[{'id':'published-baseline','metrics':metrics(x,old_labels,indices,neighbors),'baseline':str(base)}];candidates=[]
    cases=[('old-features-greedy',old_x,balanced_assign),('new-features-greedy',x,balanced_assign),('new-features-flow',x,flow_assign)]
    for name,matrix,solver in cases:
        for seed in range(20261012,20261012+args.seeds):
            labels,centres,history=train(matrix,seed,solver,args.iterations)
            result={'id':name+'-'+str(seed),'method':name,'seed':seed,'history':history,'metrics':metrics(x,labels,indices,neighbors)}
            results.append(result);np.savez_compressed(run/(result['id']+'.npz'),cp=[r['cp'] for r in observed],labels=labels,centres=centres)
            if name=='new-features-flow':candidates.append((min(history),result,labels,centres))
    _,winner,labels,centres=min(candidates,key=lambda item:(item[0],item[1]['seed']))
    labels,mapping=align(labels,old_labels);order=np.argsort(mapping);centres=centres[order]
    cost=distances(x,centres);lookup={};migrations=[]
    for i,r in enumerate(observed):
        primary=ACTIVE[int(labels[i])];before=base_map[r['cp']]['primary']
        lookup[r['cp']]={'primary':primary,'aliases':[ACTIVE[j] for j in boundary_aliases(cost[i],int(labels[i]))],
            'distance':float(cost[i,labels[i]]),'nearestBucket':ACTIVE[int(cost[i].argmin())],'font':r['feature']['font'],'status':'optimized-draft-frozen'}
        if primary!=before:migrations.append({'cp':r['cp'],'char':r['char'],'before':before,'after':primary})
    rows=[dict(cp=r['cp'],char=r['char'],**lookup.get(r['cp'],{'primary':None,'aliases':[],'status':'pending-glyph'})) for r in records]
    capacity={'scope':len(records),'observed':len(observed),'plannedLower':LOWER,'plannedUpper':UPPER,'fitLower':LOWER,'fitUpper':UPPER,
        'history':winner['history'],'assignmentSolver':'OR-Tools integer minimum-cost flow; fixed-centre optimum; Lloyd iterations not global optimum'}
    model.update(letters=ACTIVE,centres=centres.tolist(),selectedSeed=winner['seed'],capacity=capacity,
        explainedPixelVariance=model['pixelVarianceExplained'])
    save(run/'模型.json',model);save(run/'冻结分组.json',{'version':'optimized-v1','capacity':capacity,'characters':rows})
    save(run/'范围规则.json',policy);save(run/'字符迁移.json',{'baseline':str(base),'characters':migrations})
    summary=publish_report(run,rows,model,capacity,source,records)
    old_all=json.loads((base/'全部收纳.json').read_text(encoding='utf-8'))['characters'];reserved=[r for r in old_all if r['primary'] in ('y','z')]
    allrows=sorted(rows+reserved,key=lambda r:r['cp']);counts=Counter(r['primary'] for r in allrows if r['primary']);counts['x']=0
    save(run/'全部收纳.json',{'policy':policy,'characters':allrows})
    with gzip.open(model['qualityRecords'],'rt',encoding='utf-8') as stream:quality=list(map(json.loads,stream))
    qa={'twoViewsAccepted':sum(r['acceptedViews']==2 for r in quality),'alternateDisagreements':sum('alternate-font-disagreement' in r['reviewFlags'] for r in quality),
        'fewInkPixels':sum('few-ink-pixels' in r['reviewFlags'] for r in quality)}
    summary.update(scopeRecords=len(allrows),ordinaryScope=len(records),ordinaryAssigned=len(observed),assigned=sum(counts.values()),
        letters='abcdefghijklmnopqrstuvwxyz',counts=dict(counts),reserved={'x':0,'y':counts['y'],'z':counts['z']},policy=policy,
        quality=qa,baseline=str(base),winner=winner['id'],movedCharacters=len(migrations),comparisons=results,
        solverVersion=ortools.__version__,sourceFontManifest=source['featureManifest'],elapsedSeconds=time.monotonic()-started)
    save(run/'摘要.json',summary)
    page_path=run/'单层分桶核对.html';page=page_path.read_text(encoding='utf-8');payload=json.dumps({'summary':summary,'rows':allrows},ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    page=re.sub(r'const data=.*?;const \$=',lambda m:'const data='+payload+';const $=',page,count=1,flags=re.S)
    page=page.replace("data.summary.counts[k]+' 字</b><br><img src=\"代表字形/'+k+'.png\" alt=\"'+k+'桶字形\"></article>'",
        "data.summary.counts[k]+' 字</b><br>'+(data.summary.representatives[k]?'<img src=\"代表字形/'+k+'.png\" alt=\"'+k+'桶字形\">':(k==='x'?'暂时留空':k==='y'?'排除文字收纳，不参加容量平衡':'中文收纳，不参加容量平衡'))+'</article>'")
    page=page.replace('只冻结第一位分桶，第三／四位尚未重新生成。','第一次优化：96px渲染、64px轮廓、骨架与多字体视图，23桶容量500～2000；x/y/z布局不变，尚未发布输入法。')
    page_path.write_text(page,encoding='utf-8')
    preview=run/'全部字符预览';preview.mkdir()
    for letter in ACTIVE:(preview/(letter+'.md')).write_bytes(''.join(r['char'] for r in rows if r['primary']==letter).encode('utf-8'))
    lines=['# 第一次字形优化实验','','四个优化方向均已实施：样本质量与一致字体视图、轮廓与骨架结构、容量受限最小费用流、多次初始化。', '',
        f'普通范围{len(records)}字；可观测{len(observed)}字；待补{len(records)-len(observed)}字。a～w容量500～2000，x留空，y/z不参与容量平衡。', '',
        f'采用{args.seeds}个随机种子，每个至多{args.iterations}轮；新特征最小费用流方案中按最低自身训练误差选出{winner["id"]}。不同特征空间的训练误差不能直接比较。', '',
        f'多字体一致视图接受{qa["twoViewsAccepted"]}字，分歧标记{qa["alternateDisagreements"]}字。分歧字仅用主字体，不平均不一致字形。质量日志和字体校验见模型及摘要。', '',
        f'标签用最大重叠一一匹配对齐旧版；仍有{len(migrations)}字改变主桶，详见字符迁移.json。旧版未覆盖。', '',
        '## 对照实验','','所有方法使用相同字符集，容量对照为500～2000。共有特征评价统一使用新特征；近邻指标在同一个固定512字样本上比较，每字5个近邻，不代表真人视觉准确率。原已发布实验基线容量较紧，单列供参考。','',
        '| 方法／种子 | 共有特征MSE | 近邻同主桶 | 最小桶 | 最大桶 |','|---|---:|---:|---:|---:|']
    for r in results:
        m=r['metrics'];lines.append(f'| {r["id"]} | {m["commonFeatureMSE"]:.5f} | {m["sampleNeighborSamePrimary"]:.2%} | {m["minBucket"]} | {m["maxBucket"]} |')
    lines+=['','## 技术限度','','64维PCA轮廓、24项结构、128维方向梯度组成216维特征。骨架在32px计算，拓扑与位置在64px计算；不把整体大小作为形族分组条件。最多采用主字体与一款一致的第二字体，暂不补全所有缺失字体。','',
        '最小费用流保证每次固定中心下整数代价的全局最优分配，平方距离按100000倍四舍五入；不保证聚类中心和整个方案全局最优。贪心对照与流方案均使用同一组随机种子；没有用真人相似对训练或验收。','',
        '第三、第四位未改动，正式码本和小狼毫未发布。下一步收集相似字符对后，以独立人工样本检验新旧方案。','',
        'Egyptology Extended Font by Land of Kemet (https://landofkemet.com)，基于 Serge Rosmorduc 与 Serge J.P. Thomas 的JSesh字形，CeCILL v2.1。其他字体来源及SHA-256见摘要。','']
    (run/'第一次优化报告.md').write_text('\n'.join(lines),encoding='utf-8')
    (run/'单层分桶报告.md').write_text('\n'.join(lines),encoding='utf-8')
    for name in ('shape_quality_v2.py','optimize_shape_buckets.py','shape_bucket_scope.py'):
        path=Path(__file__).parent/name;(run/name).write_bytes(path.read_bytes())
    save(ROOT/'最新优化.json',{'run':str(run),'completed':True,'baseline':str(base),'effectiveCodebooksChanged':False})
    print(json.dumps({'run':str(run),'winner':winner['id'],'quality':qa,'counts':dict(counts),'migrations':len(migrations)},ensure_ascii=False))


if __name__=='__main__':main()
