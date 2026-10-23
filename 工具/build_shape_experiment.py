"""Build a complete, read-only four-key review proposal outside the active codebook."""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json,math,os,shutil,sys,time
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image
from shape_experiment_features import VERSION,render,observe,serialize,component_mask
from shape_experiment_rules import FAMILIES,RULES,TRIAL_KEYS,dictionary,family_dictionary,semantic_family_dictionary,facts,paths

PROJECT=Path(__file__).resolve().parents[1]
DATA=PROJECT/'数据/三模式';ROOT=DATA/'规则库/四键实验';EDITOR=PROJECT/'原型/键位编辑器'
LETTERS='abcdefghijklmnopqrstuvw'


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    temporary=p.with_name(p.name+'.tmp');temporary.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');temporary.replace(p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def protected_inputs(source):
    files=[DATA/'shape-stage.json',DATA/'codebooks.json',DATA/'全形第四位-当前布局.json',
           EDITOR/'data/shape-stage.json',EDITOR/'data/mode-data.json',source/'全部收纳.json',
           source/'人工约束.json',source/'模型.json']
    rime=Path(os.environ.get('APPDATA',''))/'Rime'
    if os.environ.get('APPDATA') and rime.is_dir():files.extend(p for p in rime.rglob('*') if p.is_file())
    return {str(p):{'sha256':sha(p),'mtime_ns':p.stat().st_mtime_ns} for p in files}


def font_sources(model):
    cache=DATA/'规则库/首次优化/缓存'/(model['scopeSignature']+'.manifest.json')
    manifest=read(cache);primary={cp:(path,index) for cp,path,index in manifest['primary']}
    with gzip.open(model['qualityRecords'],'rt',encoding='utf-8') as f:quality={q['cp']:q for q in map(json.loads,f)}
    byfamily={f['family']:(f['path'],f.get('index',0)) for f in manifest['fonts']}
    for cp,q in quality.items():
        if q.get('primaryFontPath'):primary[cp]=(q['primaryFontPath'],0)
        elif cp not in primary and q.get('primaryFont') in byfamily:primary[cp]=byfamily[q['primaryFont']]
    def resolve_font(path):
        if Path(path).is_file():return path
        # The complete engineering tree moved out of the vault on 2026-10-15.
        marker='数据/三模式/规则库/字体/'
        normalized=path.replace('\\','/')
        if marker in normalized:
            candidate=PROJECT/marker/normalized.split(marker,1)[1]
            if candidate.is_file():return str(candidate)
        return path
    primary={cp:(resolve_font(path),index) for cp,(path,index) in primary.items()}
    return primary,quality,manifest


def prototypes(primary,fonts):
    items=[]
    for key,(_,_,anchors) in FAMILIES.items():
        for char in dict.fromkeys(anchors):
            if ord(char) not in primary:continue
            path,index=primary[ord(char)]
            try:mask,extent=render(char,path,index,fonts=fonts);f=observe(mask,extent)
            except (OSError,ValueError):continue
            items.append({'key':key,'cp':ord(char),'signature':f['signature'],'ratio':f['ratio'],
                          'font':path,'bbox':f['bbox']})
            if key=='u':
                for turns in (1,2,3):
                    rotated=observe(np.rot90(mask,turns).copy(),extent)
                    items.append({'key':key,'cp':ord(char),'signature':rotated['signature'],'ratio':rotated['ratio'],
                                  'font':path,'bbox':rotated['bbox'],'rotation':90*turns})
    for char in '∞8B':
        if ord(char) not in primary:continue
        path,index=primary[ord(char)];mask,extent=render(char,path,index,fonts=fonts);f=observe(mask,extent)
        items.append({'key':None,'cp':ord(char),'signature':f['signature'],'ratio':f['ratio'],
                      'font':path,'bbox':f['bbox'],'role':'boundary' if char=='B' else 'positive',
                      'familyId':'family.double-loop'})
    if set(FAMILIES)-{a['key'] for a in items}:raise ValueError('Missing family anchors')
    return items


