"""Full current-chvc review using confirmed sample geometry, never new codes."""
import io
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from audit_shape_historical_buckets import protect
from build_shape_turn_samples import PROJECT, sha, PALETTE
from shape_stroke_topology_trial import analyze, render_locked, VERSION

sys.path.insert(0,str(PROJECT/'原型/键位编辑器'))
import shape_overview as overview

SOURCE=overview.RUNS/'20261024-turn-junction-samples-v2'
OUTPUT=overview.RUNS/'20261024-chvc-turn-classification-v1'
FIELDS=('corners','forks','crosses','straightSegments','curveSegments')
NAMES=('折角','分叉','交叉','直线段','曲线段')
CELL=96
ATLAS_COLUMNS=16


def signature(stats):
    return tuple(stats[k] for k in FIELDS)


def class_label(key):
    return ' · '.join(f'{name}{n}' for name,n in zip(NAMES,key))


def classify_records(records):
    buckets=defaultdict(list)
    for r in records:
        s=r['statistics']
        if r['errors'] or not r['stableAcrossNineVariants']:
            key='pending-unstable'
        elif s['otherJunctions'] or s['uncertainSegments'] or not s['totalSegments']:
            key='pending-interpretation'
        else:
            key=signature(s)
        buckets[key].append(r)
    ordered=sorted((k for k in buckets if isinstance(k,tuple)),key=lambda k:(-len(buckets[k]),k))
    groups=[]
    for n,key in enumerate(ordered,1):
        group=dict(id=f'class-{n:03}',label=class_label(key),signature=list(key),count=len(buckets[key]),status='stable')
        groups.append(group)
        for r in buckets[key]:r.update(groupId=group['id'],status='stable')
    for key,label in [('pending-unstable','九扰动不稳定，分类待核'),('pending-interpretation','计数稳定，但有多出口或未定线段')]:
        if key not in buckets:continue
        groups.append(dict(id=key,label=label,count=len(buckets[key]),status=key))
        for r in buckets[key]:r.update(groupId=key,status=key)
    return groups


def tile(mask,result,annotated):
    image=Image.fromarray(255-mask.astype('uint8')*(65 if annotated else 255)).convert('RGB')
    if annotated:
        d=ImageDraw.Draw(image)
        for n,s in enumerate(result['segments']):
            d.line([tuple(p) for p in s['points']],fill=PALETTE[n%len(PALETTE)],width=3)
        for j in result['junctions']:
            x,y=j['xy']
            if j['arms']==4:d.polygon([(x,y-6),(x+6,y),(x,y+6),(x-6,y)],outline='#a315a8',width=3)
            else:d.ellipse((x-6,y-6,x+6,y+6),outline='#d11e35',width=3)
        for c in result['corners']:
            x,y=c['xy'];d.rectangle((x-5,y-5,x+5,y+5),outline='#1452e6',width=3)
    return image.resize((CELL,CELL),Image.Resampling.LANCZOS).tobytes()


def observe(job):
    old=job
    variants=[dict(v,weight=0) for v in old['variants']]
    errors=list(old['errors'])
    for size in (96,192,256):
        for weight in (-1,1):
            try:
                s=analyze(render_locked(old['char'],old['font'],size=size,weight=weight))['statistics']
                variants.append(dict(size=size,weight=weight,statistics=s))
            except (ValueError,IndexError,KeyError) as error:
                errors.append(dict(size=size,weight=weight,error=str(error)))
                variants.append(dict(size=size,weight=weight,statistics=None))
    mask=render_locked(old['char'],old['font'])
    baseline=analyze(mask)
    assert baseline['statistics']==old['statistics'], (old['cp'],'cached base no longer reproducible')
    stable=not errors and all(v['statistics']==baseline['statistics'] for v in variants)
    r={k:old[k] for k in ('cp','char','font','originalCodes','stableAcrossThreeSizes')}
    r.update(statistics=baseline['statistics'],stableAcrossNineVariants=stable,variants=sorted(variants,key=lambda v:(v['size'],v['weight'])),
             variantsAgreeWithBaseline=sum(v['statistics']==baseline['statistics'] for v in variants),errors=errors,
             corners=baseline['corners'],junctions=baseline['junctions'],prunedSpurCount=baseline['prunedSpurCount'])
    return r,tile(mask,baseline,False),tile(mask,baseline,True)


