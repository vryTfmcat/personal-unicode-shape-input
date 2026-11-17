"""Pinned 1/7 whole-glyph scope proof and unaccepted additive candidate comparison.
No global thresholds, runtime datasets, authority, entity or public pages are written.
"""
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import numpy as np
from PIL import Image,ImageDraw,ImageFont

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
OUT=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/第一位分桶专项-20261025/1与7对象补验'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    if OUT.exists():raise SystemExit('拒绝覆盖已有补验现场')
    OUT.mkdir()
    baseline=OUT.parent/'a-c代表字筛选/验证.json'
    protected={ROOT/rel for rel in json.loads(baseline.read_text(encoding='utf-8'))['protectedHashes']}
    protected|=set((ROOT/'原型/键位编辑器').glob('*.py'))
    before={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    (OUT/'开始Git状态.txt').write_bytes(subprocess.check_output(['git','-c','core.quotepath=false','status','--porcelain=v1','-uall'],cwd=ROOT))
    import shape_overview as s
    from shape_stroke_topology_trial import render_locked,analyze
    from shape_stroke_continuation_trial import analyze_continuation
    from shape_experiment_features import render,observe
    from shape_recovery_geometry import visible_fork,two_stroke_angle
    from shape_lab_features import components
    v=s.get_overview()
    def api(endpoint,**params):
        with urlopen('http://127.0.0.1:8765/api/shape-overview/'+endpoint+'?'+urlencode(params),timeout=60) as r:return json.load(r)
    definitions={(r['position'],r['key']):r.get('meaning','未定义') for r in v.allocation_keys()}
    def gloss(code):return '；'.join(f'{i}/{k}＝{definitions[i,k]}' for i,k in enumerate(code,1))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
    records=[]
    for ch in '17TΓI':
        d=v.detail(ord(ch),True);locked=d['font'];mask,extent=render(ch,locked['path'],locked.get('index',0));f=observe(mask,extent)
        junctions=[]
        for j in f['junctionObjects']:
            box=j['coreBbox'];cx,cy=(box[0]+box[2]-1)/2,(box[1]+box[3]-1)/2
            yy,xx=np.indices(mask.shape);r2=(xx-cx)**2+(yy-cy)**2
            span=max(f['bbox'][2]-f['bbox'][0],f['bbox'][3]-f['bbox'][1]);radius=max(8.,min(12.,span*.20))
            ports=[len([p for p in components(mask&((r2>=(r-1.25)**2)&(r2<=(r+1.25)**2)),8) if p['area']>=2]) for r in (radius,radius+2)]
            junctions.append(dict(raw=j,ringPorts=ports,visibleProof=visible_fork(f,j)))
        glyph=Image.fromarray(255-mask.astype('uint8')*255).convert('RGB').resize((256,256),Image.Resampling.NEAREST)
        draw=ImageDraw.Draw(glyph)
        for j in junctions:
            box=j['raw']['coreBbox'];draw.rectangle(tuple(int(x*4) for x in box),outline='red',width=2)
        glyph.save(OUT/(format(ord(ch),'04x')+'-64原墨迹.png'))
        sheet=Image.new('RGB',(3*200,3*235),'white');draw=ImageDraw.Draw(sheet);variants=[];graphbaseline=None
        for i,(size,weight) in enumerate((size,weight) for size in (96,192,256) for weight in (-1,0,1)):
            m=render_locked(ch,locked,size=size,weight=weight);a=analyze(m);c=analyze_continuation(m,a)
            counts=dict(a['statistics'],**c['statistics']);sig={k:counts[k] for k in ('corners','forks','crosses','straightStrokes','curveStrokes','uncertainStrokes','loops')}
            vv=dict(size=size,weight=weight,maskSHA256=hashlib.sha256(m.tobytes()).hexdigest(),statistics=counts,
                signature=sig,topologyAgrees=c['topologyAgrees'],ambiguities=c['ambiguities'],
                prunedSpurCount=a['prunedSpurCount'],prunedSpurs=a['prunedSpurs'],junctions=a['junctions'])
            variants.append(vv)
            im=Image.fromarray(255-m.astype('uint8')*100).convert('RGB');idraw=ImageDraw.Draw(im)
            colors=['#005fbe','#ce3b1f','#008f4c','#a020a0']
            for stroke in c['strokes']:
                ps=[tuple(x) for x in stroke['points']]
                if len(ps)>1:idraw.line(ps,fill=colors[stroke['id']%4],width=2)
            for j in a['junctions']:
                x,y=j['xy'];idraw.ellipse((x-5,y-5,x+5,y+5),outline='red',width=2)
            for corner in a['corners']:
                x,y=corner['xy'];idraw.rectangle((x-4,y-4,x+4,y+4),outline='black',width=2)
            x=(i%3)*200;y=(i//3)*235;sheet.paste(im,(x,y));draw.text((x+2,y+193),f"{size}/{weight:+}: A{sig['corners']} B{sig['forks']} X{sig['crosses']}",font=font,fill='black');draw.text((x+2,y+212),f"straight={sig['straightStrokes']}, curve={sig['curveStrokes']}",font=font,fill='black')
            if (size,weight)==(192,0):graphbaseline=dict(graph=a,continuation=c)
        sheet.save(OUT/(format(ord(ch),'04x')+'-九扰动.png'))
        signature_hist=Counter(json.dumps(x['signature'],sort_keys=True) for x in variants)
        valid=all(x['topologyAgrees'] and not x['ambiguities'] and not x['statistics']['uncertainStrokes'] for x in variants)
        records.append(dict(char=ch,cp=ord(ch),font=dict(locked,sha256=sha(Path(locked['path']))),
            originalBucket=v.brief(ord(ch),True)['bucket'],originalFamily=v.brief(ord(ch),True)['familyKey'],
            oldRoutes=d['familyRoutes'],oldPaths=d['paths'],oldObjects=d['objects'],
            legacy64=dict(maskSHA256=hashlib.sha256(mask.tobytes()).hexdigest(),bbox=f['bbox'],ratio=f['ratio'],extent=f['extent'],
                endpoints=f['endpoints'],junctions=junctions,twoStrokeAngle=two_stroke_angle(f)),
            variants=variants,distinctSignatures=len(signature_hist),signatureHistogram=dict(signature_hist),
            allNineWholeStable=len(signature_hist)==1 and valid,allNineValid=valid,baselineGraph=graphbaseline))
    save('对象与九扰动证据.json',records)
    # These are isolated semantic candidates, not a second codebook. 1 is not
    # allowed to acquire count codes just because a subset of counts is stable.
    scenarios=[]
    for ch in '17':
        r=next(r for r in records if r['char']==ch);b=v.brief(ord(ch),True)
        proposals=['aaec','aavc']
        if ch=='7' and r['allNineWholeStable']:
            signature=r['variants'][0]['signature']
            if signature['corners']==1:proposals.append('aaau')
            if signature['straightStrokes']==2:proposals.append('aajb')
        new=[]
        for code in proposals:
            members=set(v.allocation_members(code));assert api('query',allocation=1,prefix=code)['total']==len(members)
            new.append(dict(code=code,gloss=gloss(code),beforeCandidates=len(members),
                afterCandidates=len(members|{ord(ch)}),beforeContainsTarget=ord(ch) in members,
                objectId=f'candidate-{ord(ch):04x}-whole-glyph',thirdFourthObjectSame=True,
                countEvidenceEligible=(not code[2] in 'abgjq' or r['allNineWholeStable'])))
        oldcounts={c:len(v.allocation_members(c)) for c in b['codes']}
        scenarios.append(dict(char=ch,cp=ord(ch),status='独立候选，未确认/未集成',
            beforeBucket=b['bucket'],proposedBucket='a',beforeFamily=b['familyKey'],proposedFamily='a',
            assumption='人判断锁定字形的整字可作为角折主体；未据机器稳定性代替形族确认',
            oldCodes=b['codes'],oldCodeCounts=oldcounts,newRoutes=new,
            pathsBefore=len(b['codes']),pathsAfter=len(b['codes'])+len(new),coverageDelta=0,
            preferredBefore=b['preferredCodes'],preferredAfter=b['preferredCodes'],
            bestBefore=min(oldcounts.values()),bestAfter=min([*oldcounts.values(),*[p['afterCandidates'] for p in new]]),
            limitations=('不生成角点/分叉计数，整套签名不稳；仅有基于已锁定整字对象的无孔/比例候选' if ch=='1' else '即使九扰动通过，仍须确认弯斜干与横顶能否按角折主体解释；64px严格双直角折检测未过'),
            learningCost='保留原路并增加a/a角折查法；须辨角折与钩/交叉，旧路仍存在；不是无记忆成本的均分',
            intake=False))
    # Shared new codes must count both targets once in each candidate group.
    joint={p['code']:{sc['cp'] for sc in scenarios if any(x['code']==p['code'] for x in sc['newRoutes'])} for sc in scenarios for p in sc['newRoutes']}
    jointdiff=[]
    for code,cps in sorted(joint.items()):jointdiff.append(dict(code=code,gloss=gloss(code),before=len(v.allocation_members(code)),after=len(set(v.allocation_members(code))|cps),addedCPs=sorted(cps)))
    save('独立候选与人数差异.json',dict(status='未实施',scenarios=scenarios,jointGroups=jointdiff,
        aliasesAdded=sum(len(x['newRoutes']) for x in scenarios),coverageDelta=0,oldPathsRetained=True,
        warning='单字afterCandidates为该字单独接入，jointGroups为两字共同接入；不可混用'))
    # Live replay is restricted to existing paths; new candidates have no live route.
    for sc in scenarios:
        for code,n in sc['oldCodeCounts'].items():
            assert api('query',allocation=1,prefix=code,text='U+'+format(sc['cp'],'X'))['total']==1
            assert api('query',allocation=1,prefix=code)['total']==n
    current={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    assert before==current,'其它专项或本轮改变了受保护文件，需重新核对后才认定通过'
    save('验证.json',dict(passed=True,protectedHashes=before,nineVariantsPerCharacter=True,characters=5,
        observations=45,thresholdsChanged=False,algorithmChanged=False,runtimeChanged=False,
        manualChanged=False,countsAreMachineObservationsNotHumanApproval=True,
        proposalPathChecks='新路只作独立集合模拟，不宣称线上可达'))
    print(json.dumps(dict(results=[{k:r[k] for k in ('char','distinctSignatures','allNineWholeStable')} for r in records],
        candidates=jointdiff,output=str(OUT)),ensure_ascii=False))


if __name__=='__main__':main()
