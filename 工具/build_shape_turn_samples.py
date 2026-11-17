"""Review seven user examples before any chvc-wide rollout or letter binding."""
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from audit_shape_historical_buckets import protect
from shape_stroke_topology_trial import analyze, render_locked, VERSION

PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / '数据/三模式/规则库/四键实验/键位试验/20261024-turn-junction-samples-v1'
LOCK_SOURCE = OUTPUT / '锁定样本源.json'
SAMPLES = [
    ('ꡲ', {'forks':1}, '用户：一个分叉'),
    ('ᚨ', {'forks':1,'corners':1}, '用户：一个分叉＋一个折角'),
    ('߃', {'forks':1,'corners':1}, '用户：一个分叉＋一个折角向下'),
    ('𐿪', {'corners':1}, '用户：曲线有一个折角'),
    ('ᶔ', {'corners':2}, '用户：曲线有两个折角'),
    ('ᱤ', {'forks':1,'corners':1,'straightSegments':3,'curveSegments':1,'totalSegments':4},
     '用户最新更正：一分叉＋一直角；三直一曲，共四段'),
    ('𐰫', {'crosses':1}, '用户：一个交叉'),
]
PALETTE = ['#067ac1','#e47712','#14924e','#9b4ac9','#d14063','#8a6508','#07858e']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(stats, expected):
    return {k:dict(expected=v,actual=stats[k]) for k,v in expected.items() if stats[k]!=v}


