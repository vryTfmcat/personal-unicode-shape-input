"""Render frozen 1/7 evidence; no public page or authority writes."""
import base64
import html
import io
import json
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/第一位分桶专项-20261025/1与7对象补验'


def main():
    records=json.loads((OUT/'对象与九扰动证据.json').read_text(encoding='utf-8'))
    raw=json.loads((OUT/'独立候选与人数差异.json').read_text(encoding='utf-8'))
    if (OUT/'七字最小接入候选.json').exists() and not (OUT/'7字最小接入候选.json').exists():
        (OUT/'七字最小接入候选.json').rename(OUT/'7字最小接入候选.json')
    minimal=json.loads((OUT/'7字最小接入候选.json').read_text(encoding='utf-8'))
    # Place captions only after all tiles are pasted; keep count labels unclipped.
    sys.path.insert(0,str(ROOT/'工具'))
    from shape_stroke_topology_trial import render_locked
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
    for r in records:
        code=format(r['cp'],'04x');old=Image.open(OUT/(code+'-九扰动.png')).convert('RGB')
        clean=Image.new('RGB',(660,750),'white');draw=ImageDraw.Draw(clean)
        for i,variant in enumerate(r['variants']):
            x=(i%3)*220;y=(i//3)*250
            tile=old.crop(((i%3)*200,(i//3)*235,(i%3)*200+192,(i//3)*235+192))
            clean.paste(tile,(x+10,y+5))
            s=variant['signature'];draw.text((x+5,y+202),f"size={variant['size']} weight={variant['weight']:+}",font=font,fill='black')
            draw.text((x+5,y+220),f"corner={s['corners']} fork={s['forks']} cross={s['crosses']}",font=font,fill='black')
            draw.text((x+5,y+235),f"straight={s['straightStrokes']} curve={s['curveStrokes']}",font=font,fill='black')
        clean.save(OUT/(code+'-九扰动清晰标注.png'))
    esc=lambda x:html.escape(str(x))
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>1与7对象补验</title><style>body{font:16px/1.7 system-ui;max-width:1050px;margin:24px auto;padding:0 18px;background:#f9f8f4;color:#20303a}article{background:white;border:1px solid #ddd;border-radius:8px;padding:20px;margin:20px 0}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%}td,th{padding:5px;border-bottom:1px solid #ddd;text-align:left}.scroll{overflow:auto}code{overflow-wrap:anywhere}summary{cursor:pointer}</style><h1>1与7：对象补验与独立候选</h1><p>未实施迁桶、改码或改首选。固定原字体和原计数器，5字共45观测；没有调参或扩展到其它字。AI机器证据与人的形族判断分开。</p>',
        '<p><b>结论：</b>1整套观测不稳，暂不派计数。7九扰动稳定；建议只增一角入口aaau，旧12路保留。人需判断的只是本字整字角折归属及本次接入，不是全库通则。</p>',
        '<p>aaau：第一位a线与转折·纵长；第二位a角折；第三位a整字角点集；第四位u一个。候选79→80，7现有最小644→80；路径12→13，覆盖新增0，原首选状态保留。</p>',
        '<p>aajb两直笔与aaau的一角候选集合完全相同，均为79个旧成员；本次建议不同时新增。无孔/比例码改善有限，不加入最小方案。</p>']
    lines=['# 1与7对象补验及独立候选','',
        '状态：机器补验与候选比较完成，7最小接入方案等待人的判断；运行未变。','',
        '## 证据范围','',
        '固定现行Segoe UI Symbol的字体文件、字形与SHA，复用原计数器和原九扰动（字号96/192/256×粗细−1/0/+1），画布192。render_locked会把墨迹归一到同一画布；这检验栅格/粗细扰动，不代表多个字体或任意字号。另复现原64px局部分叉检验。未修改阈值、算法或原观测。','',
        '|字|九扰动签名数|整套稳定|作用|','|---|---:|---|---|']
    for r in records:
        lines.append(f"|{r['char']}|{r['distinctSignatures']}|{r['allNineWholeStable']}|{'目标' if r['char'] in '17' else '正/负对照'}|")
    lines+=['','## 实际发现','',
        '1：原64px骨架出现3臂候选，但可见墨迹分叉检验未过；它不等于人眼可辨的真实分叉。九扰动共有3套签名，叉点0/1、角点0/1、直连续笔2/3变化。因此不只叉点不稳，直笔本身也不稳定，不得放宽整体稳定门槛或生成1的计数路。','',
        '7：九扰动均1角、0三叉、0四叉、2直连续笔、0曲连续笔、0孔；拓扑一致、无计数歧义。64px为2端点、无交点，不能支持当前交叉主族；钩形原型原本未过。注意64px严格双直角折拟合仍未通过：下干有弯曲，不能把“整字角折”直接说成已由该严格检测器认证。人的直观形族判断仍需明确。','',
        'T为稳定三叉正对照，Γ为稳定角折正对照，I为稳定单线负对照。三字九扰动均只有1套签名；没有为使1/7通过而调计数器。','',
        '## 候选比较与最小方案','',
        '先独立模拟两字按a/a角折取形的各入口，不写运行数据。主归属候选1从c→a、7仍a；但人的形族判断未收到前均不实施。所有旧路、首选保护。','',
        '|候选码|逐位键义|原人数|两字候选共同接入后|','|---|---|---:|---:|']
    for p in raw['jointGroups']:lines.append(f"|{p['code']}|{p['gloss']}|{p['before']}|{p['after']}|")
    lines+=['','两字共同模拟的aaec为549、aavc624；7单独接入则为548/623。它们不优于7的计数候选，并且1现有最小523还比新无孔路好。因此不为凑路径而把这些弱路一起接入。','',
        '推荐最小方案只针对7：角折主体a、原第一位a不变，仅新增aaau一角；79→80候选、事后最佳644→80，12→13路、覆盖新增0。aajb的79旧成员与aaau完全相同，只新增一种较易直观看到的思路；不把同一集合算两次收益。','',
        '1暂缓主归属和新增码，保持原c/h与全部旧路，不复审ρ/ộ或其它历史字。保留“主形不直观”的待核结论，并不把原c/h认作已解决。','',
        '学习成本：新增“折角整体→一个角”的查法，仍需记住原桶a；12条兼容路不强删。不宣称80候选等于人类自然选键已通过。计数是机器观测，形族确认与数值事实分开。','',
        '## 人的判断范围','',
        '仅7锁定字形的整字角折归属和本批aaau接入；不授权全体数字7、其它字体、角折通则或旧码批量撤回。若只接受形族，不自动生成计数码；若暂缓，保持运行不变。','']
    for r in records:
        code=format(r['cp'],'04x');parts+=['<article><h2>'+esc(r['char'])+' · U+'+format(r['cp'],'04X')+'</h2><p>签名数'+str(r['distinctSignatures'])+'；整套稳定：'+str(r['allNineWholeStable'])+'。</p>']
        for name,label in [(code+'-64原墨迹.png','64像素原墨迹及原交点候选红框'),(code+'-九扰动清晰标注.png','九扰动：颜色为连续笔，红圈为交点，黑框为角点')]:
            data=base64.b64encode((OUT/name).read_bytes()).decode();parts+=['<p>'+label+'</p><img alt="'+label+'" src="data:image/png;base64,'+data+'">']
        parts+=['<div class="scroll"><table><tr><th>字号/粗细</th><th>角/三叉/四叉</th><th>直/曲笔</th><th>拓扑一致</th></tr>']
        for vv in r['variants']:
            s=vv['signature'];parts+=['<tr>'+''.join('<td>'+esc(x)+'</td>' for x in [str(vv['size'])+'/'+str(vv['weight']),f"{s['corners']}/{s['forks']}/{s['crosses']}",f"{s['straightStrokes']}/{s['curveStrokes']}",vv['topologyAgrees']])+'</tr>']
        parts+=['</table></div></article>']
    parts+=['<p>本页为只读材料，没有确认保存或运行切换接口。答复回原对话后才进入既有人工审议。</p></html>']
    (OUT/'对象补验与最小候选.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (OUT/'1与7对象审阅.html').write_text(''.join(parts),encoding='utf-8')
    print('补验报告、独立只读审阅页和清晰图已生成')


if __name__=='__main__':main()
