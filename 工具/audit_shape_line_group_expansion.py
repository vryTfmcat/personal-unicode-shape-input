"""Read every ordinary glyph; propose similar layer groups, never move buckets."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont

from audit_shape_historical_buckets import SOURCE,DEFAULT_OUTPUT as PILOT,protect,load
from build_shape_keyboard_full import save
from shape_experiment_features import bounds,render
from shape_historical_bucket_pilot import parallel_layers,ink_info,stable_probe

OUTPUT=SOURCE.parent/'20261022-u-line-group-expansion-v1'
PROJECT=Path(__file__).resolve().parents[1]
BOUNDARY_CHARS='EFH≠≈∴⫽'


def multi_segment_layers(info):
    """Broader visual queue only: permit three pieces in each layer and shorter pieces."""
    parts,mask=info['parts'],info['mask']
    if len(parts)<2 or sum(p['area'] for p in parts)<mask.sum()*.995:return None
    for axis in (0,1):
        along,across=('x','y') if axis==0 else ('y','x')
        lengths=np.array([p[along+'1']-p[along+'0'] for p in parts])
        widths=np.array([p[across+'1']-p[across+'0'] for p in parts])
        if (lengths/widths<1.5).any() or widths.max()/widths.min()>1.6:continue
        if any(p['area']/(length*width)<.85 for p,length,width in zip(parts,lengths,widths)):continue
        bands=[]
        for p in sorted(parts,key=lambda p:p['c'+across]):
            if not bands or abs(p['c'+across]-np.mean([b['c'+across] for b in bands[-1]]))>widths.mean()*.7:bands.append([])
            bands[-1].append(p)
        if len(bands)<2 or any(len(b) not in (1,2,3) for b in bands):continue
        spans=[max(p[along+'1'] for p in b)-min(p[along+'0'] for p in b) for b in bands]
        centres=[(max(p[along+'1'] for p in b)+min(p[along+'0'] for p in b))/2 for b in bands]
        if max(spans)/min(spans)>1.15 or np.ptp(centres)>max(spans)*.08:continue
        if any(len(b)>1 and max(p['area'] for p in b)/min(p['area'] for p in b)>1.5 for b in bands):continue
        gaps=np.diff([np.mean([p['c'+across] for p in b]) for b in bands])
        if gaps.min()<widths.mean()*1.1 or gaps.max()/gaps.min()>1.25:continue
        return {'memberDirection':'h' if axis==0 else 'i','arrangement':'i' if axis==0 else 'h',
                'layerCount':len(bands),'pieceCount':len(parts),'piecesPerLayer':[len(b) for b in bands],
                'bbox':info['bbox'],'ruleExpansionRequired':True,
                'scope':'visual-review-queue-only; does not relax accepted strict detector'}
    return None


def broad_stability(row,base,fonts):
    variants=[];signature=lambda o:(o['memberDirection'],o['layerCount'],tuple(o['piecesPerLayer']))
    for size in (48,96,128):
        for weight in (-1,0,1):
            try:
                mask,_=render(row['char'],row['font']['path'],row['font'].get('index',0),size=size,weight=weight,fonts=fonts)
                candidate=multi_segment_layers(ink_info(mask))
                good=candidate is not None and signature(candidate)==signature(base)
            except (OSError,ValueError):good=False
            variants.append({'size':size,'weight':weight,'passed':good})
    return {'passed':all(v['passed'] for v in variants),'variants':variants,
            'scope':'broader-proposal-only; not strict-definition acceptance'}


def sheet(output,name,records,maximum=120):
    selected=records[:maximum];cols=10; font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
    canvas=Image.new('RGB',(1120,48+max(1,(len(selected)+cols-1)//cols)*104),'white');draw=ImageDraw.Draw(canvas)
    draw.text((10,10),name.replace('.png','')+' · 原锁定字形，候选不是已迁移',font=font,fill='black')
    sprites={}
    for i,r in enumerate(selected):
        p=r['preview'];path=PROJECT/'原型/键位编辑器'/p['url']
        if str(path) not in sprites:sprites[str(path)]=Image.open(path).convert('RGB')
        x=10+(i%cols)*111;y=40+(i//cols)*104
        canvas.paste(sprites[str(path)].crop((p['x'],p['y'],p['x']+64,p['y']+64)),(x,y))
        draw.text((x,y+65),f'U+{r["cp"]:04X}',font=font,fill='black')
        obj=r.get('strictObject') or r.get('broadObject')
        if obj:draw.text((x,y+82),f"{obj['layerCount']}层 / {obj['pieceCount']}块",font=font,fill='#486267')
    canvas.save(output/name)


def build():
    if OUTPUT.exists():raise FileExistsError('不覆盖已有候选审议结果')
    before=protect();pilot=load(PILOT/'历史桶整理与新用途试验.json')
    current=set(pilot['trials']['u']['cps']);records=[];boundaries=[];sprites={};fonts={};scanned=0
    for number,path in enumerate(sorted((SOURCE/'details').glob('*.json'))):
        chunk=load(path)
        for row in chunk['records']:
            scanned+=1;parts=row.get('features',{}).get('parts',[])
            if row['char'] in BOUNDARY_CHARS:
                boundaries.append({k:row.get(k) for k in ('cp','char','bucket','preview','font','familyKey')})
            if len(parts)<2:continue
            # Only a necessary axis-aligned aspect test; all surviving ink is then checked.
            if not any(all((p[axis+'1']-p[axis+'0'])/(p[other+'1']-p[other+'0'])>=1.5
                           for p in parts) for axis,other in [('x','y'),('y','x')]):continue
            p=row['preview'];sprite=PROJECT/'原型/键位编辑器'/p['url']
            if str(sprite) not in sprites:sprites[str(sprite)]=Image.open(sprite).convert('L')
            mask=np.array(sprites[str(sprite)].crop((p['x'],p['y'],p['x']+64,p['y']+64)))<128
            info={'mask':mask,'parts':parts,'bbox':bounds(mask)}
            strict=parallel_layers(info);broad=multi_segment_layers(info)
            if strict is None and broad is None:continue
            stable=stable_probe(row,parallel_layers,fonts) if strict else None
            broad_check=broad_stability(row,broad,fonts) if broad and not strict else None
            existing=row['cp'] in current
            category=('原u已保留42字' if existing else
                      '同一定义稳定新候选' if strict and stable['passed'] else
                      '同形线群但检测不稳定' if strict else
                      '多段层列扩展候选')
            records.append({k:row.get(k) for k in ('cp','char','bucket','familyKey','preview','font','oldReviewed','codes')}|
                           {'category':category,'alreadyInU':existing,'strictObject':strict,'strictStability':stable,
                            'broadObject':broad,'broadStability':broad_check,
                            'alternateFontDisagreement':'alternate-font-disagreement' in row.get('warnings',[]),
                            'migrationApplied':False,'newCodeApplied':False})
        if (number+1)%40==0:print(f'已读 {scanned}/28223 字，发现 {len(records)} 个线群近似对象',flush=True)
    assert scanned==28223 and before==protect()
    assert current<={r['cp'] for r in records if r['alreadyInU']}
    groups={name:[r for r in records if r['category']==name] for name in
            ['原u已保留42字','同一定义稳定新候选','同形线群但检测不稳定','多段层列扩展候选']}
    report={'version':'u-layer-expansion-scan-20261022-v1','date':'2026-10-22',
            'source':chunk['experimentId'],'sourceIndexSHA256':before[str((SOURCE/'发布核对索引.json').relative_to(PROJECT))],
            'ordinaryScanned':scanned,'currentUCount':42,'groupCounts':{k:len(v) for k,v in groups.items()},
            'records':records,'boundaries':boundaries,'runtimeDeployed':False,'bucketsChanged':False,
            'protectedHashes':before,'protectedInputsUnchanged':True,
            'strictStableNewByLayers':dict(Counter(str(r['strictObject']['layerCount']) for r in groups['同一定义稳定新候选'])),
            'measurementExplanation':{'font':'同一锁定字体，不更换字体',
                                      'sourceSizes':[48,96,128],'normalizedCanvas':[64,64],
                                      'inkPerturbations':[-1,0,1],
                                      'meaning':'字号重新栅格化并归一64像素；墨迹做一像素收缩、原样、膨胀，模拟粗细，不是字体真实粗体字重',
                                      'notEvidenceOf':['查找习惯自然','跨字体相同','字符应迁移主桶','唯一编码']},
            'limitations':['只扫描28223个普通字符；全局未分类5220字和xyz保留集合未纳入本轮。',
                           '严格规则限横／竖、每层一或两段且规则对齐；三段层列只列扩展候选。',
                           '不稳定候选仍展示，不能把检测失败直接解释成字形不相似。',
                           '不自动迁移已有主桶，不改已有编码；优先考虑增加u补充入口。'],
            'sourceHashes':{Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    save(OUTPUT/'u线群全量近似候选.json',report)
    for name,items in groups.items():sheet(OUTPUT,name+'.png',items)
    sheet(OUTPUT,'边界对照.png',boundaries)
    save(OUTPUT/'验收.json',{'passed':True,'ordinaryRead':28223,'current42Retained':True,
                           'protectedInputsUnchanged':True,'bucketsChanged':False,'runtimeDeployed':False})
    print(json.dumps({'groups':report['groupCounts'],'newStableLayers':report['strictStableNewByLayers'],
                      'stableExamples':''.join(r['char'] for r in groups['同一定义稳定新候选']),
                      'unstableExamples':''.join(r['char'] for r in groups['同形线群但检测不稳定']),
                      'broadExamples':''.join(r['char'] for r in groups['多段层列扩展候选'])},ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':build()
