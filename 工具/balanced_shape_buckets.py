"""Single-level capacity-constrained visual drafts. Existing primary assignments stay frozen."""
from __future__ import annotations
import argparse,gzip,hashlib,heapq,json,math,os,time
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
from shape_strategy_lab import LAB,save
from inspect_shape_lab import load_run

ROOT=LAB/'单层分桶';LETTERS='abcdefghijklmnopqrstuvwxyz';SIZE=24;SEED=20261012


def distances(x,centres):
    return np.maximum(0,(x*x).sum(1)[:,None]+(centres*centres).sum(1)[None,:]-2*x@centres.T)


def balanced_assign(cost,lower,upper):
    """Greedy minimum-regret repairs; feasible capacities, not an exact min-cost-flow solver."""
    n,k=cost.shape
    if not k*lower<=n<=k*upper:raise ValueError('容量不可行')
    labels=cost.argmin(1);counts=np.bincount(labels,minlength=k);heap=[]
    for i in np.flatnonzero(counts[labels]>upper):
        source=labels[i];alternatives=np.where((counts<upper)&(np.arange(k)!=source))[0]
        target=alternatives[np.argmin(cost[i,alternatives])]
        heapq.heappush(heap,(float(cost[i,target]-cost[i,source]),int(i),int(source),int(target)))
    while np.any(counts>upper):
        if not heap:raise RuntimeError('上限修复无候选')
        delta,i,source,target=heapq.heappop(heap)
        if labels[i]!=source or counts[source]<=upper:continue
        if counts[target]>=upper:
            alternatives=np.where((counts<upper)&(np.arange(k)!=source))[0]
            target=int(alternatives[np.argmin(cost[i,alternatives])])
            heapq.heappush(heap,(float(cost[i,target]-cost[i,source]),i,source,target));continue
        labels[i]=target;counts[source]-=1;counts[target]+=1
    for target in sorted(range(k),key=lambda j:(counts[j],j)):
        if counts[target]>=lower:continue
        candidates=np.flatnonzero(counts[labels]>lower)
        regret=cost[candidates,target]-cost[candidates,labels[candidates]]
        for i in candidates[np.argsort(regret,kind='stable')]:
            source=labels[i]
            if source==target or counts[source]<=lower:continue
            labels[i]=target;counts[source]-=1;counts[target]+=1
            if counts[target]>=lower:break
    assert np.all(counts>=lower) and np.all(counts<=upper)
    return labels


def fit(x,lower,upper,k=26,iterations=16):
    rng=np.random.default_rng(SEED);centres=[x[rng.integers(len(x))]];nearest=np.full(len(x),np.inf)
    for _ in range(1,k):
        nearest=np.minimum(nearest,((x-centres[-1])**2).sum(1));total=nearest.sum()
        centres.append(x[rng.choice(len(x),p=nearest/total if total else None)])
    centres=np.array(centres,dtype=np.float32);best=None;previous=None;history=[]
    for iteration in range(iterations):
        cost=distances(x,centres);labels=balanced_assign(cost,lower,upper)
        new=np.array([x[labels==j].mean(0) for j in range(k)],dtype=np.float32)
        loss=float(((x-new[labels])**2).sum(1).mean());history.append(loss)
        print(f'平衡分桶 {iteration+1}/{iterations}，均方距离 {loss:.5f}',flush=True)
        if best is None or loss<best[0]:best=(loss,labels.copy(),new.copy())
        if previous is not None and np.array_equal(labels,previous):break
        previous=labels.copy();centres=new
    return best[1],best[2],history


