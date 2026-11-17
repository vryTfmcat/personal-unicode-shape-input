"""Screen a/c long-tail representatives; report only, no authority/runtime writes."""
import base64
import hashlib
import html
import io
import itertools
import json
import math
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'原型/键位编辑器'),str(ROOT/'工具')]
OUT=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/第一位分桶专项-20261025/a-c代表字筛选'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    if OUT.exists() and any(OUT.iterdir()):raise SystemExit('拒绝覆盖已有代表字筛选现场')
    # Recheck the last accepted runtime checkpoint, rather than assuming an old status.
    last=ROOT.parent/'archive/2026-10-25-第一位分桶首批确认/主归属恢复清单.json'
    manifest=json.loads(last.read_text(encoding='utf-8'))
    checkpoint_differences=[]
    for r in manifest['files']:
        if digest(ROOT/r['path'])!=r['sha256']:
            checkpoint_differences.append(r['path'])
    # Two other ongoing specialties appended independent accepted records.
    # Validate the precise additions; retain their current bytes and never write them.
    manual_rel='数据/三模式/规则库/四键实验/人工审议.json'
    assert set(checkpoint_differences)<={manual_rel},checkpoint_differences
    previous_manual=json.loads((Path(manifest['restored'])/manual_rel).read_text(encoding='utf-8'))
    current_manual=json.loads((ROOT/manual_rel).read_text(encoding='utf-8'))
    added=set(current_manual)-set(previous_manual)
    assert added<={'roundSubjectBrowseExclusionAcceptance20261025Batch1','pathRecommendationAcceptance20261025Batch1'},added
    assert all(current_manual[k]==value for k,value in previous_manual.items())
    OUT.mkdir(exist_ok=True)
    save('其它专项衔接.json',dict(changedSinceCheckpoint=checkpoint_differences,addedAuthorityKeys=sorted(added),
        existingAuthorityFieldsUnchanged=True,handling='只读保留新确认；本批不修改共享文件'))
    protected=set(ROOT/p for p in json.loads((OUT.parent/'保护与验证.json').read_text(encoding='utf-8'))['protectedHashes'])
    protected|={ROOT/r['path'] for r in manifest['files']}
    before={p.relative_to(ROOT).as_posix():digest(p) for p in protected}
    (OUT/'开始Git状态.txt').write_bytes(subprocess.check_output(['git','-c','core.quotepath=false','status','--porcelain=v1','-uall'],cwd=ROOT))
    import shape_overview as s
    v=s.get_overview()
    def api(endpoint,**kw):
        with urlopen('http://127.0.0.1:8765/api/shape-overview/'+endpoint+'?'+urlencode(kw),timeout=60) as f:return json.load(f)
    boot=api('bootstrap')
    assert boot['id']==v.id and boot['structureBindings']['version']=='structure-count-bindings-v5'
    definitions={(r['position'],r['key']):r.get('meaning','未定义') for r in v.allocation_keys()}
    def decode(code):return '；'.join(f'{i}/{k}＝{definitions[i,k]}' for i,k in enumerate(code,1))
    rows={cp:v.brief(cp,True) for cp in v.rows if cp not in s.exclusive_intake()}
    codes={c for row in rows.values() for c in row['codes'] if len(c)==4}
    counts={c:len(v.allocation_members(c)) for c in codes}
    big={c:set(v.allocation_members(c)) for c,n in counts.items() if c[0] in 'ac' and n>600}
    cohort=set().union(*big.values())
    groups=[dict(code=c,count=len(cps),gloss=decode(c)) for c,cps in sorted(big.items(),key=lambda x:(-len(x[1]),x[0]))]
    identical=[dict(a=a,b=b,count=len(big[a])) for a,b in itertools.combinations(sorted(big),2) if big[a]==big[b]]
    history={r['cp'] for r in s.read(s.RUN/'历史确认145字逐字核查.json')['records']}
    screening=[]
    for cp in sorted(cohort):
        b=rows[cp];cs=[c for c in b['codes'] if len(c)==4];best=min(cs,key=lambda c:(counts[c],c))
        screening.append(dict(cp=cp,char=chr(cp),primary=b.get('bucket'),codePaths=len(b['codes']),
            firstKeyRoutes=sorted({c[0] for c in b['codes']}),bestCode=best,bestCount=counts[best],
            largeRoutes=[c for c in b['codes'] if c in big],historical145=cp in history,
            oldReviewed=b.get('oldReviewed',False)))
    totals=dict(largeGroups=len(big),uniqueLargeCandidateSets=len({frozenset(x) for x in big.values()}),
        candidateOccurrences=sum(map(len,big.values())),uniqueCharacters=len(cohort),
        bestAtMost60=sum(r['bestCount']<=60 for r in screening),
        best61To180=sum(60<r['bestCount']<=180 for r in screening),
        best181To600=sum(180<r['bestCount']<=600 for r in screening),
        bestOver600=sum(r['bestCount']>600 for r in screening),
        noPersonalFrequencyCorpus=True)
    save('大组筛选统计.json',dict(totals=totals,groups=groups,identicalGroups=identical,characters=screening))
    # Deliberate small sample: two genuine weak cases, three reusable existing-route
    # comparisons, and one correct-bucket control; settled E/F remain controls only.
    plans={
        '1':dict(kind='优先对象复核',baseline='chmw',choice=None,
            reason='当前唯一c/h路的分叉证据verified=false、dominantSubject=false；不能用疑似顶部交点替代清楚主形。最小四码仍523。',
            next='先核对锁定字形的顶部/底部墨迹及是否存在真实三叉；尚无足够依据迁桶或派新码。'),
        '7':dict(kind='优先对象复核',baseline='ajvc',choice='cxeg',
            reason='a/j钩形原型verified=false；跨a/c的12码全在大组，事后最小仍644。改主归属本身不变更任何候选。',
            next='先判锁定字形是否含中横及真实交叉、是否存在钩尾；不从字符名称或其它字体推断。'),
        'T':dict(kind='已有路比较',baseline='chmw',choice='chjb',
            reason='当前首选523；已有整字2直连续笔路161。保留c/h，不以记住新桶作为代价。',
            next='比较上方三叉位置与整字2直连续笔哪个更自然；不自动改首选。'),
        'Y':dict(kind='已有路比较',baseline='chmo',choice='chjt',
            reason='当前首选中心三叉199；已有整字3直连续笔路114。已有分叉主体证据通过，桶不是当前主要疑点。',
            next='比较中心交点与3直连续笔的学习成本；不自动改首选。'),
        'r':dict(kind='跨桶现有路比较',baseline='chmj',choice='aamj',
            reason='同一左上交点，现c/h路220、既有a/a路76；后两位mj保持。c/h分叉主形证据已通过，不能仅因a路较小就判c桶错误。',
            next='比较分叉主体与角折主体的直观性；只展示现有备选，不迁主归属、不新增别名。'),
        'I':dict(kind='正确桶保护对照',baseline='alli',choice='allc',
            reason='a/l单直主体直观；单线纵向896、尺寸中156、整字1直165。问题在属性辨识度，迁桶将破坏第一位纵长线义。',
            next='保留a；比较单线尺寸码是否比1直计数更自然。尺寸依赖固定字体，不推广通用阈值。'),
        '|':dict(kind='相似字保护对照',baseline='alli',choice='alev',
            reason='同为a/l，使用同码大候选不说明桶错误；本字已有尺寸相关76候选。只作I的大小/字形对照。',
            next='不改变键义或分桶，保留相似字允许同码。'),
        'E':dict(kind='已完成控制',baseline='chzt',choice='chzt',reason='已接入3横笔组查法17候选；不重复审核既有决定。',next='保持当前首选。'),
        'F':dict(kind='已完成控制',baseline='chzb',choice='chzb',reason='已接入2横笔组查法17候选；更小11不自动成为更自然首选。',next='保持当前首选。')}
    records=[];routechecks=0
    for ch,plan in plans.items():
        cp=ord(ch);b=rows[cp];d=v.detail(cp,True)
        paths=[]
        for p in d['paths']:
            c=p['code'];n=len(v.allocation_members(c))
            assert api('query',allocation=1,prefix=c)['total']==n
            assert api('query',allocation=1,prefix=c,text='U+'+format(cp,'X'))['total']==1
            if len(c)==4:assert api('query',allocation=1,prefix=c[1:]+c[0],order='back')['total']==n
            paths.append(dict(code=c,count=n,gloss=decode(c),preferred=p.get('preferred',False),
                evidence=p.get('evidence',[]),compatibilityOnly=p.get('compatibilityOnly',False)))
            routechecks+=1
        rec=dict(char=ch,cp=cp,bucket=b.get('bucket'),family=b.get('familyKey'),
            historical145=cp in history,oldReviewed=b.get('oldReviewed',False),plan=plan,
            baselineCount=counts[plan['baseline']],choiceCount=counts[plan['choice']] if plan['choice'] else None,
            codePathsBefore=len(b['codes']),codePathsAfter=len(b['codes']),
            coverageDelta=0,aliasesAdded=0,runtimeChanged=False,
            preferredBefore=b['preferredCodes'],preferredAfter=b['preferredCodes'],
            paths=paths,objects=d.get('objects',[]),routes=d['familyRoutes'],preview=b['preview'])
        records.append(rec)
    assert not {961,7897}&{r['cp'] for r in records}
    assert not set(s.exclusive_intake())&{r['cp'] for r in records}
    save('小批代表字证据与比较.json',records)
    # Existing locked glyph crops only; no redraw, fallback font or name-based shapes.
    contact=Image.new('RGB',(9*110,150),'#f7f7f4');draw=ImageDraw.Draw(contact)
    cards=[]
    for i,r in enumerate(records):
        p=r['preview']
        with Image.open(ROOT/'原型/键位编辑器'/p['url']) as sheet:
            crop=sheet.crop((p['x'],p['y'],p['x']+64,p['y']+64)).convert('RGB')
        contact.paste(crop,(i*110+20,40));draw.text((i*110+12,10),'U+'+format(r['cp'],'04X'),fill='black')
        buf=io.BytesIO();crop.save(buf,format='PNG');rimage=base64.b64encode(buf.getvalue()).decode()
        cards.append((r,rimage))
    contact.save(OUT/'九字锁定原图.png')
    lines=['# a/c大负担组：小批代表字筛选','',
        '已完成只读筛选与现有路径比较。没有新增码、迁桶、改首选或人工确认。ρ、ộ不在本批；E/F只作已完成控制，不重审。','',
        '## 筛选口径','',
        '从现行a/c中四码候选>600的30组取字符并集，再按每字全部现有完整码的事后最小人数区分负担。多组重叠、相同候选集合不重复当覆盖。随后选常见字作解释样本，不称个人频率实测或随机总体样本。','',
        '`'+json.dumps(totals,ensure_ascii=False)+'`','',
        '相同候选集合组对：`'+json.dumps(identical,ensure_ascii=False)+'`。g正置与i纵向在这些字上可落相同集合，不能把这类备选码当独立分桶收益；本批不删除旧路。','',
        '## 六字主批及三个控制','',
        '|字|处理类型|比较前入口/候选|现有备选/候选|路数前→后|判断|',
        '|---|---|---|---|---|---|']
    for r in records:
        p=r['plan'];choice=p['choice']+'/'+str(r['choiceCount']) if p['choice'] else '无可直接采用的新路'
        lines.append(f"|{r['char']}|{p['kind']}|{p['baseline']}/{r['baselineCount']}|{choice}|{r['codePathsBefore']}→{r['codePathsAfter']}|{p['reason']}|")
    lines+=['','比较前入口不全部等于现首选：T/Y用当前首选；r用现主桶内相同特征mj；I用拥挤的单线纵向；7用a桶常见比例路。不能把这些比较写成全库自动优化收益。','',
        '所有比较覆盖变化0、备选路增加0、原首选改变0；“选择已有更小码”是使用建议，不是码表人数下降。T/Y需记整字连续笔计数，r需辨c分叉与a角折，I需记同族尺寸。人类自然选键未测。','',
        '## 优先级及具体对象','',
        '1. 先1、7：候选确实拥挤，并且主要形族证据不足。1的c/h分叉visible-fork-scale-check未通过；7的a/j钩形原型未通过，c/x交叉又缺少本批逐字核验。先看原墨迹和对象，再生成迁桶/新增码候选，不能直接搬字。',
        '2. T、Y、r：已有更小可达路，先做自然选键比较。T/Y的c分叉证据通过；r在c/a均已有路，主归属与最小码不同不必强制统一。',
        '3. I及|：保持a/l作保护对照，说明纵长线桶正确也可能有大候选。E/F保持已确认笔组路，不重复审议。','',
        '## 逐码键义与对象依据','']
    for r in records:
        lines+=['### '+r['char']+' U+'+format(r['cp'],'04X'),'',r['plan']['next'],'',
            '当前主桶/形族：'+str(r['bucket'])+'/'+str(r['family'])+'。历史145身份：'+str(r['historical145'])+'；oldReviewed：'+str(r['oldReviewed'])+'。这些标志不代表其它一般规则从未接受。','',
            '|规范码|人数|逐位键义|','|---|---:|---|']
        for p in r['paths']:lines.append(f"|{p['code']}|{p['count']}|{p['gloss']}|")
    lines+=['','## 确认与后续边界','',
        '本轮只完成筛选，不将AI读图或machine-proposal写成人工答复。需要人的判断限定为锁定字体的1/7形族边界，另三字是自然选键实验；没有ρ/ộ重审题，也没有全局均分提案。',
        '若以后提出新入口，须先固定1/7对象、字体与参照，复用既有检测证据，再比较原码/候选/覆盖/路径/学习成本与历史影响；保持后三位键义、旧确认与t/b排他。仅调主归属不改变查询人数，不能冒称解决523/644的大候选。',
        '本批未切换运行、重启服务、重跑39项或全部旧浏览器回归；只读路径回放及保护哈希检查见验证.json。']
    (OUT/'a-c小批筛选与比较.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    esc=lambda x:html.escape(str(x))
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>a/c小批筛选</title><style>body{font:16px/1.7 system-ui;max-width:1000px;margin:24px auto;padding:0 18px;background:#f8f7f3;color:#20313a}article{background:white;padding:20px;margin:18px 0;border:1px solid #ddd;border-radius:8px}img{width:128px;height:128px}table{border-collapse:collapse;width:100%}td,th{padding:6px;border-bottom:1px solid #ddd;text-align:left}small{color:#52626c}details{margin:12px 0}.scroll{overflow:auto}</style><h1>a/c大负担组：六字主批</h1><p>只读筛选，未迁桶、未改码或首选。ρ、ộ不重审；E/F仅为已完成控制。图像直接裁取原锁定字体，不按系统字体替换。</p>']
    parts+=['<p>'+esc(json.dumps(totals,ensure_ascii=False))+'</p>']
    for r,img in cards:
        p=r['plan'];parts+=['<article><h2>'+esc(r['char'])+' · U+'+format(r['cp'],'04X')+' · '+esc(p['kind'])+'</h2><img alt="锁定原字形" src="data:image/png;base64,'+img+'"><p>'+esc(p['reason'])+'</p><p>'+esc(p['next'])+'</p>',
            '<p>比较：'+esc(p['baseline'])+' / '+str(r['baselineCount'])+' → '+esc((p['choice']+' / '+str(r['choiceCount'])) if p['choice'] else '尚无可靠新路')+'。路径 '+str(r['codePathsBefore'])+'→'+str(r['codePathsAfter'])+'，覆盖增加0，原首选保留。</p>',
            '<details><summary>全部规范码、逐位键义与候选</summary>']
        for code in r['paths']:parts+=['<p><b>'+esc(code['code'])+'</b> / '+str(code['count'])+'候选<br><small>'+esc(code['gloss'])+'</small></p>']
        parts+=['</details><details><summary>原对象与形族证据</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+esc(json.dumps(r['routes'],ensure_ascii=False,indent=2))+'</pre></details></article>']
    parts+=['<p>本页没有答复保存或提交接口；不是人工确认来源。候选人数不等于自然选键成绩。</p></html>']
    (OUT/'a-c小批原字形与比较.html').write_text(''.join(parts),encoding='utf-8')
    after={p.relative_to(ROOT).as_posix():digest(p) for p in protected}
    assert before==after,'既有文件发生变化，停止认定只读验收'
    save('验证.json',dict(passed=True,protectedCount=len(before),protectedHashes=before,
        previousCheckpointFiles=len(manifest['files']),representatives=len(records),routeChecks=routechecks,
        currentVersion='structure-count-bindings-v5',runtimeChanged=False,manualChanged=False,
        fullCodeCounts=counts,naturalSelectionTest=False,old39TestsRerun=False))
    print(json.dumps(dict(totals=totals,representatives=len(records),routeChecks=routechecks,output=str(OUT)),ensure_ascii=False))


if __name__=='__main__':main()
