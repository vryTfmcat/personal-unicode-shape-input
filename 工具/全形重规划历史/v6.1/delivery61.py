"""Publish compact static cards, the offline quiz and v6.1 audit tables."""
from collections import Counter,defaultdict
from html import escape
from html.parser import HTMLParser
import io,json,random,base64,re
from run61 import OUT,RESULT,T1,P,ATTACH,WATCH,old,old_tb
from pixels61 import Image, np, pictorial_images, font_manifest

REPORT="v6.1-BCD量化对比报告.md"
CARDS="v6.1-BCD审图小卡片.html"
QUIZ="v6.1-真人BCD选择题-20字.html"
ANSWERS="v6.1-真人BCD选择题-答案对照.md"

def put(name,content):
    (OUT/name).write_text(content+"\n",encoding="utf-8")

def table(header,rows):
    def line(values):
        return "| "+" | ".join(str(v).replace("|","&#124;").replace("\n"," ") for v in values)+" |"
    return "\n".join((line(header),line(["---"]*len(header)),*(line(row) for row in rows)))

def pct(n,d):
    return f"{n/d*100:.2f}%"

def distribution(d):
    n=d["total"]
    return (f'{n:,}',f'{d["bDefault"]:,}（{pct(d["bDefault"],n)}）',d["bCount"]["G"],d["bcUsed"],
            d["bcdUsed"],*(f"{v:,}（{k}）" for k,v in (d["maxBC"],d["maxBCD"])),
            f'{d["p50"]} / {d["p90"]}',pct(d["atMost20"],n))

def report(result,t1,quiz_n,card_n):
    d=result["comparison"]["v6.1"]
    blind=result["blind"]
    checks=result["regression"]
    sources=result["imageCount"]
    out=["# v6.1 BCD 量化对比","",
         f'2026-11-25 · 自动断言 {sum(x["passed"] for x in checks)}/{len(checks)} · 本轮 v6.1 几何 {d["total"]:,} 字，独立 T1 {t1["total"]:,} 字。',"",
         "## 四版对照",""]
    out.append(table(("指标",*result["comparison"]),zip(
        ("几何域字数","B 默认／待核","G 行","有字 BC 格","有字 BCD 格","最大 BC","最大 BCD",
         "按字 BCD 候选数 p50 / p90","候选 ≤20 的字占比"),
        *(distribution(x) for x in result["comparison"].values()))))
    out.extend(["","旧版默认口径沿用各自账本。v6.1 按 Z 统计待核，含 7 个无图占位。T1 迁出 4 个有图字，盲标与继承回归使用迁出前口径。BCD 候选数仅统计规范主路径。","",
                "### 26 行与前十大 BCD 字数",""])
    b=d["bCount"]
    out.append(table(("B 行","字数","B 行","字数"),[(a+" "+old.NAMES[a],b[a],c+" "+old.NAMES[c],b[c]) for a,c in
                                                     zip(tuple(b)[:13],tuple(b)[13:])]))
    out.extend(["","粗外观离散度为各项中非众数组别的比例，依次为包络、孔数、墨件数、交接团。",""])
    out.append(table(("BCD","负载","粗外观离散度"),[(r["code"],r["count"]," / ".join(
        pct(v["variation"],1) for v in r["diagnostics"].values())) for r in result["diagnostics"]]))
    good=d["maxBCD"][1]<450,d["p50"]<60,d["atMost20"]>.25*d["total"]
    out.extend(["", "目标检查 "+ "、".join(f"{label} {'达到' if item else '未达到'}" for label,item in
         zip(("最大 BCD <450","p50 <60","≤20 字占比 >25%"),good))+"。","",
         "## C 列释放与空格",""])
    before=result["comparison"]["v6"]["countsBC"]
    out.append(table(("C 格","v6","v6.1"),[(k,before.get(k,0),d["countsBC"].get(k,0)) for k in WATCH]))
    out+=["",f'按规格 203 个定义格，现有 {len(result["emptyCells"])} 个空格。'+
          "、".join(str(k)+" → "+str(v["proposal"] or "待核") for k,v in result["emptyCells"].items())+"。","",
          "## 654 盲标映射与稳定性","",
          f'Top-1 **{blind["top1"]}/654（{pct(blind["top1"],654)}）**，Top-2 **{blind["top2"]}/654（{pct(blind["top2"],654)}）**，∅ **{blind["noPrediction"]}**。沿用 v6 的 26 行等价映射。','',
          "前 10 混淆 "+ "、".join(f"{a}→{b} {n}" for a,b,n in blind["mainConfusions"])+"。","",
          f"稳定性分母 {sources:,} 个交付几何层有图字，128 为参照。"]
    out.append(table(("阈值","B","C","D","BCD"),[(k,*(f'{v[key]}（{pct(v[key],sources)}）' for key in ("B","C","D","BCD")))
                                                for k,v in result["stability"].items()]))
    out+=["","R 行 D 键分布 "+
          "、".join(f"{key} {n}" for key,n in Counter(r["BCD"][2] for r in result["rows"].values()
                                                      if r["BCD"][0]=="R").most_common())+"。","",
          "## 回归核对",""]
    out.append(table(("对象","预期","实测","结果"),[(r["label"],r["expected"],r["actual"],"通过" if r["passed"] else "**失败**")
                                                    for r in checks]))
    out+=["","## T1 定版","",
          f'24 行全部使用，4,366 字仅有 t 主路径。按旧 t/b 清单，{t1["scanned"]:,} 字有可判图，{len(t1["noUsableInk"]):,} 字墨迹不足。几何 D3 从有图的原图标组筛查，严选池 {t1["strictPool"]} 字，收录 {len(t1["shortlist"])} 字。','']
    lines=t1["lines"]
    out.append(table(("行","类群","字数","行","类群","字数"),
        [(a["code"],a["name"],a["count"],b["code"],b["name"],b["count"]) for a,b in zip(lines[:12],lines[12:])]))
    out+=["", "几何 D3 草案  "+"、".join(f'{r["char"]} {r["tPrimary"]}→{r["BCD"]}' for r in t1["shortlist"])+"。","",
          f'复算脚本 python -B run61.py。{len(result["inputSHA256"]):,} 项输入与图源 SHA256 写入分配 JSON。验收页含 {card_n} 个裁片、{quiz_n} 道三步题。']
    if result["specRevision"]:
        out.append("总设计草案文件 SHA256 较 v6 记录有变动，已逐项核对 203 个 C 格定义一致。新旧草案摘要均记录在分配 JSON。")
    put(REPORT,"\n".join(out))

