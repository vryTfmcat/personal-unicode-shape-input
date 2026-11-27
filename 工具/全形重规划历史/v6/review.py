"""Create the three v6 review artifacts from the frozen experiment outputs."""
import base64
from collections import Counter, defaultdict
import html
import io
import random
from html.parser import HTMLParser
from geometry import OUT, Image, ImageDraw, ImageFont, P, np, read, font_manifest, pictorial_images
from extract import FEATURES
from experiment import RESULT, NAMES, D_KEYS, THRESHOLDS
from pictorial import DETAIL, lookup

REPORT="v6-BCD量化对比报告.md"
CARDS="v6-BCD审图小卡片.html"
QUIZ="v6-真人BCD试推题-20字.md"
SHEET="v6-真人BCD试推图-20字.png"
ANSWERS="v6-真人BCD试推题-答案对照.md"

def md(name,lines):
    (OUT/name).write_text("\n".join(lines)+"\n",encoding="utf-8")

def pct(n,d):
    return f"{n/d*100:.2f}%"

def table(header, rows):
    def line(row):
        return "| "+" | ".join(str(i).replace("|","&#124;") for i in row)+" |"
    return [line(header),line(["---"]*len(header)),*(line(row) for row in rows)]

def format_stats(stat):
    n=stat["total"]
    return (f'{stat["bDefault"]:,}（{pct(stat["bDefault"],n)}）',
            f'{stat["bCount"]["G"]:,}',str(stat["gz"]),stat["bcUsed"],stat["bcdUsed"],
            *[f"{num:,}（{code}）" for code,num in (stat["maxBC"],stat["maxBCD"])],
            f'{stat["p50"]} / {stat["p90"]}',pct(stat["atMost20"],n))

