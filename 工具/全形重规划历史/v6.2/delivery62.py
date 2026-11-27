"""Publish the freeze review pages and offline quiz."""
import json,random
from collections import Counter,defaultdict
from html import escape
from run62 import OUT,P,old
from delivery61 import table,pct,distribution,figure,doc,essay_choice,ImgParser,NEAR
REPORT="v6.2-BCD终局验收报告.md"
CARDS="v6.2-BCD审图小卡片.html"
QUIZ="v6.2-真人BCD选择题-20字.html"
ANSWERS="v6.2-真人BCD选择题-答案对照.md"
MOTTO="附标看附标在哪边。箭头、尾巴、枝头看指向。开口弧、折角看弧背或尖角所在侧，也就是开口的反方向。复杂无开口先看对称、双线、斜倾，再看哪边更重。"
RULES=[
"1. **有离散附标，看附标相对主体的位置。** 主路径为 AG/LN/DI/FI/JH/KG/EG/BM/MF/NG/CI/GG/HH/IF/YP 时，以附标所在侧取八向。上下两侧都有附标取 V。",
"2. **箭尖、尾巴和枝头，看向哪边。** P、J、N 以及 L 三角的方向次路径按指向取键。PF 弧弯箭与回旋箭开放全部八向。",
"3. **开口弧、折角和单叉，看弧背、尖角或分叉所在侧。** C 与 B 取开口的反方向。I 看两叉展开的一侧。例如 ) 右、( 左、∪ 下、∩ 上、┐ 右上、y 上分叉。",
"4. **复杂无开口且无附标，先看对称、双线、斜倾，再看哪边更重。** R 等复杂族先按结构属性分流，其余按整字哪侧墨迹更重取八向，居中均衡取 F。",
"",
"八向固定为 J/W/K · A/F/D · N/S/M，F 是居中均衡。以上四条作为正式输入法方向规范，后续发布说明沿用。"]

def put(name,content):
    (OUT/name).write_text(content+"\n",encoding="utf-8")

