"""Refresh wedge glyphs, then optimize their visual assignments with a nonexclusive o."""
import base64,copy,gzip,hashlib,html,json,re
from pathlib import Path
from datetime import datetime
from collections import Counter
import numpy as np
from PIL import Image
from shape_quality_v2 import render,describe
from shape_lab_features import font_cmap
from purify_wedge_bucket import redistribute

PROJECT=Path(__file__).resolve().parents[1];LAB=PROJECT/'数据/三模式/规则库';ACTIVE='abcdefghijklmnopqrstuvw'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def distances(a,b):return np.maximum(0,(a*a).sum(1)[:,None]+(b*b).sum(1)[None,:]-2*a@b.T)
def transform(raw,m):
    v=(raw['pixels']-np.array(m['pixelMean'],dtype='float32'))@np.array(m['basis'],dtype='float32')/m['visualScale']
    s=(raw['stats']-np.array(m['structureMean']))/np.array(m['structureScale'])*np.array(m['structureWeights'])
    return np.concatenate([v,s,raw['hog']*m['hogMultiplier']],1).astype('float32')

def main():
    source=Path(read(LAB/'人工核对/最新人工核对.json')['run']);original=read(source/'全部收纳.json');rows=original['characters'];bycp={r['cp']:r for r in rows};rules=read(source/'人工约束.json')
    assert 'wedgeFamily' not in rules and rules['shapePolicy']['oExclusive'] is False
    wedge=set(rules['wedgeTag']['members']);model=read(source/'模型.json')
    with gzip.open(model['qualityRecords'],'rt',encoding='utf-8') as f:qa=list(map(json.loads,f))
    with np.load(model['featureCache']) as f:raw={k:list(f[k]) for k in ('pixels','stats','hog')}
    index={q['cp']:i for i,q in enumerate(qa)}
    fontpaths=[LAB/'字体/NotoSansCuneiform-Regular.ttf',Path('C:/Windows/Fonts/seguisym.ttf'),Path('C:/Windows/Fonts/seguihis.ttf')]
    fonts=[(p,*font_cmap(p)) for p in fontpaths];renderer={};render_manifest=[]
    for number,cp in enumerate(sorted(wedge),1):
        p,coverage,family=next((p,c,fam) for p,c,fam in fonts if cp in c)
        image,ratio,size=render(chr(cp),str(p),0,renderer);stats,hog=describe(image,ratio)
        pixels=np.array(Image.fromarray((image*255).astype('uint8')).resize((32,32),Image.Resampling.BOX),dtype='float32').flatten()/255
        q={'cp':cp,'primaryFont':family,'primaryFontPath':str(p),'renderSize':size,'acceptedViews':1,'alternate':None,'reviewFlags':['native-wedge-refresh-single-view']}
        if cp not in index:
            index[cp]=len(qa);qa.append(q)
            for key,value in (('pixels',pixels),('stats',stats),('hog',hog)):raw[key].append(value)
        else:
            i=index[cp];qa[i]=q
            for key,value in (('pixels',pixels),('stats',stats),('hog',hog)):raw[key][i]=value
        render_manifest.append({'cp':cp,'font':str(p),'family':family,'size':size})
        if number%200==0:print('native glyphs refreshed',number,'/',len(wedge),flush=True)
    raw={k:np.array(v,dtype='float32') for k,v in raw.items()};matrix=transform(raw,model)
    observed=[i for i,q in enumerate(qa) if bycp[q['cp']]['primary'] in list(ACTIVE)]
    x=matrix[observed];members=[bycp[qa[i]['cp']] for i in observed];cps=np.array([r['cp'] for r in members]);labels=np.array([ACTIVE.index(r['primary']) for r in members]);k=len(ACTIVE);oi=ACTIVE.index('o')
    centres=np.array([x[labels==j].mean(0) for j in range(k)],dtype='float32');basecost=distances(x,centres)
    # Wedge rows are unlocked. Other ordinary rows may enter o only; confirmed rows stay fixed.
    unlocked_wedge=[i for i,r in enumerate(members) if r['cp'] in wedge and not r.get('shapeAssignmentLocked')]
    incoming=[i for i,r in enumerate(members) if r['cp'] not in wedge and r['status']=='optimized-draft-frozen' and not r.get('shapeAssignmentLocked')]
    incoming=sorted((i for i in incoming if basecost[i,labels[i]]-basecost[i,oi]>-.10),key=lambda i:float(basecost[i,oi]-basecost[i,labels[i]]))[:600]
    ids=np.array(unlocked_wedge+incoming,dtype=int);variable=set(ids.tolist());counts=Counter(r['primary'] for r in rows if r['primary'] in list(ACTIVE));fixed=np.array([counts[a] for a in ACTIVE]);np.add.at(fixed,labels[ids],-1)
    print('optimization pool',len(unlocked_wedge),'wedge +',len(incoming),'possible incoming',flush=True)
    before=float(((x-centres[labels])**2).sum(1).mean());experiments=[];solutions=[]
    for penalty in (.03,.08,.15):
        current=labels.copy();c=centres.copy();best=None;history=[]
        for iteration in range(6):
            cost=distances(x[ids],c)
            for n,i in enumerate(ids):
                if i not in set(unlocked_wedge):
                    allowed=cost[n,[labels[i],oi]].copy();cost[n,:]=1e6;cost[n,[labels[i],oi]]=allowed
            cost+=penalty*(np.arange(k)[None,:]!=labels[ids,None])
            assigned=redistribute(cost,np.maximum(0,500-fixed),2000-fixed)
            assert all(cost[n,j]<1e5 for n,j in enumerate(assigned))
            proposed=labels.copy();proposed[ids]=assigned
            c=np.array([x[proposed==j].mean(0) for j in range(k)],dtype='float32')
            mse=float(((x-c[proposed])**2).sum(1).mean());moved=int((proposed!=labels).sum());objective=mse+.08*moved/len(x)
            history.append({'iteration':iteration+1,'mse':mse,'moves':moved,'comparisonObjective':objective})
            if best is None or objective<best[0]:best=(objective,proposed.copy(),c.copy())
            print('penalty',penalty,'iteration',iteration+1,'mse',mse,'moves',moved,flush=True)
            if np.array_equal(current,proposed):break
            current=proposed
        experiments.append({'penalty':penalty,'history':history,'objective':best[0]});solutions.append(best)
    selected=min(range(len(solutions)),key=lambda j:solutions[j][0]);_,proposed,newcentres=solutions[selected]
    assert float(((x-newcentres[proposed])**2).sum(1).mean())<before
    output=copy.deepcopy(original);newby={r['cp']:r for r in output['characters']};changes=[];changed=np.flatnonzero(proposed!=labels)
    for offset in range(0,len(changed),64):
        ii=changed[offset:offset+64];d=distances(x[ii],x);d[np.arange(len(ii)),ii]=np.inf;nn=np.argpartition(d,8,axis=1)[:,:8]
        for n,i in enumerate(ii):
            cp=int(cps[i]);r=newby[cp];r.update(primary=ACTIVE[int(proposed[i])],status='shape-only-wedge-proposal');r['aliases']=[a for a in r['aliases'] if a!=r['primary']]
            neighbors=nn[n][np.argsort(d[n,nn[n]])]
            changes.append({'cp':cp,'char':r['char'],'before':ACTIVE[int(labels[i])],'after':r['primary'],'wedgeTag':cp in wedge,
                'neighbors':[{'cp':int(cps[j]),'char':members[j]['char'],'before':ACTIVE[int(labels[j])],'after':ACTIVE[int(proposed[j])]} for j in neighbors]})
    aftercounts=Counter(r['primary'] for r in output['characters'] if r['primary']);assert all(500<=aftercounts[a]<=2000 for a in ACTIVE)
    assert all(newby[r['cp']]==r for r in rows if r.get('shapeAssignmentLocked') or r['primary'] in ('x','y','z'))
    assert all(newby[r['cp']]==r for r in rows if r['cp'] not in wedge and r['cp'] not in {int(cps[i]) for i in incoming})
    run=LAB/'邻域优化/运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    np.savez_compressed(run/'刷新后字形特征.npz',**raw)
    with gzip.open(run/'刷新后字形质量.jsonl.gz','wt',encoding='utf-8') as f:
        for q in qa:f.write(json.dumps(q,ensure_ascii=True)+'\n')
    model.update(featureCache=str(run/'刷新后字形特征.npz'),qualityRecords=str(run/'刷新后字形质量.jsonl.gz'),centres=newcentres.tolist(),nativeWedgeRefresh=1315,transformRetrained=False)
    save(run/'候选模型.json',model);save(run/'候选分组.json',output);save(run/'迁移建议.json',changes)
    manifest={'fonts':[{'path':str(p),'family':fam,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,_,fam in fonts],'renders':render_manifest,'note':'重渲染楔笔标签集合全部1315字；这份标签仅用于确定本轮工作范围，不作为分桶特征。'};save(run/'字形刷新依据.json',manifest)
    summary={'source':str(source),'applied':False,'scope':'o-unlocked-shape-only','nativeRefreshed':len(wedge),'newlyObservable':196,'moves':len(changes),'wedgeMovedOut':sum(c['wedgeTag'] and c['before']=='o' and c['after']!='o' for c in changes),'nonWedgeMovedIn':sum(not c['wedgeTag'] and c['after']=='o' for c in changes),'beforeCounts':dict(counts),'afterCounts':dict(aftercounts),'beforeMSE':before,'afterMSE':float(((x-newcentres[proposed])**2).sum(1).mean()),'experiments':experiments,'selected':selected,'nonNearestAssignments':int(sum(proposed[i]!=distances(x[i:i+1],newcentres).argmin(1)[0] for i in ids)),
        'limitations':['仅刷新楔笔标签集合字形，其他字符仍用既有特征。','保留原PCA投影与结构标准化；未全量重训。','本轮为单字体视图，缺少第二字体一致性验证。','距离改善不等于人工相似度准确率，容量下限仍可能保留边界字符。']}
    save(run/'摘要.json',summary)
    preview=run/'全部字符预览';preview.mkdir()
    for a in ACTIVE+'x':(preview/(a+'.md')).write_text(''.join(r['char'] for r in output['characters'] if r['primary']==a),encoding='utf-8')
    (preview/'a-w.md').write_text('\n\n'.join('# '+a+'\n'+(preview/(a+'.md')).read_text(encoding='utf-8') for a in ACTIVE),encoding='utf-8')
    oldpage=(source/'字体全面检查-20261014/全部桶字体核对.html').read_text(encoding='utf-8');style=re.search(r'<style>(.*?)</style>',oldpage,re.S).group(1);stack=re.search(r'\.chars\{font-family:(.*?);font-size:',style).group(1)
    # Review the same Cuneiform outlines used for refreshed descriptors, not a different system fallback.
    native_range=','.join('U+%X'%cp for cp in sorted(wedge & fonts[0][1]))
    style+='@font-face{font-family:WedgeReviewedNative;src:url("data:font/ttf;base64,'+base64.b64encode(fontpaths[0].read_bytes()).decode()+'");unicode-range:'+native_range+';}.chars{font-family:WedgeReviewedNative,'+stack+';}'
    stack='WedgeReviewedNative,'+stack
    heading='<h1>o取消专属限制后的图形优化草稿</h1><p>原楔笔移出 '+str(summary['wedgeMovedOut'])+' 字，其他字符移入o '+str(summary['nonWedgeMovedIn'])+' 字。已接受的262项与x/y/z保持不变，尚未替换主分组。</p>'
    body=''.join('<h2>'+a+' · '+str(aftercounts[a])+' 字</h2><div class="chars">'+html.escape(''.join(r['char'] for r in output['characters'] if r['primary']==a))+'</div>' for a in ACTIVE+'x')
    (run/'优化后全部桶预览.html').write_text('<!doctype html><meta charset="utf-8"><style>'+style+'</style>'+heading+'<p><a href="桶分类局部优化核对.html">查看逐字迁移</a></p>'+body,encoding='utf-8')
    cards=[]
    for c in changes:
        samples=''.join('<span title="U+%04X · %s→%s">%s</span>'%(n['cp'],n['before'],n['after'],html.escape(n['char'])) for n in c['neighbors'])
        cards.append('<tr><td class="glyph">'+html.escape(c['char'])+'</td><td>U+%04X</td><td>%s → %s</td><td class="glyph neighbors">%s</td></tr>'%(c['cp'],c['before'],c['after'],samples))
    (run/'桶分类局部优化核对.html').write_text('<!doctype html><meta charset="utf-8"><style>'+style+'body{font:16px system-ui;background:#1e1e1e;color:#ddd}td{padding:14px;border-bottom:1px solid #555}.glyph{font-family:'+stack+';font-size:36px}.neighbors span{display:inline-block;min-width:50px;margin:6px}</style>'+heading+'<p><a href="优化后全部桶预览.html">查看全部桶</a></p><p>以下列出本轮变化和8个图形近邻；悬停查看近邻的前后桶。仅内部特征距离，不是人工准确率。</p><table><tr><th>字符</th><th>码位</th><th>迁移</th><th>8个近邻</th></tr>'+''.join(cards)+'</table>',encoding='utf-8')
    report={'identities':len(rows),'xyzUnchanged':True,'confirmed262Unchanged':True,'oExclusive':False,'ordinaryMin':min(aftercounts[a] for a in ACTIVE),'ordinaryMax':max(aftercounts[a] for a in ACTIVE),'wedgeRendered':len(wedge),'featureRowsMatchQuality':len(qa)==len(matrix),'allFeaturesFinite':bool(np.isfinite(matrix).all()),'canonicalChanged':False};save(run/'校验报告.json',report)
    save(LAB/'邻域优化/最新实验.json',{'run':str(run),'source':str(source),'applied':False})
    print('RESULT',str(run),json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
