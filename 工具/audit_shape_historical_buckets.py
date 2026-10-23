"""Organize six retained buckets and test two first-key ideas without migration."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont

from build_shape_keyboard_full import save
from shape_experiment_features import observe,render,normalized
from shape_family_boundaries import reference_views,fits
from shape_reviewed_routes import straight_body,bucket_for
from shape_historical_bucket_pilot import VERSION,ink_info,parallel_layers,stepped_face,stable_probe

PROJECT=Path(__file__).resolve().parents[1]
ROOT=PROJECT/'数据/三模式/规则库/四键实验'
SOURCE=ROOT/'键位试验/20261021-connected-stroke-group-full-v1'
DEFAULT_OUTPUT=ROOT/'键位试验/20261022-historical-buckets-pilot-v1'
KEYS='tujvbg'
CONTROLS='=≡∥䷀䷁☰☷⚌⚏EFTLIH○●□■△▲☆★∴∵U∩C🬥🬨🬕🭕'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protect():
    files=[SOURCE/'发布核对索引.json',ROOT/'人工审议.json',ROOT/'最新实验.json',
           PROJECT/'数据/三模式/全形核对版.json',
           PROJECT/'原型/键位编辑器/data/shape-review-profile.json',
           PROJECT/'工具/build_shape_keyboard_full.py']
    files+=sorted((SOURCE/'details').glob('*.json'))
    return {str(p.relative_to(PROJECT)):fingerprint(p) for p in files if p.is_file()}


def assert_protected_snapshot(snapshot):
    """Historical inputs stay exact, apart from one explicit append-only decision."""
    review_name=str((ROOT/'人工审议.json').relative_to(PROJECT))
    for name,digest in snapshot.items():
        if fingerprint(PROJECT/name)==digest:continue
        assert name==review_name, f'受保护源文件改变：{name}'
        old_path=SOURCE.parent/'20261022-centre-position-trial-v1/人工审议追加前快照.json'
        assert old_path.is_file() and fingerprint(old_path)==digest, '旧审议快照指纹不匹配'
        previous=load(old_path);current=load(ROOT/'人工审议.json')
        addition=current['keyboardConsultation20261020'].pop('centralPositionAcceptance20261022')
        assert current==previous, '旧审议内容发生非追加变化'
        assert addition['meaning']=='中心' and addition['meaningAccepted'] is True
        assert addition['provisionalFourthKey']=='o' and addition['letterHumanFrozen'] is False
        assert addition['preserveReliableStructuralPreferences']==418
        assert addition['runtimeDeploymentApproved'] is False
    return True


def existing_family_probe(f,views):
    if len(f['parts'])!=1 or not np.array_equal(f['body'],f['mask']):
        return None
    if straight_body(f):
        return {'family':'l','coarse':'线与转折','basis':'现有直线检验通过；无钩端或张开端'}
    choices=[]
    for family in 'ucost':
        if fits(f,family,views)[0]:
            image=normalized(f['silhouette'] if family in 'ost' else f['body'])
            error=float(np.min(np.mean((views[family]-image)**2,axis=(1,2))))
            if error<=.04:
                choices.append((error,family))
    choices.sort()
    if not choices or (len(choices)>1 and choices[1][0]-choices[0][0]<.012):
        return None
    error,family=choices[0]
    return {'family':family,'coarse':{'u':'开放曲线','c':'开放曲线','o':'闭环','s':'角形闭合','t':'角形闭合'}[family],
            'basis':'现有形族边界与原型共同通过；非仅按宽高比猜测','prototypeError':error}


def stable_existing(row,f,views,fonts):
    probe=existing_family_probe(f,views)
    if probe is None:
        return None
    variants=[]
    for size in (48,96,128):
        for weight in (-1,0,1):
            try:
                vf=observe(*render(row['char'],row['font']['path'],row['font'].get('index',0),size=size,weight=weight,fonts=fonts))
                result=existing_family_probe(vf,views)
            except (ValueError,OSError):
                result=None
            variants.append({'size':size,'weight':weight,'passed':bool(result and result['family']==probe['family'])})
    return dict(probe,stable=all(v['passed'] for v in variants),variants=variants)


def triage(row,f,probes,existing):
    if row['paths']:
        return '已有可靠入口保留', '现有补充入口不删除；旧第一位仍未迁移'
    if (probes.get('u',{}).get('stability') or {}).get('passed'):
        return '线群新用途试验', '完整墨迹可分为规则线层；第一位u仍未绑定'
    if (probes.get('v',{}).get('stability') or {}).get('passed'):
        return '块面新用途试验', '仅通过窄范围台阶拼块检验；第一位v仍未绑定'
    if existing and existing['stable']:
        return '现有形族补回候选', '九种字号粗细均通过；尚未写入码表，也未确认主桶迁移'
    if any(p.get('base') for p in probes.values()):
        return '新用途扰动不稳定', '基准字体可匹配，但九种扰动不一致；不纳入稳定候选'
    if f['holes']:
        return '闭孔与主体附件待分离', '闭孔数不等于整字形族；需要提取真实环或外框'
    if len(f['parts'])>1:
        return '分离构件待取对象', '尚未形成可靠整体入口；分别检查实际部件'
    return '开口与线骨架待核', '继续检查曲弯、直线、分叉及块面；不按骨架端点强归族'


def control_for(row,fonts):
    mask,_=render(row['char'],row['font']['path'],row['font'].get('index',0),fonts=fonts)
    info=ink_info(mask)
    probes={}
    for key,detector in [('u',parallel_layers),('v',stepped_face)]:
        base=detector(info)
        probes[key]={'base':base, 'stability':stable_probe(row,detector,fonts) if base else None}
    return probes


def figure(output,name,rows,lookup,probe=None,limit=120):
    """Only recolor existing ink; never draw a completed/model shape as evidence."""
    selected=rows[:limit]; columns=8
    height=58+((len(selected)+columns-1)//columns)*116
    canvas=Image.new('RGB',(1120,max(height,100)),'white');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    draw.text((12,10),name+'（颜色仅标识原墨迹；不是人工确认）',font=font,fill='black')
    for n,item in enumerate(selected):
        row=lookup[item['cp']];mask,_=render(row['char'],row['font']['path'],row['font'].get('index',0))
        image=np.full((64,64,3),255,dtype='uint8');image[mask]=0
        if probe and item.get('probes',{}).get(probe,{}).get('base'):
            obj=item['probes'][probe]['base']
            if probe=='u':
                for i,b in enumerate(obj['memberBBoxes']):
                    x0,y0,x1,y1=b; region=image[y0:y1,x0:x1];region[mask[y0:y1,x0:x1]]=[(25,110,165),(165,50,80),(40,135,85)][i%3]
            else:
                image[mask]=[30,125,105]
        x=12+(n%columns)*138;y=46+(n//columns)*116
        canvas.paste(Image.fromarray(image).resize((80,80),Image.Resampling.NEAREST),(x,y))
        draw.text((x,y+81),f"{item['oldBucket']}  U+{item['cp']:04X}",font=font,fill='black')
    canvas.save(output/name)


def audit(output=DEFAULT_OUTPUT):
    if output.exists():
        raise FileExistsError('保留已生成试验；请指定新的--output，不覆盖已有审议材料')
    before=protect();index=load(SOURCE/'发布核对索引.json')
    targets={r['cp'] for r in index['records'] if r['bucket'] in KEYS}
    lookup={};controls={}
    for path in sorted((SOURCE/'details').glob('*.json')):
        data=load(path)
        assert data['experimentId']==index['id']
        for row in data['records']:
            if row['cp'] in targets:lookup[row['cp']]=row
            if row['char'] in CONTROLS:controls[row['char']]=row
    assert len(lookup)==len(targets)==443
    views=reference_views(Path('C:/Windows/Fonts/seguisym.ttf'));fonts={};records=[]
    sprite_cache={}
    for n,row in enumerate(lookup.values()):
        mask,extent=render(row['char'],row['font']['path'],row['font'].get('index',0),fonts=fonts)
        f=observe(mask,extent)
        probes=control_for(row,fonts)
        existing=stable_existing(row,f,views,fonts)
        category,reason=triage(row,f,probes,existing)
        if existing:
            existing['proposedBucket']=bucket_for(index['bucketGroups'],existing['coarse'],f['ratio'])
        preview=row['preview'];sprite_path=PROJECT/'原型/键位编辑器'/preview['url']
        if str(sprite_path) not in sprite_cache:sprite_cache[str(sprite_path)]=Image.open(sprite_path).convert('L')
        sprite=np.array(sprite_cache[str(sprite_path)].crop((preview['x'],preview['y'],preview['x']+64,preview['y']+64)))<128
        records.append({'cp':row['cp'],'char':row['char'],'oldBucket':row['bucket'],
                        'historicallyReviewed':bool(row.get('oldReviewed')),'codesBefore':[p['code'] for p in row['paths']],
                        'category':category,'reason':reason,'probes':probes,'existingFamilyProbe':existing,
                        'facts':{k:f[k] for k in ('bbox','ratio','density','endpoints','junctions')},
                        'holeCount':len(f['holes']),'partCount':len(f['parts']),
                        'alternateFontDisagreement':'alternate-font-disagreement' in row.get('warnings',[]),
                        'lockedSpriteMismatchPixels':int((sprite!=mask).sum()),
                        'oldGeneratorSkippedAmendment':bool(row.get('features') and not
                            (row.get('baselineFamilyKey') or row.get('semantic',{}).get('primaryFamilyId')=='family.double-loop')),
                        'migrationApplied':False,'codesApplied':False})
        if (n+1)%75==0:print(f'已核查 {n+1}/{len(lookup)}',flush=True)
    tested_controls=[]
    for ch in CONTROLS:
        if ch not in controls:continue
        row=controls[ch];tested_controls.append({'cp':row['cp'],'char':ch,'oldBucket':row['bucket'],
                                               'probes':control_for(row,fonts)})
    assert all(not c['probes']['v']['base'] for c in tested_controls if c['char'] in '○●□■△▲☆★EFTHU∩C')
    assert all(not c['probes']['u']['base'] for c in tested_controls if c['char'] in 'EFTLIH○●□■△▲☆★∴∵U∩C')
    assert all(c['probes']['u']['stability']['passed'] for c in tested_controls if c['char'] in '=≡∥䷀䷁')
    after=protect();assert before==after
    summary={key:{'total':sum(r['oldBucket']==key for r in records),
                  'categories':dict(Counter(r['category'] for r in records if r['oldBucket']==key)),
                  'historicallyReviewed':sum(r['historicallyReviewed'] for r in records if r['oldBucket']==key)} for key in KEYS}
    trials={}
    for key,label in [('u','线群／层列'),('v','不规则实心块面')]:
        base=[r for r in records if r['probes'][key]['base']]
        stable=[r for r in base if r['probes'][key]['stability']['passed']]
        trials[key]={'meaningProposal':label,'bindingAccepted':False,'baseCount':len(base),'stableCount':len(stable),
                     'unstableCount':len(base)-len(stable),'cps':[r['cp'] for r in stable],
                     'oldBuckets':dict(Counter(r['oldBucket'] for r in stable)),
                     'cohortOnlyUnionWithRetainedOldFirst':len({r['cp'] for r in stable}|{r['cp'] for r in records if r['oldBucket']==key}),
                     'scope':'443 retained characters only; not a full-Unicode capacity result'}
    report={'version':VERSION,'source':index['id'],'sourceIndexSHA256':fingerprint(SOURCE/'发布核对索引.json'),
            'status':'independent-audit-and-unbound-semantic-pilot','date':'2026-10-22','count':len(records),
            'requestedFiveCount':sum(r['oldBucket']!='g' for r in records),'includedExtraG':True,
            'summary':summary,'categories':dict(Counter(r['category'] for r in records)),
            'historicallyReviewed':sum(r['historicallyReviewed'] for r in records),
            'existingCoded':sum(bool(r['codesBefore']) for r in records),
            'existingStableProposals':sum(bool(r['existingFamilyProbe'] and r['existingFamilyProbe']['stable']) for r in records),
            'trials':trials,'spriteMismatchCharacters':sum(r['lockedSpriteMismatchPixels']>0 for r in records),
            'rootCause':{'file':'工具/build_shape_keyboard_full.py','condition':'if f and (old_family or bind_double)',
                         'finding':'原本无主形族且无双环绑定的记录跳过amend；不是本轮边界撤回造成的失收',
                         'fixRecommendation':'先给无主族记录执行独立补充对象探测；验证后仅加可靠补充路径，不自动迁移旧主桶',
                         'implementedInGenerator':False},
            'protectedInputsUnchanged':True,'protectedHashes':before,'records':records,'controls':tested_controls,
            'limitations':['试验只覆盖六个历史保留桶443字和单列控制样本，不代表全量推广或全量重码改善。',
                           '九扰动仅限锁定字体，不等于跨字体一致；已有异字体分歧继续显示。',
                           'v仅试2×3／3×2台阶拼块，斜切块和一般不规则实心轮廓尚未覆盖。',
                           '没有添加四位编码、清空旧桶、确认新键义、改写人工确认或部署。'],
            'runtimeDeployed':False,'generatorChanged':False,'migrations':0,'newCodePaths':0,
            'sourceHashes':{name:fingerprint(PROJECT/'工具'/name) for name in ('shape_historical_bucket_pilot.py','audit_shape_historical_buckets.py')}}
    save(output/'历史桶整理与新用途试验.json',report)
    save(output/'验收.json',{'passed':True,'count':len(records),'identitiesAndCodesUnchanged':True,
                           'protectedInputsUnchanged':True,'tests':'control assertions and 3 sizes x 3 weights per proposed candidate',
                           'runtimeDeployed':False})
    for key,label in [('u','线群候选.png'),('v','块面候选.png')]:
        figure(output,label,[r for r in records if r['cp'] in trials[key]['cps']],lookup,key)
    figure(output,'现有形族补回候选.png',[r for r in records if r['existingFamilyProbe'] and r['existingFamilyProbe']['stable']],lookup)
    print(json.dumps({k:report[k] for k in ('count','summary','categories','existingStableProposals','trials','spriteMismatchCharacters')},ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    audit(parser.parse_args().output)
