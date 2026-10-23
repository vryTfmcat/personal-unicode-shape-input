"""Verify extracted ink, preserve candidate sets, and prepare lookup comparisons."""
import argparse
import json
from collections import Counter,defaultdict
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont

from build_shape_keyboard_full import save
from shape_candidate_layers import CandidateLayers,LAYERS
from shape_connected_frames import connected_frames,border_spines
from shape_experiment_features import render,observe
from shape_keyboard_trial import load
from shape_reviewed_routes import references


def audit(before,after):
    previous=load(before/'发布核对索引.json')
    current=load(after/'发布核对索引.json')
    old={r['cp']:r for r in previous['records']}
    new={r['cp']:r for r in current['records']}
    assert set(old)==set(new)
    decisions=current['definitions'].get('frameLookupDecisions',{})
    rejected=decisions.get('rejectedBorderSpines',[])
    authorized=[]
    removed_routes=[]
    program={r['cp']:{(p['familyKey'],p['target']) for p in r.get('collisionSanityExclusions',[])}
             for path in sorted((after/'details').glob('*.json')) for r in load(path)['records']
             if r.get('collisionSanityExclusions')}
    program_removals=[]
    for cp,row in old.items():
        removed=set(row['codes'])-set(new[cp]['codes'])
        if removed:
            explicit=any(d['char']==row['char'] and d['orientation']==0 for d in rejected)
            if explicit:
                assert removed <= {'wllg','wllh','wlls','wllv'}
            else:
                assert all((code[1],'body') in program.get(cp,set()) for code in removed)
                program_removals.append(row['char'])
            authorized.append({'char':row['char'],'codes':sorted(removed),
                               'reason':'explicit-human-rejection' if explicit else 'fresh-negative-geometry-certificate'})
        a={(r['bucket'],r['familyKey'],r['target']) for r in row['familyRoutes']}
        b={(r['bucket'],r['familyKey'],r['target']) for r in new[cp]['familyRoutes']}
        for route in a-b:
            explicit=any(d['char']==row['char'] and d['orientation']==0 for d in rejected)
            assert ((explicit and route[1]=='l' and route[2].startswith('border-spine-'))
                    or (route[1],route[2]) in program.get(cp,set()))
            removed_routes.append({'char':row['char'],'route':route})
    assert all(r['bucket']==new[cp]['bucket'] or cp in program for cp,r in old.items())
    expected=defaultdict(set)
    selected={}
    verified=Counter()
    views=references(Path('C:/Windows/Fonts/seguisym.ttf'))['familyViews']
    def rows():
        for path in sorted((after/'details').glob('*.json')):
            for row in load(path)['records']:
                cp=row['cp']
                expected[row['bucket']].add(cp)
                for route in row['familyRoutes']:
                    expected[route['bucket']+route['familyKey']].add(cp)
                for p in row['paths']:
                    for n in range(1,len(p['code'])+1):
                        expected[p['code'][:n]].add(cp)
                if any(r.get('frameEvidence') or r.get('spineEvidence') or r.get('reviewedLoopEvidence') for r in row['familyRoutes']):
                    font=row['font']
                    f=observe(*render(row['char'],font['path'],font.get('index',0)))
                    frames=connected_frames(f,views)
                    spines=border_spines(f)
                    for route in row['familyRoutes']:
                        if route.get('reviewedLoopEvidence'):
                            assert row['char']==decisions['irregularLoopSupplement']['char']
                            assert route['familyKey']=='p' and route['supplementOnly']
                            part=next(p for p in connected_frames(f,views,True) if p['target']==route['target'])
                            assert json.loads(json.dumps(part['proof']))==route['reviewedLoopEvidence']
                            assert part['familyKey'] is None
                            assert np.array_equal(part['feature']['mask']|part['remainder'],f['body'])
                            assert not (part['feature']['mask']&part['remainder']).any()
                            verified['humanReviewedIrregularLoopPartitions']+=1
                        if route.get('frameEvidence'):
                            part=next(p for p in frames if p['target']==route['target'])
                            assert json.loads(json.dumps(part['proof']))==route['frameEvidence']
                            assert np.array_equal(part['feature']['mask']|part['remainder'],f['body'])
                            assert not (part['feature']['mask']&part['remainder']).any()
                            verified['actualFramePartitions']+=1
                        if route.get('spineEvidence'):
                            part=next(p for p in spines if p['target']==route['target'])
                            assert part['proof']==route['spineEvidence']
                            assert not (part['mask']&~f['body']).any()
                            verified['actualSpinePartitions']+=1
                if row['char'] in '𒌒𒌷𒀖ﻄᕣTᵏJ7○●□■☆★YEF3':
                    selected[cp]=row
                yield row
    index=CandidateLayers(rows())
    assert set(expected)==set(index.entries)
    for prefix,cps in expected.items():
        result=index.query(prefix)
        assert set(result['candidates'])==cps
        assert sum(len(v) for v in result['groups'].values())==len(cps)
        assert set(index.query(prefix,'focused')['candidates'])<=cps
    report=load(after/'容量与差异报告.json')
    codes=list(dict.fromkeys(['q','qh','qhm','chvc','chec','ajvg','crvg','iocv']+[g['code'] for g in report['topCollisions'][:12]]))
    comparisons=[]
    for code in codes:
        q=index.query(code)
        old_members={cp for cp,r in old.items() if (len(code)==1 and r['bucket']==code)
                     or any(c.startswith(code) for c in r['codes'])
                     or (len(code)==2 and any(rr['bucket']+rr['familyKey']==code for rr in r['familyRoutes']))}
        comparisons.append({'code':code,'beforeAll':len(old_members),'afterAll':q['allCount'],
                            'afterFocused':q['focusedCount'],'groupCounts':{k:len(v) for k,v in q['groups'].items()},
                            'samples':{k:[index.characters[cp] for cp in v[:12]] for k,v in q['groups'].items()}})
    suggestions=[]
    for cp,row in selected.items():
        if row['char'] in 'TYEF3J7○●□■☆★':
            suggestions.append({'char':row['char'],'choices':index.suggestions(cp),
                                'status':'candidate-count-based-not-human-naturalness-confirmation'})
    summary={'passed':True,'run':current['id'],'allOldCharacterCodePairsPreserved':not authorized,
             'allRemovalsAccountedFor':True,'onlyExplicitlyRejectedPathsRemoved':not program_removals,
             'negativeCertificateRemovalCharacters':program_removals,'authorizedRemovedCodes':authorized,
             'authorizedRemovedRoutes':removed_routes,
             'allPrefixCandidateSetsExactlyMatchRawData':True,'prefixesChecked':len(expected),
             'focusedIsExplicitSubsetNotCodeDeletion':True,'freshInkChecks':dict(verified),
             'status':'independent-query-proposal-not-deployed','comparisons':comparisons,'suggestions':suggestions}
    save(after/'外框与候选分层验收.json',summary)
    make_figures(after,selected,index,views)
    print({k:v for k,v in summary.items() if k not in ('comparisons','suggestions')})
    print([(r['code'],r['beforeAll'],r['afterAll'],r['afterFocused'],r['groupCounts']) for r in comparisons[:8]])
    print(suggestions[:4])
    return summary