def canvas(record,fonts):
    f=record['feature'];key=(f['fontPath'],f.get('fontIndex',0))
    if key not in fonts:fonts[key]=ImageFont.truetype(key[0],48,index=key[1])
    mask=fonts[key].getmask(record['char'],mode='L');box=mask.getbbox()
    if box is None:raise ValueError('锁定字形已无法渲染')
    image=Image.frombytes('L',mask.size,bytes(mask)).crop(box)
    width,height=image.size;scale=(SIZE-2)/max(width,height)
    image=image.resize((max(1,round(width*scale)),max(1,round(height*scale))),Image.Resampling.LANCZOS)
    result=Image.new('L',(SIZE,SIZE));result.paste(image,((SIZE-image.width)//2,(SIZE-image.height)//2))
    return np.asarray(result,dtype=np.float32).flatten()/255


def geometry(f):
    return np.array([math.log(max(.05,f['ratio'])),f['density'],min(4,f['holes'])/4,
        min(6,f['components'])/6,f['symV'],f['symH'],f['hRun'],f['vRun'],f['cornerInk'],f['diagonal']],dtype=np.float32)


def features(records,source,model=None):
    observed=[r for r in records if r['feature']['observed']];fonts={}
    if not observed:return observed,np.empty((0,42),dtype=np.float32),model
    cache=ROOT/'缓存';cache.mkdir(parents=True,exist_ok=True)
    signature=hashlib.sha256((source['featureCache']+'canvas24-aspect-v1').encode()).hexdigest()[:20]
    path=cache/(signature+'.npz')
    if model is None and path.exists():
        with np.load(path) as data:pixels=data['pixels'];geo=data['geometry']
    else:
        pixels=[];geo=[]
        for i,r in enumerate(observed,1):
            pixels.append(canvas(r,fonts));geo.append(geometry(r['feature']))
            if i%5000==0:print(f'等比例字形预处理 {i}/{len(observed)}',flush=True)
        pixels=np.array(pixels,dtype=np.float32);geo=np.array(geo,dtype=np.float32)
        if model is None:np.savez_compressed(path,pixels=pixels,geometry=geo)
    if model is None:
        mean=pixels.mean(0);centred=pixels-mean
        covariance=centred.T@centred/max(1,len(pixels)-1)
        eigenvalues,eigenvectors=np.linalg.eigh(covariance);basis=eigenvectors[:,-32:][:,::-1].copy()
        # Fix arbitrary eigenvector signs for reproducible letter ordering.
        for col in range(basis.shape[1]):
            if basis[np.argmax(abs(basis[:,col])),col]<0:basis[:,col]*=-1
        visual_scale=float(np.sqrt(max(1e-8,eigenvalues[-32:].sum())))
        model={'pixelMean':mean.tolist(),'basis':basis.tolist(),'visualScale':visual_scale,
            'geometryMean':geo.mean(0).tolist(),'geometryScale':np.maximum(geo.std(0),.15).tolist(),
            'geometryWeights':[.42,.18,.26,.22,.18,.18,.18,.18,.12,.10],
            'canvas':SIZE,'referenceFontSize':48,'sizeIncludedInClustering':False,
            'explainedPixelVariance':float(eigenvalues[-32:].sum()/max(1e-8,eigenvalues.sum()))}
    visual=(pixels-np.array(model['pixelMean'],dtype=np.float32))@np.array(model['basis'],dtype=np.float32)/model['visualScale']
    structural=(geo-np.array(model['geometryMean']))/np.array(model['geometryScale'])*np.array(model['geometryWeights'])
    return observed,np.concatenate([visual,structural],axis=1).astype(np.float32),model


def boundary_aliases(cost,primary,maximum=2):
    row=cost[primary];threshold=max(.015,float(row)*1.12)
    return [int(i) for i in np.argsort(cost,kind='stable') if i!=primary and cost[i]<=threshold][:maximum]


def initialise(records,source,letters=LETTERS):
    observed,x,model=features(records,source);n=len(observed);total=len(records)
    k=len(letters)
    lower=math.ceil(.8*total/k);upper=math.floor(1.2*total/k)
    fit_lower=max(lower,math.ceil(.8*n/k));fit_upper=min(upper,math.floor(1.2*n/k))
    labels,centres,history=fit(x,fit_lower,fit_upper,k=k)
    # Arrange draft letters along a centroid-neighbour path; this is not a keyboard layout guarantee.
    remaining=set(range(k));order=[int(np.argmin(centres[:,0]))];remaining.remove(order[0])
    while remaining:
        nxt=min(remaining,key=lambda j:(float(((centres[j]-centres[order[-1]])**2).sum()),j))
        order.append(nxt);remaining.remove(nxt)
    inverse={old:new for new,old in enumerate(order)};labels=np.array([inverse[int(j)] for j in labels])
    centres=centres[order];cost=distances(x,centres);lookup={}
    for i,r in enumerate(observed):
        primary=int(labels[i]);lookup[r['cp']]={'primary':letters[primary],
            'aliases':[letters[j] for j in boundary_aliases(cost[i],primary)],'distance':float(cost[i,primary]),
            'nearestBucket':letters[int(cost[i].argmin())],'font':r['feature']['font'],'status':'machine-draft-frozen'}
    rows=[dict(cp=r['cp'],char=r['char'],**lookup.get(r['cp'],{'primary':None,'aliases':[],'status':'pending-glyph'})) for r in records]
    return rows,dict(model,centres=centres.tolist(),letters=letters),{'scope':total,'observed':n,'plannedLower':lower,'plannedUpper':upper,
        'fitLower':fit_lower,'fitUpper':fit_upper,'history':history,'assignmentSolver':'minimum-regret greedy repairs; capacity feasible, not exact optimum'}


def incremental(records,source,previous):
    book=json.loads((previous/'冻结分组.json').read_text(encoding='utf-8'));model=json.loads((previous/'模型.json').read_text(encoding='utf-8'))
    letters=model.get('letters',LETTERS)
    existing={r['cp']:r for r in book['characters']};counts=Counter(r['primary'] for r in existing.values() if r['primary'])
    needed=[r for r in records if r['feature']['observed'] and not existing.get(r['cp'],{}).get('primary')]
    observed,x,_=features(needed,source,model);cost=distances(x,np.array(model['centres'],dtype=np.float32)) if len(x) else []
    for i,r in enumerate(observed):
        choices=[j for j in np.argsort(cost[i],kind='stable') if counts[letters[j]]<book['capacity']['plannedUpper']]
        if not choices:continue
        primary=int(choices[0]);existing[r['cp']]={'cp':r['cp'],'char':r['char'],'primary':letters[primary],
            'aliases':[letters[j] for j in boundary_aliases(cost[i],primary)],'distance':float(cost[i,primary]),
            'nearestBucket':letters[int(cost[i].argmin())],'font':r['feature']['font'],'status':'machine-draft-frozen'}
        counts[letters[primary]]+=1
    for r in records:
        existing.setdefault(r['cp'],{'cp':r['cp'],'char':r['char'],'primary':None,'aliases':[],
            'status':'pending-capacity' if r['feature']['observed'] else 'pending-glyph'})
        if r['feature']['observed'] and not existing[r['cp']]['primary']:existing[r['cp']]['status']='pending-capacity'
    # Preserve existing entries, including those absent from a later source; never silently delete frozen identities.
    rows=sorted(existing.values(),key=lambda r:r['cp']);capacity=dict(book['capacity'],incrementalFrom=str(previous))
    return rows,model,capacity


def representative_images(run,rows,records,model):
    observed=[r for r in records if r['feature']['observed']];record_map={r['cp']:r for r in records}
    by_bucket={k:[r for r in rows if r['primary']==k and r['cp'] in record_map] for k in model.get('letters',LETTERS)}
    representatives={};font_cache={};folder=run/'代表字形';folder.mkdir()
    label_font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',12)
    for key,members in by_bucket.items():
        ordered=sorted(members,key=lambda r:(r['distance'],r['cp']))
        chosen=ordered[:8]+ordered[-4:];seen=set();chosen=[r for r in chosen if not (r['cp'] in seen or seen.add(r['cp']))]
        representatives[key]=[{'cp':r['cp'],'char':r['char'],'distance':r['distance'],'kind':'中心代表' if i<8 else '远端样本'} for i,r in enumerate(chosen)]
        image=Image.new('RGB',(480,300),'#ffffff');draw=ImageDraw.Draw(image)
        for i,row in enumerate(chosen):
            f=record_map[row['cp']]['feature'];font_key=(f['fontPath'],f.get('fontIndex',0))
            if font_key not in font_cache:font_cache[font_key]=ImageFont.truetype(font_key[0],48,index=font_key[1])
            font=font_cache[font_key];x=(i%4)*120;y=(i//4)*100;box=font.getbbox(row['char'])
            draw.rectangle((x,y,x+119,y+99),outline='#d7dee7')
            draw.text((x+60-(box[2]-box[0])/2-box[0],y+38-(box[3]-box[1])/2-box[1]),row['char'],font=font,fill='#162a40',embedded_color=False)
            draw.text((x+10,y+72),f"U+{row['cp']:04X}",font=label_font,fill='#485b70')
            draw.text((x+10,y+85),'centre' if i<8 else 'edge',font=label_font,fill='#6a7e94')
        image.save(folder/(key+'.png'))
    return representatives


def publish_report(run,rows,model,capacity,source,records):
    letters=model.get('letters',LETTERS)
    reps=representative_images(run,rows,records,model);counts=Counter(r['primary'] for r in rows if r['primary'])
    assigned=sum(counts.values());aliases=sum(bool(r['aliases']) for r in rows);forced=sum(r.get('nearestBucket')!=r['primary'] for r in rows if r['primary'])
    summary={'date':'2026-10-12','buckets':len(letters),'letters':letters,'layers':1,'scopeRecords':len(rows),'assigned':assigned,'pending':len(rows)-assigned,
        'capacity':capacity,'counts':dict(counts),'charactersWithAliases':aliases,'capacityMovedFromNearest':forced,
        'sourceRun':source['run'],'fourthHash':source['fourthHash'],'modelExplainedPixelVariance':model['explainedPixelVariance'],
        'reviewStatus':'machine draft; grouping frozen for incremental operations','effectiveCodebooksChanged':False,'rimePublished':False,
        'representatives':reps}
    save(run/'摘要.json',summary)
    lines=['# 单层26桶：第一轮机器分组','','仅分一次26桶，允许±20%容量；主归属冻结，别名不计桶容量。第三／四位暂不重编码。','',
        f"范围{len(rows):,}字符；已分配{assigned:,}；待处理{len(rows)-assigned:,}。",'',
        f"完整语料每桶允许{capacity['plannedLower']}～{capacity['plannedUpper']}字。本轮可观测字形采用更紧的上限{capacity['fitUpper']}，预留后续补字空间。",'',
        f"具有补充入口的字符{aliases:,}；容量约束使主归属偏离最近中心的字符{forced:,}。别名至多取两个距离接近的桶，阈值为主距离×1.12或0.015平方距离下限。",'',
        '算法：保持宽高比的24×24墨迹画布→32维PCA整体轮廓＋10项结构特征→26簇迭代→最小代价增量的贪心容量修复。容量保证满足，聚类不是全局最优，也未使用精确最小费用流。', '',
        '尺寸未参与聚类；原宽高比、闭孔／构件、对称、直干等参与。参考字体48px；24×24是初稿分辨率，细小附加符号仍需核验。', '',
        '字母沿中心相似路径顺序安排，仅是暂定桶标签，不是已确定的语义键义或键盘邻近布局。当前分桶未引用Unicode名称、区块或数字／字母身份。', '',
        '| 桶 | 主归属字符数 | 中心与远端代表 |','|---|---:|---|']
    for k in letters:lines.append(f"| {k} | {counts[k]} | ![{k}代表](代表字形/{k}.png) |")
    lines+=['','普通重跑保留已有主归属及别名，只给新增或补齐字形的记录分配空余容量。容量不足时进入待容量队列；不自动搬动旧字符。只有显式`--rebuild`才重分全部桶。','',
        'Egyptology Extended Font by Land of Kemet (https://landofkemet.com)，基于 Serge Rosmorduc 与 Serge J.P. Thomas 的JSesh字形，CeCILL v2.1。字体来源及许可证见原规则库字体目录。','']
    (run/'单层分桶报告.md').write_text('\n'.join(lines),encoding='utf-8')
    payload=json.dumps({'summary':summary,'rows':rows},ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    page=r'''<!doctype html><meta charset="utf-8"><title>单层26桶字形核对</title><style>body{font:16px system-ui;max-width:1200px;margin:28px auto;padding:0 20px;background:#f4f6f9;color:#22354b}h1{font-size:26px}button,input,select{font:inherit;padding:7px}#buckets{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}article{background:white;padding:18px;border-radius:12px}article img{width:100%;max-width:480px}table{width:100%;border-collapse:collapse;background:white}td,th{padding:9px;border-bottom:1px solid #dbe3ec;text-align:left}.char{font-size:30px}small{color:#61748a}</style>
<h1>单层26桶 · 机器初稿核对</h1><p id="scope"></p><p>字母是暂定桶标签。代表图前8个为靠近中心的字符，后4个为远端样本。只冻结第一位分桶，第三／四位尚未重新生成。</p><p><select id="bucket"><option value="">所有桶</option></select> <input id="query" placeholder="字符，或 U+0043"><button id="go">查询</button></p><p id="count"></p><table><thead><tr><th>字符</th><th>码位</th><th>主归属</th><th>补充入口</th><th>状态／参考字体</th></tr></thead><tbody id="results"></tbody></table><h2>26桶代表字形</h2><div id="buckets"></div><p>Egyptology Extended Font by Land of Kemet，基于Serge Rosmorduc与Serge J.P. Thomas的JSesh字形，CeCILL v2.1。完整来源和算法说明见同目录报告。</p>
<script>const data=PAYLOAD;const $=s=>document.getElementById(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function show(){let key=$('bucket').value,q=$('query').value.trim(),cp=/^U\+[0-9a-f]+$/i.test(q)?parseInt(q.slice(2),16):null,chars=new Set(Array.from(q));let rows=data.rows.filter(r=>(!key||r.primary===key||r.aliases.includes(key))&&(!q||(cp!==null?r.cp===cp:chars.has(r.char))));$('count').textContent='命中 '+rows.length+'，显示前100个；补充入口不计主桶容量。';$('results').innerHTML=rows.slice(0,100).map(r=>'<tr><td class="char" style="font-family:'+esc(r.font||'system-ui')+'">'+esc(r.char)+'</td><td>U+'+r.cp.toString(16).toUpperCase()+'</td><td>'+esc(r.primary||'待分配')+'</td><td>'+esc(r.aliases.join(' / '))+'</td><td>'+esc(r.status)+'<br><small>'+esc(r.font||'无可观测字形')+'</small></td></tr>').join('')}
$('scope').textContent=data.summary.scopeRecords+'个记录；主归属已分配'+data.summary.assigned+'；待处理'+data.summary.pending+'；每桶'+data.summary.capacity.plannedLower+'～'+data.summary.capacity.plannedUpper+'字。';$('bucket').innerHTML+=Array.from('abcdefghijklmnopqrstuvwxyz').map(k=>'<option value="'+k+'">桶 '+k+'（主归属'+data.summary.counts[k]+'）</option>').join('');$('buckets').innerHTML=Array.from('abcdefghijklmnopqrstuvwxyz').map(k=>'<article><b>桶 '+k+' · '+data.summary.counts[k]+' 字</b><br><img src="代表字形/'+k+'.png" alt="'+k+'桶字形"></article>').join('');$('go').onclick=show;$('bucket').onchange=show;$('query').addEventListener('keydown',e=>{if(e.key==='Enter')show()});show();</script>'''.replace('PAYLOAD',payload)
    faces=[]
    for font in source['featureManifest']['fonts']:
        path=Path(font['path'])
        if path.parent.name=='字体':faces.append('@font-face{font-family:'+json.dumps(font['family'])+';src:url("'+os.path.relpath(path,run).replace('\\','/')+'")}')
    page=page.replace("Array.from('abcdefghijklmnopqrstuvwxyz')", "Array.from(data.summary.letters)")
    page=page.replace('<style>','<style>'+''.join(faces));(run/'单层分桶核对.html').write_text(page,encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rebuild',action='store_true');args=parser.parse_args()
    started=time.monotonic();_,source=load_run()
    if not source['scope']['allNonHan']:raise ValueError('源实验必须为全量语料')
    with gzip.open(source['featureCache'],'rt',encoding='utf-8') as stream:records=[json.loads(line) for line in stream]
    for font in source['featureManifest']['fonts']:
        if hashlib.sha256(Path(font['path']).read_bytes()).hexdigest()!=font['sha256']:raise ValueError('参考字体改变，请先重新建立字形实验')
    ROOT.mkdir(parents=True,exist_ok=True);latest=ROOT/'最新分桶.json';previous=None
    if latest.exists():previous=Path(json.loads(latest.read_text(encoding='utf-8'))['run'])
    rows,model,capacity=incremental(records,source,previous) if previous and not args.rebuild else initialise(records,source)
    run=ROOT/'运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    save(run/'冻结分组.json',{'version':'single-bucket-v1','fourthHash':source['fourthHash'],'capacity':capacity,'characters':rows})
    save(run/'模型.json',model)
    (run/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    summary=publish_report(run,rows,model,capacity,source,records)
    save(run/'源清单.json',{'sourceRun':source['run'],'featureCache':source['featureCache'],'featureManifest':source['featureManifest'],
        'scriptSHA256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'elapsedSeconds':time.monotonic()-started})
    save(latest,{'run':str(run),'completed':True,'groupingFrozen':True,'effectiveCodebooksChanged':False})
    print(json.dumps({'run':str(run),'assigned':summary['assigned'],'pending':summary['pending'],'counts':summary['counts']},ensure_ascii=False))


if __name__=='__main__':main()
