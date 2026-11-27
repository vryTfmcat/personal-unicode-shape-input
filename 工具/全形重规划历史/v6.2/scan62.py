"""Measure the v6.2 additions on the hashed locked raster sources."""
import json,sys
from pixels62 import *
from run61 import read,THRESHOLDS
MEASURED=OUT/"全域补测-v6.2.json"

def scan(examples=False):
    features={r["codepoint"]:r for r in read(INDEX)["rows"]}
    if examples:
        chars="⭛⤴ç𔕗𐖊ÞΦ⌲🢴🮖AĀ·•●✝<∧↶🡕↷↺↻⭯∪∩↗"
        features={cp:r for cp,r in features.items() if r["char"] in chars}
    a=read(LEDGER)["measurements"]
    b=read(SCAN)["measurements"]
    faces=font_manifest()
    hashes={}
    results={}
    for cp,gray in P["glyph_pages"](features,hashes):
        central=a[cp]["128"]
        em=None
        if central["holesRaw"]==0 and central["components"]==1 and central["circle"]>=.89:
            key=int(cp[2:],16)
            em=font_evidence(key,faces.get(key),hashes)
        res={}
        unique={}
        for t in THRESHOLDS:
            key=str(t)
            binary=(gray<t).tobytes()
            if binary not in unique:
                unique[binary]=extra(gray,t,a[cp][key]|b[cp][key],em)
            res[key]=unique[binary]
        results[cp]=res
        if examples:
            print(features[cp]["char"],res["128"])
        elif len(results)%5000==0:
            print("Measured",len(results),flush=True)
    if not examples:
        assert len(results)==29089
        with MEASURED.open("w",encoding="utf-8") as f:
            json.dump(dict(inputSHA256=hashes,measurements=results),f,ensure_ascii=False,separators=(",",":"))

if __name__=="__main__":
    scan("--examples" in sys.argv)