def report(data,tb,card_sizes):
    rows=[]
    info=data["comparison"]
    stats=("B 默认字数 / 率","G 行","GZ 旧待判格","有字 BC 格","有字 BCD 格","最大 BC 格","最大 BCD 格",
           "按字计 BCD 候选数 p50 / p90","候选数 ≤20 的字占比")
    n=data["geometricCount"]
    match=data["holdout"]
    regressions=data["regression"]
    ok=sum(x["passed"] for x in regressions)
    stability=data["stability"]
    rows += ["# v6 BCD 量化对比", "",
             f"2026-11-24 · 29,096 字，{n:,} 个有图字，7 个缺证占位 · 自动回归 {ok}/{len(regressions)}。", "",
             "## 核心对比", ""]
    rows += table(("指标",*info),zip(stats,*(format_stats(item) for item in info.values())))
    rows += ["","v6 以 ZB 显式表示待核，ZA 为无图；表中默认含二者。v4.1 和 v5 沿用各自逐字 bDefault，默认计数口径因规则变更而异。旧 GZ 格在 v6 契约中撤销。v4.1 最大 BCD 格含旧缺证，旧版所用 D 为方案 B。", "",
             f'v5 的 6,975 个 G 行字在 v6 的去向为 '+ "、".join(f"{key} {n:,}" for key,n in Counter(data["oldGTransitions"]).most_common())+"。", "",
             "### 26 行字数", ""]
    br=info["v6"]["bCount"]
    keys=tuple(NAMES)
    rows += table(("B","族","字数","B","族","字数"),[
        (a,NAMES[a],f"{br[a]:,}",b,NAMES[b],f"{br[b]:,}") for a,b in zip(keys[:13],keys[13:])])
    rows += ["","## 654 样本盲标映射", "",
             f'**Top-1 {match["top1"]}/654（{pct(match["top1"],654)}），Top-2 {match["top2"]}/654（{pct(match["top2"],654)}），漏判 ∅ {match["noPrediction"]}。**', "",
             "旧标由 Claude 看锁定图独立标注，使用原项目已保存的 26 行联接。逐字 B 候选先由像素计算，再读取标签评分。旧 Y/Z 是拟像类别，v6 无对应几何行，18 字仍计入总分母。Top-2 使用第二条可解释几何/布局路径，有且仅有一个候选时沿用该候选。", "",
             "评分映射  "+"，".join(f'{a}→{"/".join(b) or "无几何等价"}' for a,b in match["mapping"].items())+"。", "",
             "前 10 混淆（旧行 → 新首选）  "+"、".join(f"{a}→{b} {n}" for a,b,n in match["mainConfusions"])+"。逐字候选与混淆表见分配文件。", "",
             "## 三阈值独立重跑", ""]
    rows += table(("阈值对 128","B","C","D","BCD"),[(t,*(f"{v[k]:,}（{pct(v[k],n)}）" for k in ("B","C","D","BCD")))
                                                 for t,v in stability.items()])
    good=all(stability[str(t)]["BCD"]<.05*n for t in (112,144))
    rows += ["",f'三键 <5% 门槛 **{"通过" if good else "未通过"}**。每档独立判定，只有 20 个冻结身份沿用同码。三阈值掩膜相同时复用同一份像素测量。', "",
             "## Bug 修复与锚点", ""]
    rows += table(("对象","预期模式","实测主路径 + D3","状态"),
                  [(r["label"],r["expected"],r["actual"],"通过" if r["passed"] else "**失败**") for r in regressions])
    rows += ["","冻结 O 类的规范路径为 AAY，A 保持空字段。D7 使用空 A 字段验证两种结构换序的全量候选集合。上下标方位来自注册字体的字形轮廓基线，锁定裁片用于核对形状。", "",
             "## 空 C 格与合并建议", ""]
    empty=data["emptyCells"]
    by_b=defaultdict(list)
    for key,v in empty.items():
        by_b[key[0]].append(f'{key} → {v["proposal"] or "保留待核"}')
    rows += [f'正文实际定义 **{len(data["cells"])} 格**（派发单称 205），空 **{len(empty)} 格**。箭头后的格是同族暂拟合并去向，复核前保留原规格。',""]
    rows += table(("B 行","零字 C 格 → 建议"),[(b,"、".join(v)) for b,v in by_b.items()])
    rows += ["","## 前十 BCD 格的粗外观诊断", "",
             "离散度为各特征中非众数样本占比。骨架交接团 ≥5 合并为一档。该表只用于找格内差异。", ""]
    rows += table(("BCD","字数","包络/闭孔/墨件/交接团离散度","主要差异"),[
        (r["code"],r["count"]," / ".join(pct(x["variation"],1) for x in r["diagnostics"].values()),
         "、".join(k for k,v in sorted(r["diagnostics"].items(),key=lambda item:-item[1]["variation"])[:2]
                  if v["variation"]>0) or "本探针未见差异") for r in data["visualDiagnostics"]])
    if info["v6"]["maxBCD"][0]=="ZBZ":
        rows += ["","另需先审 ZBZ 的有图待核字。该格混合多种轮廓，候选数应结合下阶段未决清理来读。"]
    rows += ["","## T1/T2 拟像和图标", ""]
    rows += table(("方案桶","字数","占用/容量","最大行","有字行 p50","max/p50","空行率"),[
        (k,f'{v["total"]:,}',f'{v["used"]}/{v["capacity"]}',v["max"],v["p50"],f'{v["maxOverP50"]:.2f}',
         pct(v["empty"],v["capacity"])) for k,v in tb["metrics"].items()])
    moved=[r for r in tb["extraPictorial"] if r["t1"]]
    rows += ["",f'T1 在相同的 4,362 字基线上占 24 行，另试加 18 张旧器物/生物标签裁片中可认出具体对象的 {len(moved)} 字（'+
             "、".join(f'{r["char"]} {r["evidence"]}' for r in moved)+"）。T2 保留原清单。逐行计数、18 字裁片审查意见、试加目标位均见明细文件。",
             "T1 释放 A 位一个保留字母并消去第一键的 t/b 二选一，后续仍需在物象区与图标专留区之间识别。T2 的最大行压力集中在 t；b 单独查找时容量更小。下表为类群规模代理，实际归属犹豫率需真人试推。", ""]
    rows += table(("边界类群","b 字数","t 对照类群字数","代表字"),[
        (v["label"],v["b"],v["t"]," ".join(v["representatives"])) for v in tb["edges"]])
    rows += ["",f'几何边界扫描覆盖 4,362 条记录，其中 **{tb["recognized"]:,}** 字影像可判，**{len(tb["missing"]):,}** 字的现有注册入口没有足够墨迹。可判图中 **{tb["candidateCount"]}** 字命中极简形条件，明细最多列 40 个代表例，卡片展示 20 个。未获可判图的条目仍计入 T1/T2 分布。',
             "T1 可作为减少首键分流的主方案，T2 适合保留原排他习惯。极简者可试挂几何 D3，先看卡片再裁定回流。", "",
             "## 复算与交付核对", "",
             f'本次生成 {sum(card_sizes)} 个卡片裁片，另有 20 题和单独答案。输入与图源 SHA256 共 {len(data["inputSHA256"])} 项，保存在分配 JSON，可运行 python -B experiment.py 复算。']
    md(REPORT,rows)

def gray_to_tile(gray):
    y,x=np.where(gray<235)
    return Image.fromarray(gray[y.min():y.max()+1,x.min():x.max()+1]) if x.size else Image.fromarray(gray)

