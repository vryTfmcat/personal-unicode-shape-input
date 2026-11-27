"""Compare pictorial bucket layouts, holding v17 membership fixed."""
from collections import Counter, defaultdict
from geometry import *
from extract import FEATURES,save
from rules import classify
from statistics import median

ALLOC = EDITOR/"data/pictorial-exclusive-allocation.json"
INTAKE = ROOT/"数据/三模式/规则库/四键实验/键位试验/20261024-pictorial-intake-review-v17/拟物收入全量初稿.json"
DETAIL = OUT/"tb双方案对比明细-v6.json"
AUDIT = ROOT/"数据/三模式/规则库/四键实验/人工审议.json"
T = ("人物与动作","人物与神形","身体部位","动物","鸟类","鱼类","昆虫","动物部位",
     "植物","工具与日常物品","食物与饮品","建筑与场所","交通工具","物品／火箭","象形·形象待辨")
B = ("界面／情绪图标","标识","象征标志","字符标识","棋牌符号","游戏图标","星座","自然物象",
     "人脸与表情","花","碎片／抽象拼块","装饰")
B_MERGE = (
    ("界面与游戏图标",("界面／情绪图标","游戏图标")),
    ("安全标识与象征徽标",("标识","象征标志")),
    ("字符标识",("字符标识",)),("棋牌符号",("棋牌符号",)),
    ("星座",("星座",)),("自然物象",("自然物象",)),
    ("人脸与花饰",("人脸与表情","花")),("碎片／抽象拼块",("碎片／抽象拼块",)),
    ("装饰",("装饰",)),
)
EDGE = (("花饰／植物",("b","花"),("t","植物")),("自然图标／自然物象近邻",("b","自然物象"),("t","植物")),
        ("表情／身体",("b","人脸与表情"),("t","身体部位")),
        ("徽标／器物工具",("b","象征标志"),("t","工具与日常物品")))
# This list is solely a human-readable illustration of border categories, not feature input.
EDGE_REPS = ("✿❀❁⚘☘","☀☁⚡⛰","☹☺☻","⚔⚙⚖")
# Human inspection of the 18 old pictorial-label crops, used only to model
# optional T1 intake. Geometry classification never reads this audit.
VISUAL_REVIEW = {
    "U+2667": ("图案","梅花形牌面"), "U+2DC6": ("待核","环与横梁，物象不明"),
    "U+10051": ("待核","环顶长柄，像轮廓符号"), "U+100E8": ("工具与日常物品","束口容器"),
    "U+100F9": ("工具与日常物品","带把器皿"), "U+101F5": ("图案","对称花饰"),
    "U+144BF": ("待核","成对钩瓣和横杠"), "U+115CD": ("图案","中心圆加放射装饰"),
    "U+1201A": ("待核","尖角主件内有楔形纹，像鱼但不够明确"), "U+124E6": ("鱼类","可见尾鳍和鱼身"),
    "U+1442D": ("身体部位","成对手掌"), "U+14027": ("待核","实心小物件轮廓不明"),
    "U+1EC9E": ("待核","弯尾与附点"), "U+144FB": ("待核","杆状件加环，物象不明"),
    "U+168CB": ("待核","梳齿与旗杆样部件"), "U+1D11F": ("图案","谱号"),
    "U+1F9B3": ("待核","有发际/云状外缘，单看锁定图难定"),
    "U+1FADF": ("图案","中心墨团及散点"),
}

def lookup():
    allocation=read(ALLOC)
    intake=read(INTAKE)
    by_cp={r["cp"]:r for r in allocation["allocations"]}
    assert by_cp=={r["cp"]:r for r in intake["draftFirstKeyAllocations"]}
    assert Counter(r["firstKey"] for r in by_cp.values())=={"t":3630,"b":732}
    previews={r["cp"]:r for r in intake["records"] if r["cp"] in by_cp}
    assert previews.keys()==by_cp.keys()
    return by_cp,previews

def dist(rows, keys):
    sizes=[rows.get(k,0) for k in keys]
    present=[v for v in sizes if v]
    return dict(total=sum(sizes),max=max(sizes),p50=median(present),maxOverP50=max(sizes)/median(present),
                empty=len(sizes)-len(present),capacity=len(sizes),used=len(present),
                allSlotP50=median(sizes))

