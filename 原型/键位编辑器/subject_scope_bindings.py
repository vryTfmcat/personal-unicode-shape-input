"""Scoped subject/attachment routes from the existing manual authority.

Separate object-attribute routes from frozen whole-glyph count bindings.
"""
import copy
import functools
import hashlib
import json
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[2]


@functools.lru_cache(maxsize=1)
def policy():
    d=json.loads((PROJECT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8')).get('subjectAttachmentAcceptance20261025')
    if not d or d.get('decision')!='accepted':return None
    p=(PROJECT/d['proofReport']).resolve()
    if not p.is_relative_to(PROJECT.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=d['proofSHA256']:
        raise ValueError('主体附件证据与确认源不一致，禁止猜测或继续派码')
    for r in d['records']:
        for o in r['objects']:
            assert len(o['code'])==4 and o['code'][:2]=='io' and o['code'][2] in 'ty'
            assert o['evidence']['objectId']==o['evidence']['fourthObjectId']==o['object']['id']
    return d


def record(cp):
    return next((r for r in (policy() or {}).get('records',[]) if r['cp']==cp),None)


@functools.lru_cache(maxsize=1)
def additions():
    result={}
    for r in (policy() or {}).get('records',[]):
        for o in r['objects']:
            for n in range(1,5):result.setdefault(o['code'][:n],{})[r['cp']]=1
    return result


def key_members(position,key):
    return {r['cp'] for r in (policy() or {}).get('records',[]) if any(o['code'][position-1]==key for o in r['objects'])}


@functools.lru_cache(maxsize=1)
def round_browse_exclusion_policy():
    manual=json.loads((PROJECT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    d=manual.get('roundSubjectBrowseExclusionAcceptance20261025Batch1')
    if not d or d.get('decision')!='accepted':return None
    p=(PROJECT/d['candidateReport']).resolve()
    if not p.is_relative_to(PROJECT.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=d['candidateSHA256']:
        raise ValueError('圆主体退出浏览的确认与候选证据不一致')
    assert d['familyKey']=='o' and set(d['characters'])=={7692,7696}
    assert d['preserveAllPaths'] and d['preservePreferred']
    return d


def excluded_from_current_family(key):
    d=policy() or {}
    result=set(d.get('currentRoundExclusions',[])) if key=='o' else set()
    result|={r['cp'] for r in d.get('records',[]) if key in r.get('compatibilityFamilies',[])}
    extra=round_browse_exclusion_policy() if key=='o' else None
    if extra:result.update(extra['characters'])
    if key=='o':
        from round_subject_refinement import policy as current_refinement
        refinement=current_refinement() or {}
        result.update(int(cp) for cp in refinement.get('kFamilyDecisions',{}))
        result.update(int(cp) for cp in refinement.get('boxedDDecisions',{}))
        result.update(int(cp) for cp,a in refinement.get('shapeDecisions',{}).items() if key in a['excludedCurrentFamilies'])
    return result


def brief(row,cp):
    r=record(cp)
    if r:
        row=dict(row,legacyWholeFamilyKey=row.get('familyKey'),familyKey=r['subjectFamily'],
            subjectAttachmentBinding=r,subjectAttachmentCodes=[o['code'] for o in r['objects']],
            codes=sorted(set(row['codes'])|{o['code'] for o in r['objects']}))
    if cp in excluded_from_current_family('o'):
        row=dict(row,currentFamilyExclusions=['o'],familyCompatibilityNote='现行o主体形族排除；旧o码只保留兼容查询。')
    return row


def detail(row,cp,burden):
    r=record(cp)
    excluded=cp in excluded_from_current_family('o')
    if not r and not excluded:return row
    d=copy.deepcopy(row)
    if r:
        d.update(legacyWholeFamilyKey=d.get('familyKey'),familyKey=r['subjectFamily'],subjectAttachmentBinding=r)
        d['objects'].append(dict(id=r['subjectId'],kind='body',bbox=r['subjectBBox'],scope='verified-circle-subject'))
        d['familyRoutes'].append(dict(bucket=r['subjectBucket'],familyKey='o',familyId='family.round-outline',target=r['subjectId'],
            lookupEvidence=dict(verified=True,scope='single-character-subject-attachment-review')))
        for route in d['familyRoutes']:
            if route.get('familyKey') in r.get('compatibilityFamilies',[]):route['compatibilityOnly']=True
        for path in d['paths']:
            if len(path['code'])>=2 and path['code'][1] in r.get('compatibilityFamilies',[]):path['compatibilityOnly']=True
        existing={p['code'] for p in d['paths']}
        for o in r['objects']:
            d['objects'].append(copy.deepcopy(o['object']))
            if o['code'] not in existing:
                d['paths'].append(dict(code=o['code'],preferred=False,subjectAttachment=True,evidence=[copy.deepcopy(o['evidence'])]))
            d['codeCounts'][o['code']]=burden(o['code'])
    if excluded:
        d['familyCompatibilityNote']='现行o主体形族排除；旧o路径保留为兼容，不计作现行o成员。'
        for route in d['familyRoutes']:
            if route.get('familyKey')=='o':route['compatibilityOnly']=True
        for path in d['paths']:
            if len(path['code'])>=2 and path['code'][1]=='o':path['compatibilityOnly']=True
    return d


def summary():
    d=policy()
    if not d:return None
    return dict(id=d['id'],scope=d['scope'],bindingBoundary=d['bindingBoundary'],records=d['records'],
        thirdDefinitions=d['thirdDefinitions'],currentRoundExclusions=sorted(excluded_from_current_family('o')),
        roundBrowseExclusionAcceptance=round_browse_exclusion_policy(),
        routeCount=sum(len(r['objects']) for r in d['records']))
