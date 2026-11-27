"""Extract independent threshold features without reading the holdout labels."""
from geometry import *
import json
import sys

FEATURES = V41 / "全域特征标注-29096-v4.1.json"
PRIOR = V5 / "全域特征补测-29096-v5-draft.json"
OUTPUT = OUT / "全域特征补测-29096-v6.json"
LOCKED = V41 / "BC分配-全域-v4.py"

def save(path,obj):
    with path.open("w",encoding="utf-8",newline="\n") as file:
        json.dump(obj,file,ensure_ascii=False,separators=(",",":"))

def extract():
    hashes={}
    for p in (FEATURES,PRIOR,MANIFEST,V5/"stage3.py",LOCKED,
              V41/"生成全域特征标注.py",V41/"BCD分配-D层三方案.py"):
        checksummed(p,hashes)
    faces=font_manifest()
    features={r["codepoint"]:r for r in read(FEATURES)["rows"]}
    higher=read(PRIOR)["measurements"]
    measures={}
    examples=len(sys.argv)>1 and sys.argv[1]=="--examples"
    test_chars="🭮▲▼■◆●🡕➲⮞Ԑ+×✳✦∗%ộŤĐ𝔻ᵒₒ°º"
    if examples:
        features={cp:r for cp,r in features.items() if r["char"] in test_chars}
    for cp,gray in P["glyph_pages"](features,hashes):
        masks={}
        ms={}
        for t in THRESHOLDS:
            key=(gray<t).tobytes()
            if key not in masks:
                masks[key]=measure(gray,t,higher[cp][str(t)])
            ms[str(t)]=masks[key]
        ms["position"]=placement(int(cp[2:],16),faces.get(int(cp[2:],16)),hashes) if ms["128"]["circle"]>=.87 else ""
        measures[cp]=ms
        if examples:
            m=ms["128"]
            fields="holesRaw circle hull polygon shape tip body bands midBands midBranch leftBands rightBands stems topBeam gaps rays arrow parallel".split()
            print(features[cp]["char"],ms["position"],' '.join(f"{k}={m[k]}" for k in fields))
        elif len(measures)%5000==0:
            print("Measured",len(measures),flush=True)
    if examples:
        save(OUT/"锚点测量临时.json",measures)
    else:
        assert len(measures)==29089 and all(all(v[str(t)] for t in THRESHOLDS) for v in measures.values())
        save(OUTPUT,dict(thresholds=THRESHOLDS,inputSHA256=hashes,measurements=measures))
if __name__=="__main__":
    extract()

