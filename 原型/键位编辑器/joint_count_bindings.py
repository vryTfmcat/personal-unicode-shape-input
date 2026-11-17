"""Accepted six-char count migration; independent bulk experiments never enter here."""
import json,hashlib,functools,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FIELD='jointCountSixAcceptance20261029Batch1'
BOUNDARY='jointBCNegativeBoundariesAcceptance20261029Batch1'
ID='joint-count-six-20261029-v1'
@functools.lru_cache(maxsize=1)
def policy():
    m=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'));a=m.get(FIELD)
    if not a:return None
    assert a['id']==ID and a['decision']=='accepted' and set(a['records'])=={'79','68','84','69','936','55'}
    assert sum(len(r['newCodes']) for r in a['records'].values())==11 and sum(len(r['retiredCanonicalCodes']) for r in a['records'].values())==13
    for key in ['sourceReport','baselineDetails']:
        p=(ROOT/a[key]).resolve();assert p.is_relative_to(ROOT.resolve());assert hashlib.sha256(p.read_bytes()).hexdigest()==a['baselineDetailsSHA256' if key=='baselineDetails' else 'sourceSHA256']
    for p,h in a['sourceHashes'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    b=m[BOUNDARY];assert b['decision']=='accepted' and b['noNewFgForQDot']
    assert {(r['cp'],r['BC']) for r in b['records']}=={(66,'ec'),(561,'fm')}
    assert all(not r['newCodes'] for r in b['records'])
    for r in a['records'].values():
        assert r['afterCodes']==sorted(set(r['beforeCodes'])-set(r['retiredCanonicalCodes'])|set(r['newCodes']))
        assert not set(r['preferredCodes'])&set(r['retiredCanonicalCodes'])
    return a
def record(cp):return (policy() or {}).get('records',{}).get(str(cp))
def codes():return sorted({c for r in (policy() or {}).get('records',{}).values() for c in r['newCodes']})
def migrate_structure(cp,old):
    r=record(cp);return {r['replacements'].get(c,c) for c in old} if r else set(old)
def validate_binding(cp,path,objects):
    r=record(cp)
    if not r or path not in r['paths']:raise ValueError('未批准本字码值/对象绑定')
    e=path['evidence'][0];o=objects[e['objectId']]
    if e['objectId']!=e['fourthObjectId'] or o['type']!='whole-glyph-collection':raise ValueError('须同一整字认证集合')
    n=o['count'];key={1:'u',2:'b',3:'t',4:'y'}.get(n,'p')
    if n<=0 or path['code'][3]!=key or e['count']!=n:raise ValueError('固定数量D不符')
    bc=path['code'][1:3]
    if bc[0]=='n':
        t=o['memberTypeCounts'];s=t['straight'];c=t['curve']
        if n!=s+c or bc!=('na' if c==0 else 'nc' if s==0 else 'nm'):raise ValueError('直曲构成或总数不符')
    elif bc in ['qa','qb','qg']:
        if o['feature']!={'qa':'corners','qb':'forks','qg':'crosses'}[bc]:raise ValueError('角叉集合种类不符')
    else:raise ValueError('本批无此BC')
    return True
def brief(row,cp):
    r=record(cp)
    if not r:return row
    result=dict(row,codes=sorted(set(row.get('codes',[p['code'] for p in row.get('paths',[])]))-set(r['retiredCanonicalCodes'])|set(r['newCodes'])),
        jointCountVersion=ID,canonicalRetiredCodes=r['retiredCanonicalCodes'],compatibilityCodes=r['retiredCanonicalCodes'],jointCountNote='六字已批准替换13旧关系为11新关系；其它用途/首选保持，旧码仅显式兼容。')
    if 'structuralCodes' in result:result['structuralCodes']=sorted(migrate_structure(cp,result['structuralCodes']))
    return result
def members(prefix,entries):
    for cp,r in (policy() or {}).get('records',{}).items():
        if prefix and any(c.startswith(prefix) for c in r['beforeCodes']+r['afterCodes']):
            cp=int(cp)
            if any(c.startswith(prefix) for c in r['afterCodes']):entries[cp]=min(entries.get(cp,4),1)
            else:entries.pop(cp,None)
    return entries
def key_members(position,key,entries):
    result=set(entries)
    for cp,r in (policy() or {}).get('records',{}).items():
        cp=int(cp);old=any(len(c)>=position and c[position-1]==key for c in r['beforeCodes']);new=any(len(c)>=position and c[position-1]==key for c in r['afterCodes'])
        if old and not new and not(position==2 and r['familyKey']==key):result.discard(cp)
        elif new and not old:result.add(cp)
    return result
def detail(row,cp,burden):
    if not policy():return row
    retired={c for r in policy()['records'].values() for c in r['retiredCanonicalCodes']};impacted=retired & set(row.get('codeCounts',{}))
    if impacted:
        row=copy.deepcopy(row);row.setdefault('frozenStructuralCodeCounts',{}).update({c:row['codeCounts'][c] for c in impacted})
        for c in impacted:row['codeCounts'][c]=burden(c)
        for s in row.get('suggestions',[]):
            if s['code'] in impacted:s['allCandidates']=burden(s['code'])
    r=record(cp)
    if not r:return row
    result=copy.deepcopy(row);old={p['code']:p for p in result['paths']};assert set(r['retiredCanonicalCodes'])<=set(old)
    result['paths']=[p for p in result['paths'] if p['code'] not in r['retiredCanonicalCodes']]+copy.deepcopy(r['paths'])
    assert {p['code'] for p in result['paths']}==set(r['afterCodes'])
    objects={o['id']:o for o in result['objects']}
    for path in r['paths']:validate_binding(cp,path,objects)
    result['codeCounts']={p['code']:burden(p['code']) for p in result['paths']}
    result['compatibilityPaths']=copy.deepcopy(r['compatibilityPaths'])
    result['compatibilityCodeCounts']={c:burden(c)+sum(c in t['retiredCanonicalCodes'] for t in policy()['records'].values()) for c in r['retiredCanonicalCodes']}
    result['suggestions']=[s for s in result.get('suggestions',[]) if s['code'] not in r['retiredCanonicalCodes']]+[dict(code=p['code'],allCandidates=burden(p['code']),preferred=False,scope='六字明确批准') for p in r['paths']]
    if 'structuralRecommendations' in result:result['structuralRecommendations']=sorted(migrate_structure(cp,result['structuralRecommendations']))
    result['jointBCContracts']=[dict(code=p['code'],**p['evidence'][0]) for p in r['paths']]
    result.setdefault('routeAmendments',[]).append('六字批次：'+'；'.join(c+'→'+n for c,n in r['replacements'].items())+'；旧码显式兼容')
    return brief(result,cp)
def key_definition(position,key,item):
    if not policy():return item
    paths=[p for r in policy()['records'].values() for p in r['paths'] if p['code'][position-1]==key]
    if not paths:return item
    item=copy.deepcopy(item)
    if position==2 and key=='q':item.update(meaning='角叉点整字集合·联合BC',assigned=True,status='accepted-six-character-count-BC')
    item['jointCountExamples']=[dict(code=p['code'],BC=p['evidence'][0]['BC'],meaning=p['evidence'][0]['BCMeaning'],scope='仅六字明确批准') for p in paths]
    item['condition']=(item.get('condition','')+' 六字计数组合按BC合读；数量D固定，原主/备形族不随对象类字母迁移。').strip()
    return item
def summary():
    return dict(id=ID,characters=6,retiredCanonicalRelations=13,newRelations=11,newStrings=len(codes()),codes=codes(),boundaryExclusions=[dict(cp=66,BC='ec'),dict(cp=561,BC='fm')],noNewFgForQDot=True,largeTrialDeployed=False) if policy() else None
