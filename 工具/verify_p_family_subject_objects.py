"""Audit only five reviewed glyphs with immutable existing geometry methods.

No classifier tuning, new bindings, human decisions, or runtime writes.
"""
import hashlib
import json
import sys
import base64
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'原型/键位编辑器'))
import shape_structure_bindings as binding
from shape_stroke_topology_trial import render_locked,analyze
from shape_stroke_continuation_trial import analyze_continuation
from shape_experiment_features import render,observe,component_mask,bounds
from shape_reviewed_components import cycle_subject
from shape_lab_features import components
from audit_shape_other_collisions import FIELDS

CHARS='ρộȣᛒ𞥕'
COLORS=['#155be0','#d82028','#008b66','#8a31bc','#d67d00','#008cb8','#ad3f76','#626c00']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(mask):
    base=analyze(mask);continuation=analyze_continuation(mask,base)
    return base,continuation,dict(base['statistics'],**continuation['statistics'])


def tile(mask,base,continuation):
    im=Image.fromarray(255-mask.astype('uint8')*70).convert('RGB');draw=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
    for s in continuation['strokes']:
        points=[tuple(p) for p in s['points']]
        color=COLORS[s['id']%len(COLORS)]
        if len(points)>1:draw.line(points,fill=color,width=3)
        middle=points[len(points)//2];draw.text(middle,str(s['id'])+('S' if s['kind']=='straight' else 'C'),fill=color,font=font,stroke_width=1,stroke_fill='white')
    for corner in base['corners']:
        x,y=corner['xy'];draw.rectangle((x-3,y-3,x+3,y+3),outline='#111111',width=1)
    for j in base['junctions']:
        x,y=j['xy'];draw.ellipse((x-5,y-5,x+5,y+5),outline='#111111',width=1)
    return im


def partition(ch,mask):
    if ch=='ρ':
        extracted=cycle_subject(observe(mask))
        if extracted is None:return None
        f,tail,proof=extracted;subject=mask&~tail
        assert not (subject&tail).any() and np.array_equal(subject|tail,mask)
        return subject,tail,proof
    if ch=='ộ':
        parts=[p for p in components(mask,8) if p['area']>=3]
        candidates=[]
        for p in parts:
            component=component_mask(mask,p)
            if len(observe(component)['holes'])==1:candidates.append(component)
        if len(candidates)!=1:return None
        subject=candidates[0];remainder=mask&~subject
        assert not(subject&remainder).any() and np.array_equal(subject|remainder,mask)
        return subject,remainder,dict(kind='one-closed-connected-component',parentComponents=len(parts),
            parentPixels=int(mask.sum()),subjectPixels=int(subject.sum()),remainderPixels=int(remainder.sum()),
            subjectBBox=bounds(subject),remainderBBox=bounds(remainder),overlapPixels=0,
            partition='existing connected ink; no drawing, filling, or bbox-only cutting')
    return None


def conclusions(records):
    summaries=[]
    notes={
        'ρ':('主体分离通过；新主体计数不通过',
             '复现原64像素圆主体753／尾笔147像素的分离证据，互不重叠且并集900像素。九次高分辨率分离都保留一个闭孔，但切口附近小支杈使主体角点0—1、分叉0—1、直连续笔0—1、曲连续笔1—2。可保留原圆主体查法，不能把整字1曲或任一单次结果当主体新计数。'),
        'ộ':('独立圆主体及其计数通过',
             '九次均分成圆主体、上方折形、下方点三个墨迹部件；只提取有一个闭孔的连通部件，余墨完整保留。主体均为0角、0叉、0直连续笔、1曲连续笔、1孔；整字的1角和2直连续笔来自上方折形，不属于圆主体。'),
        'ȣ':('整字对象及一孔通过；连续笔解释待核',
             '整字是一个连通墨部件，上开下闭，九次均一个闭孔，不是两个完整闭环。机器稳定报0角、2叉、1直／3曲连续笔；其中腰部短桥被单列为直笔，左右上弧也分别断开。数值可复现，但不能仅凭稳定数值把独立直笔解释视作已核准。p候选保持原状。'),
        'ᛒ':('双闭叶主体通过；连接区计数待核',
             '整字是一个连通部件，九次均有上下两个分离闭孔，与本字已接受的两个角形闭叶相符；原b主体对象与全字墨迹范围相同。机器稳定报4角、2叉、6直连续笔，其中有连接区短桥；另剪除了两条短末梢。暂不据6直笔生成新b计数入口，也不推广其它角形双叶。'),
        '𞥕':('整字对象及现行模型计数通过',
             '整字一个连通部件、一个闭叶接开口曲尾；九次均3角、1三叉、0四叉、4直／1曲连续笔、1孔。标注图可对应四段直边和下方曲尾，未剪末梢、没有配对歧义。连接处按现行规则列三叉，3角是模型报告的非交点折角，不宣称手写笔顺，也不额外补算重合角点。原有四条p结构入口保持。'),
    }
    for r in records:
        ch=r['char'];status,note=notes[ch]
        subset=[v for v in r['variants'] if 'subjectStatistics' in v]
        if ch in 'ρộ':assert len(subset)==9 and all(v['subjectStatistics']['loops']==1 for v in subset)
        if ch=='ộ':assert all(v['subjectStatistics'][k]==value for v in subset for k,value in dict(corners=0,forks=0,crosses=0,straightStrokes=0,curveStrokes=1,loops=1).items())
        if ch=='ᛒ':assert all(v['inkComponents']==1 and v['wholeStatistics']['loops']==2 for v in r['variants'])
        bridge=min(r['baseline']['strokes'],key=lambda s:s['metrics']['pathLength'])
        summaries.append(dict(cp=r['cp'],char=ch,status=status,conclusion=note,
            countScope='circle-subject' if ch in 'ρộ' else 'whole-glyph',
            wholeStatistics=r['baseline']['statistics'],
            subjectValueSets={key:sorted({v['subjectStatistics'][key] for v in subset}) for key in ('corners','forks','crosses','straightStrokes','curveStrokes','loops')} if subset else None,
            shortestStroke=dict(id=bridge['id'],kind=bridge['kind'],pathLength=bridge['metrics']['pathLength'],
                estimatedStrokeWidth=r['baseline']['estimatedStrokeWidth'],points=bridge['points']) if ch in 'ȣᛒ' else None,
            humanCountConfirmation=False,newCodes=[]))
    return summaries


def write_page(report,sheet,out):
    slim={k:report[k] for k in ('date','activeVersion','scope','summary','bindingBoundary','handoff')}
    slim['cards']=[]
    for i,r in enumerate(report['records']):
        buf=io.BytesIO();sheet.crop((0,i*230,768,(i+1)*230)).save(buf,format='PNG')
        slim['cards'].append(dict(char=r['char'],cp=r['cp'],image='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode(),
            font=r['font'],variants=r['variants'],legacy64Partition=r['legacy64Partition']))
    template=Path(__file__).with_name('p_family_object_verification_template.html').read_text(encoding='utf-8')
    page=template.replace('__DATA__',json.dumps(slim,ensure_ascii=False).replace('</','<\\/'))
    (out/'主体对象与计数补验.html').write_text(page,encoding='utf-8')
    (PROJECT/'原型/键位编辑器/p-family-object-verification.html').write_text(page,encoding='utf-8')


def build():
    manual_path=PROJECT/'数据/三模式/规则库/四键实验/人工审议.json'
    if json.loads(manual_path.read_text(encoding='utf-8')).get('subjectAttachmentAcceptance20261025'):
        raise RuntimeError('主体附件已确认；五字补验材料保持冻结，禁止旧生成器覆盖当前p-family-object-verification.html。离线再现当前结果使用render_subject_followup.py。')
    source=PROJECT/'数据/三模式/规则库/四键实验/键位试验/20261024-other-large-collisions-v1/其他大组分析.json'
    original=json.loads(source.read_text(encoding='utf-8'))
    rows={r['char']:r for r in original['records'] if r['char'] in CHARS}
    current={r['char']:r for r in binding.review_report()['records'] if r['char'] in CHARS}
    assert set(rows)==set(CHARS) and binding.data()['version']=='structure-count-bindings-v5'
    out=binding.active_report_path().parent/'主体对象补验';out.mkdir(exist_ok=True)
    protected=[binding.PATH,binding.active_report_path(),source,
        PROJECT/'数据/三模式/规则库/四键实验/人工审议.json',
        PROJECT/'原型/键位编辑器/data/pictorial-exclusive-allocation.json',PROJECT/'数据/三模式/全形核对版.json',
        Path(__file__).with_name('shape_stroke_topology_trial.py'),Path(__file__).with_name('shape_stroke_continuation_trial.py'),
        Path(__file__).with_name('shape_reviewed_components.py'),PROJECT/'原型/键位编辑器/shape_overview.py',
        PROJECT/'原型/键位编辑器/shape_structure_bindings.py']
    before={p.relative_to(PROJECT).as_posix():sha(p) for p in protected}
    results=[];sheet=Image.new('RGB',(192*4,230*len(CHARS)),'white');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
    for i,ch in enumerate(CHARS):
        row=rows[ch];variants=[];baseline=None;objects=[]
        cached={ (v['size'],v['weight']):v for v in row['observations'] }
        # Replay exactly the existing nine observations, without changing thresholds.
        for size in (96,192,256):
            for weight in (-1,0,1):
                mask=render_locked(ch,row['font'],size=size,weight=weight)
                base,cont,count=stats(mask)
                assert [count[k] for k in FIELDS]==cached[size,weight]['values']
                assert count==current[ch]['statistics']
                value=dict(size=size,weight=weight,wholeStatistics=count,topologyAgrees=cont['topologyAgrees'],
                    ambiguities=cont['ambiguities'],inkComponents=len([p for p in components(mask,8) if p['area']>=3]))
                part=partition(ch,mask)
                if part:
                    subject,remainder,proof=part;sb,sc,ss=stats(subject)
                    value.update(subjectStatistics=ss,subjectTopologyAgrees=sc['topologyAgrees'],
                                 subjectAmbiguities=sc['ambiguities'],partition=proof,
                                 subjectInkSHA256=hashlib.sha256(subject.tobytes()).hexdigest())
                variants.append(value)
                if (size,weight)==(192,0):
                    baseline=dict(mask=mask,base=base,continuation=cont,part=part)
        # Independently replay the older 64px object-partition evidence.
        legacy_mask,extent=render(ch,row['font']['path'],row['font'].get('index',0))
        legacy=partition(ch,legacy_mask)
        legacy_partition=legacy[2] if legacy else None
        legacy_evidence=None
        chunk=json.loads((PROJECT/'数据/三模式/规则库/四键实验/键位试验/20261021-connected-stroke-group-full-v1'/row['detailUrl']).read_text(encoding='utf-8'))
        old_detail=next(r for r in chunk['records'] if r['cp']==ord(ch))
        if ch=='ρ':
            old_proof=next(r['componentPartitionProof'] for r in old_detail['familyRoutes'] if r['target']=='cycle-subject')
            assert old_proof==legacy_partition
            legacy_evidence='原64像素圆主体／尾笔划分逐字段完全复现'
        if ch=='ᛒ':
            ob={o['id']:o for o in old_detail['objects']}
            assert ob['body:p:body']['bbox']==ob['body:b:body']['bbox']==bounds(legacy_mask)
            legacy_evidence='原p、b主体包围范围均覆盖同一完整连通墨迹；新复验9次均2个闭孔'
        b=baseline;whole=Image.fromarray(255-b['mask'].astype('uint8')*255).convert('RGB')
        sheet.paste(whole,(0,i*230));sheet.paste(tile(b['mask'],b['base'],b['continuation']),(192,i*230))
        if b['part']:
            subject,remainder,proof=b['part'];colored=np.full((*subject.shape,3),255,dtype='uint8');colored[subject]=[0,115,205];colored[remainder]=[220,90,40]
            sheet.paste(Image.fromarray(colored),(384,i*230));sb,sc,ss=stats(subject);sheet.paste(tile(subject,sb,sc),(576,i*230))
        for x,text in [(0,'whole ink'),(192,'whole strokes: S=straight C=curve'),(384,'subject=blue remainder=orange'),(576,'subject strokes')]:draw.text((x+2,i*230+193),text,fill='black',font=font)
        draw.text((2,i*230+210),f'U+{ord(ch):04X} source font: {row["font"]["family"]}',fill='black',font=font)
        results.append(dict(cp=ord(ch),char=ch,font=row['font'],fontSHA256=sha(Path(row['font']['path'])),
            originalCodes=current[ch]['oldCodes'],originalPreferredCodes=current[ch]['oldPreferredCodes'],currentStructuralCodes=current[ch]['codes'],
            nineWholeReplaysMatch=True,variants=variants,legacy64Partition=legacy_partition,legacyEvidence=legacy_evidence,
            baseline=dict(statistics=current[ch]['statistics'],corners=b['base']['corners'],junctions=b['base']['junctions'],
                segments=b['base']['segments'],edges=b['base']['edges'],prunedSpurs=b['base']['prunedSpurs'],
                estimatedStrokeWidth=b['base']['estimatedStrokeWidth'],
                strokes=b['continuation']['strokes'],pairings=b['continuation']['pairings'],holes=b['continuation']['holes'])))
    sheet.save(out/'五字对象与连续笔证据.png')
    assert before=={p.relative_to(PROJECT).as_posix():sha(p) for p in protected}
    report=dict(version='p-family-subject-count-verification-v1',date='2026-10-25',activeVersion=binding.data()['version'],
        scope='仅ρ/ộ/ȣ/ᛒ/𞥕对象与计数复验；不调参、不派码、不写人工确认',records=results,protectedHashes=before,
        limitations='同一锁定字体九扰动复现不等于人工语义计数确认。主体掩膜和整字掩膜分别记录，不能混用。')
    report['summary']=conclusions(results)
    report['bindingBoundary']='当前新增第三位a/b/g/j/q定义为整字特征集合。本次ộ通过的是圆主体1曲，不得直接填成ioqu；这需要先明确主体集合如何绑定第三、第四位。ρ原圆主体查法已存在；本轮不把AI复验改写成人工计数确认，不修改v5或生成新码。'
    report['handoff']=[dict(char='ρ',issue='主体分离切口产生小支杈；原主体外形可用但九扰动连续笔不稳',action='对象提取专项复核切口；此处不调整全局提取器'),
        dict(char='ȣ',issue='腰部短桥与上方左右弧被分别列为1直、2曲，另有下环1曲',action='连续笔专项核查短桥及配对定义，不先宣称应是2曲'),
        dict(char='ᛒ',issue='连接区短桥计入第6直笔、2个三叉；同时剪除两短末梢',action='连续笔专项核查连接区简化，不按预期5直笔调参')]
    (out/'五字对象与计数复验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_page(report,sheet,out)
    lines=['# 首批五字主体对象与计数补验','',report['scope'],'',report['limitations'],'',report['bindingBoundary'],'']
    for s in report['summary']:lines.extend(['## '+s['char']+'：'+s['status'],'',s['conclusion'],''])
    (out/'主体对象与计数补验结论.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    handoff=['# 主体切口与连接区计数问题交接','','只交接可复现证据，不重复大重码算法实验，不修改公共计数器。','']
    for item in report['handoff']:handoff.extend(['## '+item['char'],'',item['issue'],item['action'],''])
    handoff.extend(['详细九扰动、字体SHA、原始线段／连续笔路径和剪枝记录见五字对象与计数复验.json；图见五字对象与连续笔证据.png。',
                    '所有现行码、原首选、t/b、冻结v5与人工审议保持；无需本人再重复判断已确认的形族。'])
    (out/'计数问题交接.md').write_text('\n'.join(handoff)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,glyphs=5,wholeVariants=45,protectedUnchanged=True,output=str(out)),ensure_ascii=False))


if __name__=='__main__':build()