def make_figures(output,selected,index,views):
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
    small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',17)
    canvas=Image.new('RGB',(1200,1040),'white')
    draw=ImageDraw.Draw(canvas)
    for n,char in enumerate('𒌒𒌷𒀖ﻄ'):
        row=selected[ord(char)]
        f=observe(*render(char,row['font']['path'],row['font'].get('index',0)))
        frames=connected_frames(f,views)
        spines=border_spines(f)
        active={r['target'] for r in row['familyRoutes'] if r.get('frameEvidence') or r.get('spineEvidence')}
        parts=[p for p in (frames if frames else spines) if p['target'] in active]
        y=n*250
        draw.text((12,y+8),f'U+{ord(char):04X} 原字',font=font,fill='black')
        base=np.full((*f['mask'].shape,3),255,dtype='uint8')
        base[f['mask']]=[0,0,0]
        canvas.paste(Image.fromarray(base).resize((192,192),Image.Resampling.NEAREST),(12,y+40))
        if not parts:
            draw.text((270,y+60),'本人不采用长横线入口；保留原字与第一位',font=font,fill='black')
        for i,part in enumerate(parts[:3]):
            mask=part['feature']['mask'] if frames else part['mask']
            pixels=np.full_like(base,255)
            pixels[f['mask']]=[210,210,210]
            pixels[mask]=[20,105,150]
            x=270+i*300
            label='四边框构件' if frames else '完整主干构件'
            draw.text((x,y+8),label+f' {i+1}',font=font,fill='black')
            canvas.paste(Image.fromarray(pixels).resize((192,192),Image.Resampling.NEAREST),(x,y+40))
    draw.text((12,1007),'蓝色均为实际墨迹；灰色不属于这条路径选中的对象。未把整字自动改判为四边形或线条。',font=font,fill='black')
    canvas.save(output/'查法核对-连接外框与主干.png')
    row=selected[ord('T')]
    f=observe(*render('T',row['font']['path'],row['font'].get('index',0)))
    canvas=Image.new('RGB',(1000,380),'white')
    draw=ImageDraw.Draw(canvas)
    objects={o['id']:o for o in row['objects']}
    for n,(code,title) in enumerate([('chvc','整字纵长／中尺寸'),('chmw','分叉交点在上方')]):
        path=next(p for p in row['paths'] if p['code']==code)
        obj=objects[path['evidence'][0]['objectId']]
        yy,xx=np.indices(f['mask'].shape)
        b=obj['bbox']
        mask=f['mask']&(xx>=b[0])&(xx<b[2])&(yy>=b[1])&(yy<b[3])
        pixels=np.full((*mask.shape,3),255,dtype='uint8')
        pixels[f['mask']]=[210,210,210]
        pixels[mask]=[20,105,150]
        x=n*500+16
        q=index.query(code)
        draw.text((x,10),title,font=font,fill='black')
        draw.text((x,40),f'{code}  全部 {q["allCount"]} / 主体与可靠构件 {q["focusedCount"]}',font=font,fill='black')
        canvas.paste(Image.fromarray(pixels).resize((256,256),Image.Resampling.NEAREST),(x+70,90))
    draw.text((12,350),'两条路径都保留。右图只定位交点，不把检测窗口的大小作为尺寸。',font=font,fill='black')
    canvas.save(output/'查法核对-T的两种对象.png')
    row=selected[ord('ᕣ')]
    f=observe(*render('ᕣ',row['font']['path'],row['font'].get('index',0)))
    raw=connected_frames(f,views,include_unclassified=True)
    part=next(p for p in raw if p['familyKey'] is None)
    canvas=Image.new('RGB',(820,360),'white')
    draw=ImageDraw.Draw(canvas)
    for n,mask in enumerate([f['mask'],part['feature']['mask']]):
        pixels=np.full((*mask.shape,3),255,dtype='uint8')
        pixels[f['mask']]=[210,210,210]
        pixels[mask]=[0,0,0] if n==0 else [20,105,150]
        assigned=any(r.get('reviewedLoopEvidence') for r in row['familyRoutes'])
        draw.text((n*400+12,10),'原字' if n==0 else ('已确认：不规则回环 ipwe' if assigned else '下部闭合小环：尚未分配这条入口'),font=font,fill='black')
        canvas.paste(Image.fromarray(pixels).resize((256,256),Image.Resampling.NEAREST),(n*400+60,55))
    draw.text((12,328),'实际墨迹分离；该小环形族依本人答复，不扩展为全部异形孔洞规则。' if assigned else '本图只展示真实分离对象，不把它自动认作圆形或不规则回环。',font=font,fill='black')
    canvas.save(output/'查法核对-未归族小环.png')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--after',type=Path,required=True)
    args=p.parse_args()
    audit(args.before,args.after)
