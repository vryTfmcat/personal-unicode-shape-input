"""Change presentation order only, using fixed visual descriptors and a short-path heuristic."""
import gzip,hashlib,html,json,re,shutil
from pathlib import Path
from datetime import datetime
import numpy as np
from optimize_unlocked_wedge_shapes import transform

PROJECT=Path(__file__).resolve().parents[1];LAB=PROJECT/'数据/三模式/规则库';ACTIVE='abcdefghijklmnopqrstuvw'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def path_cost(d,order):return float(d[order[:-1],order[1:]].sum(dtype='float64'))
def nearest_path(d,start):
    n=len(d);remaining=np.ones(n,dtype=bool);order=np.empty(n,dtype=int);current=start
    for pos in range(n):
        order[pos]=current;remaining[current]=False
        if pos+1<n:current=int(np.argmin(np.where(remaining,d[current],np.inf)))
    return order

def two_opt(d,order):
    order=order.copy();n=len(order)
    for _ in range(3):
        changed=False
        for i in range(n-2):
            j=np.arange(i+2,n-1)
            if not len(j):continue
            a,b=order[i:i+2];c=order[j];e=order[j+1]
            delta=d[a,c]+d[b,e]-d[a,b]-d[c,e];best=int(np.argmin(delta))
            if delta[best]<-1e-7:
                end=int(j[best]);order[i+1:end+1]=order[i+1:end+1][::-1];changed=True
        if not changed:break
    return order