def png64(gray):
    stream=io.BytesIO()
    gray_to_tile(gray).save(stream,format="PNG",optimize=True)
    return base64.b64encode(stream.getvalue()).decode("ascii")

def sample_review(features,data,tb):
    rng=random.Random(2026112406)
    rows=data["rows"]
    by_b=defaultdict(list)
    by_bc=defaultdict(list)
    by_char={}
    for cp,row in rows.items():
        by_char[row["char"]]=cp
        if features[cp]["source"]:
            by_b[row["BCD"][0]].append(cp)
            by_bc[row["BCD"][:2]].append(cp)
    def pick(seq,n,anchors=""):
        keys=list(dict.fromkeys(by_char[c] for c in anchors))
        source=sorted(set(seq)-set(keys))
        return keys+rng.sample(source,min(max(0,n-len(keys)),len(source)))
    solid=[cp for cp in by_b["L"] if rows[cp]["BCD"][-1]=="B"]
    first=[("实心多边形",pick(solid,20,"🭮▲▼■◆")),("箭头",pick(by_b["P"],20,"🡕➲⮞")),
           ("横枝与梳齿",pick(by_b["N"],20,"Ԑ")),("主路径与 D3",pick([],5,"%ộŤĐ𝔻"))]
    second=[(key+" "+NAMES[key],pick(by_b[key],20)) for key in "KIYHG"]
    third=[(key+" "+NAMES[key],[(cell,pick(by_bc[cell],4)) for cell in data["cells"] if cell[0]==key])
           for key in "LBX"]
    records,_=lookup()
    icons=[cp for cp,r in records.items() if r["firstKey"]=="b" and cp not in tb["missing"]]
    g=sorted({r["cp"] for r in tb["candidates"]})
    fourth=[("t 内图标专留区",rng.sample(sorted(icons),20)),("极简几何边界",rng.sample(g,min(20,len(g))))]
    quiz=[]
    cohorts=(
        ("常见字符",[cp for cp,row in rows.items() if 0x21<=ord(row["char"])<=0x3FF and row["BCD"][0] in "BNQCG"]),
        ("跨文字独体",[cp for cp,row in rows.items() if row["BCD"][0] in "HYIR" and
                       features[cp].get("block") not in ("Basic Latin","Latin-1 Supplement")]),
        ("简单闭形",[cp for cp,row in rows.items() if row["BCD"][0] in "AL"]),
        ("箭头",by_b["P"]),
        ("双孔与多孔",[cp for cp,row in rows.items() if row["BCD"][0] in "KE"]),
    )
    used=set()
    for label,candidates in cohorts:
        choices=pick((cp for cp in candidates if cp not in used and features[cp]["source"]),4)
        assert len(choices)==4
        quiz.extend((cp,label) for cp in choices)
        used.update(choices)
    rng.shuffle(quiz)
    return first,second,third,fourth,quiz

class ReviewParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=0
    def handle_starttag(self,tag,attrs):
        if tag=="img":
            source=dict(attrs)["src"]
            with Image.open(io.BytesIO(base64.b64decode(source.split(",",1)[1],validate=True))) as png:
                png.verify()
            self.images+=1

