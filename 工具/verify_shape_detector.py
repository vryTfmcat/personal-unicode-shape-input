"""Publish a small isolated detector review; never regenerate/activate full codes."""
import json,hashlib,html,math,shutil
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from build_shape_experiment import DATA,ROOT,PROJECT,EDITOR,read,save,sha,protected_inputs,font_sources,prototypes
from shape_experiment_features import render,observe,VERSION as FEATURES
from shape_experiment_detector import detect,VERSION,DOUBLE_LOOP
from shape_experiment_rules import semantic_family_dictionary


def verify():
    stage=read(DATA/'shape-stage.json');source=PROJECT/stage['source']
    before=protected_inputs(source)
    retained=[ROOT/'最新实验.json',EDITOR/'data/shape-experiment.json',ROOT/'人工审议.json']
    retained_before={str(p):sha(p) for p in retained}
    primary,quality,manifest=font_sources(read(source/'模型.json'));fonts={};anchors=prototypes(primary,fonts)
    run=ROOT/'检测器验证'/datetime.now().strftime('%Y%m%d-%H%M%S')
    run.mkdir(parents=True,exist_ok=False)
    rows=[];checks=[];semantic=semantic_family_dictionary()
    expected={c:'family.'+identity for chars,identity in [
        ('○◯O0⊙⊕⊗Q','round-outline'),('□▫■▢','quadrilateral'),('△','triangle'),('✳✴✵✷✺☆★','radial'),
        ('U∪∩⊂⊃','u-shape'),('C(','open-arc'),('+×YΨ','fork'),('⚒','compound'),('◌∴','dots')]
        for c in chars}
    expected.update({c:DOUBLE_LOOP for c in '∞8'})
    def add(name,mask,extent,font,expect=None,view=None):
        f=observe(mask,extent);r=detect(f,anchors)
        routes=[{k:v for k,v in q.items() if k!='feature'} for q in r['routes']]
        stem=f'{len(rows):03d}.png';im=Image.fromarray(np.uint8(~mask)*255).convert('RGB').resize((128,128),Image.Resampling.NEAREST)
        draw=ImageDraw.Draw(im)
        for q in routes:
            if q['target'].startswith('inner-'):
                box=[2*x for x in q['bbox']];draw.rectangle(box,outline='#087ac0',width=2)
        im.save(run/stem)
        row={'name':name,'font':font,'view':view,'glyph':stem,'primary':r['primaryFamilyId'],'primaryKey':r['primaryKey'],
             'routes':routes,'junctionArms':[j['armCount'] for j in f['junctionObjects']],
             'endpoints':f['endpoints'],'holes':len(f['holes']),'parts':len(f['parts']),
             'pendingKeyboardFamilyIds':r['pendingKeyboardFamilyIds'],'expectedPrimary':expect,
             'passed':None if expect is None else expect==r['primaryFamilyId']}
        rows.append(row)
        if expect is not None:checks.append({'name':name,'view':view,'passed':row['passed'],'expected':expect,'actual':row['primary']})
        return row
    chars='○◯O0⊙⊕⊗Q□▫■▢△✳✴✵✷✺☆★U∪∩⊂⊃C(+×YΨ∞8B⚒◌∴⌒☾♜♞✪'
    for c in chars:
        if ord(c) not in primary:raise ValueError('Missing reference font: '+c)
        path,index=primary[ord(c)]
        for size,weight in [(96,0),(48,0),(128,0),(96,-1),(96,1)]:
            mask,extent=render(c,path,index,size,weight,fonts)
            row=add(c,mask,extent,path,expected.get(c),{'size':size,'weight':weight})
            if c in '+×':checks.append({'name':c+'交叉备选','view':row['view'],'passed':any(q['familyId']=='family.cross' for q in row['routes'])})
            if c=='B':checks.append({'name':'B双环备选','view':row['view'],'passed':row['primary']!=DOUBLE_LOOP and any(q['familyId']==DOUBLE_LOOP for q in row['routes'])})
            if c=='◌':checks.append({'name':'◌轮廓双入口','view':row['view'],'passed':any(q['familyId']=='family.round-outline' for q in row['routes'])})
    alternates=[]
    byfamily={f['family']:(f['path'],f.get('index',0)) for f in manifest['fonts']}
    for c in '○O0✳✴U+×∞8':
        alt=quality[ord(c)].get('alternate')
        if not alt or alt['font'] not in byfamily:continue
        path,index=byfamily[alt['font']]
        if not Path(path).is_file():
            marker='数据/三模式/规则库/字体/';normalized=path.replace('\\','/')
            if marker in normalized:path=str(PROJECT/marker/normalized.split(marker,1)[1])
        mask,extent=render(c,path,index,96,0,fonts)
        row=add(c+' · 替代字体',mask,extent,path,view={'alternate':True,'size':96,'weight':0})
        reference=next(r for r in rows if r['name']==c and r['view']=={'size':96,'weight':0})
        alternates.append({'char':c,'font':path,'referenceFamily':reference['primary'],'alternateFamily':row['primary'],'sameFamily':reference['primary']==row['primary']})
    for count in (3,4,5,6):
        im=Image.new('1',(64,64));d=ImageDraw.Draw(im)
        for i in range(count):
            angle=2*math.pi*i/count;d.line((32,32,round(32+26*math.cos(angle)),round(32+26*math.sin(angle))),fill=1,width=3)
        row=add(f'合成交点{count}支',np.array(im,dtype=bool),1.,'合成几何', 'family.radial' if count>=5 else 'family.fork')
        checks.append({'name':row['name']+'局部计数','passed':row['junctionArms']==[count]})
    for count in (6,7,12):
        im=Image.new('1',(64,64));d=ImageDraw.Draw(im)
        for i in range(count):
            x=32+23*math.cos(2*math.pi*i/count);y=32+23*math.sin(2*math.pi*i/count);d.ellipse((x-2,y-2,x+2,y+2),fill=1)
        row=add(f'合成{count}点圆阵',np.array(im,dtype=bool),1.,'合成几何','family.dots')
        checks.append({'name':row['name']+'双入口','passed':{'family.dots','family.round-outline'}<={q['familyId'] for q in row['routes']}})
    im=Image.new('1',(64,64));d=ImageDraw.Draw(im);d.ellipse((2,2,61,61),outline=1,width=2)
    points=[]
    for i in range(10):
        angle=-math.pi/2+i*math.pi/5;radius=16 if i%2==0 else 7
        points.append((32+radius*math.cos(angle),32+radius*math.sin(angle)))
    d.polygon(points,fill=1)
    row=add('合成圆内星',np.array(im,dtype=bool),1.,'合成几何','family.round-outline')
    checks.append({'name':'圆与内部星独立对象','passed':any(q['familyId']=='family.radial' and q['target'].startswith('inner-') for q in row['routes'])})
    after=protected_inputs(source)
    unchanged=before==after and all(sha(p)==retained_before[str(p)] for p in retained)
    code_files=['shape_experiment_features.py','shape_experiment_detector.py','shape_experiment_rules.py','build_shape_experiment.py','verify_shape_detector.py']
    summary={'detectorVersion':VERSION,'featureVersion':FEATURES,'sourceStage':stage['id'],'active':False,
             'sampleCount':len(rows),'checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],
             'protectedUnchanged':unchanged,'fullCandidateRegenerated':False,'migrationApplied':False,
             'scope':'已确认样本回归；不是独立人工准确率，也不是全量字体稳定性',
             'alternateFontChecks':alternates,
             'limitations':['数值距离、2像素交点合并邻域和点构件阈值仍为试验参数。',
                            '相连星形附件不可靠时不猜造内部入口；无轮廓依据的点阵不补轮廓入口。',
                            '双环无已审定字母；只记录独立形族身份，不造编码。'],
             'retainedHashes':retained_before,'codeHashes':{f:sha(Path(__file__).with_name(f)) for f in code_files}}
    save(run/'检测器验证.json',{'summary':summary,'families':semantic,'rows':rows,'checks':checks})
    save(run/'保护基线.json',before)
    # Reports are always retained; only a passing run is offered from the editor.
    if summary['failed'] or not unchanged:
        print(json.dumps({'run':str(run),**summary},ensure_ascii=False));return 1
    mirror=EDITOR/'data/shape-detector-review'/run.name;mirror.mkdir(parents=True,exist_ok=False)
    for p in run.glob('*.png'):shutil.copy2(p,mirror/p.name)
    save(mirror/'report.json',{'summary':summary,'families':semantic,'rows':rows,'checks':checks})
    e=html.escape;cards=[]
    for row in rows:
        if row['view'] and row['view']!={'size':96,'weight':0} and not row['view'].get('alternate'):continue
        routes='；'.join(semantic[q['familyId']]['meaning']+'（'+q['basis']+'）' for q in row['routes'])
        meaning=semantic[row['primary']]['meaning'] if row['primary'] else '待定'
        cards.append(f'<article><h3>{e(row["name"])}</h3><img width="128" height="128" src="data/shape-detector-review/{run.name}/{row["glyph"]}"><p>主族：{e(meaning)}；候选字母：{e(row["primaryKey"] or "未分配")}</p><p>{e(routes)}</p><p>交点支臂：{row["junctionArms"]}；闭孔：{row["holes"]}；部件：{row["parts"]}</p><small>{e(row["font"])}</small></article>')
    alt_text=f'替代字体检查{len(alternates)}项，{sum(a["sameFamily"] for a in alternates)}项同族；差异：'+('、'.join(a['char'] for a in alternates if not a['sameFamily']) or '无')+'。这些差异未作为已解决。'
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>检测器边界验证</title><link rel="stylesheet" href="shape-experiment.css"><main><a href="shape-experiment.html">返回全量旧实验</a><h1>检测器边界验证 · {run.name}</h1><p>样本{len(rows)}项；断言{len(checks)}项全部通过。包括三个字号和粗细扰动。全量旧候选未重算，主桶迁移未应用。</p><p>{e(alt_text)}</p><p>字母均为候选映射；双环没有已审定字母。♜、♞、☾等仅显示机器判断，不代表人工确认。蓝框表示内部星形对象。</p><p><a href="data/shape-detector-review/{run.name}/report.json">全部样本、扰动结果与来源指纹</a></p>{''.join(cards)}</main></html>'''
    (EDITOR/'shape-detector-review.html').write_text(page,encoding='utf-8')
    local_page=page.replace(f'data/shape-detector-review/{run.name}/','').replace('href="report.json"','href="检测器验证.json"')
    local_page=local_page.replace('<link rel="stylesheet" href="shape-experiment.css">','<style>body{font:16px sans-serif;max-width:1000px;margin:auto}article{border:1px solid #bbb;padding:16px;margin:16px 0}small{overflow-wrap:anywhere}</style>')
    local_page=local_page.replace('<a href="shape-experiment.html">返回全量旧实验</a>','')
    (run/'核对页.html').write_text(local_page,encoding='utf-8')
    save(ROOT/'最新检测器验证.json',{'run':str(run),'detectorVersion':VERSION,'active':False})
    print(json.dumps({'run':str(run),**summary},ensure_ascii=False));return 0


if __name__=='__main__':raise SystemExit(verify())
