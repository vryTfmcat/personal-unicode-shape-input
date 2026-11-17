"""Explicit, current-view-only withdrawals and the single-character O lookup rule."""
import copy
import functools
import hashlib
import json
import continuous_total_semantics as totals
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


@functools.lru_cache(maxsize=1)
def policy():
    d=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    p=d.get('roundSubjectRefinementAcceptance20261025Batch2')
    if not p or p.get('decision')!='accepted':return None
    assert set(p['retainedCompatibility'])=={'7692','7696'}
    assert all(cs==['ioki'] for cs in p['retainedCompatibility'].values())
    assert {k:len(v) for k,v in p['withdrawnCurrentCodes'].items()}=={'7692':6,'7696':7}
    assert all('ioki' not in cs and len(set(cs))==len(cs) for cs in p['withdrawnCurrentCodes'].values())
    assert p['oLookup']['cp']==79 and p['oLookup']['code']=='ioqc'
    assert p['oLookup']['object']['fill']=='hollow'
    for name,chars in [('kFamilyScopeAcceptance20261025Batch1','ĎḊḎḒ'),('kFamilyScopeAcceptance20261025Batch2','ᴰⅮＤ𝗗'),('dStrokeKScopeAcceptance20261026','Đ')]:
        k=d.get(name)
        if not k:continue
        assert k['decision']=='accepted' and set(k['decisions'])=={str(ord(ch)) for ch in chars}
        evidence=ROOT/k['generation']['candidateReport']
        assert evidence.resolve().is_relative_to(ROOT.resolve())
        assert hashlib.sha256(evidence.read_bytes()).hexdigest()==k['generation']['candidateSHA256']
        p=copy.deepcopy(p)
        p.setdefault('kFamilyDecisions',{}).update(copy.deepcopy(k['decisions']))
        for cp,a in k['decisions'].items():
            assert a['humanConfirmed'] and not a['humanCountConfirmed'] and a['familyKey']=='k'
            p['retainedCompatibility'][cp]=a['retainedCompatibility']
            p['withdrawnCurrentCodes'][cp]=a['withdrawnCurrentCodes']
    boxed=d.get('boxedDWithdrawalAcceptance20261025')
    if boxed:
        assert boxed['decision']=='accepted' and set(boxed['decisions'])=={'127283','127347'}
        evidence=ROOT/boxed['candidateReport']
        assert evidence.resolve().is_relative_to(ROOT.resolve())
        assert hashlib.sha256(evidence.read_bytes()).hexdigest()==boxed['candidateSHA256']
        assert boxed['preservePrimary'] and boxed['preservePreferred'] and not boxed['addWholeCounts']
        p=copy.deepcopy(p)
        p['boxedDDecisions']=copy.deepcopy(boxed['decisions'])
        for cp,a in boxed['decisions'].items():
            assert a['primaryFamily']=='s' and not a['preferredCodes']
            assert all(c[1]=='o' for c in a['withdrawnCurrentCodes'])
            assert not set(a['retainedCurrentCodes']) & set(a['withdrawnCurrentCodes'])
            p['retainedCompatibility'][cp]=a['retainedCurrentCodes']
            p['withdrawnCurrentCodes'][cp]=a['withdrawnCurrentCodes']
    shapes=d.get('singleCharacterShapeAcceptance20261026Batch1')
    if shapes:
        assert shapes['decision']=='accepted' and set(shapes['records'])=={'123','42951'}
        assert shapes['noStructureCounts'] and shapes['rejectedAdditions']==['fwei']
        for item in [dict(path=shapes['candidateReport'],sha256=shapes['candidateSHA256'])]+shapes['proofs']:
            evidence=(ROOT/item['path']).resolve()
            assert evidence.is_relative_to(ROOT.resolve()) and hashlib.sha256(evidence.read_bytes()).hexdigest()==item['sha256']
        p=copy.deepcopy(p)
        p['shapeDecisions']=copy.deepcopy(shapes['records'])
        p['viewRevision']=shapes['id']
        assert p['shapeDecisions']['123']['newCodes']==['fweg'] and not p['shapeDecisions']['123']['withdrawnCurrentCodes']
        assert p['shapeDecisions']['42951']['newCodes']==[] and len(p['shapeDecisions']['42951']['withdrawnCurrentCodes'])==9
        assert (p['shapeDecisions']['123']['bucket'],p['shapeDecisions']['123']['familyKey'])==('f','w')
        assert (p['shapeDecisions']['42951']['bucket'],p['shapeDecisions']['42951']['familyKey'])==('i','b')
        assert set(p['shapeDecisions']['42951']['retainedCurrentCodes'])=={'ibis','ibiv','ibiw','ibma','ibmd'}
        assert set(p['shapeDecisions']['42951']['withdrawnCurrentCodes'])=={'iois','ioiv','ioiw','iolc','iolg','iolh','ioma','iomd','iosc'}
        for cp,a in p['shapeDecisions'].items():
            a['acceptanceId']=shapes['id']
            assert a['doNotGenerateCounts'] and not a['preferredCodes']
            assert set(a['beforeCodes'])==set(a['retainedCurrentCodes'])|set(a['withdrawnCurrentCodes'])
            assert not set(a['retainedCurrentCodes']) & set(a['withdrawnCurrentCodes'])
            p['retainedCompatibility'][cp]=a['retainedCurrentCodes']
            p['withdrawnCurrentCodes'][cp]=a['withdrawnCurrentCodes']
    for field,expected in [('dSubjectHoleShapeAcceptance20261027Batch1',{'119811','127251'}),
                           ('dSubjectHoleShapeAcceptance20261027Batch2',{'120227'}),
                           ('dSubjectHoleShapeAcceptance20261027Batch3',{'127376'})]:
        holes=d.get(field)
        if not holes:continue
        assert holes['decision']=='accepted' and set(holes['records'])==expected
        evidence=(ROOT/holes['candidateReport']).resolve()
        assert evidence.is_relative_to(ROOT.resolve())
        assert hashlib.sha256(evidence.read_bytes()).hexdigest()==holes['candidateSHA256']
        p=copy.deepcopy(p)
        for cp,a in copy.deepcopy(holes['records']).items():
            code='ekcv' if cp=='120227' else 'ikcv'
            assert a['newCodes']==[code] and a['doNotGenerateCounts']
            assert a['preferredCodes']==(['eokh'] if cp=='127376' else [])
            assert (a['bucket'],a['familyKey'])==('e' if cp=='120227' else 'i','k')
            assert set(a['beforeCodes'])==set(a['retainedCurrentCodes'])|set(a['withdrawnCurrentCodes'])
            assert a['evidence']['objectId']==a['evidence']['fourthObjectId']==a['holeObject']['id']
            assert a['evidence']['sizeReferenceObjectId']==a['wholeObject']['id']
            assert a['retainedCurrentCodes']=={'119811':['iold'],'127251':['dscv'],'120227':['eovc'],'127376':['eokh']}[cp]
            a['acceptanceId']=holes['id']
            p.setdefault('shapeDecisions',{})[cp]=a
            p['retainedCompatibility'][cp]=a['retainedCurrentCodes']
            p['withdrawnCurrentCodes'][cp]=a['withdrawnCurrentCodes']
        p['viewRevision']=holes['id']
    closure=d.get('roundSubjectClosureAcceptance20261028Batch1')
    if closure:
        assert closure['decision']=='accepted' and set(closure['records'])=={'120123','66580'}
        for item in [dict(path=closure['candidateReport'],sha256=closure['candidateSHA256']),
                     dict(path=closure['proofReport'],sha256=closure['proofSHA256'])]:
            evidence=(ROOT/item['path']).resolve()
            assert evidence.is_relative_to(ROOT.resolve()) and hashlib.sha256(evidence.read_bytes()).hexdigest()==item['sha256']
        p=copy.deepcopy(p)
        for cp,a in copy.deepcopy(closure['records']).items():
            assert a['bucket']=='i' and not a['preferredCodes'] and a['doNotGenerateStrokeCounts']
            assert a['newCodes']==(['ikiv','ikit'] if cp=='120123' else [])
            assert a['familyKey']==('k' if cp=='120123' else 'b')
            assert set(a['beforeCodes'])==set(a['retainedCurrentCodes'])|set(a['withdrawnCurrentCodes'])
            assert len(a['withdrawnCurrentCodes'])==(12 if cp=='120123' else 11)
            a['acceptanceId']=closure['id']
            p.setdefault('shapeDecisions',{})[cp]=a
            p['retainedCompatibility'][cp]=a['retainedCurrentCodes']
            p['withdrawnCurrentCodes'][cp]=a['withdrawnCurrentCodes']
        p['viewRevision']=closure['id']
    return p


