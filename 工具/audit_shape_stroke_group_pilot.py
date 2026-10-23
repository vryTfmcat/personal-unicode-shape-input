"""Unbound semantic pilot; compare slot choices without changing published codes."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont

from build_shape_keyboard_full import save
from shape_experiment_features import observe,render
from shape_keyboard_trial import load,fingerprint,PROJECT,DATA,ROOT,trial_properties
from shape_reviewed_components import cycle_subject
from shape_stroke_groups import VERSION,stable_stroke_group


def audit(source,output):
    assert not output.exists()
    index_path=source/'发布核对索引.json'
    index=load(index_path)
    protected=[index_path,DATA/'全形核对版.json',ROOT/'最新实验.json',source/'构建来源.json']
    hashes={str(p):fingerprint(p) for p in protected}
    entries=defaultdict(set)
    for row in index['records']:
        for code in row['codes']:
            entries[code].add(row['cp'])
    groups=[]; examples={}; canonical=0; inspected=0
    for path in sorted((source/'details').glob('*.json')):
        for row in load(path)['records']:
            if row['char'] in 'EFTLIQO':
                examples[row['char']]=row
            route=next((r for r in row['familyRoutes'] if r['target']=='body' and r['familyKey']=='h'),None)
            if not route:
                continue
            inspected+=1
            f=observe(*render(row['char'],row['font']['path'],row['font'].get('index',0)))
            g=stable_stroke_group(row,f)
            if g is None:
                continue
            prefix=route['bucket']+route['familyKey']
            count=g['object']['memberCount']; suffix='b' if count==2 else 't'
            assert (suffix,'选定构件组的成员数量') in trial_properties(g['object'],'h',index['definitions']['sizePolicy'])
            assert np.array_equal(g['mask']|g['remainder'],f['body'])
            assert not (g['mask']&g['remainder']).any()
            groups.append({'cp':row['cp'],'char':row['char'],'prefix':prefix,'count':count,'suffix':suffix,
                           'object':g['object'],'proof':g['proof'],'stabilityProof':g['stabilityProof']})
    buckets=defaultdict(set)
    for g in groups:
        buckets[(g['prefix'],g['suffix'])].add(g['cp'])
    comparisons=[]
    for (prefix,suffix),cps in sorted(buckets.items()):
        existing=entries[prefix+'k'+suffix]
        comparisons.append({'prefix':prefix,'quantityKey':suffix,'groupCount':2 if suffix=='b' else 3,
                            'newUnboundThirdSlotCandidates':len(cps),
                            'reuseKExistingCandidates':len(existing),'reuseKUnionCandidates':len(cps|existing),
                            'members':[chr(cp) for cp in sorted(cps)]})
    q=examples['Q']; qo={o['id']:o for o in q['objects']}
    q_choices=[]
    for path in q['paths']:
        if path['code'][2]=='y':
            q_choices.append({'code':path['code'],'candidates':len(entries[path['code']]),
                              'objects':[qo[e['objectId']] for e in path['evidence']],
                              'attributes':list({e['attribute'] for e in path['evidence']})})
    qf=observe(*render('Q',q['font']['path'],q['font'].get('index',0)))
    ring,tail,proof=cycle_subject(qf)
    assert np.array_equal(ring['mask']|tail,qf['body']) and not (ring['mask']&tail).any()
    assert q_choices
    assert not any(path['code'][2]=='y' for path in examples['O']['paths'])
    assert all(fingerprint(Path(p))==sha for p,sha in hashes.items())
    by_char={g['char']:g for g in groups}
    assert by_char['E']['count']==3 and by_char['F']['count']==2
    assert all(c not in by_char for c in 'TLI')
    report={'passed':True,'version':VERSION,'source':index['id'],
            'status':'unbound-third-slot-semantic-pilot-not-codebook-not-deployed',
            'ordinaryCharactersRead':len(index['records']),'existingForkBodyRoutesInspected':inspected,
            'stableConnectedStrokeGroups':len(groups),'comparisons':comparisons,
            'E_F_SeparatedByQuantity':True,'T_L_I_NotMiscounted':True,
            'thirdSlotAssigned':False,'kMeaningChanged':False,'keyboardBindingsChanged':False,
            'oldSourceCodebookHashesUnchanged':True,'protectedInputs':hashes,
            'QExistingTailChoices':q_choices,'QTailProof':proof,'OHasNoTailChoice':True,
            'QRoundPreferredEntryNotOverridden':True,'runtimeDeployed':False,
            'sourceHashes':{name:fingerprint(PROJECT/'工具'/name) for name in
                            ('shape_stroke_groups.py','audit_shape_stroke_group_pilot.py')}}
    save(output/'笔画组与附笔试验.json',report)
    save(output/'未定键笔画组对象.json',{'status':'semantic-only-no-third-key-binding','records':groups})
    make_figures(output,examples,by_char,qf,tail)
    print(json.dumps(report,ensure_ascii=False))
    return report


def make_figures(output,examples,groups,qf,tail):
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    canvas=Image.new('RGB',(1120,760),'white'); draw=ImageDraw.Draw(canvas)
    for n,ch in enumerate('EF'):
        row=examples[ch]; f=observe(*render(ch,row['font']['path'],row['font'].get('index',0)))
        result=stable_stroke_group(row,f); y=n*250
        original=np.full((*f['mask'].shape,3),255,dtype='uint8'); original[f['mask']]=0
        draw.text((12,y+8),f'{ch} 原字：一个连通墨块',font=font,fill='black')
        canvas.paste(Image.fromarray(original).resize((192,192),Image.Resampling.NEAREST),(12,y+38))
        pixels=np.full_like(original,255); pixels[f['mask']]=[205,205,205]
        for mask,color in zip(result['members'],[(20,105,150),(150,45,65),(45,135,90)]):
            pixels[mask]=color
        draw.text((270,y+8),f"实际横笔组：{result['object']['memberCount']}个成员",font=font,fill='black')
        canvas.paste(Image.fromarray(pixels).resize((192,192),Image.Resampling.NEAREST),(270,y+38))
        draw.text((530,y+60),'每个成员横向，整组上下排列。',font=font,fill='black')
        draw.text((530,y+92),'数量键分别为 t三个 / b两个；第三位未绑定。',font=font,fill='black')
    for n,ch in enumerate('TLI'):
        row=examples[ch]; f=observe(*render(ch,row['font']['path'],row['font'].get('index',0)))
        pixels=255-f['mask'].astype('uint8')*255
        x=n*260+12
        draw.text((x,510),f'{ch}：不生成横笔组',font=font,fill='black')
        canvas.paste(Image.fromarray(pixels).resize((160,160),Image.Resampling.NEAREST),(x,545))
    draw.text((12,727),'颜色仅标识原有墨迹；未补画、未把竖干或衬线当作额外横笔。',font=font,fill='black')
    canvas.save(output/'E-F横笔组与反例.png')
    canvas=Image.new('RGB',(820,360),'white'); draw=ImageDraw.Draw(canvas)
    for n,mask in enumerate([qf['mask'],tail]):
        pixels=np.full((*mask.shape,3),255,dtype='uint8'); pixels[qf['mask']]=[205,205,205]
        pixels[mask]=[0,0,0] if n==0 else [20,105,150]
        draw.text((n*400+12,10),'Q原字' if n==0 else '实际尾笔：使用现有第三位y',font=font,fill='black')
        canvas.paste(Image.fromarray(pixels).resize((256,256),Image.Resampling.NEAREST),(n*400+60,55))
    draw.text((12,328),'圆环入口保留；尾笔属性只描述这条实际尾笔，不借圆环的尺寸。',font=font,fill='black')
    canvas.save(output/'Q实际尾笔查法.png')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); audit(args.source,args.output)
