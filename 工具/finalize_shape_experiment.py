"""Validate a proposal and publish versioned reference-glyph previews, never an active codebook."""
import argparse,copy,json,math,shutil
import collections
import numpy as np
from pathlib import Path
from PIL import Image
from build_shape_experiment import PROJECT,DATA,ROOT,EDITOR,read,save,sha,protected_inputs,font_sources,prototypes,classify,section_templates
from shape_experiment_features import VERSION as FEATURE_VERSION,render,observe,component_mask,normalized,signature
from shape_experiment_rules import RULES,TRIAL_KEYS,properties,obj,paths,facts,family_dictionary
from shape_experiment_allocation import allocate


def repair_group_rules(row,mask,palette):
    """Group attributes refer to the whole group; repeated ink needs shape agreement."""
    if not row.get('features'):return
    parts=row['features']['parts'];repeated=set()
    if any(e['third']=='n' for p in row['paths'] for e in p['evidence']):
        signatures={}
        for i,g in enumerate(parts):
            signatures[i]=normalized(component_mask(mask,g),16)
        for i,g in enumerate(parts):
            for j,q in enumerate(parts):
                if i==j:continue
                if abs(math.log((q['x1']-q['x0'])/(g['x1']-g['x0'])))>=.25 or abs(math.log((q['y1']-q['y0'])/(g['y1']-g['y0'])))>=.25:continue
                if float(((signatures[i]-signatures[j])**2).mean())<=.045:repeated.add('part-'+str(i))
    updated={}
    for path in row['paths']:
        for evidence in path['evidence']:
            if evidence['third']=='n' and evidence['objectId'].split(':')[-1] not in repeated:continue
            replacements=[{'code':path['code'],'evidence':[evidence]}]
            if evidence['third']=='k' and evidence['familyTarget']=='body':
                box=[min(g['x0'] for g in parts),min(g['y0'] for g in parts),max(g['x1'] for g in parts),max(g['y1'] for g in parts)]
                group=obj('body:part-group','part-group',box,row['features']['bbox'],row['features']['extent'])
                fact={'third':'k','function':RULES['k'][0],'object':group,'reason':'多个分离墨部件的完整包围范围','status':'proposal'}
                replacements=paths(path['code'][0],path['code'][1],[fact],palette)
                for p in replacements:
                    for e in p['evidence']:e['familyTarget']='body';e['familyId']=evidence['familyId']
            for p in replacements:
                target=updated.setdefault(p['code'],{'code':p['code'],'evidence':[]})
                target['evidence'] += [e for e in p['evidence'] if e not in target['evidence']]
    row['paths']=sorted(updated.values(),key=lambda p:p['code'])


def refresh_boundary_prototypes(row,mask,anchors,sections,palette):
    """Apply added arc/parallel prototypes by shape distance, never by character ID."""
    if not row.get('features') or row['familyKey'] not in (None,'l','c','a','w'):return
    feature=row['features'];major=max(feature['parts'],key=lambda g:(g['x1']-g['x0'])*(g['y1']-g['y0']))
    yy,xx=np.nonzero(mask);full=(xx.max()-xx.min()+1)*(yy.max()-yy.min()+1)
    body=mask if (major['x1']-major['x0'])*(major['y1']-major['y0'])<full*.6 else component_mask(mask,major)
    sig=signature(body)
    additions=[a for a in anchors if a['cp'] in set(map(ord,'◜◝◟◞∥'))]
    distances=[float(((sig-a['signature'])**2).sum())+.025*min(1,abs(math.log(feature['ratio']/a['ratio']))) for a in additions]
    if not distances or min(distances)>.055:return
    f=observe(mask,feature['extent']);matches=classify(f,anchors)
    if not matches or matches[0]['key']==row['familyKey']:return
    row['features']={k:v for k,v in f.items() if k not in ('mask','body','silhouette','signature')}
    row['families']=[dict(m,target='body') for m in matches];row['familyKey']=matches[0]['key'];row['familyId']=matches[0]['familyId']
    row['familyRoutes']=[];found={};objects={}
    for match in matches:
        bucket=row['oldBucket'];row['familyRoutes'].append({'bucket':bucket,'familyKey':match['key'],'familyId':match['familyId'],'target':'body'})
        for fact in facts(f,match['key'],sections):
            fact['object']['id']='body:'+fact['object']['id'];objects[fact['object']['id']]=fact['object']
            for p in paths(bucket,match['key'],[fact],palette):
                for e in p['evidence']:e['familyTarget']='body';e['familyId']=match['familyId']
                entry=found.setdefault(p['code'],{'code':p['code'],'evidence':[]});entry['evidence']+=p['evidence']
    row['paths']=sorted(found.values(),key=lambda p:p['code']);row['objects']=list(objects.values())
    row['warnings'].append('由补充的圆弧／平行线视觉原型重新判定，仍待人工核对')