def section_templates(primary,fonts):
    result=[]
    for char,third,position in [('◡','p',[0,.5]),('◠','p',[0,-.5]),('(','p',[-.5,0]),(')','p',[.5,0]),
                                ('◜','f',[-.5,-.5]),('◝','f',[.5,-.5]),('◟','f',[-.5,.5]),('◞','f',[.5,.5])]:
        if ord(char) not in primary:continue
        path,index=primary[ord(char)];mask,extent=render(char,path,index,fonts=fonts);f=observe(mask,extent)
        result.append({'cp':ord(char),'third':third,'relativePosition':position,'signature':f['signature'],'ratio':f['ratio']})
    return result


def classify(f,anchors):
    from shape_experiment_detector import shape_routes,dot_group
    scores={};examples={}
    for a in anchors:
        if a['key'] is None:continue
        # Filled silhouette dominates; retained aspect is a soft tie-breaker.
        distance=float(((f['signature']-a['signature'])**2).sum())+.025*min(1,abs(math.log(f['ratio']/a['ratio'])))
        key=a['key']
        if key not in scores or distance<scores[key]:scores[key]=distance;examples[key]=a['cp']
    # These gates test measured geometry, never Unicode names, scripts or codepoint ranges.
    if f['endpoints']<5:scores['r']+=.35
    if len(f['parts'])==1 and len(f['holes'])<=2 and f['junctions']<3:scores['m']+=.35
    if not f['holes']:scores['p']+=.25
    if len(f['parts'])==1 and f['extent']>.35:scores['d']+=.15
    if f['junctions']==0:scores['h']+=.18
    is_dots=dot_group(f)
    if not is_dots:scores['d']+=.35
    line_parts=bool(f['parts']) and all(max((g['x1']-g['x0'])/(g['y1']-g['y0']),(g['y1']-g['y0'])/(g['x1']-g['x0']))>=3 for g in f['parts'])
    if not line_parts and not (f['anisotropy']>=9 and f['junctions']==0):scores['l']+=.35
    # A sparse open skeleton is not a closed round/angular body merely because
    # low-resolution pixel distance happens to be small.
    if not f['holes'] and f['density']<.40:
        for key in ('o','s','t'):scores[key]+=.35
    ranked=sorted(scores,key=lambda k:(scores[k],k));best=ranked[0]
    # Refuse weak matches. A second plausible prototype remains an alternative, not a new identity.
    result=[{'key':k,'familyId':'family.'+FAMILIES[k][0],'distance':round(scores[k],6),
             'anchor':examples[k],'basis':'主体填孔轮廓＋骨架原型距离；无名称／语种特征',
             'status':'machine-proposal'} for k in ranked if scores[k]<=min(.30,scores[best]+.035)]
    additions=shape_routes(f,anchors,[a for a in anchors if a['key'] is None])
    for route in additions:
        if not route['priority']:continue
        key=route['key']
        if key is None:return [] # semantic family established, keyboard letter awaits review
        if key=='u' and scores['c']<=route['distance']+.008:continue
        if route['target'].startswith('junction-') and f['density']>.55 and best in ('o','s','t'):continue
        match={'key':key,'familyId':route['familyId'],'distance':round(route['distance'],6),
               'anchor':examples[key],'basis':route['basis'],'status':'machine-proposal'}
        return [match]+[r for r in result if r['key']!=key and (not is_dots or r['key']=='d')]
    return result if scores[best]<=.30 else []