CSS="""*{box-sizing:border-box}html{color-scheme:light}body{margin:0;background:#f5f7f1;color:#1f2d24;font:16px/1.5 system-ui,sans-serif}
main{max-width:1100px;margin:auto;padding:18px 24px 52px}h1{font-size:clamp(28px,5vw,40px);line-height:1.15}
h2{margin-top:24px}article,section.export{background:white;border:1px solid #dbe2d8;padding:16px;border-radius:10px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(84px,1fr));gap:7px}
figure{margin:0;text-align:center;padding:6px;background:#eff3ee;border-radius:6px}.glyph img{mix-blend-mode:multiply;image-rendering:pixelated;object-fit:contain}
figcaption{font:12px ui-monospace,monospace;overflow-wrap:anywhere}.quiz article h2{margin-top:0;font-size:20px}
.quiz article .glyph{float:left;margin:0 14px 12px 0;padding:14px;min-width:136px}
fieldset{border:1px solid #dfe6dc;border-radius:6px;margin:0 0 8px;min-width:0}legend{font-weight:650}
label{display:inline-flex;gap:6px;align-items:baseline;padding:5px 7px;margin:3px;border-radius:5px;background:#f1f5ef;vertical-align:top}
label:has(:checked){background:#d6ebe0;outline:1px solid #478167}button{font:inherit;padding:9px 12px;border:1px solid #546c5c;border-radius:6px;background:#e1efe5;color:#173b24}
button:disabled{opacity:.52}.answer{clear:both;padding:9px;background:#eef4ec}.answer span{display:block}.different{color:#8a3d19;font-weight:650}
[hidden]{display:none!important}textarea{width:100%;min-height:13rem;font:14px ui-monospace,monospace;margin:8px 0}
@media(max-width:650px){main{padding:12px}.quiz article .glyph{float:none;width:max-content;margin:0 0 12px}}"""

