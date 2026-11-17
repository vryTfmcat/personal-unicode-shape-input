"""Approved seven BC routes, applied last so retired canonical routes cannot revive."""
import copy,functools,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FIELD='jointBCSevenAcceptance20261029Batch1'
ID='joint-bc-seven-20261029-v1'

@functools.lru_cache(maxsize=1)
def policy():
    authority=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    a=authority.get(FIELD)
    if not a:return None
    assert a['id']==ID and a['decision']=='accepted'
    assert set(a['records'])=={'56','7897','272','120123'}
    assert set(a['approvedCodes'])=={'eesw','eeci','ifgb','ifmg','inmt','iegt','iezv'}
    p=(ROOT/a['baselineDetails']).resolve();assert p.is_relative_to(ROOT.resolve())
    assert hashlib.sha256(p.read_bytes()).hexdigest()==a['baselineDetailsSHA256']
    eight=authority['holeGroupDirectionAcceptance20261027Batch1']
    source=ROOT/eight['proofReport'];assert hashlib.sha256(source.read_bytes()).hexdigest()==eight['proofSHA256']
    variants=json.loads(source.read_text(encoding='utf-8'))['variants']
    assert len(variants)==9 and all(0<v['topBottomAreaRatio']<1 and 0<v['topBottomMaxSideRatio']<1 for v in variants)
    for rel,h in a['sourceHashes'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h
    for cp,r in a['records'].items():
        assert sorted(set(r['beforeCodes'])-set(r['retiredCanonicalCodes'])|set(r['newCodes']))==r['afterCodes']
        assert not set(r['preferredCodes'])&set(r['retiredCanonicalCodes'])
        for path in r['paths']:
            assert path['code'] in r['newCodes']
            e=path['evidence'][0];assert e['objectId']==e['fourthObjectId']
            assert path['code'][1:3]==e['BC']
    return a

def record(cp):return (policy() or {}).get('records',{}).get(str(cp))
def codes():return (policy() or {}).get('approvedCodes',[])
def validate_binding(cp,path,objects):
    """Validate this approved locked binding; deliberately no general classifier."""
    r=record(cp)
    if not r or path['code'] not in r['newCodes']:raise ValueError('本字未批准该四码或D值')
    expected=next(p for p in r['paths'] if p['code']==path['code'])
    if path!=expected:raise ValueError('绑定对象或固定D证据不符本字批准')
    e=path['evidence'][0];o=objects[e['objectId']];bc=e['BC']
    if e['objectId']!=e['fourthObjectId']:raise ValueError('第三第四位对象不一致')
    if bc=='es':
        domain=[objects[m] for m in e['comparisonDomainIds']]
        if len(domain)!=2 or any(x['kind']!='hole' for x in domain):raise ValueError('较小孔比较域必须恰两孔')
        span=lambda x:max(x['bbox'][2]-x['bbox'][0],x['bbox'][3]-x['bbox'][1])
        if any(o['area']>=x['area'] or span(o)>=span(x) for x in domain if x['id']!=o['id']):raise ValueError('较小孔不唯一或两度量冲突')
    elif bc in ['ec','fg','fm','eg']:
        count=3 if bc=='eg' else 2
        if len(o['members'])!=count or o['members']!=e['members']:raise ValueError('完整组成员不符，不得任取子集')
        if bc in ['ec','eg'] and any(objects[m]['kind']!='hole' for m in o['members']):raise ValueError('孔组含非空孔对象')
        if bc in ['fg','fm'] and 'reviewed-ộ-circle-subject' in o['members']:raise ValueError('外件组混入主体')
    elif bc=='nm':
        t=o['memberTypeCounts']
        if not(t['straight']>0 and t['curve']>0 and o['count']==sum(t.values())==3):raise ValueError('非混合整字总集三组')
    elif bc=='ez':
        b=objects[e['sizeReferenceObjectId']]
        span=lambda x:max(x['bbox'][2]-x['bbox'][0],x['bbox'][3]-x['bbox'][1])
        if e['referenceScope']!='whole-glyph' or span(o)/span(b)!=49/60:raise ValueError('中央孔须相对批准整字参照')
    return True
def migrate_structure(cp,old):
    r=record(cp)
    import joint_count_bindings
    base={r['replacements'].get(c,c) for c in old} if cp==272 and r else set(old)
    return joint_count_bindings.migrate_structure(cp,base)

def brief(row,cp):
    r=record(cp)
    if not r:return row
    result=dict(row,codes=sorted((set(row.get('codes',[p['code'] for p in row.get('paths',[])]))-set(r['retiredCanonicalCodes']))|set(r['newCodes'])),
        jointBCVersion=ID,canonicalRetiredCodes=r['retiredCanonicalCodes'],compatibilityCodes=r['retiredCanonicalCodes'],
        jointBCNote='七组合已按本字锁定对象批准；旧等用途规范路已替换，仅显式兼容可达。主形族、桶、原首选及其它用途保持。')
    if 'structuralCodes' in result:result['structuralCodes']=sorted(migrate_structure(cp,result['structuralCodes']))
    return result

def members(prefix,entries):
    if not policy() or not prefix:return entries
    for cp,r in policy()['records'].items():
        cp=int(cp)
        if any(c.startswith(prefix) for c in r['beforeCodes']+r['afterCodes']):
            if any(c.startswith(prefix) for c in r['afterCodes']):entries[cp]=min(entries.get(cp,4),1)
            else:entries.pop(cp,None)
    return entries

@functools.lru_cache(maxsize=1)
def baseline_families():
    a=policy()
    return {int(cp):d.get('familyKey') for cp,d in json.loads((ROOT/a['baselineDetails']).read_text(encoding='utf-8')).items()} if a else {}

def key_members(position,key,entries):
    result=set(entries)
    if not policy():return result
    for cp,r in policy()['records'].items():
        cp=int(cp)
        old=any(len(c)>=position and c[position-1]==key for c in r['beforeCodes'])
        new=any(len(c)>=position and c[position-1]==key for c in r['afterCodes'])
        if old and not new and not(position==2 and baseline_families().get(cp)==key):result.discard(cp)
        elif new and not old:result.add(cp)
    return result

def detail(row,cp,burden):
    r=record(cp)
    retired={c for x in (policy() or {}).get('records',{}).values() for c in x['retiredCanonicalCodes']}
    impacted=retired & set(row.get('codeCounts',{}))
    if impacted:
        row=copy.deepcopy(row)
        row['frozenStructuralCodeCounts']={c:row['codeCounts'][c] for c in impacted}
        for c in impacted:row['codeCounts'][c]=burden(c)
        for option in row.get('suggestions',[]):
            if option['code'] in impacted:option['allCandidates']=burden(option['code'])
    if not r:return row
    result=copy.deepcopy(row);oldpaths={p['code']:p for p in result['paths']}
    assert set(r['retiredCanonicalCodes'])<=set(oldpaths)
    result['paths']=[p for p in result['paths'] if p['code'] not in r['retiredCanonicalCodes']]+copy.deepcopy(r['paths'])
    assert {p['code'] for p in result['paths']}==set(r['afterCodes'])
    result['codeCounts']={p['code']:burden(p['code']) for p in result['paths']}
    result['compatibilityPaths']=copy.deepcopy(r['compatibilityPaths'])
    result['compatibilityCodeCounts']={p['code']:burden(p['code'])+1 for p in r['compatibilityPaths']}
    # Existing approved object IDs, members and parents must still match the source.
    objects={o['id']:o for o in result['objects']}
    for path in r['paths']:
        e=path['evidence'][0];assert e['objectId'] in objects
        assert all(m in objects for m in e['members'])
        expected=next(o for o in r['objects'] if o['id']==e['objectId'])
        assert objects[e['objectId']]==expected
        validate_binding(cp,path,objects)
    if 'structuralRecommendations' in result:result['structuralRecommendations']=sorted(migrate_structure(cp,result['structuralRecommendations']))
    result['suggestions']=[s for s in result.get('suggestions',[]) if s['code'] not in r['retiredCanonicalCodes']]
    result['suggestions'] += [dict(code=p['code'],allCandidates=burden(p['code']),preferred=False,scope='本人批准本字BC组合') for p in r['paths']]
    for k in ['holeGroupNote','currentFeedbackNote','roundRefinementNote']:
        if k in result:result[k]='旧确认历史见兼容路径；现行七组合为 '+ ' / '.join(r['newCodes'])+'。旧码已退出本字规范推荐，不反向注入。'
    result=brief(result,cp)
    if cp==56:result['currentFeedbackNote']='本人确认上小下大；eesw取较小孔w上，eeci取共同圆弧孔组i纵向；ebii仅显式兼容。'
    if cp==272:result['currentFeedbackNote']='当前全局总数3（直2＋曲1）语义保持；inmt取混合整字总集合，旧ikjt/ikqt仅显式兼容。'
    result['jointBCContracts']=[dict(code=p['code'],**p['evidence'][0]) for p in r['paths']]
    result.setdefault('routeAmendments',[]).append('2026-10-29：'+ '；'.join(c+'→'+v for c,v in r['replacements'].items())+'；旧码仅显式兼容，历史不改。')
    return result

def key_definition(position,key,item):
    if not policy():return item
    relevant=[p for r in policy()['records'].values() for p in r['paths'] if p['code'][position-1]==key]
    if not relevant and not(position==3 and key in 'ik'):return item
    item=copy.deepcopy(item)
    if position==2 and key in 'efn':
        item.update(meaning={'e':'孔与孔组·联合BC','f':'分离外附件·联合BC','n':'笔线与连续组·联合BC'}[key],assigned=True,status='accepted-single-character-joint-BC')
    if item.get('acceptedGroupCodes'):
        item['historicalAcceptedGroupCodes']=item['acceptedGroupCodes']
        item['acceptedGroupCodes']=[c for c in item['acceptedGroupCodes'] if c not in {'ebii','ikit'}]
    if item.get('acceptedHoleQuantityCode')=='ikit':item['historicalHoleQuantityCode']=item.pop('acceptedHoleQuantityCode')
    if (item.get('lookupException') or {}).get('code')=='iokg':item['historicalLookupException']=item.pop('lookupException')
    if position==3 and key=='i':item['condition']='8 ebii、𝔻 ikiv/ikit已于七组合批次退出规范推荐；以下单字确认文字为此前历史依据。 '+item.get('condition','')
    if position==3 and key=='k':item['condition']='ộ iokg已退出规范推荐；原k全字墨组保持，下列外附件例外文字为此前历史依据。 '+item.get('condition','')
    if position==4 and key=='t':item['condition']='𝔻旧ikit仅为历史，本字现用iegt数三孔；t含义仍三个。 '+item.get('condition','')
    item['jointBCExamples']=[dict(code=p['code'],BC=p['evidence'][0]['BC'],meaning=p['evidence'][0]['BCMeaning'],scope='仅批准四字七路') for p in relevant]
    item['condition']=(item.get('condition','')+' 联合BC七路按本字锁定对象解释；BC须合读，D含义保持，不改全库旧形族解释。').strip()
    return item

def summary():
    return dict(id=ID,approvedCodes=codes(),characters=4,retiredCanonicalRelations=6,newRelations=7,
        classifierComplete=False,scope='本人批准的四字锁定组合；非全矩阵部署') if policy() else None

def compatibility_query(overview,params):
    get=lambda k,d='':params.get(k,[d])[0]
    if get('allocation')!='1':raise ValueError('显式兼容读取仅用于当前视图')
    if set(params)-{'allocation','compatibility','order','routeLength','prefix','text','offset'}:raise ValueError('兼容查询不能混用队列或键位筛选')
    order=get('order','front');typed=get('prefix').lower()
    if order not in ('front','back') or not re.fullmatch('[a-z]{4}',typed):raise ValueError('兼容查询须输入完整四码')
    if get('routeLength','4')!='4':raise ValueError('本批旧兼容仅四码')
    canonical=typed[-1]+typed[:-1] if order=='back' else typed
    entries=dict(overview.allocation_members(canonical));retired=set()
    import joint_count_bindings
    combined=dict((policy() or {}).get('records',{}));combined.update((joint_count_bindings.policy() or {}).get('records',{}))
    for cp,r in combined.items():
        if canonical in r['retiredCanonicalCodes']:entries[int(cp)]=1;retired.add(int(cp))
    wanted=get('text').strip()
    if wanted:
        match=re.fullmatch(r'(?:U\+|0x)([0-9a-f]{1,6})',wanted,re.I)
        keep={int(match[1],16)} if match else {ord(c) for c in wanted}
        entries={cp:t for cp,t in entries.items() if cp in keep}
    cps=sorted(entries,key=lambda cp:(entries[cp],cp));offset=max(0,int(get('offset','0')))
    rows=[dict(overview.brief(cp,True),matchedCompatibilityCode=canonical if cp in retired else None,
        compatibilityOnly=cp in retired,lookupPaths=[dict(canonical=canonical,code=typed)],
        layer=('primary','component','supplement','pending')[entries[cp]]) for cp in cps[offset:offset+60]]
    return dict(id=overview.id,allocation=True,total=len(cps),offset=offset,rows=rows,groups={},audit=None,
        compatibility=True,canonical=canonical,lookupOrder=order,routeLength=4,crossBucket=False,
        semantics='显式旧码兼容；不计入当前规范路径、键位或默认候选集合',jointBCVersion=ID)