def surviving_codes(p,cp):
    result=(p['retainedCompatibility'][cp]
            +p.get('kFamilyDecisions',{}).get(cp,{}).get('newCodes',[])
            +p.get('shapeDecisions',{}).get(cp,{}).get('newCodes',[]))
    if totals.active():
        import shape_structure_bindings as binding
        result=totals.resolve_codes(int(cp),result)+((binding.record(int(cp)) or {}).get('codes',[]))
    return list(dict.fromkeys(result))


def affected_codes(cp, codes):
    p=policy()
    if not p:return list(codes)
    withdrawn=set(p['withdrawnCurrentCodes'].get(str(cp),[]))
    return [c for c in codes if c not in withdrawn]


def members(prefix, entries):
    p=policy()
    if not p:return entries
    for key, keep in p['retainedCompatibility'].items():
        withdrawn=p['withdrawnCurrentCodes'][key]
        surviving=surviving_codes(p,key)
        minimum=1 if key in p.get('boxedDDecisions',{}) or key in p.get('shapeDecisions',{}) else 2
        if len(prefix)>=minimum and any(c.startswith(prefix) for c in withdrawn) and not any(c.startswith(prefix) for c in surviving):
            entries.pop(int(key),None)
    code=p['oLookup']['code']
    if code.startswith(prefix) and prefix:entries[79]=min(entries.get(79,4),0)
    for cp,a in p.get('shapeDecisions',{}).items():
        if prefix and any(c.startswith(prefix) for c in a['newCodes']):entries[int(cp)]=min(entries.get(int(cp),4),1)
    return entries


