"""Build the isolated v6.2 baselines and run frozen regression checks."""
import argparse,json,re
from collections import Counter,defaultdict
from scan62 import *
from run61 import old,old_tb,T1 as PRE_T1,RESULT as PRE_RESULT,MOVED,O20,named_assertions,checksummed,digest
from rules62 import classify62,ATTACHED,DIR_SET
from pixels61 import pictorial_images
from pathlib import Path

RESULT=OUT/"BCD分配结果-全域-v6.2.json"
T1=OUT/"tb落地结果-T1-v6.2.json"
TASK=old.PROJECT/"派发单-Codex-v6.2-BCD终局收口与冻结前验收-2026-11-25.md"

def persist(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")

def triangle(gray):
    a=P["tight_mask"](gray,128)
    h,w=a.shape
    rates=[float(v[:max(1,round(.16*len(v)))].mean()) for v in (a,a[::-1],a.T,a.T[::-1])]
    # The broad side of a symmetric triangle is opposite its point.
    return ("LB","LA","LD","LC")[rates.index(max(rates))]+"B"

def t1():
    source=read(PRE_T1)
    hashes={}
    checksummed(PRE_T1,hashes)
    for path,sha in source["inputSHA256"].items():
        checksummed(Path(path),hashes,sha)
    candidates=source["shortlist"]
    preview=old_tb.lookup()[1]
    selected={r["cp"] for r in candidates}
    assert len(selected)==9
    images={}
    for cp,gray,kind in pictorial_images({cp:preview[cp] for cp in sorted(selected)},hashes,font_manifest()):
        images[cp]=gray
    assert selected==images.keys()
    edits=[]
    for row in candidates:
        before=row["BCD"]
        if row["group"]=="三角":
            row["BCD"]=triangle(images[row["cp"]])
        if row["BCD"]!=before:
            edits.append((row["char"],before,row["BCD"]))
            source["rows"][str(row["cp"])]["geometricD3"]=[row["BCD"]]
    source["corrections"]=edits
    source["inputSHA256"]=hashes
    assert len(source["rows"])==4366 and len(source["lines"])==24
    persist(T1,source)
    return source

def exact_checks(rows,cells,tb,stability,denom):
    subjects={r["char"]:r for r in rows.values()}
    checks=[]
    def add(label,expected,actual,ok):
        try:
            assert ok,label
            valid=True
        except AssertionError:
            valid=False
        checks.append(dict(label=label,expected=expected,actual=actual,passed=valid))
    def check(char,pattern,extras=()):
        r=subjects[char]
        add(char,pattern+(" ＋ "+"、".join(extras) if extras else ""),
            " + ".join([r["BCD"],*r["secondaryPaths"]]),
            re.fullmatch(pattern,r["BCD"]) is not None and
            all(any(re.fullmatch(p,s) for s in r["secondaryPaths"]) for p in extras))
    for char in "ç𔕗𖢌𐖊":check(char,"[^P]..")
    check("🢴","[WX]..")
    check("🮖","(LO.|X..)")
    check("⌲","X..",("K..",))
    check("Þ","FC.")
    check("Φ","FG.")
    check("➑","WA.")
    for char in "⬗⬖⬘⬙":check(char,"LL.",("LH.",))
    check("ƹ","[HGY]..")
    for char,key in (("ࢡ","V"),("ﱵ","V"),("ᣱ","W")):
        check(char,".."+key)
    for char,code in dict(zip("）𝚌𝗨✔⸤⅃┐7)(∪∩∧∨<>┌└┘yλ",
        ("CBD","CAA","CCS","BES","BAN","BBM","BDK","BDK","CBD","CAA","CCS","CDW",
         "BFW","BES","BGA","BHD","BCJ","BAN","BBM","IAW","IBS"),strict=True)).items():
        check(char,code)
    check("⤴","PFW")
    check("⭛","PFM")
    for char in "⦾◎":check(char,"XA.",("AAE",))
    check("Ā","D.W",("TAW","J.."))
    check("A","D..",("J..",))
    add("T1 🔽","仅 🔽 改为 LBB",str(tb["corrections"]),
        tb["corrections"]==[["🔽","LCB","LBB"]] or tb["corrections"]==[("🔽","LCB","LBB")])
    counts=Counter(r["BCD"][:2] for r in rows.values())
    for k in ("QE","QF"):
        add(k,"主路径字数 >0",counts[k],counts[k]>0)
    add("BC 标题","单直角 L · 开口向右下",cells["BC"],cells["BC"]=="单直角 L · 开口向右下")
    for t in (112,144):
        v=stability[t]["BCD"]/denom
        add(f"{t} ↔ 128","三键改码率 <5%",f"{v:.2%}",v<.05)
    attach=[r["BCD"] for r in rows.values() if r["BCD"][:2] in ATTACHED]
    add("15 个离散附标 C 格","D 为八向或上下双附标 V",f"{len(attach)} 字",
        bool(attach) and all(code[-1] in DIR_SET|{"V"} for code in attach))
    arrows=[r["BCD"] for r in rows.values() if r["BCD"].startswith("P")]
    pf={code[-1] for code in arrows if code.startswith("PF")}
    add("P 指向与 PF 八向","所有 P 按尖头方向，PF 实测覆盖八向"," ".join(sorted(pf)),
        all(code[-1] in DIR_SET for code in arrows) and pf==DIR_SET)
    return checks

def top20(rows,measurements,loads):
    grouped=defaultdict(list)
    for cp,r in rows.items():
        if cp in measurements:
            grouped[r["BCD"]].append(measurements[cp]["128"])
    items=[]
    for code,n in loads.most_common(20):
        samples=grouped[code]
        dims={}
        for field in ("shape","holesRaw","components","junctions"):
            source=[min(5,m[field]) if field=="junctions" else m[field] for m in samples]
            counts=Counter(source)
            dims[field]=dict(counts=counts,variation=1-max(counts.values())/len(source)) if source else None
        items.append(dict(code=code,count=n,evidence=len(samples),diagnostics=dims))
    return items

def run(artifacts=True):
    hashes={}
    reused_scripts=[PREV/name for name in ("geometry.py","pixels61.py","scan61.py","rules.py","rules61.py",
                                           "run61.py","delivery61.py")]
    reused_scripts.extend(old.V41.parent/"整体重规划-20261124-v6-BCD规则重构"/name
                          for name in ("experiment.py","pictorial.py","extract.py"))
    for path in (PRE_RESULT,PRE_T1,LEDGER,SCAN,INDEX,MEASURED,TASK,old.SPEC,old.MATCH,*old.PROTECTED,*reused_scripts):
        checksummed(path,hashes)
    historic=read(PRE_RESULT)
    a=read(LEDGER)
    b=read(SCAN)
    c=read(MEASURED)
    tb=t1()
    checksummed(T1,hashes)
    spec_drift=[]
    for d in (historic,a,b,c,tb):
        for path,sha in d["inputSHA256"].items():
            resolved=Path(path)
            key=str(resolved.resolve())
            current=checksummed(resolved,hashes)
            # Historical requirements notes are versioned evidence. The current
            # specification supersedes them; raster inputs and protected files must match.
            if current!=sha:
                if resolved not in (old.SPEC,old.TASK):
                    raise AssertionError(f"输入摘要不一致 {path}")
                item=dict(path=path,previous=sha,current=current)
                if item not in spec_drift:
                    spec_drift.append(item)
    features={r["codepoint"]:r for r in read(INDEX)["rows"]}
    cells=historic["cells"].copy()
    cells["BC"]="单直角 L · 开口向右下"
    orig=a["measurements"]
    prior=b["measurements"]
    supp=c["measurements"]
    full={}
    assert orig.keys()==prior.keys()==supp.keys()
    for cp,f in features.items():
        choices={}
        for t in map(str,THRESHOLDS):
            if cp in O20:
                raw=classify62(orig[cp][t]|prior[cp][t]|supp[cp][t],orig[cp]["position"])
                choices[t]=("AAY",[],raw[2])
            elif cp in orig:
                choices[t]=classify62(orig[cp][t]|prior[cp][t]|supp[cp][t],orig[cp]["position"])
            else:
                choices[t]=classify62(None)
        bcd,secondary,ranks=choices["128"]
        assert all(k[:2] in cells and k[-1] in historic["D"] for k in [bcd,*secondary,*(x[0] for x in choices.values())])
        full[cp]=dict(char=f["char"],BCD=bcd,secondaryPaths=secondary,bDefault=bcd.startswith("Z"),
                      independent={k:v[0] for k,v in choices.items()},rawRanks=ranks)
    rows={cp:r for cp,r in full.items() if r["char"] not in MOVED}
    labeled=old.holdout(features,full)
    assert len(full)==29096 and len(rows)==29092 and len({ord(r["char"]) for r in rows.values()}&{int(x) for x in tb["rows"]})==0
    images=rows.keys()&orig.keys()
    stable=old.threshold_metrics(rows,images)
    checks=old.invariants(full,read(old.AUDIT))+named_assertions(rows)
    previous_checks=historic["regression"]
    assert len(checks)==len(previous_checks)==93 and [a["label"] for a in checks]==[a["label"] for a in previous_checks]
    checks+=exact_checks(rows,cells,tb,stable,len(images))
    stat=old.distribute({cp:r["BCD"] for cp,r in rows.items()},sum(r["bDefault"] for r in rows.values()))
    compare=historic["comparison"].copy()
    compare["v6.2"]=stat
    for path,sha in hashes.items():
        assert digest(Path(path))==sha,path
    result=dict(rows=rows,priorGeometryNowT1={cp:full[cp] for cp in full.keys()-rows.keys()},comparison=compare,
                stability=stable,fixedDomainStability=old.threshold_metrics(full,orig),imageCount=len(images),
                blind=labeled,regression=checks,D=historic["D"],cells=cells,emptyCells=old.empty_cells(cells,stat["countsBC"]),
                diagnostics=top20(rows,orig,stat["countsBCD"]),inputSHA256=hashes,specRevision=spec_drift)
    persist(RESULT,result)
    for test in checks:
        print("通过" if test["passed"] else "失败",test["label"],test["actual"])
    print("failures",[(r["label"],r["actual"]) for r in checks if not r["passed"]],flush=True)
    if artifacts:
        from delivery62 import deliver
        deliver(result,tb,features)
        assert all(r["passed"] for r in checks),"冻结前仍有回归未通过，详见报告"

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--reuse",action="store_true")
    parser.add_argument("--measure-only",action="store_true")
    args=parser.parse_args()
    if not args.reuse:
        scan()
    run(not args.measure_only)