def deliver():
    data,tb=read(RESULT),read(DETAIL)
    rows=data["rows"]
    features={r["codepoint"]:r for r in read(FEATURES)["rows"]}
    first,second,third,fourth,quiz=sample_review(features,data,tb)
    needed={cp for _,group in first+second for cp in group}
    needed|={cp for _,family in third for _,group in family for cp in group}
    needed|={cp for cp,_ in quiz}
    images={cp:gray for cp,gray in P["glyph_pages"]({cp:features[cp] for cp in sorted(needed)},{})}
    _,previews=lookup()
    pict_ids={cp for _,group in fourth for cp in group}
    pict={cp:gray for cp,gray,kind in pictorial_images({cp:previews[cp] for cp in sorted(pict_ids)},{},font_manifest())}
    assert set(images)==needed and set(pict)==pict_ids

    esc=html.escape
    sections=['''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>v6 BCD 审图小卡片</title><style>
*{box-sizing:border-box}body{background:#f5f5f1;color:#1e2b24;font:16px/1.5 system-ui,sans-serif;margin:0}
main{max-width:1130px;margin:auto;padding:14px 24px 60px}h1{font-size:38px}h2{margin-top:40px}h3,p{margin:0 0 10px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(330px,100%),1fr));gap:12px}
article{border:1px solid #d5ded5;background:#fff;border-radius:9px;padding:14px}
.set{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px;margin-bottom:9px}
figure{margin:0;display:grid;align-content:start;justify-items:center;background:#f2f5f2;padding:6px 1px;min-width:0}
img{width:40px;height:40px;object-fit:contain;image-rendering:pixelated;mix-blend-mode:multiply}
figcaption{width:100%;font:10px/1.3 ui-monospace,monospace;text-align:center;overflow-wrap:anywhere}
.rule{font-size:14px;color:#46574f}.empty{color:#66766b;font-size:13px}
@media(max-width:520px){main{padding:12px}h1{font-size:28px}} 
</style><main><h1>v6 BCD 审图小卡片</h1><p>每张图是锁定裁片，图下标主码及 D3 次路径。T1/T2 板块用 v17 登记图源。</p>''']
    pict_detail={r["cp"]:r for r in tb["candidates"]}
    count=[]
    def card(title,cps,pictorial=False):
        sections.append(f"<article><h3>{esc(title)}</h3>")
        figures(cps,pictorial)
        sections.append("</article>")
    def figures(cps,pictorial=False):
        if not cps:
            sections.append('<p class="empty">此格 0 字</p>')
            return
        count.append(len(cps))
        sections.append('<div class="set">')
        for cp in cps:
            if pictorial:
                r=tb["rows"][str(cp)]
                text=r["t1"]+" / "+r["t2"]
                if cp in pict_detail:
                    text+=" · "+pict_detail[cp]["BCD"]
                img=pict[cp]
                name=f'U+{cp:04X} '+r["category"]
            else:
                r=rows[cp]
                text=r["BCD"]+"".join(" · "+path for path in r["secondaryPaths"])
                name=cp+" "+r["char"]
                img=images[cp]
            sections.append(f'<figure title="{esc(name)}"><img width="40" height="40" alt="{esc(name)}" src="data:image/png;base64,{png64(img)}"><figcaption>{esc(text)}</figcaption></figure>')
        sections.append("</div>")
    for title,cards in (("Bug 修复与锚点",first),("五个新拆分族",second)):
        sections.append(f'<h2>{title}</h2><div class="cards">')
        for label,items in cards:card(label,items)
        sections.append("</div>")
    sections.append('<h2>同一 B 行内的 C 子形</h2><div class="cards">')
    for label,group in third:
        sections.append(f"<article><h3>{esc(label)}</h3>")
        for cell,cps in group:
            rule=data["cells"][cell]
            sections.append(f'<p class="rule"><strong>{cell}</strong> {esc(rule)}</p>')
            figures(cps)
        sections.append("</article>")
    sections.append('</div><h2>T1 / T2 与几何边界</h2><div class="cards">')
    for label,cps in fourth:card(label,cps,True)
    sections.append("</div></main></html>")
    md(CARDS,sections)
    p=ReviewParser()
    p.feed((OUT/CARDS).read_text(encoding="utf-8"))
    assert p.images==sum(count)
    page=Image.new("L",(940,754),255)
    draw=ImageDraw.Draw(page)
    marker=ImageFont.truetype("arial.ttf",20)
    for i,(cp,kind) in enumerate(quiz):
        x=(i%5)*186+6;y=(i//5)*186+6
        draw.rounded_rectangle((x,y,x+176,y+176),radius=9,outline=188,width=2)
        draw.text((x+12,y+8),f"{i+1:02}",font=marker,fill=72)
        tile=gray_to_tile(images[cp])
        scale=124/max(tile.size)
        tile=tile.resize(tuple(max(1,round(k*scale)) for k in tile.size),Image.Resampling.NEAREST)
        page.paste(tile,(x+(176-tile.width)//2,y+28+(132-tile.height)//2))
    page.save(OUT/SHEET,optimize=True)
    md(QUIZ,["# v6 真人 BCD 试推 · 20 字","","按图中号码填写 BCD。先定主体 B，再找 C 子形，最后按 D 属性。能想到第二路径可单记，拿不准可标问号。","","![](v6-真人BCD试推图-20字.png)",""]+
       table(("题号","BCD","犹豫或第二路径"),[(f"{i:02}","","") for i in range(1,21)]))
    md(ANSWERS,["# v6 真人 BCD 试推 · 答案对照","","本表为本轮机器候选。若与看图判断有分歧，可用说明定位分支。",""]+
       table(("题号","字","抽样层","BCD","C 判据","D","D3"),[
           (f"{i:02}",features[cp]["char"],kind,rows[cp]["BCD"],data["cells"][rows[cp]["BCD"][:2]],
            D_KEYS[rows[cp]["BCD"][-1]]," ".join(rows[cp]["secondaryPaths"]))
           for i,(cp,kind) in enumerate(quiz,1)]))
    report(data,tb,count)
    print("Review images",p.images,"Quiz",len(quiz),flush=True)

