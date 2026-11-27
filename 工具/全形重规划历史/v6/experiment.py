"""v6 BCD assignment, repeatable metrics and regressions."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import re
from geometry import OUT, ROOT, THRESHOLDS, V41, V5, checksummed, digest, read
from extract import FEATURES, OUTPUT, P, save, extract
from pictorial import ALLOC, AUDIT, DETAIL, INTAKE, analyze
from rules import classify, D_KEYS, NAMES

RESULT=OUT/"BCD分配结果-全域-v6.json"
PROJECT=ROOT.parents[3]/"Obsidian/Obsidian-codx/70_unicode/个人Unicode音型输入法/理论"
SPEC=PROJECT/"全形模式-BCD规则重构草案-v6-2026-11-24.md"
TASK=PROJECT/"派发单-Codex-v6-BCD规则重构与tb双方案-2026-11-24.md"
BASE=V41/"BC分配结果-全域-v4.1.json"
BASE_D=V41/"BCD分配结果-全域-方案B-v4.1.json"
V5_CODES=V5/"BCDA分配结果-全域-v5-draft.json"
MATCH=V41/"族内特征-加权.json"
PROTECTED=(AUDIT, ALLOC, ROOT/"数据/三模式/shape-stage.json", ROOT/"原型/键位编辑器/data/structure-count-bindings.json")
O20=P["O20"]

# Frozen-domain holdout crosswalk, independent of predicted rows.
MAP={key:(key,) for key in NAMES}
MAP.update(E=("K","E"),G=("G","I","Y"),H=("H",),I=("H",),J=("J",),K=("J",),Y=(),Z=())

def cell_table():
    structure=SPEC.read_text(encoding="utf-8-sig").split("## 三、",1)[1].split("## 四、",1)[0]
    cells={}
    for line in structure.splitlines():
        if not line.startswith("| "):
            continue
        columns=[v.strip() for v in line.strip("|").split("|")]
        if len(columns)<3:
            continue
        keys=re.findall("(?:^| / )([A-Z]{2})(?= / |$)",columns[0].strip(chr(96)))
        if len(keys)==1:
            cells[keys[0]]=columns[1].replace("**","").replace(chr(96),"")
        elif len(keys)>1:
            shape=columns[1].replace("**","")
            hints=("偏上重","偏下重","偏左重/口","偏右重/口","均衡密集")
            for key,hint in zip(keys,hints,strict=True):
                cells[key]=shape+" · "+hint
    assert len(cells)==203 and set(key[0] for key in cells)==set(NAMES)
    return cells

def distribute(rows, default_count):
    n=len(rows)
    b,bc,bcd=(Counter(code[:i] for code in rows.values()) for i in range(1,4))
    per_char=sorted(bcd[code] for code in rows.values())
    return dict(total=n,bDefault=default_count,bCount={k:b[k] for k in NAMES},
                gz=bc["GZ"],bcUsed=len(bc),bcdUsed=len(bcd),
                maxBC=bc.most_common(1)[0],maxBCD=bcd.most_common(1)[0],
                p50=per_char[(n+1)//2-1],p90=per_char[(9*n+9)//10-1],
                atMost20=sum(v<=20 for v in per_char),countsBC=bc,countsBCD=bcd)

def holdout(features, assigned):
    # Label access starts only after the independent pixel assignments are complete.
    sample={x["codepoint"]:x for x in read(MATCH)["rows"] if x["layer"]=="geometry-observed"}
    assert len(sample)==654
    assert sample.keys()=={cp for cp,r in features.items() if "sourceAnnotation" in r}
    rows=[]
    confusion=Counter()
    one=two=nmiss=0
    for cp,r in sorted(sample.items()):
        fr=features[cp]
        assert fr["sourceAnnotation"]["primary"]==r["primary"]
        old=fr["primary"]
        equal=MAP[old]
        candidates=assigned[cp]["rawRanks"]
        guess=candidates[0] if candidates else "∅"
        confusion[old,guess]+=1
        nmiss+=not candidates
        one+=guess in equal
        two+=any(key in equal for key in candidates[:2])
        rows.append(dict(codepoint=cp,old=old,originalFamily=r["primary"],eligible=equal,ranked=candidates))
    return dict(total=len(sample),top1=one,top2=two,noPrediction=nmiss,
                representable=sum(bool(r["eligible"]) for r in rows),mapping=MAP,
                confusion=[(a,b,n) for (a,b),n in confusion.most_common()],
                mainConfusions=[(a,b,n) for (a,b),n in confusion.most_common() if b not in MAP[a]][:10],rows=rows)

def threshold_metrics(assigned,images):
    output={}
    for t in (112,128,144):
        pairs=[(assigned[cp]["BCD"],assigned[cp]["independent"][str(t)]) for cp in images]
        output[t]=dict(zip(("B","C","D","BCD"),[sum(a[i]!=b[i] for a,b in pairs) for i in range(3)]+
                           [sum(a!=b for a,b in pairs)]))
    return output

def invariants(assigned, audit):
    chars={r["char"]:r for r in assigned.values()}
    checks=[]
    def capture(label,condition,expected,actual):
        try:
            assert condition, label
            ok=True
        except AssertionError:
            ok=False
        checks.append(dict(label=label,expected=expected,actual=actual,passed=ok))
    def check(c,pattern,extra=None):
        r=chars[c]
        primary=r["BCD"]
        second=r["secondaryPaths"]
        capture(c,re.fullmatch(pattern,primary) is not None and
                (not extra or any(re.fullmatch(extra,p) for p in second)),
                pattern+(" + "+extra if extra else ""),primary+(" + "+" ".join(second) if second else ""))
    check("🭮","LCB")
    for c in "▲▼■◆": check(c,"L..")
    check("●","AAB")
    for c,pattern in (("🡕","PBK"),("➲","PD."),("⮞","PH."),("Ԑ","NC.")):
        check(c,pattern)
    for c in "+×✳✦∗": check(c,"O..")
    for c,pattern,extra in (("%","KC.","VC."),("ộ","AG.","TC."),("Ť","R[AF].","TA."),
                            ("Đ","FH.",None),("𝔻","EFE",None)):
        check(c,pattern,extra)
    for c,pos in (("ᵒ","W"),("ₒ","S"),("°","W"),("º","W")):
        check(c,"A..","A."+pos)
    # These entries are read only for traceability of earlier endorsed lookup meanings.
    assert "%" in str(audit.get("jointLookupAcceptance20261101Batch1"))
    capture("冻结 O 类 20 字",len(O20)==20 and all(
        assigned[cp]["BCD"]=="AAY" and set(assigned[cp]["independent"].values())=={"AAY"} for cp in O20),
        "20 × AAY",str(Counter(assigned[cp]["BCD"] for cp in O20)))
    empty=[cp for cp,r in assigned.items() if r["BCD"]=="ZAZ"]
    capture("无图占位",len(empty)==7,"7 × ZAZ",str(len(empty)))
    # D7 is tested with a constant empty A field solely as an address projection.
    # The experiment publishes no A code.
    xy, yx=defaultdict(set),defaultdict(set)
    for cp,r in assigned.items():
        xy[tuple(r["BCD"])+(None,)].add(cp)
        yx[(None,)+tuple(r["BCD"])].add(cp)
    capture("D7 空 A 结构换序",len(assigned)==29096 and len(xy)==len(yx) and
            all(yx[key[-1:]+key[:3]]==values for key,values in xy.items()) and
            all(xy[key[1:]+key[:1]]==values for key,values in yx.items()),
            "29,096 字双序同候选",f"{len(assigned):,} 字、{len(xy):,} 集")
    capture("D 方位键锁",len(D_KEYS)==25 and "O" not in D_KEYS and
            [D_KEYS[k] for k in "WASDJKNM"]==["正上","正左","正下","正右","左上","右上","左下","右下"],
            "W/A/S/D/J/K/N/M 固定、O 备用"," ".join(D_KEYS))
    return checks

def diagnostics(rows, measures, counts):
    grouped=defaultdict(list)
    for cp,r in rows.items():
        if cp in measures:
            grouped[r["BCD"]].append(measures[cp]["128"])
    items=[]
    for code,count in counts.most_common(10):
        ms=grouped[code]
        if not ms:
            continue
        tallies={}
        for name,attribute in (("包络","shape"),("闭孔数","holesRaw"),("连通件数","components"),("骨架交接团","junctions")):
            vs=[m[attribute] for m in ms]
            if attribute=="junctions": vs=[min(v,5) for v in vs]
            tally=Counter(vs)
            dominant=tally.most_common(1)[0]
            tallies[name]={"counts":dict(sorted(tally.items())),"variation":1-dominant[1]/len(ms)}
        items.append(dict(code=code,count=count,evidence=len(ms),diagnostics=tallies))
    return items

MERGE={
    "A":{"D":"A","E":"A","F":"A","H":"G","I":"A"}, "L":{"K":"J","L":"E","M":"J","N":"J","O":"J"},
    "W":{"E":"C","F":"A","G":"D"}, "X":{"D":"C","H":"G","I":"E"},
    "D":{"H":"A","I":"A"}, "F":{"G":"C","H":"C","I":"C"},
    "J":{"E":"A","F":"A","G":"D","H":"A"}, "K":{"D":"A","E":"A","F":"B","G":"A"}, "E":{"F":"A","G":"A"},
    "Q":{"G":"A"}, "B":{"K":"G","L":"I","M":"I"}, "M":{"D":"B","F":"B"}, "N":{"F":"A","G":"C"},
    "R":{"D":"E","F":"A"}, "O":{"C":"D","E":"D","F":"A"}, "P":{"C":"A","D":"A","E":"A","F":"E","G":"C","H":"A"},
    "C":{"E":"A","F":"B","G":"C","H":"D","I":"A"}, "G":{"D":"C","E":"A","F":"A","G":"A"},
    "H":{"E":"A","F":"C","G":"B","H":"A"}, "I":{"E":"A","F":"A"},
    "S":{"F":"C"}, "T":{"D":"A","E":"B","F":"C"}, "U":{"D":"B"}, "V":{"E":"D","F":"D"},
}

def empty_cells(cells,counts):
    empty={}
    for key,rule in cells.items():
        if counts.get(key):
            continue
        b,c=key
        populated=[k for k in cells if k[0]==b and counts.get(k)]
        proposed=b+MERGE.get(b,{}).get(c,"A")
        empty[key]=dict(rule=rule,proposal=proposed if proposed in populated else
                        max(populated,key=lambda k:counts[k]) if populated else None,
                        suggestion="审图后合并，当前留空")
    return empty

def experiment():
    hashes={}
    for path in (SPEC,TASK,BASE,BASE_D,V5_CODES,MATCH,FEATURES,OUTPUT,DETAIL,INTAKE,*PROTECTED):
        checksummed(path,hashes)
    source=read(OUTPUT)
    tb=read(DETAIL)
    for src_hash in (source["inputSHA256"],tb["inputSHA256"]):
        for path,sha in src_hash.items():
            checksummed(Path(path),hashes,sha)
    features={r["codepoint"]:r for r in read(FEATURES)["rows"]}
    measures=source["measurements"]
    cells=cell_table()
    assigned={}
    for cp,f in features.items():
        measurements=measures.get(cp,{})
        runs={str(t):classify(measurements.get(str(t)),measurements.get("position","")) for t in THRESHOLDS}
        code,secondary,ranks=runs["128"]
        if cp in O20:
            code,secondary="AAY",[]
        assert code[:2] in cells and code[-1] in D_KEYS and all(p[:2] in cells and p[-1] in D_KEYS for p in secondary)
        assert all(p[:2] in cells and p[-1] in D_KEYS for p,_,_ in runs.values())
        assigned[cp]=dict(char=f["char"],BCD=code,secondaryPaths=secondary,bDefault=code[0]=="Z",
                          independent={t:("AAY" if cp in O20 else p) for t,(p,_,_) in runs.items()},
                          rawRanks=ranks)
    assert len(assigned)==29096 and len(measures)==29089
    canonical={cp:r["BCD"] for cp,r in assigned.items()}
    old=read(BASE)["rows"]
    prev4=read(BASE_D)
    prev5=read(V5_CODES)["rows"]
    scores={"v4.1":distribute({cp:r["BCD"] for cp,r in prev4.items()},sum(r["bDefault"] for r in old)),
            "v5-draft":distribute({cp:r["BCD"] for cp,r in prev5.items()},sum(r["bDefault"] for r in prev5.values())),
            "v6":distribute(canonical,sum(r["bDefault"] for r in assigned.values()))}
    assert prev4.keys()==prev5.keys()==assigned.keys()
    b_map=Counter(r["BCD"][0] for cp,r in assigned.items() if prev5[cp]["BCD"][0]=="G")
    errors=invariants(assigned,read(AUDIT))
    stat=dict(geometricCount=len(measures),rows=assigned,cells=cells,D=D_KEYS,regression=errors,
              comparison=scores,stability=threshold_metrics(assigned,measures),
              holdout=holdout(features,assigned),oldGTransitions=dict(b_map),
              emptyCells=empty_cells(cells,scores["v6"]["countsBC"]),
              visualDiagnostics=diagnostics(assigned,measures,scores["v6"]["countsBCD"]))
    for p,sha in hashes.items():
        assert digest(Path(p))==sha,p
    save(RESULT,stat|dict(inputSHA256=hashes))
    print("v6",scores["v6"]["bcUsed"],scores["v6"]["maxBCD"],stat["stability"],flush=True)
    print("Regressions",[(r["label"],r["actual"]) for r in errors if not r["passed"]],flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse",action="store_true",help="reuse the independently measured pixel features and t/b results")
    args=parser.parse_args()
    if not args.reuse:
        extract()
        analyze()
    experiment()
    from review import deliver
    deliver()
    assert all(r["passed"] for r in read(RESULT)["regression"]), "有锚点失败，详见验收报告"