def analyze():
    records,previews=lookup()
    hashes={}
    for path in (ALLOC,INTAKE,MANIFEST,FEATURES,AUDIT):
        checksummed(path,hashes)
    merge={value:i for i,(_,values) in enumerate(B_MERGE) for value in values}
    cat=Counter((r["firstKey"],r["category"]) for r in records.values())
    codes={}
    t1,t2t,t2b=Counter(),Counter(),Counter()
    for cp,r in records.items():
        key,category=r["firstKey"],r["category"]
        index=T.index(category) if key=="t" else len(T)+merge[category]
        index2=(T if key=="t" else B).index(category)
        a,b="t"+chr(65+index),key+chr(65+index2)
        codes[cp]=dict(category=category,t1=a,t2=b,char=r["char"])
        t1[a]+=1
        (t2t if key=="t" else t2b)[b]+=1
    base_t1=dist(t1,["t"+chr(65+i) for i in range(24)])
    subjects={r["codepoint"]:r for r in read(FEATURES)["rows"] if r.get("primary") in ("Y","Z")}
    assert subjects.keys()==VISUAL_REVIEW.keys()
    geo_review=[]
    for cp,(category,evidence) in VISUAL_REVIEW.items():
        char=subjects[cp]["char"]
        if category not in T:
            geo_review.append(dict(codepoint=cp,char=char,category=category,evidence=evidence,t1=None))
            continue
        cp_int=ord(char)
        assert cp_int not in records
        target="t"+chr(65+T.index(category))
        geo_review.append(dict(codepoint=cp,char=char,category=category,evidence=evidence,t1=target))
        t1[target]+=1
    def label(prefix,names,counts,capacity):
        return [{"code":prefix+chr(65+i),"name":names[i] if i<len(names) else "空位",
                 "count":counts[prefix+chr(65+i)]} for i in range(capacity)]
    t1_names=T+tuple(n for n,_ in B_MERGE)
    layouts=dict(T1=label("t",t1_names,t1,24),T2t=label("t",T,t2t,26),T2b=label("b",B,t2b,26))
    sizes={k:dist({r["code"]:r["count"] for r in v},[r["code"] for r in v]) for k,v in layouts.items()}
    candidates=[]
    counts=Counter()
    seen=set()
    for cp,gray,kind in pictorial_images(previews,hashes,font_manifest()):
        m=measure(gray,128)
        if not m:
            continue
        seen.add(cp)
        counts[kind]+=1
        code,second,_=classify(m)
        group=code[0]
        geom=(group in "ALQ" and m["hull"]>=.89 and m["components"]<=2) or \
             (group=="X" and m["components"]<=3 and m["hull"]>=.86) or \
             (group=="W" and code[1] in "AC" and m["components"]<=3 and m["hull"]>=.86) or \
             (group in "SU" and m["components"]<=3 and m["junctions"]==0 and m["straight_ratio"]>=.88) or \
             (group=="O" and m["rays"] in (4,5,6,8) and m["attrs"][2]>=.82 and m["straight_ratio"]>=.77)
        if not geom:
            continue
        skin=min(1.,m["straight_ratio"]+.17) if group in "LSUQ" else m["hull"]
        candidates.append(dict(cp=cp,**codes[cp],BCD=code,
                               action="建议几何 D3 并保留拟像查法" if records[cp]["firstKey"]=="t" or group in "WX" else
                                      "可对照几何回流与 D3 两案",
                               score=round(skin,5),shape=[m["components"],m["holesRaw"],m["polygon"]],
                               imageKind=kind))
    candidates.sort(key=lambda r:(-r["score"],r["cp"]))
    by_cat=Counter(r["category"] for r in candidates)
    picked=[]
    sample_by_group=defaultdict(list)
    for r in candidates:
        key=(records[r["cp"]]["firstKey"],r["BCD"][0],r["category"])
        sample_by_group[key].append(r)
    for rank in range(40):
        for group in sample_by_group.values():
            if rank<len(group) and len(picked)<40:
                picked.append(group[rank])
        if len(picked)==40:break
    edge_rows=[]
    for (label,left,right),ex in zip(EDGE,EDGE_REPS):
        edge_rows.append(dict(label=label,left=left,right=right,b=cat[left],t=cat[right],
                              representatives=[c for c in ex if ord(c) in records]))
    sums=dict(T1Base=base_t1,metrics=sizes,layouts=layouts,recognized=len(seen),missing=sorted(records.keys()-seen),
              sourceKinds=dict(counts),candidateCount=len(candidates),candidateCategories=dict(by_cat),
              candidates=picked,edges=edge_rows,extraPictorial=geo_review)
    result=dict(inputSHA256=hashes,rows=codes,**sums)
    save(DETAIL,result)
    print("t/b",len(seen),len(candidates),sizes,flush=True)

if __name__=="__main__":
    analyze()

