"""Scoped attachments and object-local graph comparisons, not a full-table build."""
import base64
import hashlib
import io
import json
import sys
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

import numpy as np
from PIL import Image

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'原型/键位编辑器'))
import shape_structure_bindings as binding
from shape_stroke_topology_trial import render_locked,analyze
from shape_stroke_continuation_trial import analyze_continuation
from shape_subject_graph import cycle_object,contract_closed_core
from shape_experiment_features import render,observe,component_mask,bounds
from shape_keyboard_trial import obj,trial_properties
from verify_p_family_subject_objects import tile


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def fetch(url):
    with urlopen('http://127.0.0.1:8765/api/shape-overview/'+url,timeout=30) as f:return json.load(f)


def radial_audit():
    sets={}
    for position in (2,3):
        first=fetch(f'query?allocation=1&position={position}&key=r')
        urls=[f'query?allocation=1&position={position}&key=r&offset={n}' for n in range(60,first['total'],60)]
        with ThreadPoolExecutor(max_workers=6) as pool:pages=[first]+list(pool.map(fetch,urls))
        sets[position]={r['cp'] for page in pages for r in page['rows']}
        assert len(sets[position])==first['total']
    examples=[]
    for ch in '*☆★✳⁂':
        d=fetch('detail?allocation=1&cp='+str(ord(ch)))
        paths=[p for p in d['paths'] if len(p['code'])>=3 and p['code'][2]=='r']
        examples.append(dict(char=ch,cp=ord(ch),secondR=ord(ch) in sets[2],thirdR=ord(ch) in sets[3],
                             localPaths=paths))
    return dict(secondR=len(sets[2]),thirdR=len(sets[3]),intersection=len(sets[2]&sets[3]),
        onlySecond=len(sets[2]-sets[3]),onlyThird=len(sets[3]-sets[2]),examples=examples,
        conclusion='第二位为主体外形族，第三位为局部至少5臂交点。单中心*的qrr区分价值有限；⁂的多个交点有位置属性，第三位仍能提供信息。重叠人数不代表全部成员语义已核准。',
        recommendation='保留两键，第三位改为更明确的显示名；后续不优先推荐没有新增对象属性的重复路径。未删除或改动任何r旧码。')


