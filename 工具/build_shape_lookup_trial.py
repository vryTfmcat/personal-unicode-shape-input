"""Read-only live retrieval audit and a local-draft human lookup experiment."""
import base64
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/代表字实际查找测试'
BASE = 'http://127.0.0.1:8765'
CASES = [
 ('O','完整圆主体','整字与圆主体范围相同。'),
 ('Q','圆主体与相连尾笔','圆主体与整字范围不同；保留旧查法。'),
 ('ρ','圆主体与连接附件','主体计数已补验，不代表已派主体计数码。'),
 ('ộ','外部点块与外部折线','分别尝试按下方点和上方折线查找；两条路分别记录。'),
 ('D','非圆闭合轮廓','核对当前k与旧o兼容入口的区别。'),
 ('8','双环主体','作为双闭叶的对照。'),
 ('ᛒ','角形双闭叶','形态已接受；局部连接区修正尚未全局接入。'),
 ('ȣ','回绕与连接区','保留p候选；不使用被拒绝的连接区合并。'),
 ('𞥕','回绕形态与整字计数','已有整字计数证据；不按书写笔顺猜计数。'),
 ('*','单个放射交点','观察第二位r与第三位r是否提供额外帮助。'),
 ('☆','星芒轮廓对照','星形外轮廓不自动等于局部五臂交点。'),
 ('⁂','多个放射交点','观察局部交点位置能否帮助缩小候选。'),
]

def api(endpoint, **params):
    with urlopen(BASE+'/api/shape-overview/'+endpoint+'?'+urlencode(params),timeout=60) as r:
        return json.load(r)

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/'原型/键位编辑器/data/structure-count-bindings.json', ROOT/'数据/三模式/规则库/四键实验/人工审议.json']
    before={str(p.relative_to(ROOT)):digest(p) for p in protected}
    boot=api('bootstrap'); records=[]; route_checks=0; totals={}
    for ch,topic,note in CASES:
        d=api('detail',allocation=1,cp=ord(ch)); paths=[]
        for p in d['paths']:
            code=p['code']
            q=api('query',allocation=1,prefix=code,text='U+'+format(ord(ch),'X'))
            assert q['total']==1,(ch,code,'detail/query mismatch')
            route_checks+=1
            n=d['codeCounts'][code]
            if code not in totals: totals[code]=api('query',allocation=1,prefix=code)['total']
            assert totals[code]==n,(ch,code,'candidate total mismatch')
            paths.append(dict(code=code,count=n,preferred=p.get('preferred',False),
                kind='附件新路' if p.get('subjectAttachment') else '整字计数新路' if p.get('structuralCollection') else '既有路径',
                compatibilityOnly=p.get('compatibilityOnly',False),evidence=p.get('evidence',[])))
        preview=d.get('preview'); image=None
        if preview:
            source=ROOT/'原型/键位编辑器'/preview['url']
            with Image.open(source) as sheet:
                crop=sheet.crop((preview['x'],preview['y'],preview['x']+64,preview['y']+64))
                buf=io.BytesIO();crop.save(buf,format='PNG')
                image='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
        old=[p for p in paths if p['kind']=='既有路径' and len(p['code'])==4]
        new=[p for p in paths if p['kind']!='既有路径' and len(p['code'])==4]
        records.append(dict(char=ch,cp=ord(ch),topic=topic,note=note,image=image,
            paths=paths,oldBest=min(old,key=lambda p:p['count']) if old else None,
            newBest=min(new,key=lambda p:p['count']) if new else None,
            preferred=[p for p in paths if p['preferred']],warnings=d.get('warnings',[])))
    after={str(p.relative_to(ROOT)):digest(p) for p in protected};assert before==after
    report=dict(date=datetime.now().astimezone().isoformat(),baseline=boot['structureBindings']['version'],
        humanTestStatus='等待本人实际试查；机器回放不证明自然选键',records=records,
        routeChecks=route_checks,protectedHashes=before,protectedUnchanged=True,
        scopePending=boot['structureBindings']['statistics']['wholeScopePending'],
        historicalMissing=boot['allocationQueueCounts']['historical'])
    (OUT/'代表字查找基线.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    template=Path(__file__).with_name('shape_lookup_trial_template.html').read_text(encoding='utf-8')
    html=template.replace('__DATA__',json.dumps(report,ensure_ascii=False).replace('</','<\\/'))
    (OUT/'代表字试查.html').write_text(html,encoding='utf-8')
    (ROOT/'原型/键位编辑器/shape-lookup-trial.html').write_text(html,encoding='utf-8')
    lines=['# 12字实际查找测试基线','',report['humanTestStatus'],'',
        '只读回放当前工作总览，候选数不是Rime部署候选。所有已列路径均以字符过滤查询验证可达；不据候选人数声称人工使用通过。',
        '', '|字|测试范围|旧四码最少候选|新四码最少候选|','|---|---|---|---|']
    for r in records:
        fmt=lambda p: p['code']+' / '+str(p['count']) if p else '无四位路径'
        lines.append('|'+r['char']+'|'+r['topic']+'|'+fmt(r['oldBest'])+'|'+(fmt(r['newBest']) if r['newBest'] else '本批未接入新路')+'|')
    lines+=['','## 使用方法','',
        '打开试查页，先不展开答案，输入自己想到的1—4位码。点击候选中的目标字，记录到达、总候选和当次耗时；再填写是否自然、偏好和卡点。ộ可分别按点块和折线测试。',
        '计时包含停顿，只作辅助；查看提示后的试查单独标记。页面只保存浏览器草稿，导出或复制结果回对话后再分析，不写人工审议、不自动改首选。',
        '', '## 机器核查发现','',
        '*当前只有qre（822候选）和qrr（312候选）两条三码入口，没有四位路径。它仍可查，不应把“没有第四位”写成无覆盖；本轮不猜补第四位。',
        'ộ新iots有7候选，ioyw有46；旧最小四码epkt有44，旧首选epki有83。因此新点块查法明显缩小候选，上折线查法并不优于旧最小码。',
        'O由旧最小448缩小到新172，仍需要浏览多页。候选缩小不等于查找负担已经解决。',
        '', '## 当前限制与后续','',
        '等待人的试查结果；当前不形成自然选键评分。12字不是总体统计样本，不据此调整全局布局。',
        '之后从1307字主体/局部范围队列筛选少量对象明确的案例；历史84字单独验收。3项旧哈希守卫和独立介质备份仍未完成。']
    (OUT/'代表字查找基线与操作.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(characters=len(records),routes=route_checks,protectedUnchanged=True,output=str(OUT)),ensure_ascii=True))

if __name__=='__main__':build()
