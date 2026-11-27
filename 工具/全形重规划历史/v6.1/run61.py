"""Reproduce the v6.1 experiment inside this directory."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
import sys
from scan61 import BASE,LEDGER,INDEX,SCAN,scan
from pixels61 import OUT,P,THRESHOLDS,checksummed,digest,read,font_manifest,pictorial_images,measure,supplement
from rules61 import classify,ATTACH
sys.path.append(str(BASE))
import experiment as old
import pictorial as old_tb

RESULT=OUT/"BCD分配结果-全域-v6.1.json"
T1=OUT/"tb落地结果-T1-v6.1.json"
V6=BASE/"BCD分配结果-全域-v6.json"
T6=BASE/"tb双方案对比明细-v6.json"
TASK=old.PROJECT/"派发单-Codex-v6.1-BCD纠偏与T1落地及选择题验收-2026-11-25.md"
MOVED="𐃨𐃹𒓦𔐭"  # User-approved bucket transfer only, never a shape predicate.
O20=P["O20"]
WATCH=list(ATTACH.values())+["BD","LL"]

def write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")

def build_t1():
    hashes={}
    for path in (old_tb.ALLOC,old_tb.INTAKE,T6,INDEX,TASK):
        checksummed(path,hashes)
    historic=read(T6)
    source,preview=old_tb.lookup()
    rows={cp:{"tPrimary":historic["rows"][str(cp)]["t1"],"char":r["char"],"category":r["category"],
              "geometricD3":[]} for cp,r in source.items()}
    for row in historic["extraPictorial"]:
        if row["char"] in MOVED:
            assert row["t1"] and ord(row["char"]) not in rows
            rows[ord(row["char"])]=dict(tPrimary=row["t1"],char=row["char"],category=row["category"],geometricD3=[])
    assert len(rows)==4366 and len({r["tPrimary"] for r in rows.values()})==24
    assert all(r["tPrimary"].startswith("t") for r in rows.values())
    recognized=set()
    candidates=defaultdict(list)
    for cp,gray,kind in pictorial_images(preview,hashes,font_manifest()):
        m=measure(gray,128)
        if not m:
            continue
        recognized.add(cp)
        m=supplement(gray,128,m)
        code,_,_=classify(m)
        bc=code[:2]
        w,h=m["size"]
        lr,ud,rot=m["attrs"][:3]
        if min(w,h)<11 or source[cp]["firstKey"]!="b" or source[cp]["category"] in (
                "自然物象","花","人脸与表情","装饰","星座","棋牌符号"):
            continue
        if bc=="AA" and m["components"]==1 and m["circle"]>=.95 and m["hull"]>=.95 and min(lr,ud)>=.84 and (
                not m["holesRaw"] or m["hole"] and min(m["hole"]["sym"][:2])>=.84 and m["hole"]["ellipse"]>=.91
                and m["hole"]["convex"]>=.92):
            group,quality="圆",m["circle"]
        elif bc in ("LE","LF","LG","LH") and m["components"]==1 and m["polygon"]==4 and m["hull"]>=.96 and \
             m["contourStraight"]>=.88 and min(lr,ud)>=.85 and m["holesRaw"]<=1:
            group,quality="方与菱形",m["hull"]
        elif bc in ("LA","LB","LC","LD") and m["components"]==1 and m["polygon"]==3 and m["hull"]>=.95 and \
             m["contourStraight"]>=.85 and max(lr,ud)>=.82:
            group,quality="三角",m["hull"]
        elif bc in ("XA","XB","XC","XE","XF","XG") and m["inner"] and m["hull"]>=.95 and \
             min(m["inner"]["sym"][:2])>=.86 and m["inner"]["count"]==1:
            group,quality="规则几何框",min(m["inner"]["sym"][:2])
        elif bc in ("PA","PB","PD") and m["arrowProfile"] and max(lr,ud)>=.89 and \
             not m["centeredJunction"] and m["endpoints"] in (2,3) and \
             m["junctions"]<=1 and m["contourStraight"]>=.85:
            group,quality="箭头",max(lr,ud)
        elif bc[0] in "SMUQ" and m["components"]==2 and m["holesRaw"]==0 and min(lr,ud)>=.91 and \
             m["straight_ratio"]>=.92 and all(p[4]>=.88*p[2]*p[3] and max(p[2:4])>=2.5*min(p[2:4])
                                             for p in m["boxes"]):
            group,quality="平行双条",min(lr,ud)
        else:
            continue
        candidates[group].append(dict(cp=cp,char=rows[cp]["char"],tPrimary=rows[cp]["tPrimary"],BCD=code,
                                      imageKind=kind,group=group,quality=quality))
    for group in candidates.values():
        group.sort(key=lambda r:(-r["quality"],r["cp"]))
    shortlist=[]
    taken=set()
    # Round-robin keeps visually distinct groups visible in the short review.
    for i in range(max(map(len,candidates.values()),default=0)):
        for name in sorted(candidates):
            group=candidates[name]
            if i<len(group) and group[i]["cp"] not in taken and len(shortlist)<30:
                item=group[i]
                taken.add(item["cp"])
                rows[item["cp"]]["geometricD3"]=[item["BCD"]]
                shortlist.append(item)
    assert len(shortlist)<=30
    counts=Counter(r["tPrimary"] for r in rows.values())
    for path,sha in hashes.items():
        assert digest(Path(path))==sha,path
    write(T1,dict(total=len(rows),rows=rows,counts=counts,
                  lines=[r|{"count":counts[r["code"]]} for r in historic["layouts"]["T1"]],
                  scanned=len(recognized),noUsableInk=sorted(set(source)-recognized),
                  strictPool=sum(len(v) for v in candidates.values()),shortlist=shortlist,inputSHA256=hashes))

def named_assertions(rows):
    bychar={r["char"]:r["BCD"] for r in rows.values()}
    checks=[]
    groups=[
      ("ဉ𒾴🗸ᣔ꘍ߪ𐲄ᛎ",lambda x:not x.startswith("P"),"排除 P"),
      ("↶↷↺↻⭯",lambda x:x.startswith("PF"),"归 PF"),
      ("🡆",lambda x:x.startswith("P"),"归 P"),
      ("𒃌𓨩",lambda x:x.startswith("SF"),"归 SF"),
      ("–ⲓˈ🭶╺𝩼",lambda x:x.startswith("Q"),"归 Q"),
      ("𝝈ᴰه",lambda x:not x.startswith("LJ"),"排除 LJ"),
      ("✱﹡",lambda x:x.startswith("O"),"归 O"),
      ("🆉🅲㊿⑳⑦➀🄳🄹🅳❹🅠➍🄾",lambda x:x.startswith("W"),"归 W"),
      ("𝚌𝗨",lambda x:x.startswith("C"),"归 C"),
      ("✔",lambda x:x.startswith("B"),"归 B"),
      ("𝟣",lambda x:not x.startswith("BF"),"排除 BF"),
      ("◧◨◩◪⬒⬓",lambda x:x.startswith("LL"),"归 LL"),
      ("⸤⅃լ┐7",lambda x:x[:2] in ("BA","BB","BC","BD"),"归 BA–BD"),
    ]
    def add(label,expected,actual,condition):
        try:
            assert condition,label
            ok=True
        except AssertionError:
            ok=False
        checks.append(dict(label=label,expected=expected,actual=actual,passed=ok))
    for chars,test,expected in groups:
        for char in chars:
            code=bychar.get(char)
            if code:
                add(char,expected,code,test(code))
            elif char in "ဉ𒾴🗸↶⭯🡆𒃌𓨩–ⲓˈ𝝈ᴰه✱﹡🆉🅲㊿⑳⑦➀🄳🄹🅳𝚌𝗨✔𝟣":
                add(char,expected,"域外",False)
    counts=Counter(r["BCD"][:2] for r in rows.values())
    for key in WATCH:
        add(key,"主路径 >0",str(counts[key]),counts[key]>0)
    return checks

def experiment(deliver=True):
    hashes={}
    for p in (INDEX,LEDGER,SCAN,V6,T6,T1,old.SPEC,TASK,old.MATCH,*old.PROTECTED):
        checksummed(p,hashes)
    original=read(V6)
    baseline=read(LEDGER)
    scan_data=read(SCAN)
    t1=read(T1)
    assert old.cell_table()==original["cells"]
    spec_drift=None
    for data in (original,baseline,scan_data,t1):
        for p,sha in data["inputSHA256"].items():
            if Path(p)==old.SPEC and hashes[str(old.SPEC.resolve())]!=sha:
                spec_drift={"v6":sha,"current":hashes[str(old.SPEC.resolve())],"sameCellContract":True}
                continue
            checksummed(Path(p),hashes,sha)
    features={r["codepoint"]:r for r in read(INDEX)["rows"]}
    supplements=scan_data["measurements"]
    geometric=baseline["measurements"]
    results={}
    for cp,f in features.items():
        ms=geometric.get(cp,{})
        runs={}
        for t in map(str,THRESHOLDS):
            m=ms.get(t)
            runs[t]=classify(m|supplements[cp][t],ms["position"]) if m else classify(None)
        bcd,secondary,ranks=runs["128"]
        if cp in O20:
            bcd,secondary="AAY",[]
        results[cp]=dict(char=f["char"],BCD=bcd,secondaryPaths=secondary,bDefault=bcd.startswith("Z"),
                         independent={t:("AAY" if cp in O20 else v[0]) for t,v in runs.items()},rawRanks=ranks)
        assert all(k[:2] in original["cells"] and k[-1] in original["D"] for k in
                   [bcd,*secondary,*results[cp]["independent"].values()])
    assert len(results)==29096 and len(geometric)==29089
    # Fixed domain first, then publish an exclusive T1/geometry partition.
    audit=old.invariants(results,read(old.AUDIT))
    scored=old.holdout(features,results)
    routes={cp:r for cp,r in results.items() if r["char"] not in MOVED}
    removed={cp:r for cp,r in results.items() if r["char"] in MOVED}
    assert len(routes)==29092 and len(removed)==4
    assert {ord(r["char"]) for r in routes.values()}.isdisjoint({int(k) for k in t1["rows"]})
    assert len(routes)+t1["total"]==len(results)+4362
    audit+=named_assertions(routes)
    compare=original["comparison"].copy()
    compare["v6"]=old.distribute({cp:r["BCD"] for cp,r in original["rows"].items()},
                               sum(r["bDefault"] for r in original["rows"].values()))
    stat=old.distribute({cp:r["BCD"] for cp,r in routes.items()},sum(r["bDefault"] for r in routes.values()))
    compare["v6.1"]=stat
    kept_images=set(geometric)&routes.keys()
    stable=old.threshold_metrics(routes,kept_images)
    for cp in stat["countsBC"]:
        assert cp in original["cells"]
    for path,sha in hashes.items():
        assert digest(Path(path))==sha,path
    package=dict(rows=routes,priorGeometryNowT1=removed,comparison=compare,stability=stable,
                 fixedDomainStability=old.threshold_metrics(results,geometric),imageCount=len(kept_images),
                 blind=scored,regression=audit,D=original["D"],cells=original["cells"],
                 emptyCells=old.empty_cells(original["cells"],stat["countsBC"]),
                 diagnostics=old.diagnostics(routes,geometric,stat["countsBCD"]),inputSHA256=hashes,
                 specRevision=spec_drift)
    write(RESULT,package)
    for a in audit:
        print(("通过" if a["passed"] else "失败"),a["label"],a["actual"],flush=True)
    print("metrics", {k:v for k,v in stat.items() if not k.startswith("counts")},flush=True)
    if deliver:
        from delivery61 import deliver_all
        deliver_all(package,t1,features)
        assert all(a["passed"] for a in audit),"仍有未通过项，详见报告"

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--reuse",action="store_true")
    parser.add_argument("--measure-only",action="store_true")
    parser.add_argument("--t1-only",action="store_true")
    args=parser.parse_args()
    if not args.reuse and not args.t1_only:
        scan()
    if not args.reuse or args.t1_only:
        build_t1()
    if not args.t1_only:
        experiment(not args.measure_only)

