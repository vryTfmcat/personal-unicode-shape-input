"""Verify additive z routes, unchanged old codes, and actual group ink."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont

from build_shape_keyboard_full import save
from shape_candidate_layers import CandidateLayers
from shape_experiment_features import observe,render
from shape_keyboard_trial import load,fingerprint,PROJECT
from shape_stroke_groups import stable_stroke_group


def audit(before,after,pilot):
    old_index,new_index=[load(p/'发布核对索引.json') for p in (before,after)]
    old,new=[{r['cp']:r for r in ix['records']} for ix in (old_index,new_index)]
    assert set(old)==set(new) and old_index['collections']==new_index['collections']
    assert old_index['unclassified']==new_index['unclassified']
    assert 'z' not in old_index['definitions']['third']
    assert new_index['definitions']['third']['z']['function']=='component.connected_horizontal_group'
    assert old_index['definitions']['fourth']==new_index['definitions']['fourth']
    assert all(v==new_index['definitions']['third'][k] for k,v in old_index['definitions']['third'].items())
    expected_pilot={r['cp']:r for r in load(pilot/'未定键笔画组对象.json')['records']}
    added,changed,groups=[],[],[]
    expected=defaultdict(set)
    rows=[]
    for path in sorted((after/'details').glob('*.json')):
        for row in load(path)['records']:
            cp=row['cp'];a,b=set(old[cp]['codes']),set(new[cp]['codes'])
            assert a<=b, row['char']
            assert old[cp]['bucket']==row['bucket'] and old[cp]['familyKey']==row['familyKey']
            assert set(old[cp]['preferredCodes'])<=set(new[cp]['preferredCodes'])
            delta=sorted(b-a)
            if delta:
                assert cp in expected_pilot and all(code[2]=='z' for code in delta)
                changed.append(cp);added.extend((cp,code) for code in delta)
            expected[row['bucket']].add(cp)
            for route in row['familyRoutes']:
                expected[route['bucket']+route['familyKey']].add(cp)
                if not route.get('connectedStrokeGroupEvidence'):
                    continue
                f=observe(*render(row['char'],row['font']['path'],row['font'].get('index',0)))
                group=stable_stroke_group(row,f)
                assert group is not None
                fresh={'proof':group['proof'],'stabilityProof':group['stabilityProof']}
                assert json.loads(json.dumps(fresh))==route['connectedStrokeGroupEvidence']
                assert np.array_equal(group['mask']|group['remainder'],f['body'])
                assert not (group['mask']&group['remainder']).any()
                assert group['object']['memberCount']==expected_pilot[cp]['count']
                groups.append({'cp':cp,'char':row['char'],'prefix':route['bucket']+route['familyKey'],
                               'count':group['object']['memberCount'],'proofVariants':9})
            for p in row['paths']:
                for n in range(1,len(p['code'])+1):
                    expected[p['code'][:n]].add(cp)
                if p['code'][2]=='z':
                    assert len(p['code'])==4
                    objects={o['id']:o for o in row['objects']}
                    for e in p['evidence']:
                        o=objects[e['objectId']]
                        assert e['objectId']==e['fourthObjectId']
                        assert o['groupType']=='connected-stroke-group' and o['kind']=='part-group'
            rows.append(row)
    assert set(changed)==set(expected_pilot)=={g['cp'] for g in groups}
    view=CandidateLayers(rows)
    assert set(expected)==set(view.entries)
    for prefix,cps in expected.items():
        result=view.query(prefix)
        assert result['mode']=='all' and set(result['candidates'])==cps
    for ch,code in [('E','chzt'),('F','chzb')]:
        assert code in new[ord(ch)]['preferredCodes']
        assert view.suggestions(ord(ch))[0]['code']==code
    assert all(not any(code[2]=='z' for code in new[ord(ch)]['codes']) for ch in 'TLI')
    assert new[ord('Q')]['codes']==old[ord('Q')]['codes']
    assert new[ord('Q')]['preferredCodes']==old[ord('Q')]['preferredCodes']
    assert 'ioym' in new[ord('Q')]['codes'] and 'ioym' not in new[ord('O')]['codes']
    provenance=load(after/'构建来源.json')
    assert all(fingerprint(PROJECT/'工具'/name)==sha for name,sha in provenance['codeHashes'].items())
    comparison=[]
    for code in ('chvc','chma','chzt','chzb','qhzt','iose','ioym'):
        comparison.append({'code':code,'before':sum(code in r['codes'] for r in old.values()),
                           'after':sum(code in r['codes'] for r in new.values())})
    report={'passed':True,'before':old_index['id'],'after':new_index['id'],
            'allOldCharacterCodePairsPreserved':True,'allOldPreferredPathsPreserved':True,
            'allFirstBucketsAndMainFamiliesUnchanged':True,'legacyKMeaningUnchanged':True,
            'onlyNewThirdKey':'z','newFourthBindings':False,
            'changedCharacters':len(changed),'addedCharacterCodePairs':len(added),
            'freshStableGroups':len(groups),'perturbationsPerGroup':9,
            'allPrefixCandidateSetsExactlyMatchRawData':True,'prefixesChecked':len(expected),
            'newlyFirstKeyOnly':0,'newlyDetailed':0,'coverageUnchanged':True,
            'codeComparisons':comparison,'groups':groups,
            'QExistingTailCodeVerified':'ioym','QRoundPreferencePreserved':True,
            'sourceCodeHashesMatch':True,'runtimeDeployed':False,
            'scope':'additive-contrast-entries-not-removal-of-broad-collision-codes'}
    save(after/'连接横笔组全量验收.json',report)
    draw_examples(after,rows,view)
    print(json.dumps({k:v for k,v in report.items() if k!='groups'},ensure_ascii=False))
    return report


def draw_examples(output,rows,view):
    selected={r['char']:r for r in rows if r['char'] in 'EFTLI'}
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    canvas=Image.new('RGB',(1120,760),'white'); draw=ImageDraw.Draw(canvas)
    for n,(ch,code) in enumerate([('E','chzt'),('F','chzb')]):
        row=selected[ch];f=observe(*render(ch,row['font']['path'],row['font'].get('index',0)))
        g=stable_stroke_group(row,f);y=n*250
        original=np.full((*f['mask'].shape,3),255,dtype='uint8');original[f['mask']]=0
        draw.text((12,y+8),f'{ch} 原字：一个连通墨块',font=font,fill='black')
        canvas.paste(Image.fromarray(original).resize((192,192),Image.Resampling.NEAREST),(12,y+38))
        pixels=np.full_like(original,255);pixels[f['mask']]=[205,205,205]
        for mask,color in zip(g['members'],[(20,105,150),(150,45,65),(45,135,90)]):
            pixels[mask]=color
        draw.text((270,y+8),f"实际横笔组：{g['object']['memberCount']}个成员",font=font,fill='black')
        canvas.paste(Image.fromarray(pixels).resize((192,192),Image.Resampling.NEAREST),(270,y+38))
        draw.text((530,y+60),f"{code}：全部 {view.query(code)['allCount']} 候选",font=font,fill='black')
        draw.text((530,y+92),'第三位 z 连接横笔组；第四位 t三个 / b两个。',font=font,fill='black')
        draw.text((530,y+124),'单笔横向，整组上下排列；原查法保留。',font=font,fill='black')
    for n,ch in enumerate('TLI'):
        row=selected[ch];f=observe(*render(ch,row['font']['path'],row['font'].get('index',0)))
        x=n*260+12
        draw.text((x,510),f'{ch}：不增加第三位z入口',font=font,fill='black')
        canvas.paste(Image.fromarray(255-f['mask'].astype('uint8')*255).resize((160,160),Image.Resampling.NEAREST),(x,545))
    draw.text((12,727),'颜色仅标识原有墨迹。独立试验已绑定z，现行编辑器和输入法尚未部署。',font=font,fill='black')
    canvas.save(output/'E-F横笔组新码.png')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--after',type=Path,required=True)
    p.add_argument('--pilot',type=Path,required=True)
    args=p.parse_args();audit(args.before,args.after,args.pilot)