def build():
    if OUTPUT.exists():raise FileExistsError('不覆盖既有分类实验')
    old_path=SOURCE/'当前chvc全组结构比较.json'
    old=json.loads(old_path.read_text(encoding='utf-8'))
    model_path=PROJECT/'工具/shape_stroke_topology_trial.py'
    assert sha(model_path)==old['sourceHashes'][str(model_path.relative_to(PROJECT))]
    before=protect()
    o=overview.Overview();members=set(o.allocation_members('chvc'));intake=set(overview.exclusive_intake())
    assert members=={r['cp'] for r in old['records']}
    assert not members&intake
    assert all(o.brief(r['cp'],True)['codes']==r['originalCodes'] for r in old['records'])
    inputs=[old_path,model_path,Path(__file__)]+[PROJECT/'原型/键位编辑器'/n for n in
            ('shape_overview.py','shape-key-overview.js','shape-key-overview.html','data/pictorial-exclusive-allocation.json')]
    fingerprints={str(p.relative_to(PROJECT)):sha(p) for p in inputs}
    OUTPUT.mkdir();(OUTPUT/'atlas').mkdir()
    records=[]
    plain=Image.new('RGB',(CELL*ATLAS_COLUMNS,CELL*ATLAS_COLUMNS),'white')
    annotated=plain.copy()
    with ProcessPoolExecutor(max_workers=4) as executor:
        for n,(r,raw,marked) in enumerate(executor.map(observe,old['records'])):
            atlas=n//256;slot=n%256;x=slot%16*CELL;y=slot//16*CELL
            plain.paste(Image.frombytes('RGB',(CELL,CELL),raw),(x,y))
            annotated.paste(Image.frombytes('RGB',(CELL,CELL),marked),(x,y))
            r['preview']=dict(atlas=atlas,x=x,y=y,cell=CELL)
            r['originalPreferredCodes']=o.brief(r['cp'],True)['preferredCodes']
            records.append(r)
            if slot==255 or n==len(old['records'])-1:
                plain.save(OUTPUT/f'atlas/{atlas:03}-plain.png')
                annotated.save(OUTPUT/f'atlas/{atlas:03}-annotated.png')
                plain=Image.new('RGB',(CELL*ATLAS_COLUMNS,CELL*ATLAS_COLUMNS),'white');annotated=plain.copy()
            if (n+1)%150==0:print(f'九扰动分类与标注 {n+1}/{len(members)}',flush=True)
    groups=classify_records(records)
    assert {r['cp'] for r in records}==members
    assert sum(g['count'] for g in groups)==len(members)
    assert before==protect()
    assert fingerprints=={str(p.relative_to(PROJECT)):sha(p) for p in inputs}
    assert members==set(o.allocation_members('chvc'))
    assert all(o.brief(r['cp'],True)['codes']==r['originalCodes'] and o.brief(r['cp'],True)['preferredCodes']==r['originalPreferredCodes'] for r in records)
    stats=dict(cohort=len(records),stableThreeSizes=sum(r['stableAcrossThreeSizes'] for r in records),
               stableNineVariants=sum(r['stableAcrossNineVariants'] for r in records),
               unstableNineVariants=sum(not r['stableAcrossNineVariants'] for r in records),
               classifiedStable=sum(r['status']=='stable' for r in records),
               interpretationPending=sum(r['status']=='pending-interpretation' for r in records),
               stableClassCount=sum(g['status']=='stable' for g in groups),
               largestStableClass=max((g['count'] for g in groups if g['status']=='stable'),default=0),
               withPrunedSpurs=sum(bool(r['prunedSpurCount']) for r in records),
               charactersWithError=sum(bool(r['errors']) for r in records),
               reviewedSampleCount=7)
    sample=json.loads((SOURCE/'七例转折与分段结果.json').read_text(encoding='utf-8'))
    report=dict(version='chvc-turn-classification-v1',detector=VERSION,runTime=datetime.now().astimezone().isoformat(),
                statistics=stats,groups=groups,records=records,
                sampleAcceptance=dict(userText='核对正确，可以推广到chvc内所有字符中测试一下分类',
                                      scope='七例标注与显示计数已人工核对；授权全chvc独立分类测试，不是全族或新键义确认',
                                      samples=[dict(cp=r['cp'],statistics=r['baseline']['statistics']) for r in sample['records']]),
                protectedHashes=before,sourceHashes=fingerprints,
                currentChvcBefore=len(members),currentChvcAfter=len(members),newCodes=0,removedPaths=0,tBReentry=0,
                publicIntegration=False,newLetterBindings=False,
                limitations=['分类依据为五个独立计数，不按字符名称／语种分组。',
                             '九扰动稳定只证明机器重复性，只有七例是本轮人工核对样本。',
                             '不稳定字符仍展示基准临时计数与九次结果，不隐藏或删码。',
                             '短支修剪可能误伤真实短支，应优先核对；多于四出口连接未强行归为分叉或交叉。',
                             '分组尚未绑定输入码，不能把组人数当现行chvc候选人数。'])
    (OUTPUT/'分类数据.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    write_page(report)
    print(json.dumps(stats,ensure_ascii=False),flush=True)
    return report


def write_page(report):
    slim={k:report[k] for k in ('statistics','groups','limitations','sampleAcceptance')}
    slim['records']=[{k:r[k] for k in ('cp','char','statistics','status','groupId','preview','variantsAgreeWithBaseline','stableAcrossNineVariants',
                                     'prunedSpurCount','variants','originalPreferredCodes','originalCodes','corners','junctions')} for r in report['records']]
    data=json.dumps(slim,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (OUTPUT/'分类审阅.html').write_text(PAGE.replace('/*DATA*/',f'window.REVIEW_DATA={data};'),encoding='utf-8')
    (OUTPUT/'review.js').write_text(JS,encoding='utf-8')
    (OUTPUT/'review.css').write_text(CSS,encoding='utf-8')


PAGE='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>chvc 全字符结构分类试验</title><link rel="stylesheet" href="review.css"><body>
<header><div><span class="eyebrow">独立分类实验 · 原码与候选保留</span><h1>chvc：按折角、分叉、交叉与直曲段分类</h1><p id="summary"></p></div><a href="分类数据.json">完整数据</a></header>
<section class="note">蓝方框＝折角 · 红圆＝三线分叉 · 紫菱形＝四线交叉。折角和交点均分段；同处重合只分一次。七例已人工核对，其余均为程序分类，待核字符完整保留。<br>不同颜色表示不同线段。<strong>这些分类尚未绑定输入码，chvc 仍有 1,554 字。</strong></section>
<nav id="modes" aria-label="检测状态"><button data-mode="all">全部</button><button data-mode="stable">稳定分类</button><button data-mode="pending-unstable">九扰动不稳定</button><button data-mode="pending-interpretation">多出口等待解释</button><button data-mode="pruned">有短支修剪</button></nav>
<section class="filters"><label>查字或码位<input id="search" placeholder="ᱤ / U+1C64 / 1C64"></label><div id="facets"></div><label>字形视图<select id="view"><option value="annotated">结构标注</option><option value="plain">原始字形</option></select></label><button id="reset">重置筛选</button></section>
<main><aside><h2>稳定分类 <small id="groupCount"></small></h2><button id="allGroups">所有分类</button><div id="groupList"></div></aside><section class="result"><div class="resultHead"><h2 id="resultTitle">全部字符</h2><span id="resultCount" role="status"></span></div><div id="grid"></div><div class="pagination"><button id="prev">上一页</button><span id="pageInfo"></span><button id="next">下一页</button></div></section></main>
<dialog id="detail"><button id="closeDetail" aria-label="关闭详情">关闭</button><h2 id="detailTitle"></h2><div id="detailImage" class="sprite enlarged"></div><div id="detailText"></div><h3>九扰动结果</h3><div class="tableWrap"><table><thead><tr><th>字号</th><th>粗细</th><th>折／叉／交</th><th>直／曲／总段</th></tr></thead><tbody id="variantRows"></tbody></table></div></dialog>
<footer>分类不表示主桶迁移或新增键义。全部路径、旧偏好、t／b排他名单与小狼毫未改。</footer><script>/*DATA*/</script><script src="review.js"></script></body></html>'''

CSS='''*{box-sizing:border-box}body{margin:0;background:#f6f7f9;color:#202a32;font:15px/1.55 system-ui,"Microsoft YaHei",sans-serif}header{display:flex;gap:24px;justify-content:space-between;padding:24px 30px;background:white;border-bottom:1px solid #dce3e8}h1{font-size:24px;margin:5px 0}h2{font-size:18px;margin:8px 0}h3{font-size:16px}.eyebrow{color:#34786d;font-size:13px}p{margin:6px 0}a{color:#28665c}button,input,select{font:inherit}button,select,input{border:1px solid #b9c7cc;border-radius:6px;background:white;padding:7px 10px;min-width:0}button{cursor:pointer;text-align:left}button:hover{border-color:#2e7f6c}button.active{background:#dfefe8;border-color:#27816b}button:disabled{opacity:.45;cursor:default}.note{margin:18px 28px;background:#eaf3f1;padding:13px 16px;border-left:4px solid #3d8b78;border-radius:5px}nav{display:flex;gap:8px;padding:0 28px;flex-wrap:wrap}.filters{display:flex;gap:10px;flex-wrap:wrap;padding:16px 28px}.filters label{display:flex;flex-direction:column;font-size:12px;gap:4px}.filters input{width:200px}.filters button{align-self:end}#facets{display:flex;gap:8px;flex-wrap:wrap}main{display:grid;grid-template-columns:280px minmax(0,1fr);gap:18px;padding:0 28px 28px}aside{background:white;padding:12px;border-radius:8px;align-self:start;position:sticky;top:12px;max-height:82vh;display:flex;flex-direction:column}aside small{font-size:12px;color:#64757a}#groupList{overflow:auto;margin-top:8px;display:grid;gap:5px}#groupList button{font-size:12px;padding:8px}#groupList button b{display:block;color:#317663}.resultHead{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px}#resultCount{font-size:13px;color:#5a6b72}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(146px,1fr));gap:10px}.card{border:1px solid #c9d5d9;border-bottom:4px solid #4a8d7a;background:white;padding:10px 8px;text-align:center;display:flex;flex-direction:column;align-items:center;gap:5px;min-height:208px}.card.pending{border-bottom-color:#c48a3b}.sprite{display:block;width:96px;height:96px;background-repeat:no-repeat;background-color:white;flex-shrink:0}.cp{font-size:13px;font-weight:600}.counts{font-size:12px}.status{font-size:11px;color:#4e7065}.pending .status{color:#97652b}.spur{font-size:11px;color:#94612d}.pagination{display:flex;gap:12px;align-items:center;justify-content:center;padding:20px}.empty{padding:40px;text-align:center;color:#6a757e}dialog{width:min(720px,calc(100% - 24px));max-height:92vh;border:1px solid #b8c6ce;border-radius:12px;padding:20px;overflow:auto}dialog::backdrop{background:#17242c88}#closeDetail{float:right}.enlarged{width:288px;height:288px;max-width:100%;margin:10px auto}#detailText{font-size:14px}.tableWrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:6px;text-align:left;border-bottom:1px solid #d8e0e4}tr.different{background:#fff0d8}footer{padding:12px 28px 28px;color:#66757b;font-size:12px}@media(max-width:900px){main{grid-template-columns:1fr}aside{position:static;max-height:240px}#groupList{grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}}@media(max-width:480px){header{padding:16px;display:block}h1{font-size:21px}.note{margin:12px}.filters,nav{padding:12px}main{padding:0 12px}#grid{grid-template-columns:repeat(2,minmax(0,1fr))}.filters input{width:165px}.resultHead{display:block}.card{padding:8px 2px}.counts{font-size:11px}}'''

JS=r'''(()=>{'use strict';
const D=window.REVIEW_DATA, $=id=>document.getElementById(id), fields=['corners','forks','crosses','straightSegments','curveSegments'], names=['折角','分叉','交叉','直线段','曲线段'];
let state={mode:'all',group:'',search:'',page:0,view:'annotated'}, filtered=[], selected=null; const pageSize=48;
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const gs=new Map(D.groups.map(g=>[g.id,g]));
$('summary').textContent=`全部 ${D.statistics.cohort} 字 · 九扰动计数稳定 ${D.statistics.stableNineVariants} 字 · 可分类 ${D.statistics.classifiedStable} 字 · 不稳定 ${D.statistics.unstableNineVariants} 字 · 稳定分类 ${D.statistics.stableClassCount} 类`;
$('groupCount').textContent=`${D.statistics.stableClassCount} 类`;
fields.forEach((key,i)=>{const label=document.createElement('label');label.textContent=names[i];const select=document.createElement('select');select.id='facet-'+key;select.innerHTML='<option value="">不限</option>'+[...new Set(D.records.map(r=>r.statistics[key]))].sort((a,b)=>a-b).map(v=>`<option value="${v}">${v}</option>`).join('');select.onchange=()=>{state.group='';state.page=0;render()};label.append(select);$('facets').append(label)});
function status(r){return r.status==='stable'?'九扰动稳定':r.status==='pending-interpretation'?'稳定但需解释':`待核：${r.variantsAgreeWithBaseline}/9与基准一致`}
function sprite(el,r,scale=1){const p=r.preview;el.style.backgroundImage=`url("atlas/${String(p.atlas).padStart(3,'0')}-${state.view}.png")`;el.style.backgroundPosition=`${-p.x*scale}px ${-p.y*scale}px`;el.style.backgroundSize=`${1536*scale}px ${1536*scale}px`}
function queryMatch(r){const q=state.search.trim();if(!q)return true;if(r.char===q)return true;const cp=q.replace(/^U\+/i,'').replace(/^0x/i,'');return /^[0-9a-f]{2,6}$/i.test(cp)&&parseInt(cp,16)===r.cp}
function save(){const h=new URLSearchParams({mode:state.mode,group:state.group,q:state.search,page:String(state.page),view:state.view});fields.forEach(k=>{const v=$('facet-'+k).value;if(v)h.set(k,v)});history.replaceState(null,'','#'+h)}
function render(){
 filtered=D.records.filter(r=>queryMatch(r)&&(!state.group||r.groupId===state.group)&&(state.mode==='all'||state.mode==='pruned'&&r.prunedSpurCount>0||r.status===state.mode)&&fields.every(k=>!$('facet-'+k).value||r.statistics[k]===Number($('facet-'+k).value)));
 filtered.sort((a,b)=>D.groups.findIndex(g=>g.id===a.groupId)-D.groups.findIndex(g=>g.id===b.groupId)||a.cp-b.cp);
 const pages=Math.max(1,Math.ceil(filtered.length/pageSize));state.page=Math.max(0,Math.min(state.page,pages-1));$('resultTitle').textContent=state.group?gs.get(state.group).label:'全部分类';$('resultCount').textContent=`${filtered.length} / ${D.statistics.cohort} 字`;
 document.querySelectorAll('#modes button').forEach(b=>b.classList.toggle('active',b.dataset.mode===state.mode));
 $('groupList').innerHTML=D.groups.filter(g=>g.status==='stable').map(g=>`<button data-group="${g.id}" class="${state.group===g.id?'active':''}">${escape(g.label)}<b>${g.count} 字</b></button>`).join('');
 $('grid').replaceChildren();const slice=filtered.slice(state.page*pageSize,(state.page+1)*pageSize);
 slice.forEach(r=>{const b=document.createElement('button'),s=r.statistics;b.className='card'+(r.status==='stable'?'':' pending');b.dataset.cp=r.cp;b.innerHTML=`<span class="sprite"></span><span class="cp">U+${r.cp.toString(16).toUpperCase().padStart(4,'0')}</span><span class="counts">折${s.corners} · 叉${s.forks} · 交${s.crosses}<br>直${s.straightSegments} · 曲${s.curveSegments} · 共${s.totalSegments}段</span><span class="status">${escape(status(r))}</span>${r.prunedSpurCount?'<span class="spur">有短支修剪，优先核对</span>':''}`;sprite(b.querySelector('.sprite'),r);b.onclick=()=>detail(r);$('grid').append(b)});
 if(!slice.length)$('grid').innerHTML='<p class="empty">当前筛选没有字符；可重置后查看全部。</p>';
 $('pageInfo').textContent=`第 ${state.page+1} / ${pages} 页`;$('prev').disabled=state.page===0;$('next').disabled=state.page>=pages-1;save();
}
function detail(r){selected=r;$('detailTitle').textContent=`${r.char} · U+${r.cp.toString(16).toUpperCase()}`;sprite($('detailImage'),r,3);const s=r.statistics;
 $('detailText').innerHTML=`<p>${escape(gs.get(r.groupId).label)}</p><p>${escape(status(r))}；直${s.straightSegments}＋曲${s.curveSegments}＝${s.totalSegments}段。${s.otherJunctions?`另有 ${s.otherJunctions} 个五出口及以上连接区。`:''}</p><p>观测层短支修剪 ${r.prunedSpurCount} 处；原码和候选完整保留。</p><p>原偏好：${escape(r.originalPreferredCodes.join('、')||'无')}。这里没有生成新码。</p>`;
 $('variantRows').innerHTML=r.variants.map(v=>{const t=v.statistics;return `<tr class="${JSON.stringify(t)===JSON.stringify(s)?'':'different'}"><td>${v.size}</td><td>${{'-1':'细','0':'原','1':'粗'}[v.weight]}</td><td>${t?`${t.corners}／${t.forks}／${t.crosses}`:'未取得'}</td><td>${t?`${t.straightSegments}／${t.curveSegments}／${t.totalSegments}`:'待核'}</td></tr>`}).join('');if(!$('detail').open)$('detail').showModal();}
$('modes').onclick=e=>{const b=e.target.closest('[data-mode]');if(!b)return;state.mode=b.dataset.mode;state.group='';state.page=0;render()};
$('groupList').onclick=e=>{const b=e.target.closest('[data-group]');if(!b)return;state.mode='all';state.group=b.dataset.group;state.page=0;render()};
$('allGroups').onclick=()=>{state.group='';state.page=0;render()};$('search').oninput=()=>{state.search=$('search').value;state.page=0;render()};
$('view').onchange=()=>{state.view=$('view').value;render();if(selected&&$('detail').open)detail(selected)};
$('prev').onclick=()=>{state.page--;render()};$('next').onclick=()=>{state.page++;render()};$('closeDetail').onclick=()=>$('detail').close();
$('reset').onclick=()=>{state={mode:'all',group:'',search:'',page:0,view:'annotated'};$('search').value='';$('view').value='annotated';fields.forEach(k=>$('facet-'+k).value='');render()};
try{const h=new URLSearchParams(location.hash.slice(1));if(['all','stable','pending-unstable','pending-interpretation','pruned'].includes(h.get('mode')))state.mode=h.get('mode');if(gs.has(h.get('group')))state.group=h.get('group');state.search=h.get('q')||'';state.page=Math.max(0,Number(h.get('page'))||0);if(h.get('view')==='plain')state.view='plain';fields.forEach(k=>{if([...$('facet-'+k).options].some(o=>o.value===h.get(k)))$('facet-'+k).value=h.get(k)});}catch(e){}$('search').value=state.search;$('view').value=state.view;render();
})();'''


if __name__=='__main__':build()