def brief(row,cp):
    p=policy()
    if not p:return row
    if str(cp) in p['retainedCompatibility']:
        row=dict(row,codes=affected_codes(cp,row.get('codes',[p['code'] for p in row.get('paths',[])])),roundRefinementNote='已撤回其余旧o路；仅保留原首选ioki兼容查询。退出当前圆主体浏览；不改历史视图。')
        if str(cp) in p.get('kFamilyDecisions',{}):
            keep='/'.join(p['retainedCompatibility'][str(cp)])
            row.update(currentFamilyExclusions=['o'],roundRefinementNote='本字整字有孔复合k已确认，整字计数复用九扰动；旧o仅留'+keep+'兼容，其余已撤。原首选状态保持，计数不是人工逐项确认。')
            if cp==272:
                row['roundRefinementNote']='Đ整字k已确认，仅接入ikab／ikgu／ikjb；本字ikqu被拒绝，未生成。保留ioma兼容，iocv／iosc已撤；原首选仍空。本人“两笔写成”与机器曲连续笔计数分开，不改全局q。'
        if str(cp) in p.get('boxedDDecisions',{}):
            row.update(currentFamilyExclusions=['o'],familyCompatibilityNote='错误o备选已撤；保留既有s主族及其它路径。',roundRefinementNote='方框D的错误o备选已撤；s主族与其它既有路径保留，原首选仍未设置；未新增k或整字计数。')
    if cp==79:
        row=dict(row,codes=sorted(set(row.get('codes',[p['code'] for p in row.get('paths',[])]))|{'ioqc'}),roundRefinementNote='ioqc：本字空心圆主体／中等尺寸；ioqu仍表示整字一曲计数。原首选iose保留。')
    a=p.get('shapeDecisions',{}).get(str(cp))
    if a:
        row=dict(row,bucket=a['bucket'],familyKey=a['familyKey'],
            codes=sorted(set(row['codes'])|set(a['newCodes'])),shapeBoundaryAcceptance=a.get('acceptanceId',p['viewRevision']),
            primaryShapeScope=a.get('selectedScope','whole-glyph'))
        if cp==123:
            row.update(legacyPrimaryBucket=a['beforeBucket'],legacyPrimaryFamily=a['beforeFamily'],
                roundRefinementNote='本字按f开放曲线·纵长／w波形查找，仅增fweg；旧6路和空首选保留，不新增计数，不扩展右花括号。')
        elif cp==42951:
            row.update(currentFamilyExclusions=['o'],familyCompatibilityNote='本字上下双闭叶b已确认，九条旧o路已撤；旧b路径保留。',
                roundRefinementNote='Ꟈ按上下双闭叶b处理，退出圆主体；仅留5条既有b路。原计数unstable不改，不新增计数。')
        elif cp==66580:
            row.update(currentFamilyExclusions=['o'],familyCompatibilityNote='本字上下双闭叶b已确认；七条既有b路保留，十一条o路已撤。',
                roundRefinementNote=a['note'])
        else:
            row.update(currentFamilyExclusions=a['excludedCurrentFamilies'],
                familyCompatibilityNote='仅保留'+a['retainedCurrentCodes'][0]+'兼容；旧形族不作为本字已接受主体。',
                roundRefinementNote=a['note'])
    return row