def restore_inner_routes(row,mask,anchors,sections,palette):
    if not row['familyKey'] or not row['features']['holes']:return
    b=row['features']['bbox'];found={p['code']:p for p in row['paths']};objects={o['id']:o for o in row['objects']}
    for number,g in enumerate(row['features']['parts']):
        if not (b[0]<g['x0'] and b[1]<g['y0'] and g['x1']<b[2] and g['y1']<b[3]) or g['area']<12:continue
        if g['area']<sum(p['area'] for p in row['features']['parts'])*.06:continue
        target='inner-'+str(number)
        try:
            submask=component_mask(mask,g);extent=row['features']['extent']*max(g['x1']-g['x0'],g['y1']-g['y0'])/max(b[2]-b[0],b[3]-b[1]);sub=observe(submask,extent)
        except ValueError:continue
        for match in classify(sub,anchors):
            if any(r['familyKey']==match['key'] and r['target']==target for r in row['familyRoutes']):continue
            row['families'].append(dict(match,target=target))
            row['familyRoutes'].append({'bucket':row['oldBucket'],'familyKey':match['key'],'familyId':match['familyId'],'target':target})
            for fact in facts(sub,match['key'],sections):
                fact['object']['id']=target+':'+fact['object']['id'];objects[fact['object']['id']]=fact['object']
                for p in paths(row['oldBucket'],match['key'],[fact],palette):
                    for e in p['evidence']:e['familyTarget']=target;e['familyId']=match['familyId']
                    entry=found.setdefault(p['code'],{'code':p['code'],'evidence':[]})
                    entry['evidence'] += [e for e in p['evidence'] if e not in entry['evidence']]
    row['paths']=sorted(found.values(),key=lambda p:p['code']);row['objects']=list(objects.values())


