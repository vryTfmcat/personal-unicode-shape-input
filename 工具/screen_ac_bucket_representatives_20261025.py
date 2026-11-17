"""Screen six a/c workload representatives; read-only, no family or bucket migration."""
import base64
import hashlib
import html
import io
import json
import math
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from PIL import Image

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'原型/键位编辑器'),str(ROOT/'工具')]
BASE=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5'
OLD=BASE/'第一位分桶专项-20261025'
OUT=BASE/'a-c大候选组代表字首筛-20261025'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dist(ns):
    a=sorted(ns)
    return dict(n=len(a),min=a[0],median=a[(len(a)-1)//2],p90=a[math.ceil(len(a)*.9)-1],max=a[-1]) if a else dict(n=0)


def main():
    if (OUT/'首筛结果.json').exists():raise SystemExit('拒绝覆盖已有首筛结果')
    OUT.mkdir(exist_ok=True)
    old=json.loads((OLD/'保护与验证.json').read_text(encoding='utf-8'))
    protected={ROOT/p for p in old['protectedHashes']}
    protected|=set((ROOT/'原型/键位编辑器').glob('*.py'))
    protected.add(ROOT/'工具/verify_shape_release.py')
    protected.add(ROOT/'工具/test_first_bucket_primary.py')
    before={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    (OUT/'开始Git状态.txt').write_bytes(subprocess.check_output(['git','-c','core.quotepath=false','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT))
    previous=json.loads((ROOT.parent/'archive/2026-10-25-第一位分桶首批确认/主归属恢复清单.json').read_text(encoding='utf-8'))
    externalChanges=[r['path'] for r in previous['files'] if sha(ROOT/r['path'])!=r['sha256']]
    assert set(externalChanges)<= {'数据/三模式/规则库/四键实验/人工审议.json'}, '上轮运行源码已有外部修改，须重审'
    currentManual=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    oldManual=json.loads((Path(previous['restored'])/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    assert all(currentManual.get(k)==value for k,value in oldManual.items()), '既有人工字段已变化'
    addedManualKeys=sorted(set(currentManual)-set(oldManual))
    assert set(addedManualKeys)<={'pathRecommendationAcceptance20261025Batch1','roundSubjectBrowseExclusionAcceptance20261025Batch1'}
    import shape_overview as s
    v=s.get_overview()
    def api(endpoint,**params):
        with urlopen('http://127.0.0.1:8765/api/shape-overview/'+endpoint+'?'+urlencode(params),timeout=60) as r:return json.load(r)
    boot=api('bootstrap')
    definitions={(r['position'],r['key']):r for r in v.allocation_keys()}
    def decode(code):
        return [dict(position=n,key=k,meaning=definitions[n,k].get('meaning','未定义')) for n,k in enumerate(code,1)]
    cached={}
    def count(code):
        if code not in cached:cached[code]=len(v.allocation_members(code))
        return cached[code]
    full=json.loads((OLD/'完整码候选分布.json').read_text(encoding='utf-8'))
    for r in full:assert count(r['code'])==r['count'],r
    large=[r for r in full if r['code'][0] in 'ac' and r['count']>600]
    union=set().union(*(set(v.allocation_members(r['code'])) for r in large))
    intake=s.exclusive_intake();assert not union&set(intake)
    scope=[]
    for cp in sorted(union):
        row=v.brief(cp,True);codes=row['codes'];f=[c for c in codes if len(c)==4]
        best=min(f,key=lambda c:(count(c),c)) if f else None
        scope.append(dict(cp=cp,char=chr(cp),bucket=row['bucket'],family=row['familyKey'],
            codeRoutes=len(codes),queryBuckets=sorted({c[0] for c in codes}),
            bestFull=best,bestCount=count(best) if best else None,
            preferred=[dict(code=c,count=count(c)) for c in row['preferredCodes']],
            affectedLargeCodes=[r['code'] for r in large if r['code'] in codes]))
    summary=dict(groups=len(large),groupsA=sum(r['code'][0]=='a' for r in large),groupsC=sum(r['code'][0]=='c' for r in large),
        memberships=sum(r['count'] for r in large),uniqueCharacters=len(union),
        bestAcrossExistingFullCodes=dist(r['bestCount'] for r in scope if r['bestCount'] is not None),
        bestAtMost60=sum(r['bestCount'] is not None and r['bestCount']<=60 for r in scope),
        bestAtMost180=sum(r['bestCount'] is not None and r['bestCount']<=180 for r in scope),
        bestAbove600=sum(r['bestCount'] is not None and r['bestCount']>600 for r in scope),
        mainOutsideAC=sum(r['bucket'] not in ('a','c') for r in scope),
        noMeasuredFrequency=True)
    historical={r['cp'] for r in s.read(s.RUN/'历史确认145字逐字核查.json')['records']}
    notes={
      '7':('优先1：真实高负担与形族证据问题','主归属a的纵长线/转折可能仍合适；旧j钩弯原型未通过，备选c/x交叉也须核原图。只改第一位不能纠正第二位。','先核整字轮廓与顶端折角，暂不迁桶/造新码；保留全部12路。'),
      '1':('优先1：真实高负担与假分叉问题','锁定原图上端斜肩与竖干组成一次转折，未见T/Y那样的三臂；现h可见分叉验证为空。c→a同时保留h会继续表达未证实的分叉，不能直接派ah码。','先核斜肩/竖干是单个角折还是其它对象；待第二位边界有结论后才试a桶候选，不动旧7路。'),
      'T':('优先2：既有查法可减轻负担','整字分叉证据通过，c/h仍直观。原首选chmw523，已有整字直连续笔chjb161；不是需要均分迁桶的证据。','在独立试查中比较顶部交点与2直笔，原首选保留。'),
      'Y':('优先2：既有查法可减轻负担','整字分叉证据通过，c/h仍直观。原首选chmo199，已有整字3直连续笔chjt114。','比较中心交点与3直笔是否自然，保留c桶和原首选。'),
      'J':('保护对照：大组内已有可用小入口','a/j钩弯证据通过，已有ajqu70且属于原ajqu确认组，不重复审核、不调整a桶或该组。','仅用作“同在千人大组，但已有70候选入口”的保护对照。'),
      'I':('保护对照：线形明确且已有较小入口','a/l整字竖线，已有allc156、alju165。大组allg/alli不能代表其最小实际负担。','对照单线尺寸与1直笔的学习成本，不新增别名或改桶。'),
      'E':('已优化对照','c/h分叉证据与横笔组证据已存在，原首选chzt17。','沿用原决定，不另起一轮分叉均分。'),
      'F':('已优化对照','c/h与a/a备选并存，原首选chzb17、现有chzw11。','保留原首选与备选；较小码不自动替代推荐。')}
    reps=[];checks=0
    for ch in '71TYJIEF':
        cp=ord(ch);r=v.brief(cp,True);d=v.detail(cp,True);paths=[]
        for p in d['paths']:
            c=p['code'];n=count(c)
            assert api('query',allocation=1,prefix=c)['total']==n
            assert api('query',allocation=1,prefix=c,text='U+'+format(cp,'X'))['total']==1
            if len(c)==4:assert api('query',allocation=1,prefix=c[1:]+c[0],order='back')['total']==n
            checks+=1
            paths.append(dict(code=c,count=n,decode=decode(c),preferred=p.get('preferred',False),
                structuralCollection=p.get('structuralCollection',False),evidence=p.get('evidence',[])))
        best=min((p for p in paths if len(p['code'])==4),key=lambda p:(p['count'],p['code']))
        pref=[p for p in paths if p['preferred']]
        p=r['preview']
        with Image.open(ROOT/'原型/键位编辑器'/p['url']) as sheet:
            crop=sheet.crop((p['x'],p['y'],p['x']+64,p['y']+64));buf=io.BytesIO();crop.save(buf,format='PNG')
        role,issue,action=notes[ch]
        reps.append(dict(cp=cp,char=ch,role=role,issue=issue,nextAction=action,bucket=r['bucket'],family=r['familyKey'],
            preferred=pref,bestFull=best,paths=paths,routeCount=len(paths),bucketRoutes=sorted({p['code'][0] for p in paths}),
            image='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode(),
            familyRoutes=d.get('familyRoutes',[]),objects=d.get('objects',[]),oldReviewed=r.get('oldReviewed'),
            historical145=cp in historical,intake=cp in intake,
            wholeRuleStatus='现有整字集合规则；数值为机器观测，非本人逐字确认',
            comparison=dict(beforePreferredCandidates=min([p['count'] for p in pref]) if pref else None,
                afterExistingBestCandidates=best['count'],codeRoutesBefore=len(paths),codeRoutesAfter=len(paths),
                coverageDelta=0,aliasesDelta=0,bucketChanges=0,
                meaning='只比较已有查询策略，不更改首选/码表；没有首选时不虚构改前基线')))
    assert all(r['cp'] in union for r in reps)
    assert all(not r['historical145'] and not r['intake'] for r in reps)
    # Do not reopen or amend either primary-subject confirmation.
    for cp in (961,7897):assert v.brief(cp,True)['bucket']=='i'
    after={p.relative_to(ROOT).as_posix():sha(p) for p in protected};assert before==after
    report=dict(status='只读首筛；未改码、未迁桶、未重新审核ρ/ộ',
        selectionMethod='先取a/c全部>600候选四码的去重字符并集，计算每字所有现有路的最小实际负担，再选常见且对象可检查的6字；E/F为已有优化的保护对照。没有输入频率语料，不按桶总人数排序迁移。',
        summary=summary,largeGroups=sorted(large,key=lambda r:-r['count']),cohort=scope,
        representatives=reps,representativePathChecks=checks,
        protectedHashes=before,protectedUnchanged=True,externalManualAdditions=addedManualKeys,
        scopeLimits=['不把每字最小码当自然首选','现有整字计数不等于本人逐字确认','不把首筛材料计为覆盖或队列解决','本轮不改runtime、实体、人工审议、部署或Git索引'])
    write('首筛结果.json',report)
    write('保护与验证.json',dict(passed=True,protectedCount=len(before),protectedHashes=before,
        allFullCodeCountsVerified=len(full),representativePathChecks=checks,apiVersion=boot['id'],
        priorPrimaryDeltaSHA=previous['deltaSHA256'],unchangedPrimaryCharacters=[961,7897],externalManualAdditions=addedManualKeys,
        currentVersion=boot['structureBindings']['version'],runtimeWritten=False,
        noFullRebuild=True,tests='本批只读数据/在线候选回放/保护SHA；未重跑39项运行回归'))
    esc=lambda t:html.escape(str(t))
    gloss=lambda c:'；'.join(f"{d['position']}/{d['key']} {d['meaning']}" for d in c['decode'])
    lines=['# a/c大候选组：六字首筛与两字对照','',report['status'],'',report['selectionMethod'],'',
        '## 全部30个大组的范围','',json.dumps(summary,ensure_ascii=False),'',
        'memberships是组内人次之和，不是去重字符覆盖。bestAtMost60与bestAtMost180为包含关系，不能相加。最佳码按所有现有四码取最小，不能当作用户会自然选到的码。','',
        '## 本批顺序','',
        '|字|角色|主桶/形族|现首选人数|已有最小四码/人数|规范码路数|可查桶|','|---|---|---|---|---|---:|---|']
    for r in reps:
        pref=', '.join(p['code']+'/'+str(p['count']) for p in r['preferred']) or '未设，不虚构基线'
        lines.append(f"|{r['char']}|{r['role']}|{r['bucket']}/{r['family']}|{pref}|{r['bestFull']['code']}/{r['bestFull']['count']}|{r['routeCount']}|{','.join(r['bucketRoutes'])}|")
    lines+=['','## 结论','',
        '先看7与1。两字最小入口仍分别644（11页）、523（9页），其主要形族证据也未通过；二者不是“有一个大组但其它路已很好”的情况。7的a桶未必错，问题首先在j/x路径；1的c/h分叉与锁定原图不符，不能简单换A后保留h。','',
        'T/Y保留c/h，优先比较已有码的查找思路：T现首选523对现有161，Y现首选199对现有114。新路数0、覆盖增量0、备选增量0，尚无人类自然选键结果，不自动改首选。','',
        'J/I作为同桶的保护对照：J已有ajqu70，原ajqu组确认继续有效；I有allc156与alju165。E/F原横笔组首选均17，保留已有成果，不重做已通过优化。','',
        '六字与E/F均不在固定历史145字或t/b收入名单；这不等于没有既有规则/对象确认。全部现有码、首选和确认受保护，ρ/ộ完全沿用上一批。','',
        '## 对象与学习成本','']
    for r in reps:
        lines+=['### '+r['char']+'：'+r['role'],'',r['issue'],'',r['nextAction'],'',
            '现有最小码：`'+r['bestFull']['code']+'`，'+gloss(r['bestFull'])+'。',
            '比较是已有路之间的选择，不新增字符覆盖；路数保持'+str(r['routeCount'])+'。','']
    lines+=['## 下一步与人的判断范围','',
        '下一批只处理7、1的实际对象：7是顶横线接弯斜干，还是满足现行j的钩弯主体；1的上斜肩接竖干应按单角折还是其它结构。T/Y为分叉正对照。先形成这两字对象证据和第二位边界差异，再决定是否需要第一位迁移；未经确认不新增a/h之类语义未通过的码。','',
        '本次仅筛选和留证，不要求重复确认ρ/ộ，不批量修改ajqu确认组，也不把AI看图结论写入人工审议。','',
        '验证：4299个四码组人数与上批基线一致；8字全部路径逐码在线可达、前置/后置候选人数一致；受保护文件SHA一致。未重跑39项运行或原四轮UI测试，本轮无运行变更。']
    (OUT/'六字首筛与下一步.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    page=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>a/c 六字首筛</title><style>body{font:16px/1.65 system-ui;max-width:1050px;margin:24px auto;padding:0 16px;background:#f7f6f2;color:#18262f}article{background:white;padding:20px;margin:18px 0;border:1px solid #d8dbd6;border-radius:8px}img{width:96px;height:96px}table{border-collapse:collapse;width:100%}td,th{text-align:left;border-bottom:1px solid #ddd;padding:7px}code{color:#15516a}small{color:#51616b}.scroll{overflow:auto}details{margin:12px 0}</style><h1>a/c：六字首筛与E/F对照</h1><p>'+esc(report['status'])+'</p><p>优先7、1的对象/形族问题；T、Y比较已有查法；J、I保护对照。保留所有原码和首选，不按桶总人数均分。ρ、ộ不再审核。</p><p>'+esc(json.dumps(summary,ensure_ascii=False))+'</p>']
    for r in reps:
        page+=['<article><h2>'+esc(r['char'])+' · U+'+format(r['cp'],'04X')+' · '+esc(r['role'])+'</h2><img src="'+r['image']+'" alt="既有锁定原字形"><p>'+esc(r['issue'])+'</p><p>'+esc(r['nextAction'])+'</p>',
            '<p>主桶/形族 '+esc(r['bucket']+'/'+r['family'])+'；现首选 '+esc(', '.join(p['code']+'/'+str(p['count']) for p in r['preferred']) or '未设')+'；已有最小码 '+esc(r['bestFull']['code'])+' / '+str(r['bestFull']['count'])+'候选。</p>',
            '<small>'+esc(gloss(r['bestFull']))+'</small><details><summary>全部'+str(r['routeCount'])+'路：键义与对象证据</summary>']
        for p in r['paths']:
            page+=['<p><code>'+esc(p['code'])+'</code> / '+str(p['count'])+(' · 原首选' if p['preferred'] else '')+'<br><small>'+esc(gloss(p))+'</small></p>']
        page+=['<pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+esc(json.dumps(r['familyRoutes'],ensure_ascii=False,indent=2))+'</pre></details></article>']
    page+=['<p>这是只读首筛材料，没有确认写入或提交功能。本人自然选键/输入频率未测；机器最小码不是新首选。</p></html>']
    (OUT/'六字首筛审阅.html').write_text(''.join(page),encoding='utf-8')
    print(json.dumps(dict(summary=summary,pathChecks=checks,output=str(OUT),protectedCount=len(before)),ensure_ascii=False))


if __name__=='__main__':main()