def main():
    run=Path(read(LAB/'人工核对/最新人工核对.json')['run']);identity=run/'全部收纳.json';identity_hash=digest(identity)
    rows=read(identity)['characters'];bycp={r['cp']:r for r in rows};model=read(run/'模型.json')
    with gzip.open(model['qualityRecords'],'rt',encoding='utf-8') as f:qa=list(map(json.loads,f))
    with np.load(model['featureCache']) as f:matrix=transform({k:f[k] for k in ('pixels','stats','hog')},model)
    index={q['cp']:i for i,q in enumerate(qa)};orders={};metrics=[]
    for letter in ACTIVE:
        members=[r for r in rows if r['primary']==letter];assert all(r['cp'] in index for r in members)
        x=matrix[[index[r['cp']] for r in members]];d=np.maximum(0,(x*x).sum(1)[:,None]+(x*x).sum(1)[None,:]-2*x@x.T);np.sqrt(d,out=d);np.fill_diagonal(d,0)
        original=np.arange(len(members));centre=x.mean(0);start=int(np.argmax(((x-centre)**2).sum(1)));opposite=int(np.argmax(d[start]));central=int(np.argmin(((x-centre)**2).sum(1)))
        candidates=[original]+[nearest_path(d,s) for s in dict.fromkeys((start,opposite,central))]
        best=min(candidates,key=lambda order:path_cost(d,order));best=two_opt(d,best)
        if members[int(best[0])]['cp']>members[int(best[-1])]['cp']:best=best[::-1]
        assert set(best.tolist())==set(original.tolist())
        orders[letter]=[members[int(i)]['cp'] for i in best]
        before=path_cost(d,original);after=path_cost(d,best);assert after<=before+1e-5
        metrics.append({'bucket':letter,'characters':len(members),'beforeMeanAdjacentDistance':before/(len(members)-1),'afterMeanAdjacentDistance':after/(len(members)-1),'beforePathLength':before,'afterPathLength':after,'reduction':1-after/before})
        print(letter,len(members),'adjacent distance reduction',round((1-after/before)*100,2),'%',flush=True)
    # x is a dependent-mark collection; 251 entries lack descriptors, so do not invent a visual order.
    orders['x']=[r['cp'] for r in rows if r['primary']=='x']
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S');backup=run/('排序前备份-'+stamp);backup.mkdir()
    preview=run/'全部字符预览';shutil.copytree(preview,backup/'全部字符预览')
    for name in ('全部桶预览.html','单层分桶核对.html'):
        shutil.copy2(run/name,backup/name)
    fontpage=run/'字体全面检查-20261014/全部桶字体核对.html'
    shutil.copy2(fontpage,backup/'字体核对.html')
    for letter in ACTIVE:(preview/(letter+'.md')).write_text(''.join(bycp[cp]['char'] for cp in orders[letter]),encoding='utf-8')
    (preview/'a-w.md').write_text('\n\n'.join('# '+letter+'\n'+(preview/(letter+'.md')).read_text(encoding='utf-8') for letter in ACTIVE),encoding='utf-8')
    note='<p>桶内已按图形相似度排列，仅改变展示顺序。相邻通常更相近，不代表相邻字符必须同义；长链之间仍可能有跳跃。x附加符号保留原顺序。</p>'
    for page in (run/'全部桶预览.html',fontpage):
        text=page.read_text(encoding='utf-8');matches=list(re.finditer(r'<div class="chars">.*?</div>',text,re.S));assert len(matches)==24
        for letter,m in reversed(list(zip(ACTIVE+'x',matches))):
            if letter=='x':continue
            replacement='<div class="chars">'+html.escape(''.join(bycp[cp]['char'] for cp in orders[letter]))+'</div>'
            text=text[:m.start()]+replacement+text[m.end():]
        text=text.replace('</h1>','</h1>'+note,1);page.write_text(text,encoding='utf-8')
    # Search results use this order while canonical identity records remain sorted by codepoint.
    page=run/'单层分桶核对.html';text=page.read_text(encoding='utf-8');m=re.search(r'const data=(.*?);const \$=',text,re.S);data=json.loads(m.group(1));rank={cp:n for letter in ACTIVE+'x' for n,cp in enumerate(orders[letter])};bucket_rank={letter:n for n,letter in enumerate(ACTIVE+'xyz')}
    data['rows'].sort(key=lambda r:(bucket_rank.get(r['primary'],99),rank.get(r['cp'],r['cp'])))
    data['summary']['displayOrder']='visual-nearest-path-v1';data['summary']['representatives']={letter:[{'cp':orders[letter][i],'char':bycp[orders[letter][i]]['char']} for i in np.linspace(0,len(orders[letter])-1,12,dtype=int)] for letter in ACTIVE}
    payload=json.dumps(data,ensure_ascii=True,separators=(',',':'));text=text[:m.start(1)]+payload+text[m.end(1):];text=text.replace('</h1>','</h1>'+note,1);page.write_text(text,encoding='utf-8')
    target=LAB/'首次优化/运行/20261012-171242/全部字符预览'
    for p in preview.glob('*.md'):shutil.copy2(p,target/p.name)
    save(run/'桶内图形顺序.json',{'version':'visual-nearest-path-v1','sourceFeatureCache':model['featureCache'],'featureHash':digest(Path(model['featureCache'])),'orders':orders,'xUnchanged':True})
    total_before=sum(r['beforePathLength'] for r in metrics);total_after=sum(r['afterPathLength'] for r in metrics)
    report={'characters':sum(len(orders[a]) for a in ACTIVE),'buckets':23,'identityDataUnchanged':digest(identity)==identity_hash,'membershipUnchanged':True,'xUnchanged':True,'algorithm':'three deterministic nearest-neighbor starts, then open-path 2-opt; heuristic, not globally optimal','distance':'Euclidean distance in the existing 216D visual feature space','meanAdjacentReduction':1-total_after/total_before,'metrics':metrics,'backup':str(backup),'limitation':'相邻距离指标不是人工分类准确率；本轮没有重新提取字体或改变桶归属。'}
    assert report['identityDataUnchanged']
    for a in ACTIVE+'x':
        text=(preview/(a+'.md')).read_text(encoding='utf-8');assert len(text)==len(orders[a]) and '\n' not in text and '\r' not in text
        assert set(orders[a])=={r['cp'] for r in rows if r['primary']==a}
    save(run/'图形排序校验.json',report)
    summary=read(run/'摘要.json');summary['displayOrder']='visual-nearest-path-v1';summary['representatives']=data['summary']['representatives'];save(run/'摘要.json',summary)
    save(target.parent/'预览来源.json',{'source':str(run),'updated':'2026-10-16','displayOrder':'visual-nearest-path-v1','note':'a-w按图形距离排序；桶归属不变，x保留原顺序'})
    print('RESULT',str(run),json.dumps({k:v for k,v in report.items() if k!='metrics'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