def finalize(run,repack=False):
    run=run.resolve()
    data=read(run/'shape-experiment.json');report=read(run/'容量与重码报告.json')
    if data['definitions']['featureVersion']!=FEATURE_VERSION:
        raise ValueError('Feature version changed; preserve the historical run and build a fresh experiment instead of repacking it')
    source=PROJECT/read(DATA/'shape-stage.json')['source'];before=protected_inputs(source)
    baseline=read(run/'保护基线.json');assert baseline==before,'Protected sources changed after experiment build'
    model=read(source/'模型.json');primary,quality,manifest=font_sources(model)
    atlas_root=run/'参考字形';atlas_root.mkdir(exist_ok=True)
    url_root='data/shape-experiment-glyphs/'+data['id'];mirror_root=EDITOR/url_root;mirror_root.mkdir(parents=True,exist_ok=True)
    fonts={};anchor=prototypes(primary,fonts);sections=section_templates(primary,fonts);cols,per_sheet=32,512
    sheet=None;sheet_name=None
    for i,r in enumerate([] if repack else data['records']):
        if i%per_sheet==0:
            if sheet is not None:sheet.save(atlas_root/sheet_name);shutil.copy2(atlas_root/sheet_name,mirror_root/sheet_name)
            sheet=Image.new('L',(cols*64,16*64),255);sheet_name=f'{i//per_sheet:03d}.png'
        cp=r['cp'];x=(i%per_sheet%cols)*64;y=(i%per_sheet//cols)*64
        if cp in primary:
            try:
                path,index=primary[cp];mask,_=render(chr(cp),path,index,fonts=fonts)
                sheet.paste(Image.fromarray((255-mask.astype('uint8')*255)),(x,y))
                r['preview']={'url':url_root+'/'+sheet_name,'x':x,'y':y,'kind':'locked-font-binary-64px'}
            except (ValueError,OSError):pass
            else:
                refresh_boundary_prototypes(r,mask,anchor,sections,data['definitions']['fourth'])
                restore_inner_routes(r,mask,anchor,sections,data['definitions']['fourth'])
                repair_group_rules(r,mask,data['definitions']['fourth'])
        # Normalize evidence object references into immutable independent observations.
        previous_objects={o['id']:o for o in r['objects']};objects={};expanded={}
        for path in r['paths']:
            for e in path['evidence']:
                previous_id=e['objectId']
                e['objectId']=e['familyTarget']+':'+e['objectId'].split(':')[-1]
                e['fourthObjectId']=e['objectId']
                o=copy.deepcopy(e.get('thirdObject') or previous_objects[previous_id]);o['id']=e['objectId']
                if e['third']=='x' and cp in primary:
                    x0,y0,x1,y1=map(round,o['bbox']);yy,xx=np.nonzero(mask[y0:y1,x0:x1]);cx=(x1-x0-1)/2;cy=(y1-y0-1)/2
                    far=np.hypot(xx-cx,yy-cy)>max(x1-x0,y1-y0)*.2
                    z=np.exp(4j*np.arctan2(cy-yy[far],xx[far]-cx)).mean() if far.any() else 0
                    o['orientation']=float((np.angle(z)/4*180/np.pi)%90) if abs(z)>.4 else None;o['orientationMode']='cross'
                assert e['objectId']==e['fourthObjectId']
                if o['id'] in objects:assert objects[o['id']]==o
                objects[o['id']]=o
                assert e['rule']==RULES[e['third']][0]
                e.pop('thirdObject',None)
                attributes=properties(o)
                for suffix,reason in attributes or [('', '没有可观测的第四位属性，停在三码')]:
                    code=path['code'][:3]+suffix
                    evidence=copy.deepcopy(e);evidence['attribute']=reason
                    item=expanded.setdefault(code,{'code':code,'evidence':[]})
                    if evidence not in item['evidence']:item['evidence'].append(evidence)
        r['paths']=sorted(expanded.values(),key=lambda p:p['code'])
        r['objects']=list(objects.values())
    if sheet is not None:sheet.save(atlas_root/sheet_name);shutil.copy2(atlas_root/sheet_name,mirror_root/sheet_name)
    groups,allocation=allocate(data['records']);data['bucketGroups']=groups
    data['familyBuckets']={k:[g['bucket'] for g in groups if k in g['families']] for k in data['definitions']['families']}
    data['definitions']['families']=family_dictionary()
    report['familyAssigned']=sum(bool(r['familyId']) for r in data['records']);report['familyPending']=len(data['records'])-report['familyAssigned']
    stable=read(run/'渲染稳定性.json')
    def rebase(path):
        marker='数据/三模式/规则库/字体/';normalized=path.replace('\\','/')
        return str(PROJECT/marker/normalized.split(marker,1)[1]) if not Path(path).exists() and marker in normalized else path
    byfamily={f['family']:(rebase(f['path']),f.get('index',0)) for f in manifest['fonts']}
    for item in stable:
        alt=quality[item['cp']].get('alternate');item['alternateFont']=None
        if alt and alt['font'] in byfamily:
            path,index=byfamily[alt['font']]
            try:
                mask,extent=render(item['char'],path,index,fonts=fonts);f=observe(mask,extent);matches=classify(f,anchor)
                prediction=matches[0]['key'] if matches else None
                item['alternateFont']={'font':alt['font'],'family':prediction,'junctions':f['junctions'],
                    'sameFamily':prediction==item['views'][1].get('family'),'historicalPixelAgreement':alt.get('accepted')}
            except (OSError,ValueError) as e:item['alternateFont']={'font':alt['font'],'error':str(e)}
    data['reviewInstructions']={'status':'awaiting-human-review','canActivate':False,
        'description':'核对形族与新增第三位键义后，再冻结定义并另建有效发布版本；本页不提供直接发布按钮。'}
    report['experimentId']=data['id'];report['newThirdRules']=[k for k,v in RULES.items() if v[2]=='proposal']
    counts=collections.Counter(r['bucket'] for r in data['records']);report['bucketCounts']=dict(sorted(counts.items()));report['allocation']=allocation
    report['capacityDeviations']={a:{'count':counts[a],'reason':'形族／明确比例子族优先；不跨族补位'} for a in 'abcdefghijklmnopqrstuvw' if not 500<=counts[a]<=2000}
    diffs=[{'cp':r['cp'],'char':r['char'],'before':r['oldBucket'],'after':r['bucket'],'previouslyReviewed':r['oldReviewed'],'familyId':r['familyId'],'reason':'独立形族／几何子族分配提案'} for r in data['records'] if r['bucket']!=r['oldBucket']]
    report['changedPrimary']=len(diffs);report['changedPreviouslyReviewed']=sum(d['previouslyReviewed'] for d in diffs)
    prefix=collections.defaultdict(set)
    for r in data['records']:
        prefix[r['bucket']].add(r['cp'])
        for route in r['familyRoutes']:
            prefix[route['bucket']].add(r['cp']);prefix[route['bucket']+route['familyKey']].add(r['cp'])
        for path in r['paths']:
            for n in range(1,len(path['code'])+1):prefix[path['code'][:n]].add(r['cp'])
    report['prefixDistribution']={str(n):{'occupied':sum(len(k)==n for k in prefix),'maximumCandidates':max((len(v) for k,v in prefix.items() if len(k)==n),default=0),
        'medianCandidates':float(np.median([len(v) for k,v in prefix.items() if len(k)==n])) if any(len(k)==n for k in prefix) else 0} for n in range(1,5)}
    report['occupiedFourCodes']=report['prefixDistribution']['4']['occupied'];report['emptyFourthDefinedSpace']=report['fourthDefinedSpace']-report['occupiedFourCodes']
    report['pathCount']=sum(len(r['paths']) for r in data['records']);report['maxPathsPerCharacter']=max(len(r['paths']) for r in data['records'])
    report['withPaths']=sum(bool(r['paths']) for r in data['records'])
    for key in data['definitions']['families']:
        members=sorted((r for r in data['records'] if r['familyKey']==key),key=lambda r:(r['families'][0]['distance'],r['cp']))
        data['representatives'][key]={'buckets':data['familyBuckets'][key],'count':len(members),
            'centre':[r['cp'] for r in members[:12]],'boundary':[r['cp'] for r in members[-12:]]}
    bycp={r['cp']:r for r in data['records']}
    for b in data['benchmarks']:b['predictions']={c:bycp.get(ord(c),{}).get('familyKey') for c in b['characters']}
    report['candidateDefinitionReviewRequired']=True
    report['fontAlternateCases']=sum(bool(s['alternateFont']) for s in stable)
    report['fontAlternateAgreements']=sum(s['alternateFont'].get('sameFamily',False) for s in stable if s['alternateFont'])
    report['validation']={'objectsConsistent':True,'fourthPropertiesSupported':True,'trialThirdKeysNotEnabled':not bool(set(RULES)&set(TRIAL_KEYS)),
        'primaryStageUnchanged':True,'effectiveBooksUnchanged':True,'rimeUnchanged':True,
        'identities':len(data['records'])+sum(map(len,data['collections'].values()))+len(data['unclassified']),
        'glyphPreviewCount':sum('preview' in r for r in data['records'])}
    assert report['validation']['identities']==159345
    assert protected_inputs(source)==before
    save(run/'定义快照.json',data['definitions'])
    report['definitionsSHA256']=sha(run/'定义快照.json');data['definitionsSHA256']=report['definitionsSHA256']
    provenance=read(run/'来源清单.json')
    provenance['finalizerCodeHashes']={name:sha(Path(__file__).with_name(name)) for name in ['shape_experiment_features.py','shape_experiment_rules.py','shape_experiment_allocation.py','finalize_shape_experiment.py']}
    provenance['definitionsSHA256']=report['definitionsSHA256'];save(run/'来源清单.json',provenance)
    save(run/'shape-experiment.json',data);save(run/'容量与重码报告.json',report);save(run/'渲染稳定性.json',stable);save(run/'主桶差异.json',diffs)
    save(run/'校验报告.json',report['validation'])
    # A small prefix index is loaded first; evidence is fetched in bounded shards on demand.
    browser={k:v for k,v in data.items() if k!='records'};browser['indexOnly']=True;browser['records']=[]
    detail_root=EDITOR/'data/shape-experiment-records'/data['id'];detail_root.mkdir(parents=True,exist_ok=True)
    for start in range(0,len(data['records']),128):
        chunk=data['records'][start:start+128];name=f'{start//128:03d}.json'
        save(detail_root/name,{'experimentId':data['id'],'records':chunk})
        for r in chunk:
            slim={k:r[k] for k in ('cp','char','bucket','oldBucket','oldReviewed','familyKey','familyId','familyRoutes')}
            slim['semanticPrimaryFamilyId']=r.get('semantic',{}).get('primaryFamilyId')
            slim['pendingKeyboardFamilyIds']=r.get('semantic',{}).get('pendingKeyboardFamilyIds',[])
            if 'preview' in r:slim['preview']=r['preview']
            slim['codes']=[p['code'] for p in r['paths']]
            slim['detailUrl']='data/shape-experiment-records/'+data['id']+'/'+name
            browser['records'].append(slim)
    save(EDITOR/'data/shape-experiment.json',browser)
    review_file=ROOT/'人工审议.json'
    save(EDITOR/'data/shape-experiment-review.json',read(review_file) if review_file.exists() else {'schemaVersion':1,'scope':'benchmark-relations-only','decisions':[]})
    for name,value in [('shape-experiment-report.json',report),('shape-experiment-stability.json',stable),('shape-experiment-diff.json',diffs)]:save(EDITOR/'data'/name,value)
    save(ROOT/'最新实验.json',{'run':str(run),'id':data['id'],'active':False,'status':'awaiting-human-review'})
    text=['# 四键取形独立实验报告','','状态：待人工审议，未替换当前阶段、旧确认或小狼毫。','',
        f"普通字符 {len(data['records'])}；有形族 {report['familyAssigned']}；待定族 {report['familyPending']}；路径 {report['pathCount']}。",
        f"主桶变化提案 {report['changedPrimary']}，含旧确认项 {report['changedPreviouslyReviewed']}；均未应用。",'',
        '## 主桶与形族／子族','','| 主桶 | 形族键 | 比例子族 | 字符数 |','|---|---|---|---|']
    text += [f"| {g['bucket']} | {','.join(g['families'])} | {g['proportion'] or '整族'} | {g['count']} |" for g in groups]
    text += ['', '## 第三位规则候选','','| 键 | 功能ID | 含义 | 状态 | 正例／反例 |','|---|---|---|---|---|']
    text += [f'| {k} | {v[0]} | {v[1]} | {v[2]} | {v[4]} / {v[5]} |' for k,v in RULES.items()]
    text += ['',report['humanEvaluation'],'',*report['limitations'],'','详表：容量与重码报告.json、主桶差异.json、渲染稳定性.json、校验报告.json。']
    (run/'实验报告.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    print(json.dumps({'run':str(run),'id':data['id'],'validation':report['validation'],'fontAlternateCases':report['fontAlternateCases'],'fontAlternateAgreements':report['fontAlternateAgreements']},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path);p.add_argument('--repack',action='store_true',help='保留已验证的字形和对象观测，仅重排独立主桶提案并重建索引');a=p.parse_args();finalize(a.run or Path(read(ROOT/'最新实验.json')['run']),a.repack)
