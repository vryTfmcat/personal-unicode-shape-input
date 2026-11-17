"""Render existing read-only census, including original glyph crops and code glosses."""
import base64
import html
import io
import json
import sys
from pathlib import Path
from PIL import Image

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/第一位分桶专项-20261025'


def main():
    read=lambda name:json.loads((OUT/name).read_text(encoding='utf-8'))
    data=read('统计.json');boot=read('运行API快照.json');reps=read('代表字与对象证据.json');candidate=read('候选差异.json')
    definitions={(r['position'],r['key']):r for r in boot['allocationKeys']}
    def decode(code):
        return [dict(position=n,key=k,meaning=definitions[n,k].get('meaning','未定义')) for n,k in enumerate(code,1)]
    def gloss(code):return '；'.join(f"{d['position']}/{d['key']} {d['meaning']}" for d in decode(code))
    def esc(s):return html.escape(str(s))
    decoded={p['code']:decode(p['code']) for r in reps for p in r['paths']}
    for r in candidate['rejectedAliasScenario']:
        for c in r['addedCodes']:decoded[c]=decode(c)
    (OUT/'逐码键义.json').write_text(json.dumps(decoded,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    geom=[r for r in data['buckets'] if r['bucket'] not in 'bgjtuvxyz' and r['primary']]
    global_unclassified=set(data['unclassifiedCPs'])-set(map(int,data['ownership']))
    supplementary=dict(unclassifiedCurrent=len(global_unclassified),
        unclassifiedIntakeOverlap=data['total']['unclassifiedOverlap'],
        primaryPendingVsUnclassifiedOverlap=len(set(data['primaryPendingCPs'])&global_unclassified),
        activeGeometricPrimaryMax=max(geom,key=lambda r:r['primary'])['bucket'],
        activeGeometricPrimaryMin=min(geom,key=lambda r:r['primary'])['bucket'],
        maxMinPrimaryRatio=round(max(r['primary'] for r in geom)/min(r['primary'] for r in geom),3),
        largeGroups=sum(r['fullCodes'].get('histogram',{}).get('>600',0) for r in geom),
        aAndCLargeGroups=sum(r['fullCodes'].get('histogram',{}).get('>600',0) for r in geom if r['bucket'] in 'ac'))
    (OUT/'关键证据补充.json').write_text(json.dumps(supplementary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    extra=['','## 最重要的证据与解释','',
        '1. 常规几何桶主归属最多c=3432、最少o=524，约6.55倍；q主归属3332，查询4383。该差异说明分布不均，不能证明c/q分类错误。u=42、v=1属于小试验入口，x/y/z为保留集合，均不参与这个比例。',
        '2. 4299个真实四码的候选中位数11、p90为118、最大1554。38个超过600候选的四码中，a占13、c占17；q虽查询人数最多，这类组只有2个。第一位桶人数不足以解释完整码负担。',
        '3. f有1102/2055、h有1171/2142主归属字仅第一位（约53.6%/54.7%），属于细码覆盖问题；迁桶本身不会补齐细码。',
        '4. a查询3344而主归属1919，w查询1269而主归属607；两者都明显受到备选路影响。a/c交集953；4387个有路字符跨桶，不能把查询人数之和当字符总量。',
        '5. 主归属待定392=已有路93+无路299；旧unclassified为5220，其中1997已收入t/b，现行全局未分类3223。392与3223是不同来源队列且本次交集0，不能互相替代或重复称全部缺口。',
        '6. 历史145字守恒51有几何路+10收入t/b+84缺口。84按主归属集中在h16、d/o各14、k13等，c/q均为0。优先处理历史缺口与优先减轻最大桶也不是同一目标。',
        '7. 独立别名压力测试：D 11→17路、ρ 12→18路、ộ 9→16路，合计增加19条别名、覆盖增加0；局部线/弧移到闭环i还违反第一位对象键义。该反事实拒绝集成。',
        '8. 推荐的两字主归属候选不增删任何路径，e主归属1336→1334、i1816→1818；e/i查询仍1634/2449，候选、覆盖、首选均相同。收益是推荐参照更一致，非减轻候选负担；确认前不落入runtime。','',
        '逐码完整键义见同目录逐码键义.json；它读取当次API allocationKeys，不拿10月8日早期键表解释现行规范ABCD。',
        '独立审阅页第一位分桶审阅.html嵌入现有原字形截图，无提交接口；公开总览页面未改。']
    report=OUT/'第一位分桶统计与候选.md'
    text=report.read_text(encoding='utf-8')
    if '## 最重要的证据与解释' not in text:
        report.write_text(text+'\n'.join(extra)+'\n',encoding='utf-8')
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>第一位分桶：统计与两字待审</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:24px auto;padding:0 20px;color:#182630;background:#faf9f5}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border-bottom:1px solid #ccc;text-align:left;padding:6px}article{background:white;border:1px solid #ddd;padding:20px;margin:20px 0;border-radius:8px}img{width:96px;height:96px;image-rendering:auto}small{color:#52606a}code{color:#174e6e}details{margin:12px 0}summary{cursor:pointer}h1,h2{line-height:1.3}.scroll{overflow:auto}</style><h1>第一位分桶：统计与两字待审</h1>',
        '<p>统计已执行；候选未确认、未接入运行。保留原分桶、后三位键义和ABCD/BCDA共用码表。下图直接裁取既有锁定字形，不重画。</p>',
        '<p>优先比较：ρ、ộ只调整推荐主归属e→i，全部原码和首选保留。候选人数、覆盖、路径数变化均为0。D、O、Q是既有决定的保护对照。</p>',
        '<h2>关键证据</h2><ul>'+''.join('<li>'+esc(x[3:])+'</li>' for x in extra if x[:1].isdigit())+'</ul>']
    for ch in 'ρộDOQ':
        r=next(r for r in reps if r['char']==ch);p=r['preview']
        with Image.open(ROOT/'原型/键位编辑器'/p['url']) as sheet:
            crop=sheet.crop((p['x'],p['y'],p['x']+64,p['y']+64));buf=io.BytesIO();crop.save(buf,format='PNG')
        image=base64.b64encode(buf.getvalue()).decode()
        parts+=['<article><h2>'+esc(ch)+' · U+'+format(r['cp'],'04X')+'</h2><img alt="锁定原字形" src="data:image/png;base64,'+image+'">',
            '<p>当前主桶：'+esc(r['bucket'])+'；可用路径桶：'+esc(', '.join(r['bucketRoutes']))+'；规范码路数：'+str(r['codePaths'])+'。</p>']
        if ch in 'ρộ':
            parts+=['<p><b>待判断：</b>是否把推荐主归属改为i（闭环·均衡），优先按圆主体找？全部旧e码保留。'+('原首选epki不变。' if ch=='ộ' else '不新增圆主体计数码。')+'</p>']
        if ch=='D':parts+=['<p>整字i/k有孔复合；局部竖干a/l；右半弧f/c。旧i/o只作兼容。四者不可混成“D整字为线条纵长”。</p>']
        parts+=['<div class="scroll"><table><tr><th>桶/形族</th><th>取形范围</th><th>状态</th></tr>']
        for route in r['routes']:
            parts+=['<tr><td>'+esc(str(route['bucket'])+'/'+str(route['familyKey']))+'</td><td>'+esc(route['target'])+'</td><td>'+('旧兼容' if route['compatibilityOnly'] else '当前路径；不等于逐字人工全确认')+'</td></tr>']
        parts+=['</table></div><details><summary>全部路径：四位键义及候选人数</summary>']
        for p in r['paths']:
            parts+=['<p><code>'+esc(p['code'])+'</code> / '+str(p['count'])+'候选'+(' · 首选' if p['preferred'] else '')+(' · 旧兼容' if p['compatibilityOnly'] else '')+'<br><small>'+esc(gloss(p['code']))+'</small></p>']
        parts+=['</details></article>']
    parts+=['<h2>各桶统计</h2><div class="scroll"><table><tr><th>桶</th><th>键义</th><th>主归属</th><th>查询</th><th>主归属仅第一位</th><th>四码p90</th></tr>']
    for r in data['buckets']:
        parts+=['<tr>'+''.join('<td>'+esc(s)+'</td>' for s in [r['bucket'],r['meaning'],r['primary'],r['query'],r['primaryOnlyFirst'],r['fullCodes'].get('p90','—')])+'</tr>']
    parts+=['</table></div><p>本页只读，无保存/提交接口；答复应回到原对话。确认记录仍只写既有人工审议，本页不是确认源。自然选键与个人频率未测。</p></html>']
    (OUT/'第一位分桶审阅.html').write_text(''.join(parts),encoding='utf-8')
    print(json.dumps(supplementary,ensure_ascii=False))


if __name__=='__main__':main()