def detail(row,cp,burden):
    p=policy()
    if not p or (cp!=79 and str(cp) not in p['retainedCompatibility']):return row
    row=copy.deepcopy(brief(row,cp))
    if cp!=79:
        withdrawn=set(p['withdrawnCurrentCodes'][str(cp)])
        old=row['paths'];row['paths']=[r for r in old if r['code'] not in withdrawn]
        row['withdrawnCurrentCodes']=[r['code'] for r in old if r['code'] in withdrawn]
        row['codeCounts']={c:n for c,n in row['codeCounts'].items() if c not in withdrawn}
        row['suggestions']=[s for s in row.get('suggestions',[]) if s['code'] not in withdrawn]
        for route in row.get('familyRoutes',[]):
            if route.get('familyKey')=='o':route['compatibilityOnly']=True
        for route in row['paths']:
            if route['code'].startswith('io'):route['compatibilityOnly']=True
        a=p.get('shapeDecisions',{}).get(str(cp))
        if a:
            obj=copy.deepcopy(a['wholeObject']);row['objects'].append(obj)
            if cp==123:
                for route in row['familyRoutes']:route['compatibilityOnly']=True
                for path in row['paths']:path['compatibilityOnly']=True
                row['familyRoutes'].append(dict(bucket='f',familyKey='w',familyId='family.wave',target='body',
                    primary=True,lookupEvidence=dict(verified=True,scope='human-accepted-single-character-whole',acceptance=a.get('acceptanceId',p['viewRevision']))))
                row['paths'].append(dict(code='fweg',preferred=False,acceptedShapeRoute=True,evidence=[dict(
                    rule='topology.no_hole',objectId=obj['id'],fourthObjectId=obj['id'],familyTarget='body',familyId='family.wave',
                    attribute='同一整字无闭孔；同一整字长轴正置',status='human-accepted-single-character-shape-route')]))
                row['codeCounts']['fweg']=burden('fweg')
            elif cp in (42951,66580):
                row['familyRoutes']=[r for r in row['familyRoutes'] if r.get('familyKey')!='o']
                for route in row['familyRoutes']:
                    if route.get('familyKey')=='b':
                        route.update(primary=True,supplementOnly=False,newGeometryBasis='本人接受本字上下双闭叶；不外推所有共边双孔',
                            lookupEvidence=dict(verified=True,scope='human-accepted-single-character-whole',acceptance=a.get('acceptanceId',p['viewRevision'])))
                        if cp==66580:route['selectedSubjectObjectId']=obj['id']
            elif cp==120123:
                import hole_group_bindings as hole_groups
                group=copy.deepcopy(a['holeGroupObject'])
                hole_groups.validate_count_members(row['objects'])
                assert len({o['id'] for o in row['objects']})==len(row['objects'])
                row['objects'].append(group)
                for route in row['familyRoutes']:route.update(primary=False,compatibilityOnly=True)
                for path in row['paths']:path['compatibilityOnly']=True
                row['familyRoutes'].append(dict(bucket='i',familyKey='k',familyId='family.hole-topology',target='body',
                    primary=True,selectedSubjectObjectId=obj['id'],
                    lookupEvidence=dict(verified=True,scope='whole-glyph',acceptance=a['acceptanceId'])))
                for code,key in [('ikiv','singleHoleEvidence'),('ikit','holeGroupEvidence')]:
                    evidence=copy.deepcopy(a[key])
                    evidence.update(familyTarget='body',familyId='family.hole-topology',acceptance=a['acceptanceId'],
                        status='human-accepted-locked-glyph-hole-binding')
                    row['paths'].append(dict(code=code,preferred=False,acceptedShapeRoute=True,evidence=[evidence]))
                    row['codeCounts'][code]=burden(code)
                row.update(holeCountBinding=a['acceptanceId'],holeCountNote=a['note'])
            else:
                hole=copy.deepcopy(a['holeObject']);row['objects'].append(hole)
                for route in row['familyRoutes']:
                    route.update(primary=False,compatibilityOnly=True)
                for path in row['paths']:path['compatibilityOnly']=True
                row['familyRoutes'].append(dict(bucket=a['bucket'],familyKey='k',familyId='family.hole-topology',
                    target=a['selectedTarget'],primary=True,selectedSubjectObjectId=obj['id'],
                    lookupEvidence=dict(verified=True,scope=a['selectedScope'],acceptance=a['acceptanceId'])))
                evidence=copy.deepcopy(a['evidence'])
                evidence.update(familyTarget=a['selectedTarget'],familyId='family.hole-topology',
                    attribute='同一个孔：单闭孔c；孔最长边／所选主体最长边为大v',
                    status='human-accepted-single-character-non-count-route',acceptance=a['acceptanceId'])
                code=a['newCodes'][0]
                row['paths'].append(dict(code=code,preferred=False,acceptedShapeRoute=True,evidence=[evidence]))
                row['codeCounts'][code]=burden(code)
    else:
        obj=copy.deepcopy(p['oLookup']['object']);obj['id']='accepted-O-hollow-subject'
        row['objects'].append(obj)
        row['paths'].append(dict(code='ioqc',preferred=False,roundSubjectRefinement=True,
            evidence=[dict(rule='accepted-O-hollow-subject-size',objectId=obj['id'],fourthObjectId=obj['id'],
                           familyTarget='body',attribute='同族同填充参考系列：空心主体中等尺寸c',
                           status='human-accepted-single-character-binding')]))
        row['codeCounts']['ioqc']=burden('ioqc')
    return row