def build():
    manual=json.loads((PROJECT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    if manual.get('subjectAttachmentAcceptance20261025',{}).get('decision')=='accepted':
        raise RuntimeError('主体附件proof已被人工审议按SHA锁定，禁止覆盖冻结证据；当前结果页使用render_subject_followup.py离线再现。新实验须使用隔离候选流程。')
    out=binding.active_report_path().parent/'主体附件与连接区处理';out.mkdir(exist_ok=True)
    source=PROJECT/'数据/三模式/规则库/四键实验/键位试验/20261024-other-large-collisions-v1/其他大组分析.json'
    rows={r['char']:r for r in json.loads(source.read_text(encoding='utf-8'))['records'] if r['char'] in 'ρộȣᛒ'}
    protected=[binding.PATH,binding.active_report_path(),PROJECT/'原型/键位编辑器/data/pictorial-exclusive-allocation.json',PROJECT/'数据/三模式/全形核对版.json']
    before={p.relative_to(PROJECT).as_posix():sha(p) for p in protected}
    repairs=[];illustrations=[]
    for ch in 'ρȣᛒ':
        row=rows[ch];variants=[]
        for size in (96,192,256):
            for weight in (-1,0,1):
                m=render_locked(ch,row['font'],size=size,weight=weight);old=analyze(m);oc=analyze_continuation(m,old)
                assert dict(old['statistics'],**oc['statistics'])==row['statistics']
                if ch=='ρ':
                    correction=cycle_object(old);assert correction['verified']
                    record=dict(size=size,weight=weight,correction=correction)
                    if (size,weight)==(192,0):
                        im=Image.fromarray(255-m.astype('uint8')*70).convert('RGB')
                        from PIL import ImageDraw
                        ImageDraw.Draw(im).line([tuple(p) for p in correction['sourcePoints']],fill='#0675c8',width=3)
                        illustrations.append((ch,im))
                else:
                    new=analyze(m,graph_transform=contract_closed_core);nc=analyze_continuation(m,new)
                    assert nc['graphCycleCount']==oc['graphCycleCount'] and nc['topologyAgrees']
                    record=dict(size=size,weight=weight,before=dict(old['statistics'],**oc['statistics']),
                        after=dict(new['statistics'],**nc['statistics']),proof=new['objectGraphCorrection'])
                    if (size,weight)==(192,0):illustrations.append((ch,tile(m,new,nc)))
                variants.append(record)
        if ch=='ρ':
            status='inherited-cycle-fixed-nine-of-nine; no cut reskeletonization'
            assert all(v['correction']['statistics']['curveStrokes']==1 for v in variants)
        else:
            signatures={json.dumps(v['after'],sort_keys=True) for v in variants}
            status='candidate-stable-nine-of-nine-not-runtime-applied' if len(signatures)==1 else 'candidate-rejected-not-nine-view-stable'
            if ch=='ᛒ':assert len(signatures)==1 and all(v['after']['straightStrokes']==5 and v['after']['crosses']==1 for v in variants)
            if ch=='ȣ':assert len(signatures)>1
        repairs.append(dict(char=ch,cp=ord(ch),status=status,variants=variants))
    # Counterexamples are open junctions, a round outline, and a framed bar.
    controls=[];font=dict(path='C:/Windows/Fonts/seguisym.ttf',index=0)
    for ch in 'HTXO⊟':
        for size in (96,192,256):
            for weight in (-1,0,1):
                m=render_locked(ch,font,size=size,weight=weight);a=analyze(m);b=analyze(m,graph_transform=contract_closed_core)
                assert a['statistics']==b['statistics'],('negative control changed',ch,size,weight)
                controls.append(dict(char=ch,size=size,weight=weight,unchanged=True))
    # Exact connected masks for the reviewed ộ attachments; no bbox clipping.
    row=rows['ộ'];mask,extent=render('ộ',row['font']['path'],row['font'].get('index',0));f=observe(mask)
    parts=[component_mask(mask,p) for p in f['parts']]
    ring=next(p for p in parts if len(observe(p)['holes'])==1);rb=bounds(ring)
    extras=[p for p in parts if not np.array_equal(p,ring)];extra_objects=[]
    for p in extras:
        pf=observe(p);box=bounds(p);below=box[1]>rb[3];third='t' if below else 'y'
        identity='reviewed-ộ-external-dot' if below else 'reviewed-ộ-external-caret'
        o=obj(identity,'part',box,rb,extent,area=int(p.sum()))
        props=dict(trial_properties(o));fourth='s' if below else 'w';assert fourth in props
        extra_objects.append(dict(code='io'+third+fourth,third=third,fourth=fourth,object=o,
            evidence=dict(rule='component.external_dot' if below else 'component.external_stroke',objectId=identity,
                fourthObjectId=identity,familyTarget='reviewed-circle-subject',attribute='主体下方的外部点块' if below else '主体上方的外部折线构件',
                status='human-scope-accepted-machine-object-verified')))
    colored=np.full((*mask.shape,3),255,dtype='uint8')
    for part in parts:
        colored[part]=([0,112,205] if np.array_equal(part,ring) else
                       [205,55,55] if bounds(part)[1]>rb[3] else [220,125,15])
    Image.fromarray(colored).resize((256,256),Image.Resampling.NEAREST).save(out/'ộ主体与附件原墨迹.png')
    variants=[]
    for size in (96,192,256):
        for weight in (-1,0,1):
            m=render_locked('ộ',row['font'],size=size,weight=weight)
            from verify_p_family_subject_objects import partition
            subject,remainder,proof=partition('ộ',m);parts2=observe(remainder)['parts'];assert len(parts2)==2
            sb=bounds(subject);positions=sorted('below' if p['y0']>sb[3] else 'above' for p in parts2)
            assert positions==['above','below'];variants.append(dict(size=size,weight=weight,positions=positions,partition=proof))
    a=radial_audit()
    report=dict(date='2026-10-25',version='subject-attachment-and-core-followup-v1',structureVersion=binding.data()['version'],
        repairs=repairs,negativeControls=controls,radial=a,attachment=dict(char='ộ',cp=ord('ộ'),subjectBBox=rb,
            subjectPixels=int(ring.sum()),sourcePixels=int(mask.sum()),sourceInkSHA256=hashlib.sha256(mask.tobytes()).hexdigest(),
            ringInkSHA256=hashlib.sha256(ring.tobytes()).hexdigest(),objects=extra_objects,variants=variants),
        protectedHashes=before,scope='对象局部修正与附件路由；默认全局计数未变，不重建全表')
    assert before=={p.relative_to(PROJECT).as_posix():sha(p) for p in protected}
    (out/'主体附件与连接区验证.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    atlas=Image.new('RGB',(576,192),'white')
    for i,(_,im) in enumerate(illustrations):atlas.paste(im,(i*192,0))
    atlas.save(out/'原图继承环与连接区候选.png')
    print(json.dumps(dict(passed=True,repairVariants=27,controlVariants=len(controls),attachmentVariants=9,
        routes=[o['code'] for o in extra_objects],radialCounts={k:a[k] for k in ('secondR','thirdR','intersection')}),ensure_ascii=False))
    return report


if __name__=='__main__':build()