def doc(title,body,mode=""):
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{CSS}</style><main class="{mode}"><h1>{escape(title)}</h1>{body}</main></html>"""

def encode(gray):
    y,x=np.where(gray<235)
    assert len(x)
    im=Image.fromarray(gray[y.min():y.max()+1,x.min():x.max()+1])
    buf=io.BytesIO()
    im.save(buf,format="PNG",optimize=True)
    return base64.b64encode(buf.getvalue()).decode()

def figure(g,label="",hint="",large=False):
    z=112 if large else 45
    return f'<figure class="glyph"><img width="{z}" height="{z}" src="data:image/png;base64,{encode(g)}" alt="{escape(hint or "锁定字形")}">'+(
        f'<figcaption>{escape(label)}</figcaption>' if label else "")+"</figure>"

NEAR={
"A":"DLXW","B":"CQHNP","C":"GHIBD","D":"AFJK","E":"KXWF","F":"DJRKN","G":"CHIYB","H":"CGIBR",
"I":"HYGNO","J":"DFHK","K":"EFDX","L":"AQBX","M":"RNHS","N":"RMHO","O":"INPL","P":"BOCHR",
"Q":"LBMS","R":"NHMF","S":"UTVXM","T":"SUVRH","U":"STVM","V":"STUO","W":"XALK","X":"WALO","Y":"HIENG"}
D_NEAR=("WASDJKNM","GLURFT","HBCPE","VXQIF")

def essay_choice(rows,features,cells,dkeys,rng):
    by_b=defaultdict(list)
    for cp,r in rows.items():
        if features[cp]["source"] and len(set(r["independent"].values()))==1 and r["BCD"][0] not in "Z" and r["BCD"][2] not in "YZ":
            by_b[r["BCD"][0]].append(cp)
    def families(keys):
        return [cp for k in keys for cp in by_b[k]]
    cohorts=[
      ("常见字符",4,[cp for cp in families("ABCDFGHNQ") if 33<=ord(rows[cp]["char"])<=0x390]),
      ("跨文字独体",3,[cp for cp in families("HRIY") if ord(rows[cp]["char"])>=0x400]),
      ("简单闭形与外框",3,families("ALWX")),
      ("箭头与折角",3,families("PB")),
      ("双孔或多孔",3,families("KE")),
      ("带附标",4,[cp for cp in families("BMNCGHIY") if rows[cp]["BCD"][:2] in ATTACH.values()]),
    ]
    questions=[]
    already=set()
    for tag,num,pool in cohorts:
        eligible=sorted(set(pool)-already)
        assert len(eligible)>=num,(tag,len(eligible))
        for cp in rng.sample(eligible,num):
            r=rows[cp]
            code=r["BCD"]
            b=code[0]
            d=code[2]
            bopts=[b,*rng.sample(list(NEAR[b]),3)]
            pool=next((x for x in D_NEAR if d in x),"BGFT")
            other=list(dict.fromkeys(key for key in pool+"FGWB" if key!=d))
            dopts=[d,*rng.sample(other,3)]
            rng.shuffle(bopts)
            rng.shuffle(dopts)
            questions.append(dict(cp=cp,code=code,b=bopts,d=dopts,cohort=tag))
            already.add(cp)
    rng.shuffle(questions)
    return questions

class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count=0
    def handle_starttag(self,tag,attrs):
        if tag=="img":
            blob=dict(attrs)["src"].split(",",1)[1]
            with Image.open(io.BytesIO(base64.b64decode(blob,validate=True))) as im:
                im.verify()
            self.count+=1

def deliver_all(result,t1,features):
    rng=random.Random(61120261125)
    rows=result["rows"]
    families=old.NAMES
    bychar={r["char"]:cp for cp,r in rows.items()}
    def pick(keys,n=10,characters="",predicate=lambda r:True):
        anchors=[bychar[c] for c in dict.fromkeys(characters) if c in bychar and features[bychar[c]]["source"]]
        pool=[cp for cp,r in rows.items() if any(r["BCD"].startswith(key) for key in keys) and
              features[cp]["source"] and predicate(r) and cp not in anchors]
        return anchors+rng.sample(sorted(pool),min(len(pool),max(0,n-len(anchors))))
    sections=[
        ("实心多边形、半实半空",pick(["L"],10,"🭮▲■◧◨◩◪⬒⬓")),
        ("细直条单线",pick(["Q"],10,"–🭶╺ⲓ𝩼ˈ")),
        ("外框包字符",pick(["W"],12,"🆉🅲㊿⑳⑦➀🄳🄹🅳")),
        ("纯几何内件",pick(["X"],10,"⊙⊕⊞")),
        ("箭头与回旋",pick(["P"],14,"🡆🡕⭯↶↷↺↻➲⮞")),
        ("被排除的伪箭头",pick([],0,"ဉ𒾴ᣔ꘍ߪ𐲄ᛎ🗸")),
        ("双孔回环",pick(["K"],10,"8B∞%")),
        ("非规则外包内离",pick(["SF"],10,"𒃌𓨩")),
        *[(key+" · "+result["cells"][key],pick([key],4)) for key in WATCH if key!="LL"],
        ("贯通顶线的 D 分流",sum([pick(["R"],2,predicate=lambda r,d=d:r["BCD"][2]==d)
                                for d in "GLURADSNMETVXQF"],[])),
    ]
    questions=essay_choice(rows,features,result["cells"],result["D"],rng)
    needed={q["cp"] for q in questions}|{cp for _,ids in sections for cp in ids}
    images=dict(P["glyph_pages"]({cp:features[cp] for cp in sorted(needed)},{}))
    assert images.keys()==needed
    card_body=["<p>锁定裁片下方显示当前主路径及 D3。回归例和抽样字并列，便于核对族间串味。</p>"]
    for key,ids in sections:
        card_body.append(f"<article><h2>{escape(key)}</h2><div class='grid'>")
        if not ids:
            card_body.append("<p>实测空格</p>")
        for cp in ids:
            r=rows[cp]
            label=r["BCD"]+(" · "+", ".join(r["secondaryPaths"]) if r["secondaryPaths"] else "")
            card_body.append(figure(images[cp],label,cp+" "+r["char"]))
        card_body.append("</div></article>")
    previews=old_tb.lookup()[1]
    chosen={r["cp"] for r in t1["shortlist"]}
    pict={cp:g for cp,g,_ in pictorial_images({cp:previews[cp] for cp in sorted(chosen)}, {}, font_manifest())}
    card_body.append("<article><h2>T1 极简图标与几何 D3 草案</h2><div class='grid'>")
    for r in t1["shortlist"]:
        card_body.append(figure(pict[r["cp"]],r["tPrimary"]+" → "+r["BCD"],r["char"]))
    card_body.append("</div></article>")
    put(CARDS,doc("v6.1 BCD 审图小卡片","\n".join(card_body)))
    cells=defaultdict(list)
    for code,description in result["cells"].items():
        cells[code[0]].append((code,description))
    data=json.dumps(dict(questions=[{k:q[k] for k in ("code","b","d")} for q in questions],
                         cells=cells,families=families,attrs=result["D"]),ensure_ascii=False).replace("<","\\u003c")
    templates="".join(f'<template data-num="{i}">{figure(images[q["cp"]],large=True)}</template>'
                      for i,q in enumerate(questions,1))
    controls=("<p>看图选择中文形貌。先选主体，再选子形及属性。拿不准可选「都不像／难以判断」。</p>"
              '<div id="questions"></div><p id="progress" role="status"></p>'
              '<button id="check" disabled>核对答案与导出反馈</button>'
              '<section id="output" class="export" hidden><h2>Markdown 反馈</h2>'
              '<label for="feedback">可直接粘贴回对话</label><textarea id="feedback" readonly></textarea>'
              '<button id="copy">复制 Markdown</button> <span id="copy-status" role="status"></span></section>')
    js=(OUT/"quiz61.js").read_text(encoding="utf-8")
    put(QUIZ,doc("v6.1 真人 BCD 选择题 · 20 字",controls+templates+
                 f'<script type="application/json" id="quiz-data">{data}</script><script>{js}</script>',"quiz"))
    put(ANSWERS,"# v6.1 真人 BCD 选择题 · 答案对照\n\n程序候选，留给核对使用。\n\n"+
        table(("题号","字","抽样层","程序 BCD","主体","子形","属性"),[
            (i,rows[q["cp"]]["char"],q["cohort"],q["code"],families[q["code"][0]],
             result["cells"][q["code"][:2]],result["D"][q["code"][2]]) for i,q in enumerate(questions,1)]))
    found=[]
    for name in (CARDS,QUIZ):
        parser=ImgParser()
        parser.feed((OUT/name).read_text(encoding="utf-8"))
        found.append(parser.count)
    assert found==[sum(len(ids) for _,ids in sections)+len(chosen),20]
    report(result,t1,found[1],found[0])