def key_members(position,key,entries):
    p=policy()
    if not p:return entries
    entries=set(entries)
    if position==2 and key=='o':entries-={int(cp) for name in ('kFamilyDecisions','boxedDDecisions') for cp in p.get(name,{})}
    if position==2:
        for cp,a in p.get('shapeDecisions',{}).items():
            if key in a['excludedCurrentFamilies']:entries.discard(int(cp))
            if key==a['familyKey']:entries.add(int(cp))
    if position>=3:
        for cp,keep in p['retainedCompatibility'].items():
            surviving=surviving_codes(p,cp)
            if not any(c[position-1]==key for c in surviving):entries.discard(int(cp))
    for cp,a in p.get('shapeDecisions',{}).items():
        if any(c[position-1]==key for c in a['newCodes']):entries.add(int(cp))
    if p['oLookup']['code'][position-1]==key:entries.add(79)
    return entries


def key_definition(position,key,item):
    if policy() and position==3 and key=='q':
        item.update(meaning=('含曲的整字直曲总集合；O另有空心主体入口' if totals.active() else '整字曲连续笔集；O另有空心主体入口'),
            condition=(totals.note()+' O的ioqc仍为空心圆主体＋尺寸c。' if totals.active() else '计数q＋u/b/t/y/p仍为整字曲连续笔集；本次仅O的ioqc为已接受空心圆主体＋尺寸c。两种对象不混算，不外推其它字。'),
            lookupException=dict(char='O',code='ioqc',meaning='空心圆主体／中等尺寸',scope='single-character-accepted'))
    return item
