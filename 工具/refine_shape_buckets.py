"""Conservative, reviewable neighborhood refinement; never overwrite confirmed grouping."""
import copy,gzip,json,re,sys,hashlib,html
from pathlib import Path
from datetime import datetime
from collections import Counter
import numpy as np
from purify_wedge_bucket import redistribute

PROJECT=Path(__file__).resolve().parents[1]
LAB=PROJECT/'数据/三模式/规则库'
ACTIVE='abcdefghijklmnopqrstuvw'

def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def dist(a,b):return np.maximum(0,(a*a).sum(1)[:,None]+(b*b).sum(1)[None,:]-2*a@b.T)

def main():
    source=Path(json.loads((LAB/'人工核对/最新人工核对.json').read_text(encoding='utf-8'))['run'])
    original=json.loads((source/'全部收纳.json').read_text(encoding='utf-8'));rows=original['characters'];bycp={r['cp']:r for r in rows}
    rules=json.loads((source/'人工约束.json').read_text(encoding='utf-8'))
    wedge_locked=bool(rules.get('wedgeFamily',{}).get('pure',False))
    protected='oxyz' if wedge_locked else 'xyz'
    model=json.loads((source/'模型.json').read_text(encoding='utf-8'))
    with gzip.open(model['qualityRecords'],'rt',encoding='utf-8') as f:qa=list(map(json.loads,f))
    with np.load(model['featureCache']) as f:
        visual=(f['pixels']-np.array(model['pixelMean'],dtype='float32'))@np.array(model['basis'],dtype='float32')/model['visualScale']
        structural=(f['stats']-np.array(model['structureMean']))/np.array(model['structureScale'])*np.array(model['structureWeights'])
        matrix=np.concatenate([visual,structural,f['hog']*model['hogMultiplier']],1).astype('float32')
    keep=[i for i,q in enumerate(qa) if bycp[q['cp']]['primary'] in list(ACTIVE) and (not wedge_locked or bycp[q['cp']]['primary']!='o')]
    x=matrix[keep];members=[bycp[qa[i]['cp']] for i in keep];cp=np.array([r['cp'] for r in members]);labels=np.array([ACTIVE.index(r['primary']) for r in members]);k=len(ACTIVE)
    centres=np.array([x[labels==j].mean(0) if (labels==j).any() else np.zeros(x.shape[1]) for j in range(k)],dtype='float32')
    cost=dist(x,centres)
    if wedge_locked:cost[:,ACTIVE.index('o')]=1e6
    own=cost[np.arange(len(x)),labels];target=cost.argmin(1);gain=own-cost[np.arange(len(x)),target]
    # Screen only machine assignments with substantial geometric improvement. Human rows stay fixed.
    cutoff=float(np.quantile(own,.65))
    candidates=np.array([i for i,r in enumerate(members) if r['status']=='optimized-draft-frozen' and (own[i]>=cutoff or gain[i]>.005)],dtype=int)
    near={};strong=[]
    for begin in range(0,len(candidates),64):
        ii=candidates[begin:begin+64];d=dist(x[ii],x);d[np.arange(len(ii)),ii]=np.inf
        nn=np.argpartition(d,12,axis=1)[:,:12]
        for i,indices in zip(ii,nn):
            indices=indices[np.argsort(d[np.where(ii==i)[0][0],indices])]
            votes=np.bincount(labels[indices],minlength=k);j=int(votes.argmax());support=int(votes[j]);oldSupport=int(votes[labels[i]])
            improvement=float(own[i]-cost[i,j])
            if j!=labels[i] and (not wedge_locked or j!=ACTIVE.index('o')) and support>=9 and oldSupport<=2 and improvement>-.30:
                strong.append((int(i),j,improvement,support,oldSupport));near[int(i)]=indices.tolist()
        print('neighbors',min(begin+64,len(candidates)),'/',len(candidates),'strong',len(strong),flush=True)
    strong.sort(key=lambda r:(-(r[2]+.60*(r[3]-r[4])/12),int(cp[r[0]])))
    # A small batch avoids broad memory churn; retain at most 300 proposed moves.
    strong=strong[:300];ids=np.array([r[0] for r in strong],dtype=int)
    counts=Counter(r['primary'] for r in rows if r['primary'] and r['primary'] in ACTIVE)
    fixed=np.array([counts[a] for a in ACTIVE]);np.add.at(fixed,labels[ids],-1)
    experiments=[];choices=[]
    for penalty in (.02,.08,.15):
        costs=np.full((len(ids),k),1e6,dtype='float64')
        for n,(i,j,improvement,support,oldSupport) in enumerate(strong):
            costs[n,labels[i]]=cost[i,labels[i]]+.60*(1-oldSupport/12);costs[n,j]=cost[i,j]+.60*(1-support/12)+penalty
        newlabels=redistribute(costs,np.maximum(0,500-fixed),2000-fixed) if len(ids) else np.array([],dtype=int)
        assert all(costs[n,j]<1e5 for n,j in enumerate(newlabels))
        proposed=labels.copy();proposed[ids]=newlabels
        newcentres=np.array([x[proposed==j].mean(0) if (proposed==j).any() else centres[j] for j in range(k)])
        loss=float(((x-newcentres[proposed])**2).sum(1).mean());baseline=float(((x-centres[labels])**2).sum(1).mean())
        changed=int((proposed!=labels).sum())
        beforeSupport=float(np.mean([np.mean(labels[near[int(i)]]==labels[i]) for i in ids])) if len(ids) else 0
        afterSupport=float(np.mean([np.mean(proposed[near[int(i)]]==proposed[i]) for i in ids])) if len(ids) else 0
        result={'switchPenalty':penalty,'moves':changed,'beforeMSE':baseline,'afterMSE':loss,'beforeBoundarySupport':beforeSupport,'afterBoundarySupport':afterSupport,'note':'同一旧特征空间内的拟合与候选近邻指标，不是人工准确率；未重建字体特征。'}
        experiments.append(result);choices.append(proposed);print(result,flush=True)
    # Prefer fewer moves among strategies with a measurable fit improvement.
    eligible=[i for i,r in enumerate(experiments) if r['moves'] and r['afterBoundarySupport']>r['beforeBoundarySupport'] and r['afterMSE']<=r['beforeMSE']*1.005]
    selected=min(eligible,key=lambda i:(experiments[i]['moves'],experiments[i]['afterMSE'])) if eligible else 0
    proposed=choices[selected];output=copy.deepcopy(original);newby={r['cp']:r for r in output['characters']};changes=[]
    strongmap={r[0]:r for r in strong}
    for i in np.flatnonzero(proposed!=labels):
        r=newby[int(cp[i])];before=r['primary'];after=ACTIVE[int(proposed[i])]
        r.update(primary=after,status='neighbor-refinement-proposal');r['aliases']=[a for a in r['aliases'] if a!=after]
        _,_,improvement,support,oldSupport=strongmap[int(i)]
        evidence=[{'cp':int(cp[j]),'char':members[j]['char'],'primary':members[j]['primary']} for j in near[int(i)]]
        changes.append({'cp':int(cp[i]),'char':r['char'],'before':before,'after':after,'targetNeighbors':support,'oldNeighbors':oldSupport,'neighbors':evidence,'centroidGain':improvement})
    newcounts=Counter(r['primary'] for r in output['characters'] if r['primary'] and r['primary'] in ACTIVE)
    assert all(500<=newcounts[a]<=2000 for a in ACTIVE)
    assert [r for r in rows if r['primary'] and r['primary'] in protected]==[r for r in output['characters'] if r['primary'] and r['primary'] in protected]
    assert all(newby[r['cp']]==r for r in rows if r['status']!='optimized-draft-frozen')
    run=LAB/'邻域优化/运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    save(run/'候选分组.json',output);save(run/'迁移建议.json',changes)
    summary={'source':str(source),'mode':'review-proposal-only','frozenBuckets':list(protected),'moves':len(changes),'screened':len(candidates),'highConfidenceCandidates':len(strong),'experiments':experiments,'selected':selected,'beforeCounts':dict(counts),'afterCounts':dict(newcounts),'featureCache':model['featureCache'],'featureCacheSHA256':hashlib.sha256(Path(model['featureCache']).read_bytes()).hexdigest(),'limitations':['沿用旧的216维特征，并未把新字体重新提取进训练样本。','近邻投票来自同一特征空间，须人工核对，不代表独立验证。','只生成建议，不更新冻结主分组或小狼毫。']}
    save(run/'摘要.json',summary)
    preview=run/'全部字符预览';preview.mkdir()
    for letter in ACTIVE+'x':(preview/(letter+'.md')).write_text(''.join(r['char'] for r in output['characters'] if r['primary']==letter),encoding='utf-8')
    (preview/'a-w.md').write_text('\n\n'.join('# '+a+'\n'+''.join(r['char'] for r in output['characters'] if r['primary']==a) for a in ACTIVE),encoding='utf-8')
    fontpage=(source/'字体全面检查-20261014/全部桶字体核对.html').read_text(encoding='utf-8')
    style=re.search(r'<style>(.*?)</style>',fontpage,re.S).group(1)
    fontstack=re.search(r'\.chars\{font-family:(.*?);font-size:',style).group(1)
    cards=[]
    for c in changes:
        samples=''.join('<span title="U+%04X · %s">%s</span>'%(n['cp'],n['primary'],html.escape(n['char'])) for n in c['neighbors'])
        cards.append('<tr><td class="glyph">'+html.escape(c['char'])+'</td><td>U+%04X</td><td>%s → %s</td><td>%d/12；原桶 %d/12</td><td class="glyph neighbors">%s</td></tr>'%(c['cp'],c['before'],c['after'],c['targetNeighbors'],c['oldNeighbors'],samples))
    page='<!doctype html><meta charset="utf-8"><title>桶分类局部优化建议</title><style>'+style+'body{font:16px system-ui;background:#1e1e1e;color:#ddd}table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #555}.glyph{font-family:'+fontstack+';font-size:36px}.neighbors span{display:inline-block;min-width:50px;margin:5px}small{color:#aaa}</style><h1>桶分类局部优化建议</h1><p>建议迁移 '+str(len(changes))+' 字；'+ '/'.join(protected)+' 与人工确认记录保持不变。每桶 500–2000 字。当前主分组未覆盖。</p><p>这是旧特征上的局部优化，近邻票数不是正确率。字体显示已沿用修正版。</p><table><thead><tr><th>字符</th><th>码位</th><th>迁移</th><th>目标桶支持数</th><th>12个近邻（悬停看原桶）</th></tr></thead><tbody>'+''.join(cards)+'</tbody></table>'
    (run/'桶分类局部优化核对.html').write_text(page,encoding='utf-8')
    save(LAB/'邻域优化/最新实验.json',{'run':str(run),'source':str(source),'applied':False})
    print('RESULT',str(run),json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
