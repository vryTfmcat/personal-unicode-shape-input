"""Read-only first-bucket census and isolated, explicitly unaccepted alternatives.

No runtime, authority, entity, Git-index, or public-page writes. Output must be new.
"""
import argparse
import hashlib
import itertools
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'原型/键位编辑器'), str(ROOT/'工具')]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def distribution(values):
    a = sorted(values)
    if not a:
        return dict(n=0)
    return dict(n=len(a), min=a[0], median=a[(len(a)-1)//2],
                p90=a[math.ceil(len(a)*.9)-1], max=a[-1],
                mean=round(sum(a)/len(a), 3),
                histogram=dict(Counter('1' if n==1 else '2-10' if n<=10 else
                    '11-60' if n<=60 else '61-180' if n<=180 else '181-600' if n<=600 else '>600' for n in a)))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',required=True)
    args=ap.parse_args();out=Path(args.output_dir)
    manual=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8-sig'))
    if manual.get('firstBucketPrimaryAcceptance20261025',{}).get('decision')=='accepted':
        raise SystemExit('本批已确认，统计与候选为冻结的确认前证据；禁止从确认后运行版重造原基线')
    if out.exists():
        raise SystemExit('拒绝覆盖已有统计/候选目录')
    out.mkdir(parents=True)
    status=subprocess.check_output(['git','-c','core.quotepath=false','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT)
    (out/'开始Git状态.txt').write_bytes(status)
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    protected={p for p in (ROOT/t for t in tracked if t) if p.is_file()}
    protected |= set((ROOT/'原型/键位编辑器').glob('*.py'))
    protected |= set((ROOT/'原型/键位编辑器/data').glob('*.json'))
    protected |= set((ROOT/'原型/键位编辑器').glob('*.js'))
    protected |= set((ROOT/'原型/键位编辑器').glob('*.html'))
    protected.add(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    reads=set()
    def hook(event,values):
        if event=='open' and isinstance(values[0],(str,bytes)):
            try:
                p=Path(values[0]).resolve()
                if p.is_relative_to(ROOT) and p.is_file() and not p.is_relative_to(out.resolve()):
                    reads.add(p)
            except (ValueError,OSError,TypeError):
                pass
    sys.addaudithook(hook)
    import shape_overview as s
    v=s.get_overview()
    def api(endpoint,**params):
        with urlopen('http://127.0.0.1:8765/api/shape-overview/'+endpoint+'?'+urlencode(params),timeout=60) as r:
            return json.load(r)
    boot=api('bootstrap');write(out/'运行API快照.json',boot)
    assert boot['id']==v.id
    assert boot['structureBindings']['version']==s.structure.data()['version']
    keys={r['key']:r for r in v.allocation_keys() if r['position']==1}
    intake=s.exclusive_intake()
    universe=set(v.rows)|set(intake)
    rows={cp:v.brief(cp,True) for cp in universe}
    members={k:set(v.allocation_members(k)) for k in s.LETTERS}
    # Primary is the stored brief.bucket, not candidate-layer primary and not preferred code.
    owners=defaultdict(set)
    for cp,r in rows.items(): owners[r.get('bucket')].add(cp)
    geometric=set(v.rows)-set(intake)
    allcodes={c for cp in geometric for c in rows[cp]['codes']}
    four={c:set(v.allocation_members(c)) for c in allcodes if len(c)==4}
    histories=s.read(s.RUN/'历史确认145字逐字核查.json')['records']
    historical={r['cp'] for r in histories}
    history=[]
    for cp in sorted(historical):
        r=rows[cp];cs=r['codes'];ns=[len(four[c]) for c in cs if c in four]
        history.append(dict(cp=cp,char=chr(cp),oldBucket=v.rows[cp]['oldBucket'],
            bucket=r.get('bucket'),codes=cs,codeRoutes=len(cs),bucketRoutes=sorted({c[0] for c in cs}),
            intake=cp in intake,bestFull=min(ns) if ns else None,
            status='t/b收入' if cp in intake else '几何有路' if cs else '历史缺口'))
    stats=[]
    for k in s.LETTERS:
        owned=owners[k];queried=members[k];codes=[c for c in four if c[0]==k]
        hc=[r for r in history if r['bucket']==k]
        stat=dict(bucket=k,meaning=keys[k].get('meaning'),primary=len(owned),query=len(queried),
            queryGeometry=len(queried&geometric),queryPrimaryPending=sum(rows[cp].get('bucket') is None for cp in queried if cp in rows),
            primaryOnlyFirst=sum(not rows[cp]['codes'] for cp in owned if cp not in intake),
            queryOnlyFirst=sum(not rows[cp]['codes'] for cp in queried&geometric),
            intakeOnly=sum(cp in intake for cp in owned),
            additionalMembers=len(queried-owned),primaryMissingFromQuery=len(owned-queried),
            primaryWithCodes=sum(bool(rows[cp]['codes']) for cp in owned),
            codePaths=sum(c[0]==k for cp in geometric for c in rows[cp]['codes']),
            fullCodes=distribution([len(four[c]) for c in codes]),
            topFullCodes=sorted([dict(code=c,count=len(four[c])) for c in codes],key=lambda x:(-x['count'],x['code']))[:8],
            history=dict(primary=len(hc),withCodes=sum(r['status']=='几何有路' for r in hc),
                         missing=sum(r['status']=='历史缺口' for r in hc),intake=sum(r['intake'] for r in hc),
                         bestFull=distribution([r['bestFull'] for r in hc if r['bestFull'] is not None])))
        assert api('query',allocation=1,prefix=k)['total']==len(queried),k
        stats.append(stat)
    overlaps=[]
    # x/y/z are reserve collections, never treat their overlaps as shape alternatives.
    shape_keys=[k for k in s.LETTERS if k not in 'xyz' and members[k]]
    for a,b in itertools.combinations(shape_keys,2):
        common=members[a]&members[b]
        if common: overlaps.append(dict(a=a,b=b,count=len(common),examples=[chr(cp) for cp in sorted(common)[:12]]))
    bucket_paths=Counter(len({c[0] for c in rows[cp]['codes']}) for cp in geometric if rows[cp]['codes'])
    recommendations=[]
    # Compare primary recommendation only. No aliases, no deleted paths, no code rotation copy.
    for ch in 'ρộ':
        cp=ord(ch);r=rows[cp];d=v.detail(cp,True)
        relevant=[p for p in d['paths'] if p['code'].startswith('io')]
        recommendations.append(dict(char=ch,cp=cp,status='待人确认；独立主归属建议，未集成',
            beforeBucket=r['bucket'],afterBucket='i',beforeFamily=r['familyKey'],afterFamily='o',
            subject='圆主体；整字旧入口保留',beforeCodes=r['codes'],afterCodes=r['codes'],
            beforePreferred=r['preferredCodes'],afterPreferred=r['preferredCodes'],
            codePathsBefore=len(r['codes']),codePathsAfter=len(r['codes']),
            queryBucketsBefore=sorted({c[0] for c in r['codes']}),queryBucketsAfter=sorted({c[0] for c in r['codes']}),
            candidatesChanged=0,coverageAdded=0,aliasesAdded=0,
            objectRoutes=[{k:x.get(k) for k in ('bucket','familyKey','target','compatibilityOnly')} for x in d['familyRoutes']],
            circleChoices=[dict(code=p['code'],count=len(v.allocation_members(p['code']))) for p in relevant],
            learningCost='推荐先想圆主体i；仍保留e整字旧路，须区分主归属与旧首选；自然选键未测',
            historical145=cp in historical,intake=cp in intake,
            acceptedEvidence='p首批圆主体决定；ộ另有subjectBucket=i绑定。主归属切换本身尚未确认'))
    # Deliberate rejected counterfactual: keep BCD and copy alternatives under primary A.
    # Quantify why a scope-unified first key is not a safe generic operation.
    aliases=defaultdict(set);aliascases=[]
    for ch in 'Dρộ':
        cp=ord(ch);target='i';old=rows[cp]['codes'];new=sorted({target+c[1:] for c in old if c[0]!=target}-set(old))
        for code in new: aliases[code].add(cp)
        aliascases.append(dict(char=ch,addedCodes=new,pathsBefore=len(old),pathsAfter=len(old)+len(new),
            coverageAdded=0,learningCost='要额外记同一BCD跨桶别名，且桶描述对象与形族对象可能冲突',
            status='反事实压力测试；语义未通过，拒绝集成'))
    aliasdiff=[dict(code=c,before=len(v.allocation_members(c)),after=len(set(v.allocation_members(c))|cps),
                    addedCPs=sorted(cps)) for c,cps in sorted(aliases.items())]
    reps=[]
    for ch in 'OQo○Dρộ8ᛒȣ𞥕EF∥=*☆⁂ḌḐ':
        cp=ord(ch);r=rows[cp];d=v.detail(cp,True);paths=[]
        for p in d['paths']:
            c=p['code'];n=len(v.allocation_members(c))
            # Online parity for every representative path, including legacy 3-code paths.
            assert api('query',allocation=1,prefix=c,text='U+'+format(cp,'X'))['total']==1,(ch,c)
            assert api('query',allocation=1,prefix=c)['total']==n,(ch,c)
            back=c[1:]+c[0]
            mode='short3' if len(c)==3 else 'full4'
            if len(c)==4:
                assert api('query',allocation=1,prefix=back,order='back')['total']==n
            paths.append(dict(code=c,back=back,count=n,preferred=p.get('preferred',False),
                compatibilityOnly=p.get('compatibilityOnly',False),evidence=p.get('evidence',[])))
        cs=[p for p in paths if len(p['code'])==4]
        best=min(cs,key=lambda p:p['count']) if cs else None
        reps.append(dict(cp=cp,char=ch,bucket=r.get('bucket'),family=r.get('familyKey'),
            frequencyStatus='常见/历史反馈代表样本；没有个人输入频率语料，不能称为实测高频',
            paths=paths,codePaths=len(paths),bucketRoutes=sorted({p['code'][0] for p in paths}),
            bestFull=best,minimumPages=math.ceil(best['count']/60) if best else None,
            routes=[{k:x.get(k) for k in ('bucket','familyKey','target','compatibilityOnly')} for x in d['familyRoutes']],
            preview=r.get('preview'),objects=d.get('objects',[])))
    total=dict(version=s.structure.data()['version'],universe=len(universe),geometry=len(geometric),
        primaryPending=len(owners[None]),primaryPendingWithCodes=sum(bool(rows[cp]['codes']) for cp in owners[None]),
        unclassified=len(v.unclassified),unclassifiedOverlap=len(set(v.unclassified)&universe),
        geometryWithCodes=sum(bool(rows[cp]['codes']) for cp in geometric),
        geometryOnlyFirst=sum(not rows[cp]['codes'] for cp in geometric),paths=sum(len(rows[cp]['codes']) for cp in geometric),
        actualFullCodes=len(four),fullCodeCandidates=distribution(map(len,four.values())),
        bucketRouteHistogram=dict(sorted(bucket_paths.items())),
        multiBucketCharacters=sum(n for k,n in bucket_paths.items() if k>1),
        historical=Counter(r['status'] for r in history),
        intake=Counter(r['firstKey'] for r in intake.values()),
        provisional=sum(r.get('provisional',False) for r in intake.values()))
    assert sum(len(cps) for cps in owners.values())==len(universe)
    assert all(not (set(intake)&cps) for cps in four.values())
    assert set(intake)==members['t']|members['b']
    assert len(intake)==4362 and total['provisional']==140
    write(out/'统计.json',dict(method='主归属取现行brief.bucket；非layer=primary/非首选。所有人数按码位去重；x/y/z单列保留集合。',
        total=total,buckets=stats,overlaps=sorted(overlaps,key=lambda r:-r['count']),history=history,
        primaryPendingCPs=sorted(owners[None]),unclassifiedCPs=v.unclassified,
        ownership={str(cp):dict(bucket=r.get('bucket'),codeRoutes=len(r['codes']),queryBuckets=sorted({c[0] for c in r['codes']})) for cp,r in rows.items()}))
    write(out/'完整码候选分布.json',[dict(code=c,count=len(cps)) for c,cps in sorted(four.items())])
    write(out/'代表字与对象证据.json',reps)
    write(out/'候选差异.json',dict(status='未接受、未集成；只读候选材料',primaryRecommendation=recommendations,
        acceptedScenario='无新规则确认，运行保持原样',rejectedAliasScenario=aliascases,aliasCodeDifferences=aliasdiff,
        primaryDelta={'e':-2,'i':2},queryDelta=0,coverageDelta=0,pathsDelta=0,
        manualSource='数据/三模式/规则库/四键实验/人工审议.json；不复制成第二确认库'))
    # Read dependencies are recorded separately from explicit start/end protected inputs.
    readhash={str(p.relative_to(ROOT)):sha(p) for p in sorted(reads)}
    after={str(p.relative_to(ROOT)):sha(p) for p in protected}
    assert before==after,'受保护文件发生外部或本轮变化，停止认定验收'
    write(out/'保护与验证.json',dict(passed=True,protectedCount=len(before),protectedHashes=before,
        inputHashes=readhash,apiPort=8765,apiVersion=boot['id'],
        checks=['26桶线上/离线人数一致','所有代表路径线上可达及候选数一致','代表完整码前后置人数相同',
                '主归属守恒','t/b4362排他及140暂收入','原码/首选/人工审议/公共源码保护哈希一致'],
        limits=['未做人类自然选键或频率测试','未变更运行版','未重跑历史3项固定源码守卫','本轮不重做全部实验或Rime部署验收']))
    lines=['# 第一位分桶统计与独立候选（2026-10-25）','',
        '状态：统计已执行；候选未接受、未集成。原分桶、后三位键义、原查法及首选不变。','',
        '主工作位置为既有项目；源码、全量逐字统计和证据在库外现有v5目录。','',
        '## 统计口径','',
        '主归属取当前brief.bucket，每字仅一次。这是现存字段，不表示全体主对象已由人复核；layer=primary是证据层而非归属。查询人数按allocation_members去重，含局部与兼容路。x/y/z是保留集合，不能拿来与几何桶均分；t/b收入身份不是第一位待定或待补几何细码。','',
        '第一位待定与原unclassified分别统计，不合并；仅第一位指几何字codes为空，已有实际三码也算有路。候选分布按真实四码键逐码统计，非把备选路径数当新增字符。','',
        '总体：`'+json.dumps(total,ensure_ascii=False)+'`','',
        '|桶|键义|主归属|含备选查询|主归属仅第一位|四码组数|中位/p90/最大|历史缺口|',
        '|---|---|---:|---:|---:|---:|---|---:|']
    for r in stats:
        f=r['fullCodes'];nums='/'.join(str(f[k]) for k in ['median','p90','max']) if f['n'] else '—'
        lines.append(f"|{r['bucket']}|{r['meaning']}|{r['primary']}|{r['query']}|{r['primaryOnlyFirst']}|{f['n']}|{nums}|{r['history']['missing']}|")
    lines+=['','## 跨桶重叠（几何桶，前12对）','',
        '|桶对|同字重叠|例字|','|---|---:|---|']
    for r in sorted(overlaps,key=lambda r:-r['count'])[:12]:lines.append(f"|{r['a']}/{r['b']}|{r['count']}|{''.join(r['examples'])}|")
    lines+=['','## 代表字负担','',
        '没有个人频率语料；下列是常见符号、拉丁字及已反馈字，不能据此给出全库频率加权结论。页数为60字/页的候选总页数，不是用户实际翻页次数；最小码是事后最优，不代表自然选键。','',
        '|字|主桶|可用桶|规范码路数|最佳四码/人数|至少总页数|','|---|---|---|---:|---|---:|']
    for r in reps:
        b=r['bestFull'];lines.append(f"|{r['char']}|{r['bucket']}|{','.join(r['bucketRoutes'])}|{r['codePaths']}|{b['code']+'/'+str(b['count']) if b else '仅有码内短码'}|{r['minimumPages'] or '—'}|")
    lines+=['','## 独立候选及决定','',
        '推荐比较ρ、ộ的“主归属指向圆主体i”，保留e旧路与全部首选。差异只有2个主归属建议：e−2/i+2；字符覆盖、候选集合、路径数和首选均不变。它改善对象提示一致性，不能宣称降低重码。ρ当前familyKey=p、ộfamilyKey=o却仍bucket=e，说明现存主字段与已接受圆主体参照并非总一致。主归属切换尚无确认，不能替用户选择整字或主体优先。','',
        '对照压力测试把D/ρ/ộ的其它桶BCD原样复制到i，逐码人数和新增别名见候选差异.json。该方案拒绝：D的a描述实际竖干（线与转折·纵长），f描述去干右半弧（开放曲线·纵长），i描述整字闭孔复合；统一到i会让局部线/弧路径与第一位闭环键义冲突，并增加记忆路数。后三位保持字母并不保证对象语义仍一致。','',
        'D当前主桶i/形族k符合已有整字确认；alla只是a/l局部路径，不能称D整字应归a。旧io路径已标兼容。Q以真实圆主体取i/o，尾笔属于附件；O整字与主体范围相同；ộ圆主体i与旧整字e并存。禁止把这些参照混成“每字所有路径只能用一个A”。','',
        'O/○/o可用相同ioqu，q为整字曲连续笔集、u为1；同为iose时末位是填充。把O强迁小桶不会修复大小/填充轴冗余；本专项保留这些后三位规则。Ḍ/Ḑ继承圆族路径的问题是第二位/主体语义，不能靠第一位均分解决，交后三位与对象专项。','',
        '## 待确认的两项具体判断','',
        '1. ρ：推荐先看上部闭合圆主体，主归属提示从e/p改为i/o；是否接受？下伸笔、整字旧e路全部保留，不新增主体计数码。','',
        '2. ộ：推荐先看圆主体i/o，主归属提示从e改i；是否接受？原首选epki与旧e路不变，已接入iots/ioyw不变。','',
        '这两项只确认推荐对象与主归属，不接受其它同形字迁桶，不确认几何计数；D及O/Q是保护对照，无须重复确认已有决定。','',
        '## 集成和恢复条件','',
        '无新人工答复时仅集成统计报告与项目索引，运行版不切换。收到明确答复后，在唯一人工审议追加逐字主归属决定，保留原话与旧记录；以本次输入SHA为基线重生成隔离差异，重新检查其它专项改动；保护路径/首选/t-b/历史与双顺序后，再按既有完整恢复包+新增量流程集成。独立目录禁止回读原树验收后才称可恢复，不覆盖旧包。','',
        '未完成：两字主归属确认和运行集成、人类自然选键/频率测试、2083范围和历史84字补路、t/b来源衔接、公开白名单及独立介质备份。后几项沿用现有任务，不新增系统。']
    (out/'第一位分桶统计与候选.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(total=total,output=str(out),protectedUnchanged=True),ensure_ascii=False))


if __name__=='__main__':main()