def allocate(family_rows,stage,anchors):
    """Family-first grouping. Optimal old-letter overlap avoids arbitrary letter churn."""
    keys=[k for k in FAMILIES if family_rows.get(k)]
    if not keys:return {},{}
    # One slot per family. Soft bounds permit unused letters and natural oversize families.
    overlap=np.array([[sum(1 for r in family_rows[k] if r['oldBucket']==a) for a in LETTERS] for k in keys])
    from external_paths import shape_dependency_dir
    sys.path.insert(0,str(shape_dependency_dir()))
    from ortools.graph.python import min_cost_flow
    n=len(keys);solver=min_cost_flow.SimpleMinCostFlow()
    for i in range(n):
        for j in range(23):solver.add_arc_with_capacity_and_unit_cost(i,n+j,1,int((overlap.max()-overlap[i,j])*100+j))
        solver.set_node_supply(i,1)
    sink=n+23
    for j in range(23):solver.add_arc_with_capacity_and_unit_cost(n+j,sink,1,0)
    solver.set_node_supply(sink,-n)
    if solver.solve()!=solver.OPTIMAL:raise ValueError('Family-letter mapping failed')
    mapping={keys[solver.tail(i)]:LETTERS[solver.head(i)-n] for i in range(solver.num_arcs()) if solver.tail(i)<n and solver.flow(i)}
    return mapping,{'method':'每个基础形族整族分配一个主桶；最大化旧字母重合，不设硬容量或强填空桶',
                    'capacityTarget':[500,2000],'splits':[],'note':'当前不凭容量拆族；视觉子族的进一步合并／拆分留待核对'}


BENCHMARKS=[
 ('round-family','同主族候选','○◯O0','闭环主体；保留码位身份'),
 ('radial-family','同主族候选','✳✴✵✷✺☆★','放射主体，孔洞与填充作为细节'),
 ('square-family','同主族候选','□▫■▢','方形主体，粗细／填充不同'),
 ('open-arc','同主族候选','C(','开口曲弧，比例可不同'),
 ('ring-accessories','主体／备选入口候选','○⊙⊕⊗Q','附件或内部构件不直接抹去主体'),
 ('different-family','不同主族候选','○□△','闭孔相同不等于主体同族'),
 ('compound','待人工判断','♜♞⚒','复合形不能充当低置信度兜底')]


def stability(primary,fonts,anchors):
    result=[]
    for char in '○◯O0□▫✳✴✵✷✺C⊙⊕':
        if ord(char) not in primary:continue
        path,index=primary[ord(char)];views=[]
        for size,weight in [(48,0),(96,0),(128,0),(96,-1),(96,1)]:
            try:
                mask,extent=render(char,path,index,size,weight,fonts);f=observe(mask,extent);families=classify(f,anchors)
                views.append({'size':size,'weight':weight,'family':families[0]['key'] if families else None,
                              'junctions':f['junctions'],'endpoints':f['endpoints'],'holes':len(f['holes'])})
            except (OSError,ValueError) as e:views.append({'size':size,'weight':weight,'error':str(e)})
        result.append({'cp':ord(char),'char':char,'font':path,'views':views,
                       'familyStable':len({v.get('family') for v in views})==1 and all(v.get('family') for v in views)})
    return result


