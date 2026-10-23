"""Build a local review page from completed drafts, never publishing them."""
import gzip
import json
from pathlib import Path
from inspect_shape_lab import load_run,inspect


def build():
    run,summary=load_run();best=summary['strategies'][0]
    rows=[]
    with gzip.open(run/'观测视图.jsonl.gz','rt',encoding='utf-8') as vf,gzip.open(run/'编码'/(best['id']+'.jsonl.gz'),'rt',encoding='utf-8') as cf:
        for v,c in zip(vf,cf):
            view=json.loads(v);row=json.loads(c)
            paths=[[a['code'],[view['views'][i]['target'] for i in a['views']]] for a in row['codes']]
            rows.append([row['cp'],row['char'],row['status'],view['font'],paths])
    payload=json.dumps({'strategy':best['name'],'dictionary':best['dictionary'],'fourth':summary['fourth'],'rows':rows},ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    page=r'''<!doctype html><meta charset="utf-8"><title>全形机器初稿核对</title>
<style>body{font:16px system-ui;max-width:1050px;margin:28px auto;padding:0 18px;background:#f5f7fa;color:#213244}input,button,select{font:inherit;padding:8px}article{background:white;border-radius:10px;padding:18px;margin:14px 0}.glyph{font-size:42px}code{background:#eef3f7;padding:4px}small{color:#596a7b}h1{font-size:26px}</style>
<h1>全形机器初稿 · 逐字符核对</h1><p id="strategy"></p><p>所有结果待核对；不同字体可能影响大小和轮廓。第四位沿用固定布局，此页面不会保存改码或发布输入法。</p>
<select id="kind"><option value="char">字符或 U+码位</option><option value="code">编码／编码前缀</option><option value="pending">待补字形队列</option></select> <input id="query" value="○◯Oo〇0CϹJj"><button id="go">查询</button><p id="count"></p><main id="result"></main>
<script>const data=PAYLOAD;const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function render(){let q=$('query').value.trim(),kind=$('kind').value;let cp=/^U\+[0-9a-f]+$/i.test(q)?parseInt(q.slice(2),16):null;let chars=new Set(Array.from(q));let found=data.rows.filter(r=>kind==='pending'?r[2]==='unobserved':kind==='code'?q!==''&&r[4].some(c=>c[0].startsWith(q.toLowerCase())):cp!==null?r[0]===cp:chars.has(r[1]));$('count').textContent='命中 '+found.length+' 个字符，显示前100个；多码逐条标注。';$('result').innerHTML=found.slice(0,100).map(r=>'<article><span class="glyph" style="font-family:'+esc(r[3])+', sans-serif">'+esc(r[1])+'</span> U+'+r[0].toString(16).toUpperCase()+' <small>参考字体 '+esc(r[3]||'缺失')+'</small>'+(!r[4].length?'<p>未观测字形，未生成四码。</p>':r[4].map(c=>'<p><code>'+esc(c[0])+'</code><br>'+Array.from(c[0]).map((k,i)=>'第'+(i+1)+'位 '+k+'＝'+esc(i<3?data.dictionary[i][k]:data.fourth[k].meaning)).join('；')+'<br><small>第四位描述对象：'+c[1].map(esc).join('；')+'</small></p>').join(''))+'</article>').join('')}
$('strategy').textContent='当前权重暂优：'+data.strategy+'。易记评分为先验代理，尚未经过真人记忆测试。';$('go').onclick=render;$('kind').onchange=render;$('query').addEventListener('keydown',e=>{if(e.key==='Enter')render()});render();</script>'''.replace('PAYLOAD',payload)
    faces=[]
    for font in summary['featureManifest']['fonts']:
        path=Path(font['path'])
        if path.parent.name=='字体':
            faces.append('@font-face{font-family:'+json.dumps(font['family'])+';src:url("../../字体/'+path.name+'")}')
    page=page.replace('<style>','<style>'+''.join(faces))
    path=run/'逐字符核对.html';path.write_text(page,encoding='utf-8')
    ranking=run/'规则策略实验报告.html'
    content=ranking.read_text(encoding='utf-8')
    content=content.replace("sum=keys.reduce((n,k)=>n+Number($(k).value),0)||1;", "sum=keys.reduce((n,k)=>n+Number($(k).value),0);if(!sum){$('winner').textContent='请至少给一项指标非零权重';$('rank').innerHTML='';return;}")
    ranking.write_text(content,encoding='utf-8')
    example=inspect(run,summary,'○◯Oo〇0CϹJj△□+')
    lines=['# 暂优策略首轮对照','','这些是机器实验结果，不代表已确认的新码。第四位描述对象逐条列出。','', '| 字符 | 编码 | 第1位 | 第2位 | 第3位 | 第4位 | 末位对象 |','|---|---|---|---|---|---|---|']
    for row in example['characters']:
        for code in row.get('codes',[]):lines.append('| '+row['char']+' | `'+code['code']+'` | '+' | '.join(k+'＝'+m for k,m in zip(code['code'],code['meanings']))+' | '+'；'.join(code['fourthTargets'])+' |')
    (run/'暂优策略首轮对照.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(path)


if __name__=='__main__':build()
