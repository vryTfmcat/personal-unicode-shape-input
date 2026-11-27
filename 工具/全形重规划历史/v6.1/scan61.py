"""Supplement the hashed v6 baseline, keeping pixel evidence and source identities separate."""
import argparse,json
from pixels61 import *

BASE=OUT.parent/"整体重规划-20261124-v6-BCD规则重构"
LEDGER=BASE/"全域特征补测-29096-v6.json"
INDEX=V41/"全域特征标注-29096-v4.1.json"
SCAN=OUT/"全域像素补测-v6.1.json"
EXAMPLES="↶↷↺↻⭯ဉ🡆🡕𒾴🗸✔𝟣𝚌𝗨⸤⅃լ┐7◧◩🆉🅲⑦➀🄾🅳"

def scan(examples=False):
    ledger=read(LEDGER)
    rows={r["codepoint"]:r for r in read(INDEX)["rows"] if not examples or r["char"] in EXAMPLES}
    hashes={}
    measurements={}
    for cp,gray in P["glyph_pages"](rows,hashes):
        by_threshold={}
        cache={}
        for t in THRESHOLDS:
            key=str(t)
            m=ledger["measurements"][cp][key]
            maskkey=(gray<t).tobytes()
            if maskkey not in cache:
                merged=supplement(gray,t,m)
                cache[maskkey]={k:merged[k] for k in ("inner","hole","hinge","curved","bodyGeo","rBelow","arrowProfile")}
            by_threshold[key]=cache[maskkey]
        measurements[cp]=by_threshold
        if examples:
            d=by_threshold["128"]
            print(rows[cp]["char"],d["curved"],d["hinge"],d["inner"],d["hole"],flush=True)
        elif len(measurements)%5000==0:
            print(len(measurements),flush=True)
    if not examples:
        assert len(measurements)==29089
        with SCAN.open("w",encoding="utf-8") as f:
            json.dump(dict(measurements=measurements,inputSHA256=hashes),f,ensure_ascii=False,separators=(",",":"))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--examples",action="store_true")
    scan(parser.parse_args().examples)