def build(output=None):
    started=time.monotonic();stage=read(DATA/'shape-stage.json');source=PROJECT/stage['source']
    baseline=protected_inputs(source);rows=read(source/'全部收纳.json')['characters'];old={r['cp']:r for r in rows}
    assert len(rows)==len(old)==159345 and stage['statistics']['ordinary']==28223
    model=read(source/'模型.json');primary,quality,fontmanifest=font_sources(model)
    palette=read(DATA/'全形第四位-当前布局.json')['fourth'];assert len(palette)==18 and palette['c']['function']=='size.medium'
    definitions={'format':'shape-four-key-definitions-v1','featureVersion':VERSION,'status':'awaiting-human-review',
                 'families':family_dictionary(),'semanticFamilies':semantic_family_dictionary(),
                 'third':dictionary(),'legacyTrialKeys':TRIAL_KEYS,'fourth':palette,
                 'thresholds':{'familyDistanceMax':.30,'alternateFamilyMargin':.035,'bodySize':[.35,.60,.90],
                               'relativeSize':[.18,.35,.50],'positionDeadzone':.12,'orientationDegrees':12},
                 'thresholdStatus':'experiment','approval':None}
    if (ROOT/'人工审议.json').exists():definitions['reviewSHA256']=sha(ROOT/'人工审议.json')
    run=output or ROOT/'运行'/datetime.now().strftime('%Y%m%d-%H%M%S')
    if run.exists():raise FileExistsError('Use a fresh run directory')
    run.mkdir(parents=True)
    save(run/'定义快照.json',definitions)
    fonts={};anchors=prototypes(primary,fonts);sections=section_templates(primary,fonts);features={};records=[];family_rows=collections.defaultdict(list)
    # Reuse only a versioned feature cache produced by this module and the exact font inputs.
    font_hashes={path:sha(Path(path)) for path,index in set(primary[cp] for a in LETTERS for cp in stage['buckets'][a])}
    signature=hashlib.sha256(json.dumps({'version':VERSION,'fontHashes':font_hashes,'source':sha(DATA/'shape-stage.json'),
                                        'code':sha(Path(__file__).with_name('shape_experiment_features.py'))},sort_keys=True).encode()).hexdigest()[:20]
    # Readable persisted observations; masks are rendered again for the rule/object pass in this same run.
    cache=run/'字形观测.jsonl.gz'
    with gzip.open(cache,'wt',encoding='utf-8') as stream:
        for i,cp in enumerate(cp for a in LETTERS for cp in stage['buckets'][a]):
            r={'cp':cp,'char':chr(cp),'oldBucket':old[cp]['primary'],'oldReviewed':bool(old[cp].get('shapeAssignmentLocked')),
               'status':'machine-proposal','familyId':None,'familyKey':None,'families':[],'paths':[],'objects':[],'warnings':[]}
            try:
                path,index=primary[cp];mask,extent=render(chr(cp),path,index,fonts=fonts);f=observe(mask,extent)
                r['font']={'path':path,'index':index,'family':quality[cp]['primaryFont']};r['features']=serialize(f)
                matches=classify(f,anchors)
                for item in matches:item['target']='body'
                from shape_experiment_detector import detect
                semantic=detect(f,anchors)
                r['semantic']={k:([{a:b for a,b in q.items() if a!='feature'} for q in v] if k=='routes' else v) for k,v in semantic.items()}
                # Only bound letters can enter the coding pipeline. An unbound
                # double-loop identity remains visible in semantic research data.
                if matches:
                    for route in semantic['routes']:
                        target=route['target']
                        if not route['key'] or not (target.startswith('inner-') or target=='point-array-outline'):continue
                        if any(m['key']==route['key'] and m['target']==target for m in matches):continue
                        matches.append({k:v for k,v in route.items() if k not in ('feature','priority','bbox')})
                        features[(cp,target)]=route.get('feature',f)
                # A substantial enclosed independent component can supply another family interpretation.
                for number,g in enumerate(f['parts']):
                    if g['area']<max(12,f['body'].sum()*.08) or [g['x0'],g['y0'],g['x1'],g['y1']]==f['bbox']:continue
                    b=f['bbox']
                    if b[0]<g['x0'] and b[1]<g['y0'] and g['x1']<b[2] and g['y1']<b[3]:
                        submask=component_mask(mask,g);sub=observe(submask,extent*max(g['x1']-g['x0'],g['y1']-g['y0'])/max(b[2]-b[0],b[3]-b[1]))
                        for item in classify(sub,anchors):
                            if not any(a['key']==item['key'] and a['target']=='inner-'+str(number) for a in matches):matches.append(dict(item,target='inner-'+str(number)))
                        features[(cp,'inner-'+str(number))]=sub
                r['families']=matches
                if matches and matches[0]['target']=='body':
                    r['familyKey']=matches[0]['key'];r['familyId']=matches[0]['familyId'];family_rows[r['familyKey']].append(r)
                else:r['warnings'].append('主体形族低置信度，保留原第一位，不以复合形兜底')
                features[(cp,'body')]=f
                if quality[cp].get('reviewFlags'):r['warnings']+=quality[cp]['reviewFlags']
            except (OSError,ValueError,KeyError) as e:r['warnings'].append('无法可靠观测：'+str(e))
            records.append(r);stream.write(json.dumps(r,ensure_ascii=False)+'\n')
            if (i+1)%1000==0:print('observed',i+1,'/28223',flush=True)
    mapping,allocation=allocate(family_rows,stage,anchors)
    stats=collections.Counter();code_index=collections.defaultdict(list);differences=[];family_representatives={}
    for r in records:
        cp=r['cp'];r['bucket']=mapping.get(r['familyKey'],r['oldBucket']);r['familyRoutes']=[]
        all_paths={};all_objects={}
        for match in r['families']:
            # An inner interpretation alone must not manufacture a new primary family.
            if not r['familyKey']:continue
            focus=features[(cp,match['target'])];bucket=mapping.get(match['key'])
            if not bucket:continue
            r['familyRoutes'].append({'bucket':bucket,'familyId':match['familyId'],'familyKey':match['key'],'target':match['target']})
            for fact in facts(focus,match['key'],sections):
                # A point-centre hull establishes an outline entry, not invented
                # solid ink or holes. Only its measured proportions are eligible.
                if match['target']=='point-array-outline' and fact['third'] not in ('h','v','s'):continue
                if match['target'].startswith('inner-negative-'):fact['object']['polarity']='negative-space'
                fact['object']['id']=match['target']+':'+fact['object']['id']
                all_objects[fact['object']['id']]=fact['object']
                for path in paths(bucket,match['key'],[fact],palette):
                    for e in path['evidence']:e['familyTarget']=match['target'];e['familyId']=match['familyId']
                    entry=all_paths.setdefault(path['code'],{'code':path['code'],'evidence':[]})
                    entry['evidence']+= [e for e in path['evidence'] if e not in entry['evidence']]
        r['paths']=sorted(all_paths.values(),key=lambda p:p['code']);r['objects']=list(all_objects.values())
        for path in r['paths']:code_index[path['code']].append(cp)
        stats[r['bucket']]+=1
        if r['bucket']!=r['oldBucket']:differences.append({'cp':cp,'char':r['char'],'before':r['oldBucket'],'after':r['bucket'],
            'familyId':r['familyId'],'previouslyReviewed':r['oldReviewed'],'reason':'整族聚合提案；不是容量补位'})
    for key in FAMILIES:
        matches=[r for r in records if r['familyKey']==key]
        matches.sort(key=lambda r:(r['families'][0]['distance'],r['cp']))
        family_representatives[key]={'centre':[r['cp'] for r in matches[:12]],'boundary':[r['cp'] for r in matches[-12:]],'count':len(matches),'bucket':mapping.get(key)}
    stability_records=stability(primary,fonts,anchors)
    ordinary_cps={r['cp'] for r in records};assert len(ordinary_cps)==28223
    snapshot={'format':'unicode-shape-experiment-v1','id':'shape-experiment-'+run.name,'status':'awaiting-human-review',
              'active':False,'sourceStage':stage['id'],'definitions':definitions,'familyBuckets':mapping,'representatives':family_representatives,
              'records':records,'collections':{a:stage['buckets'][a] for a in 'xyz'},'unclassified':stage['unclassified'],
              'benchmarks':[{'id':i,'relation':rel,'characters':list(chars),'rationale':why,'reviewStatus':'unreviewed',
                             'predictions':{c:next((r['familyKey'] for r in records if r['char']==c),None) for c in chars}} for i,rel,chars,why in BENCHMARKS]}
    assert len(ordinary_cps | set(snapshot['unclassified']) | set().union(*(set(v) for v in snapshot['collections'].values())))==159345
    prefix_index=collections.defaultdict(set)
    for r in records:
        prefix_index[r['bucket']].add(r['cp'])
        for route in r['familyRoutes']:prefix_index[route['bucket']+route['familyKey']].add(r['cp'])
        for path in r['paths']:
            for length in range(1,len(path['code'])+1):prefix_index[path['code'][:length]].add(r['cp'])
    distribution={str(n):{'occupied':sum(len(k)==n for k in prefix_index),'maximumCandidates':max((len(v) for k,v in prefix_index.items() if len(k)==n),default=0),
                          'medianCandidates':float(np.median([len(v) for k,v in prefix_index.items() if len(k)==n])) if any(len(k)==n for k in prefix_index) else 0} for n in range(1,5)}
    four_count=distribution['4']['occupied'];per_char=[len(r['paths']) for r in records]
    report={'status':'proposal-only','sourceStage':stage['id'],'identities':159345,'ordinary':len(records),
        'familyAssigned':sum(r['familyId'] is not None for r in records),'familyPending':sum(r['familyId'] is None for r in records),
        'withPaths':sum(bool(n) for n in per_char),'pathCount':sum(per_char),'maxPathsPerCharacter':max(per_char),
        'bucketCounts':dict(sorted(stats.items())),'capacityDeviations':{a:{'count':stats[a],'reason':'形族完整性优先，或保留未定族的旧主桶；不强行补位'} for a in LETTERS if not 500<=stats[a]<=2000},
        'allocation':allocation,'changedPrimary':len(differences),'changedPreviouslyReviewed':sum(r['previouslyReviewed'] for r in differences),
        'prefixDistribution':distribution,'definedFourKeySpace':23*len(FAMILIES)*len(RULES)*len(palette),
        'ordinaryTheoreticalSpace':23*26**3,'fourthDefinedSpace':23*26*26*len(palette),'occupiedFourCodes':four_count,
        'emptyFourthDefinedSpace':23*26*26*len(palette)-four_count,'humanFamilyAccuracy':None,
        'humanEvaluation':'人工基准尚未审议，不计算人工准确率；聚类距离不能代替该指标',
        'stabilityCases':len(stability_records),'familyStableCases':sum(r['familyStable'] for r in stability_records),
        'elapsedSeconds':round(time.monotonic()-started,2),'protectedUnchanged':baseline==protected_inputs(source),
        'limitations':['规则表和所有新路径是待审议候选，未冻结为有效码本。','只枚举已实现检测器判定成立的路径；不声称穷尽人眼可见的所有特点。',
                      '内部相连构件识别仍采用保守检测；未可靠提取时不补造路径。','多字体全量稳定性尚未验证；专项字号／粗细和可用替代字体核对另列。']}
    assert report['protectedUnchanged']
    save(run/'shape-experiment.json',snapshot);save(run/'容量与重码报告.json',report);save(run/'主桶差异.json',differences)
    save(run/'渲染稳定性.json',stability_records);save(run/'保护基线.json',baseline)
    save(run/'来源清单.json',{'stageSHA256':sha(DATA/'shape-stage.json'),'fourthSHA256':sha(DATA/'全形第四位-当前布局.json'),
        'featureSignature':signature,'fonts':font_hashes,'anchors':[{k:v for k,v in a.items() if k!='signature'} for a in anchors],
        'codeHashes':{name:sha(Path(__file__).with_name(name)) for name in ['shape_experiment_features.py','shape_experiment_detector.py','shape_experiment_rules.py','build_shape_experiment.py']}})
    text=['# 四键取形实验报告','', '状态：待人工审议；未改当前阶段、历史形码或小狼毫。','',
          f"普通字符 {len(records)}；有形族 {report['familyAssigned']}；待定族 {report['familyPending']}；候选路径 {report['pathCount']}。",
          f"主桶变化提案 {len(differences)}，其中旧确认项 {report['changedPreviouslyReviewed']}；均未应用。",'',
          '## 第三位候选规则','', '| 键 | 含义 | 状态 | 对象／条件 | 正例／反例 |','|---|---|---|---|---|']
    text += [f'| {k} | {v[1]} | {v[2]} | {v[3]} | {v[4]} / {v[5]} |' for k,v in RULES.items()]
    text += ['', '空键允许保留；不按覆盖率强填。人工形族准确率未评估。详细路径通过实验页面按字符或码位核对。',
             '', '容量、渲染稳定性和旧确认项变化详见同目录JSON。']
    (run/'实验报告.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    # Only the finalizer publishes the compact browser index after object validation.
    print(json.dumps({'run':str(run),**report},ensure_ascii=False),flush=True)
    return run,report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args();run,_=build(args.output)
    from finalize_shape_experiment import finalize
    finalize(run)