def save_json(name,data):
    (OUTPUT / name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def draw_analysis(mask, result, zoom=1.35):
    image=Image.fromarray(255-mask.astype('uint8')*65).convert('RGB')
    image=image.resize((round(mask.shape[1]*zoom),round(mask.shape[0]*zoom)))
    d=ImageDraw.Draw(image)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
    for i,s in enumerate(result['segments']):
        pts=[(x*zoom,y*zoom) for x,y in s['points']]
        d.line(pts,fill=PALETTE[i%len(PALETTE)],width=3)
        mid=pts[len(pts)//2];d.text((mid[0]+4,mid[1]+2),str(i+1)+('直' if s['kind']=='straight' else '曲' if s['kind']=='curve' else '?'),font=font,fill=PALETTE[i%len(PALETTE)])
    for j in result['junctions']:
        x,y=[v*zoom for v in j['xy']]
        if j['kind']=='cross':
            d.polygon([(x,y-8),(x+8,y),(x,y+8),(x-8,y)],outline='#9b169b',width=3)
        else:
            d.ellipse((x-7,y-7,x+7,y+7),outline='#d21d31',width=3)
    for c in result['corners']:
        x,y=[v*zoom for v in c['xy']]
        d.rectangle((x-6,y-6,x+6,y+6),outline='#1452e6',width=3)
    return image


def make_sheet(records, masks):
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    canvas=Image.new('RGB',(1260,60+math.ceil(len(records)/3)*365),'white');draw=ImageDraw.Draw(canvas)
    draw.text((12,8),'程序标注：蓝方框＝折角，红圆＝三线分叉，紫菱形＝四线交叉',font=font,fill='black')
    draw.text((12,32),'按折角与交点分段；不同颜色对应不同段；以下仅七例校准，不是全量准确率。',font=small,fill='#555555')
    for i,r in enumerate(records):
        x=i%3*420;y=60+i//3*365
        draw.text((x+12,y+4),f'U+{r["cp"]:04X}  基准匹配 {r["variantMatches"]}/9',font=font,fill='black')
        canvas.paste(draw_analysis(masks[r['cp']],r['baseline']),(x+12,y+28))
        s=r['baseline']['statistics']
        draw.text((x+12,y+290),f'程序：折{s["corners"]}／分叉{s["forks"]}／交叉{s["crosses"]}',font=small,fill='#111111')
        draw.text((x+12,y+313),f'直{s["straightSegments"]}＋曲{s["curveSegments"]}＝{s["totalSegments"]}段',font=small,fill='#111111')
        draw.text((x+12,y+338),'基准字号计数吻合' if not r['baselineMismatch'] else '基准计数尚不吻合',font=small,fill='#20683e' if not r['baselineMismatch'] else '#c22')
    canvas.save(OUTPUT / '七例转折与分段标注.png')


def build():
    if (OUTPUT/'七例转折与分段结果.json').exists():
        raise FileExistsError('禁止覆盖既有实验结果')
    OUTPUT.mkdir(exist_ok=True)
    before=protect()
    files=[PROJECT/'工具/shape_stroke_topology_trial.py',Path(__file__),
           PROJECT/'原型/键位编辑器/shape_overview.py',
           PROJECT/'原型/键位编辑器/shape-key-overview.js',
           PROJECT/'原型/键位编辑器/shape-key-overview.html',
           PROJECT/'原型/键位编辑器/data/pictorial-exclusive-allocation.json',
           LOCK_SOURCE]
    hashes={str(p.relative_to(PROJECT)):sha(p) for p in files}
    source={r['cp']:r for r in json.loads(LOCK_SOURCE.read_text(encoding='utf-8'))}
    records=[];masks={}
    for char,expected,note in SAMPLES:
        cp=ord(char);r=source[cp];mask=render_locked(char,r['font']);masks[cp]=mask
        baseline=analyze(mask);variants=[]
        for size in (96,192,256):
            for weight in (-1,0,1):
                result=analyze(render_locked(char,r['font'],size=size,weight=weight))
                variants.append(dict(size=size,weight=weight,statistics=result['statistics'],
                                     mismatch=compare(result['statistics'],expected)))
        transformations=[]
        for name,m in [('rotate90',np.rot90(mask)),('rotate180',np.rot90(mask,2)),('mirror',mask[:,::-1])]:
            result=analyze(m)
            transformations.append(dict(name=name,statistics=result['statistics'],
                                        baselineCountDifferences=compare(result['statistics'],baseline['statistics'])))
        record=dict(cp=cp,char=char,font=r['font'],fontSHA256=sha(Path(r['font']['path'])),
                    userExpected=expected,userSource=note,baseline=baseline,
                    baselineMismatch=compare(baseline['statistics'],expected),
                    variants=variants,variantMatches=sum(not v['mismatch'] for v in variants),
                    transformations=transformations)
        if cp==0x1C64:
            record['supersededJudgment']='此前两个折角／两直一曲已由用户更正，不参与验收'
            record['rightAngleStatus']='本轮只验转折位置与计数；中心线局部角未达到直角范围，不能声称直角角度已验证'
        records.append(record)
        print(f'{char} baseline={baseline["statistics"]} match={record["variantMatches"]}/9',flush=True)
    assert before==protect()
    assert hashes=={str(p.relative_to(PROJECT)):sha(p) for p in files}
    report=dict(version=VERSION,runTime=datetime.now().astimezone().isoformat(),
                definitions=dict(corner='同一中心线路径的局部方向突变；曲支与连续主干连接处可同时为分叉与折角',
                                 fork='连接区有三个独立出口',cross='连接区有四个独立出口',
                                 segments='在折角、分叉、交叉处截断；同处有多种属性只截断一次',
                                 straight='中心线去除接头圆滑端部后可被直线拟合',
                                 curve='不满足本轮直线拟合条件的线段；阈值尚属试验'),
                baselineMatched=sum(not r['baselineMismatch'] for r in records),
                allNineMatched=sum(r['variantMatches']==9 for r in records),
                records=records,protectedHashes=before,sourceHashes=hashes,
                fullChvcScanned=False,newCodes=0,runtimeIntegrated=False,
                limitations=['七例参与规则开发，属于校准样本而非独立准确率。',
                             '曲端短骨架支线可能是字形衬线，也可能是真实短支，当前启发式不能直接全量删路。',
                             '三／四出口接头会受字重、细化相位和接近交点合并影响，须看扰动与旋转结果。',
                             '直角角度与折角方向尚未作为独立通过项；曲线数不等于轮廓凸凹次数。'])
    save_json('七例转折与分段结果.json',report)
    make_sheet(records,masks)
    lines=['# 转折、分叉、交叉与线段：七例独立校准','',
           '本轮仅标注七个用户样本，未推广到1554字，未分配新键位或改动公共总览。',
           'ᱤ按用户最新更正：一个分叉、一个直角、三直一曲、共四段；旧判断保留为已更正记录。','',
           '| 字符 | 程序折角／分叉／交叉 | 程序直／曲／总段 | 用户已指定计数匹配（九扰动） |',
           '|---|---|---|---|']
    for r in records:
        s=r['baseline']['statistics'];lines.append(f'| {r["char"]} U+{r["cp"]:04X} | {s["corners"]}／{s["forks"]}／{s["crosses"]} | {s["straightSegments"]}／{s["curveSegments"]}／{s["totalSegments"]} | {r["variantMatches"]}/9 |')
    lines+=['','仅与用户明确给出的字段比较；未给出的直／曲数量仍是程序建议，不属于用户确认。',
            '折角与分叉可能位于同一连接区，本轮允许双重标注，但分段不重复计数。',
            '七例基准图计数吻合不意味着九扰动全部稳定，也不证明新字符可正确检测。',
            'ᱤ的转折定位、分叉与三直一曲分别核对；“直角”的精确角度尚未验证通过。','',
            '## 文件与接续','',
            '检测器：工具/shape_stroke_topology_trial.py；构建：工具/build_shape_turn_samples.py。',
            '结果JSON保留每个对象坐标、每段路径、拟合误差、短支修剪证据及九扰动／旋转／镜像结果。',
            '图：七例转折与分段标注.png；原始字体、码位与字体哈希在JSON。',
            '下一步先处理本报告暴露的不稳定样本，再做独立未参与调参的对照字；未满足稳定条件前不推广全量、不接入shape_overview.py。',
            '现行chvc仍1554，全部原路径及t／b排他名单保持原样。本轮机器标注尚待用户查看位置。']
    (OUTPUT/'七例校准与总控接续.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    OUTPUT=args.output.resolve()
    build()