def report(r,t,count):
    passed=sum(x["passed"] for x in r["regression"])
    total=len(r["regression"])
    d=r["comparison"]["v6.2"]
    status="自动验收全通过，待用户审图及冻结确认。" if passed==total else "仍有断言未过，冻结验收未通过。"
    lines=["# v6.2 BCD 终局验收报告","","## D 位方向四条铁律","",*RULES,"",
           f"计算日期 2026-11-26 · {passed}/{total} 项自动断言通过。{status}","",
           "## 五版量化对照",""]
    lines.append(table(("指标",*r["comparison"]),zip(
        ("几何层字数","B 默认／待核","G 行字数","有字 BC 格","有字 BCD 格","最大 BC","最大 BCD",
         "按字计 BCD 候选数 p50 / p90","BCD 候选 ≤20 字占比"),
        *(distribution(v) for v in r["comparison"].values()))))
    lines+=["","T1 排他吸纳 4 字，v6.1/v6.2 交付几何层为 29,092 字。统计只计规范主路径。各版沿用当期待核口径。","",
            "### 26 行字数",""]
    ns=d["bCount"]
    bs=list(ns)
    lines.append(table(("B 行","字数","B 行","字数"),[(b+" "+old.NAMES[b],ns[b],c+" "+old.NAMES[c],ns[c])
                                                    for b,c in zip(bs[:13],bs[13:])]))
    lines+=["",f'203 个定义格中尚空 {len(r["emptyCells"])} 格。QE {d["countsBC"].get("QE",0)} 字，QF {d["countsBC"].get("QF",0)} 字。BC 显示为「{r["cells"]["BC"]}」。',
            "空格与可审议合并去向  "+"、".join(f'{k}→{v["proposal"] or "待核"}' for k,v in r["emptyCells"].items())+"。","",
            "## 654 盲标与三阈值稳定性",""]
    h=r["blind"]
    lines += [f'Top-1 **{h["top1"]}/654（{pct(h["top1"],654)}）**，Top-2 **{h["top2"]}/654（{pct(h["top2"],654)}）**，漏判 **{h["noPrediction"]}**。沿用旧行到新行的映射，在分类完成后读取盲标。',"",
              "前十混淆  "+"、".join(f"{a}→{b} {n}" for a,b,n in h["mainConfusions"])+"。","",
              f'稳定性分母 {r["imageCount"]:,} 个交付几何层有图字。各档独立计算，128 为参照。',""]
    lines.append(table(("阈值","B","C","D","BCD"),[(t,*(f"{n:,}（{pct(n,r['imageCount'])}）" for n in v.values()))
                                                 for t,v in r["stability"].items()]))
    pf=Counter(a["BCD"][-1] for a in r["rows"].values() if a["BCD"].startswith("PF"))
    lines+=["","PF 实测 D 方向  "+"、".join(f"{k} {pf[k]}" for k in "WASDJKNM")+"。选择题罗盘在每题展示八向。","",
            "## 回归断言",""]
    lines.append(table(("对象","预期","实测","结果"),[(x["label"],x["expected"],x["actual"],"通过" if x["passed"] else "**失败**")
                                                   for x in r["regression"]]))
    lines+=["","## T1 定版与九字几何 D3","",
            f'{t["total"]:,} 字、24 行。9 个几何候选仍以 t 为主路径。筛查基线有 {t["scanned"]:,} 个可判图，{len(t["noUsableInk"]):,} 条图源墨迹不足。',"",
            "本次几何次路径改动  "+"、".join(f"{c} {p} → {a}" for c,p,a in t["corrections"])+"。",""]
    data=t["lines"]
    lines.append(table(("行","类群","字数","行","类群","字数"),[(x["code"],x["name"],x["count"],y["code"],y["name"],y["count"])
                                                        for x,y in zip(data[:12],data[12:])]))
    lines+=["",table(("字","t 主路径","几何 D3"),[(x["char"],x["tPrimary"],x["BCD"]) for x in t["shortlist"]]),"",
            "## 前 20 大 BCD 格","",
            "离散度为各特征中非众数组占比。交接团按 5+ 合档。表按字数降序，可作为后续视觉归桶的输入。",""]
    lines.append(table(("BCD","字数","包络","孔数","墨件","交接团"),
                       [(x["code"],x["count"],*(pct(z["variation"],1) if z else "缺证" for z in x["diagnostics"].values()))
                        for x in r["diagnostics"]]))
    lines+=["",f'复算入口 python -B run62.py。分配 JSON 含 {len(r["inputSHA256"]):,} 项输入与图源 SHA256、各阈值逐字码、完整盲标矩阵。审图含 {count} 个裁片。']
    if r["specRevision"]:
        lines.append("设计文档沿用当前版本，历史快照摘要差异见分配 JSON。")
    put(REPORT,"\n".join(lines))

