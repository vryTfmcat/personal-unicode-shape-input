"""Audit proven withdrawals, unknowns, and existing object-bound alternatives."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from build_shape_keyboard_full import save
from shape_candidate_layers import CandidateLayers
from shape_collision_sanity import certify
from shape_experiment_detector import dot_group
from shape_experiment_features import observe, render, component_mask, normalized
from shape_keyboard_trial import load, fingerprint, PROJECT
from shape_recovery_geometry import visible_fork
from shape_reviewed_components import cycle_subject
from shape_reviewed_routes import references


CODES = ('chvc','mdez','ajvg','cxvc','iocv','crvg')


def feature_for(row, route, f):
    if route['target']=='body':
        return f
    if route.get('componentPartitionProof'):
        return cycle_subject(f)[0]
    boxes = [o['bbox'] for o in row['objects'] if o['kind']=='body'
             and o['id'].startswith(route['target']+':'+route['familyKey']+':')]
    for part in f['parts']:
        box=[part[k] for k in ('x0','y0','x1','y1')]
        if box in boxes or box==route.get('componentEvidence',{}).get('bbox'):
            extent=f['extent']*max(box[2]-box[0],box[3]-box[1])/max(f['bbox'][2]-f['bbox'][0],f['bbox'][3]-f['bbox'][1])
            return observe(component_mask(f['mask'],part),extent)
    return None


def support(route, f, templates):
    if f is None:
        return False, '无法从当前原字独立复原所选对象；待复核'
    family=route['familyKey']
    if family=='d':
        return dot_group(f), '紧凑实心点或点组复核'
    if family=='o':
        error=float(np.min(np.mean((templates['familyViews']['o']-normalized(f['silhouette']))**2,axis=(1,2))))
        return error<=.035 and len(f['parts'])==1, '实际所选对象的圆轮廓强匹配'
    if family=='j':
        error=float(np.min(np.mean((templates['hookViews']-normalized(f['body']))**2,axis=(1,2))))
        return error<=.07, '实际所选对象的钩弯墨迹强匹配'
    if family in 'hxr':
        arms={'h':(3,4),'x':(4,),'r':range(5,17)}[family]
        valid=any(visible_fork(f,j,arms) for j in f['junctionObjects'])
        if family=='r':
            error=float(np.min(np.mean((templates['radialViews']-normalized(f['body']))**2,axis=(1,2))))
            valid=valid or error<=.065
        return bool(valid), '实际交点出口或星芒墨迹复核；不等于整字主族人工确认'
    return False, '本轮未建立该族独立正证据'


def property_category(path, objects):
    categories=set()
    for e in path['evidence']:
        o=objects[e['objectId']]
        if len(path['code'])!=4:
            continue
        k=path['code'][-1]
        if o['kind']=='junction' and k in 'adwsjknm':
            categories.add('交点相对主体位置')
        if o.get('fill') and k in 'ef':
            categories.add('所选轮廓空心／实心')
        if o['kind']=='part-group' and k in 'bt':
            categories.add('构件组数量')
        if o['kind']=='part-group' and '排列轴' in e['attribute']:
            categories.add('构件组排列')
        if o.get('triangleDirection') and k in 'ws':
            categories.add('三点组尖端朝向')
        if o.get('orientationMode')=='cross' and k in 'gq':
            categories.add('所选交叉的轴向／斜置')
    return sorted(categories)


def audit(before,after):
    old_index,new_index=[load(p/'发布核对索引.json') for p in (before,after)]
    old,new=[{r['cp']:r for r in ix['records']} for ix in (old_index,new_index)]
    assert set(old)==set(new) and old_index['collections']==new_index['collections']
    assert old_index['unclassified']==new_index['unclassified']
    rows=[r for p in sorted((after/'details').glob('*.json')) for r in load(p)['records']]
    approved={r['char']:r for r in rows if r['char'] in '𒌒𒌷𒀖ﻄᕣT'}
    assert approved['T']['paths'][0]['code']=='chmw' and approved['T']['paths'][0]['preferred']
    assert not any(r.get('spineEvidence',{}).get('orientation')==0 for r in approved['ﻄ']['familyRoutes'])
    assert any(r.get('reviewedLoopEvidence') and r['familyKey']=='p' for r in approved['ᕣ']['familyRoutes'])
    for char in '𒌒𒌷𒀖':
        assert any(r.get('frameEvidence') and r.get('reviewedRetain') and r['familyKey']=='s' for r in approved[char]['familyRoutes'])
    old_rows={r['cp']:r for p in sorted((before/'details').glob('*.json')) for r in load(p)['records']}
    view=CandidateLayers(rows)
    templates=references(Path('C:/Windows/Fonts/seguisym.ttf'))
    exclusions,unexpected,whole_primary_changes=[],[],[]
    geometry={}
    selected={r['cp'] for r in rows if any(p['code'] in CODES for p in r['paths']) or r.get('collisionSanityExclusions')}
    for row in rows:
        cp=row['cp']
        old_routes={(r['familyKey'],r['target']) for r in old_rows[cp]['familyRoutes']}
        new_routes={(r['familyKey'],r['target']) for r in row['familyRoutes']}
        proofs=row.get('collisionSanityExclusions',[])
        proved={(p['familyKey'],p['target']) for p in proofs}
        if old_routes-new_routes:
            assert old_routes-new_routes<=proved, (row['char'],old_routes-new_routes,proved)
        for path in old_rows[cp]['paths']:
            if path['code'] in new[cp]['codes']:
                continue
            assert all((path['code'][1],e['familyTarget']) in proved for e in path['evidence']), row['char']
        if old[cp]['familyKey']!=row['familyKey'] or old[cp]['bucket']!=row['bucket']:
            assert proofs
            whole_primary_changes.append({'char':row['char'],'before':old[cp]['familyKey'],'after':row['familyKey'],
                                          'beforeBucket':old[cp]['bucket'],'afterBucket':row['bucket'],
                                          'oldReviewed':row['oldReviewed'],'runtimeMigrationApproved':False})
        if cp not in selected:
            continue
        f=observe(*render(row['char'],row['font']['path'],row['font'].get('index',0)))
        geometry[cp]=f
        for proof in proofs:
            fresh=certify(row,f,proof['familyKey'])
            assert json.loads(json.dumps(fresh))==proof
            exclusions.append({'cp':cp,'char':row['char'],'familyKey':proof['familyKey'],'proof':proof})
    groups=[]
    same_cohort={cp for cp in old if old[cp]['codes'] and new[cp]['codes']}
    for code in CODES:
        old_members={cp for cp,r in old.items() if code in r['codes']}
        members={cp for cp,r in new.items() if code in r['codes']}
        verified,uncertain,alternatives=[],[],[]
        status_counts=Counter()
        for row in rows:
            if row['cp'] not in members:
                continue
            cp=row['cp']; f=geometry[cp]
            route_support={}
            route_features={}
            for route in row['familyRoutes']:
                if route['familyKey']!=code[1]:
                    continue
                rf=feature_for(row,route,f)
                key=(route['bucket']+route['familyKey'],route['target'])
                route_features[key]=rf
                route_support[key]=support(route,rf,templates)[0]
            path=next(p for p in row['paths'] if p['code']==code)
            ok=False
            objects={o['id']:o for o in row['objects']}
            for e in path['evidence']:
                key=(code[:2],e['familyTarget'])
                rf=route_features[key]
                owned=route_support[key]
                if objects[e['objectId']]['kind']=='hole' and rf is not None:
                    owned=owned and any(objects[e['objectId']]['bbox']==[h[k] for k in ('x0','y0','x1','y1')] for h in rf['holes'])
                ok=ok or owned
            (verified if ok else uncertain).append(cp)
            if not ok:
                continue
            choices=[]
            for p in row['paths']:
                if p['code']==code or p['code'][1]!=code[1]:
                    continue
                categories=property_category(p,objects)
                if code[1] not in 'hxr':
                    categories=[c for c in categories if c!='交点相对主体位置']
                if not categories:
                    continue
                accepted=[]
                for e in p['evidence']:
                    key=(p['code'][:2],e['familyTarget'])
                    if not route_support.get(key):
                        continue
                    o=objects[e['objectId']]; rf=route_features[key]
                    if o['kind']=='junction':
                        suffix=o['id'].rsplit(':',1)[-1]
                        if not suffix.startswith('junction-'):
                            continue
                        n=int(suffix.split('-')[-1])
                        arms=range(5,17) if code[1]=='r' else (4,) if code[1]=='x' else (3,4)
                        if n>=len(rf['junctionObjects']) or not visible_fork(rf,rf['junctionObjects'][n],arms):
                            continue
                    accepted.append(e['objectId'])
                if accepted:
                    choices.append({'code':p['code'],'allCandidates':view.query(p['code'])['allCount'],
                                    'categories':categories,'objectIds':accepted,'preferred':p['preferred']})
            choices.sort(key=lambda c:(not c['preferred'],c['allCandidates'],c['code']))
            if choices:
                alternatives.append({'char':row['char'],'cp':cp,'choices':choices[:3]})
                status_counts.update(choices[0]['categories'])
        groups.append({'code':code,'before':len(old_members),'after':len(members),
                       'sameCohortBefore':len(old_members & same_cohort),
                       'sameCohortAfter':len(members & same_cohort),
                       'removedCharacters':[chr(cp) for cp in sorted(old_members-members)],
                       'geometrySupported':len(verified),'uncertainRetained':len(uncertain),
                       'geometrySupportedCPs':verified,'uncertainRetainedCPs':uncertain,
                       'withExistingSpecificAlternative':len(alternatives),
                       'alternativeBestMedianCandidates':median([a['choices'][0]['allCandidates'] for a in alternatives]) if alternatives else None,
                       'bestAlternativeCategories':dict(status_counts),'alternatives':alternatives})
    hints='TEFJ○●∴∵¨+×'
    examples=[]
    for char in hints:
        matches=[{'group':g['code'],**a} for g in groups for a in g['alternatives'] if a['char']==char]
        examples.extend(matches)
    provenance=load(after/'构建来源.json')
    assert all(fingerprint(PROJECT/'工具'/k)==v for k,v in provenance['codeHashes'].items())
    report={'passed':True,'before':old_index['id'],'after':new_index['id'],
            'sameDetailedCohort':len(same_cohort),
            'removedCharacterCodePairs':sum(len(set(r['codes'])-set(new[cp]['codes'])) for cp,r in old.items()),
            'addedCharacterCodePairs':sum(len(set(r['codes'])-set(old[cp]['codes'])) for cp,r in new.items()),
            'newlyFirstKeyOnlyWithHistoricalFlag':[r['char'] for cp,r in new.items() if old[cp]['codes'] and not r['codes'] and r['oldReviewed']],
            'certifiedRemovedRoutes':len(exclusions),'certifiedCharacters':len({e['cp'] for e in exclusions}),
            'allRemovedPathsHaveFreshNegativeCertificate':True,'sourceCodeHashesMatch':True,
            'weakPositiveFailureIsNotDeletion':True,'existingAttributesOnly':True,'newBindings':False,
            'scope':'geometry-support-is-not-human-whole-family-confirmation; unknowns-remain-visible',
            'groups':groups,'examples':examples,'exclusions':exclusions,'primaryChanges':whole_primary_changes,
            'runtimeDeployed':False}
    save(after/'大重码入口与属性复核.json',report)
    make_sheet(after,rows,old_rows)
    print(json.dumps({k:v for k,v in report.items() if k not in ('groups','examples','exclusions','primaryChanges')},ensure_ascii=False))
    print(json.dumps([{k:v for k,v in g.items() if k not in ('geometrySupportedCPs','uncertainRetainedCPs','alternatives')} for g in groups],ensure_ascii=False))
    print(json.dumps(examples,ensure_ascii=False))
    return report


def make_sheet(output,rows,old):
    by_char={r['char']:r for r in rows}
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    canvas=Image.new('RGB',(1120,520),'white'); draw=ImageDraw.Draw(canvas)
    for i,char in enumerate('⧼𝑆┘⅃TJ7★'):
        row=by_char[char]; x=i%4*280; y=i//4*260
        f=observe(*render(char,row['font']['path'],row['font'].get('index',0)))
        glyph=Image.fromarray(255-f['mask'].astype('uint8')*255).resize((160,160),Image.Resampling.NEAREST)
        canvas.paste(glyph,(x+10,y+38))
        draw.text((x+10,y+8),f'U+{ord(char):04X}',font=font,fill='black')
        rejected=[p['familyKey'] for p in row.get('collisionSanityExclusions',[])]
        label='撤回 '+','.join(rejected)+' 主体误收' if rejected else '保留；不据低匹配删除'
        draw.text((x+10,y+205),label,font=font,fill='black')
    canvas.save(output/'重码误收修复示例.png')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--after',type=Path,required=True)
    args=p.parse_args()
    audit(args.before,args.after)
