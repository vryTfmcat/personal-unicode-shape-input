"""Measure the 19 frozen size-reference warnings, without rerunning classification."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]


def run(out):
    import shape_overview as so
    from shape_experiment_features import render
    base=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/规范码2至4位效率核查'
    warnings=json.loads((base/'对象一致性与冗余线索.json').read_text(encoding='utf-8'))['wholeEmOnNonBody']
    o=so.get_overview();rows=[]
    longest=lambda b:max(b[2]-b[0],b[3]-b[1])
    band=lambda n:'z' if n<=.35 else 'x' if n<=.60 else 'c' if n<=.90 else 'v'
    for w in warnings:
        d=o.detail(w['cp'],True);objects={x['id']:x for x in d['objects']};obj=objects[w['objectId']]
        parent=obj.get('sourceSubjectBBox') or objects[w['objectId'].split(':contour-section')[0]+':body']['bbox']
        ratio=longest(obj['bbox'])/longest(parent)
        local_em=obj['extentEm']*ratio
        rows.append(dict(w,objectBBox=obj['bbox'],parentBBox=parent,spanRatio=ratio,recordedEm=obj['extentEm'],
                         visibleObjectEm=local_em,oldBand=band(obj['extentEm']),visibleObjectBand=band(local_em),
                         bandChanged=band(obj['extentEm'])!=band(local_em)))
    controls=[]
    for ch in ['D','(','◜']:
        d=o.detail(ord(ch),True);font=d['font'];p=Path(font['path'])
        if not p.exists():raise FileNotFoundError(p)
        _,extent=render(ch,p,font.get('index',0),size=96)
        r=next(r for r in rows if r['cp']==ord(ch))
        assert abs(extent-r['recordedEm'])<1e-12
        controls.append(dict(char=ch,size=96,renderedEm=extent,recordedEm=r['recordedEm'],fontSHA256=hashlib.sha256(p.read_bytes()).hexdigest()))
    report=dict(status='AI-measurement-not-new-human-rule',records=rows,controls=controls,
                checked=len(rows),numericDifferences=sum(abs(r['visibleObjectEm']-r['recordedEm'])>1e-12 for r in rows),
                bandDifferences=sum(r['bandChanged'] for r in rows),runtimeChanges=0,
                interpretation='可见弧段的最长边／字号；拟合完整圆的参照用于位置，不能将拟合直径擅自代入当前尺寸键。')
    out.mkdir(parents=True,exist_ok=True)
    (out/'19条尺寸参照复核.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('records','controls')},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);run(p.parse_args().output_dir)