def deliver(r,t,features):
    rows=r["rows"]
    rng=random.Random(62120261126)
    bychar={k["char"]:cp for cp,k in rows.items()}
    def take(prefixes,n,examples="",direction=None):
        named=[bychar[c] for c in dict.fromkeys(examples) if c in bychar and features[bychar[c]]["source"]]
        pool=[cp for cp,k in rows.items() if cp not in named and features[cp]["source"] and
              any(k["BCD"].startswith(b) for b in prefixes) and (not direction or k["BCD"][-1]==direction)]
        return named+rng.sample(sorted(pool),min(max(0,n-len(named)),len(pool)))
    sets=[
        ("P 箭头与回旋",take(["PF"],8,"⤴⭛↶↷↺↻⭯")+take(["PA","PB","PD"],5,"🡕🡆")),
        ("P 去噪回看",take([],0,"ç𔕗𖢌𐖊")),
        ("双孔与外框双查法",take(["K"],10,"🢴🮖⌲8%")),
        ("左直干附圈和中干贯环",take(["FC","FG"],12,"ÞΦφɸ")),
        ("圆框单字和多字／复杂内件",take(["WA","WB"],12,"➑㊿⑳")),
        ("半实半空菱形与次路径",take(["LL"],9,"⬗⬖⬘⬙")),
        ("附标方位与双附标",take(["AG","CI","GG","YP","DI"],10,"ࢡﱵᣱĀộ")),
        ("弧背、折角与分叉方向",take([],0,"）𝚌𝗨✔⸤⅃┐7)(∪∩∧∨<>┌└┘yλ")),
        ("同心双圆与单孔双脚",take([],0,"◎⦾AĀ")),
        ("孤立单点／双点",take(["QE","QF"],10,"·•:‥¨")),
        ("BC · "+r["cells"]["BC"],take(["BC"],7,"┌")),
    ]
    pf=Counter(x["BCD"][2] for x in rows.values() if x["BCD"].startswith("PF"))
    for key in "JWKADNSM":
        sets.append(("PF "+r["D"][key]+f" · {pf[key]} 字",take(["PF"],2,direction=key)))
    questions=essay_choice(rows,features,r["cells"],r["D"],rng)
    for char,cohort in (("⭛","箭头与折角"),("ࢡ","带附标"),("ᣱ","带附标")):
        cp=bychar[char]
        if any(q["cp"]==cp for q in questions):
            continue
        if rows[cp]["BCD"][0] not in NEAR or rows[cp]["BCD"][2] in "YZ":
            continue
        slot=next(q for q in questions if q["cohort"]==cohort and q["cp"] not in {bychar["ࢡ"],bychar["ᣱ"]})
        code=rows[cp]["BCD"]
        options=[code[0],*rng.sample(list(NEAR[code[0]]),3)]
        rng.shuffle(options)
        slot.update(cp=cp,code=code,b=options)
    grid={q["cp"] for q in questions}|{cp for _,subset in sets for cp in subset}
    images=dict(P["glyph_pages"]({cp:features[cp] for cp in sorted(grid)},{}))
    assert set(images)==grid and len({q["cp"] for q in questions})==20
    blocks=["<p>逐卡核对锁定裁片。图下先显示主路径，再显示 D3 次路径。</p>"]
    for title,subset in sets:
        blocks.append(f"<article><h2>{escape(title)}</h2><div class='grid'>")
        if not subset:
            blocks.append("<p>当前无命中字形。</p>")
        for cp in subset:
            k=rows[cp]
            blocks.append(figure(images[cp]," · ".join([k["BCD"],*k["secondaryPaths"]]),k["char"]))
        blocks.append("</div></article>")
    put(CARDS,doc("v6.2 BCD 审图小卡片","\n".join(blocks)))
    cells=defaultdict(list)
    for code,label in r["cells"].items():
        cells[code[0]].append((code,label))
    data=json.dumps(dict(questions=[{k:q[k] for k in ("code","b")} for q in questions],cells=cells,
                         families=old.NAMES,attrs=r["D"]),ensure_ascii=False).replace("<","\\u003c")
    templates="".join(f'<template data-num="{i}">{figure(images[q["cp"]],large=True)}</template>'
                      for i,q in enumerate(questions,1))
    content=f'<p>{escape(MOTTO)}</p><p>每题选主体、子形和方向或结构属性，拿不准可选「都不像／难以判断」。</p>'
    content+=('<div id="questions"></div><p id="progress" role="status"></p>'
              '<button id="check" disabled>核对答案与导出反馈</button>'
              '<section id="output" class="export" hidden><h2>Markdown 分歧表</h2>'
              '<label for="feedback">可直接粘贴回对话</label><textarea id="feedback" readonly></textarea>'
              '<button id="copy">复制 Markdown</button> <span id="copy-status" role="status"></span></section>')
    js=(OUT/"quiz62.js").read_text(encoding="utf-8")
    style=""" .compass{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));max-width:330px;gap:4px;margin:5px 0 9px}
.compass label{margin:0;min-height:42px;align-items:center;justify-content:center;text-align:center;line-height:1.15}
.attributes{display:flex;flex-wrap:wrap;gap:2px}fieldset legend{font-size:15px}
@media(max-width:480px){.compass label{padding:4px;min-height:46px;font-size:13px}}"""
    result=doc("v6.2 真人 BCD 选择题 · 20 字",content+templates+
               f'<script id="quiz-data" type="application/json">{data}</script><script>{js}</script>',"quiz")
    put(QUIZ,result.replace("</style>",style+"</style>",1))
    put(ANSWERS,"# v6.2 真人 BCD 选择题 · 答案对照\n\n"+table(("题号","字","抽样层","主路径","主体","子形","属性"),[
        (i,rows[q["cp"]]["char"],q["cohort"],q["code"],old.NAMES[q["code"][0]],
         r["cells"][q["code"][:2]],r["D"][q["code"][2]]) for i,q in enumerate(questions,1)]))
    counts=[]
    for name in (CARDS,QUIZ):
        parser=ImgParser()
        parser.feed((OUT/name).read_text(encoding="utf-8"))
        counts.append(parser.count)
    assert counts==[sum(len(s) for _,s in sets),20]
    report(r,t,counts[0])

