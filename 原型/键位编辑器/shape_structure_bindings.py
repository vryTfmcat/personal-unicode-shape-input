"""Additive accepted count bindings, isolated from historical and deployed indexes."""
import functools
import copy
import json
import re
import continuous_total_semantics as totals
from pathlib import Path

PATH = Path(__file__).parent / 'data/structure-count-bindings.json'


@functools.lru_cache(maxsize=1)
def data():
    if not PATH.is_file():
        return {}
    d = json.loads(PATH.read_text(encoding='utf-8'))
    if not d.get('active'):
        return {}
    if d['runtimeDeployed'] is not False or not re.fullmatch(r'structure-count-bindings-v[1-9]\d*', d['version']):
        raise ValueError('结构计数绑定版本或独立范围错误')
    if d.get('countSemanticsVersion')==totals.MODE:
        assert d['version']==totals.authority()['targetVersion']=='structure-count-bindings-v10'
    d['byCp'] = {r['cp']: r for r in d['records']}
    if len(d['byCp']) != len(d['records']):
        raise ValueError('结构计数身份重复')
    return d


@functools.lru_cache(maxsize=1)
def additions():
    result = {}
    for code, cps in data().get('codeMembers', {}).items():
        if len(code) != 4 or code[2] not in 'abgjq' or code[3] not in 'ubtyp':
            raise ValueError('结构计数新码无效')
        for n in (2, 3, 4):
            result.setdefault(code[:n], {}).update({cp: 1 for cp in cps})
    return result


@functools.lru_cache(maxsize=1)
def key_index():
    result = {}
    for code, cps in data().get('codeMembers', {}).items():
        for p in (2, 3, 4):
            result.setdefault((p, code[p-1]), set()).update(cps)
    return result


def record(cp):
    return data().get('byCp', {}).get(cp)


def p_family_decision(cp):
    return data().get('pFamilyBoundaryReview', {}).get('decisions', {}).get(str(cp))


@functools.lru_cache(maxsize=1)
def closed_family_policy():
    project = Path(__file__).resolve().parents[2]
    manual = json.loads((project / '数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    policies = [r for r in manual.get('ruleDecisions', [])
                if r.get('function') == 'family.closed_partition' and r.get('decision') == 'accepted']
    if len(policies) > 1:
        raise ValueError('闭合形族须唯一确定当前已接受规则，不能猜测最新记录')
    return policies[0] if policies else None


@functools.lru_cache(maxsize=1)
def effective_definitions():
    """Apply accepted meaning/boundary policy without mutating the frozen candidate dataset."""
    definitions = copy.deepcopy(data().get('definitions', {}))
    policy = closed_family_policy()
    if policy:
        definitions.setdefault('second', {}).update(copy.deepcopy(policy['definitions']))
    return definitions


@functools.lru_cache(maxsize=1)
def active_report_path():
    """Resolve one report from the existing runtime version; never guess the latest folder."""
    d = data()
    if not d:
        raise ValueError('当前结构计数未启用')
    project = Path(__file__).resolve().parents[2]
    runs = project / '数据/三模式/规则库/四键实验/键位试验'
    matches = sorted(runs.glob('*-' + d['version'] + '/大组结构键位分配.json'))
    if len(matches) != 1:
        raise ValueError('当前结构计数版本须唯一对应一个报告，不能按目录日期猜测')
    return matches[0]


@functools.lru_cache(maxsize=1)
def review_report():
    d = data()
    if not d:
        return {}
    path = active_report_path()
    report = json.loads(path.read_text(encoding='utf-8'))
    if report['version'] != d['version'] or report['codeMembers'] != d['codeMembers'] or report['statistics'] != d['statistics']:
        raise ValueError('结构计数审阅报告与当前绑定不一致')
    return report


@functools.lru_cache(maxsize=1)
def queues():
    report = review_report()
    rows = report.get('records', [])
    return dict(assigned=[r['cp'] for r in rows if r['codes']],
                observationPending=[r['cp'] for r in rows if not r['eligible']],
                scopePending=[r['cp'] for r in rows if r['eligible'] and not r['codes'] and not r.get('reviewResolution')],
                reviewedRetained=[r['cp'] for r in rows if not r['codes'] and r.get('reviewResolution')],
                withdrawn=[r['cp'] for r in report.get('scopeRevision', {}).get('withdrawn', [])])


def summary():
    d = data()
    if not d:
        return None
    report = review_report()
    result = {k: d[k] for k in ('version', 'statistics', 'definitions')}
    result['definitions'] = effective_definitions()
    result['closedFamilyPolicy'] = closed_family_policy()
    result['pFamilyBoundaryReview'] = d.get('pFamilyBoundaryReview')
    result['acceptedBoundary'] = {cp:totals.effective_boundary(int(cp),a) for cp,a in d.get('acceptedBoundary', {}).items()}
    result['countSemanticsVersion']=d.get('countSemanticsVersion','separate-straight-or-curve')
    result['countSemanticsNote']=totals.note() if totals.active() else None
    result['codeCounts'] = {c: len(cps) for c, cps in d['codeMembers'].items()}
    result['queueCounts'] = {k: len(v) for k, v in queues().items()}
    result['groups'] = [{k: g[k] for k in ('code', 'before', 'withBetterRoute', 'pending', 'maxRecommendedBurden', 'medianRecommendedBurden')} for g in report['groups']]
    return result


def extend_detail(detail, cp):
    decision = p_family_decision(cp)
    if decision:
        detail = dict(detail, pFamilyBoundaryReview=decision)
    r = record(cp)
    accepted = data().get('acceptedBoundary', {}).get(str(cp))
    if accepted:
        detail = dict(detail, legacyFamilyKey=detail.get('familyKey'), familyKey=accepted['familyKey'],
                      scopeBoundaryAcceptance=totals.effective_boundary(cp,accepted), familyRoutes=list(detail.get('familyRoutes', [])))
        if accepted['scope'] == 'whole-glyph':
            detail['familyRoutes'].append(dict(bucket=accepted['bucket'], familyKey=accepted['familyKey'],
                familyId={'k':'family.hole-topology','x':'family.cross','w':'family.wave','a':'family.angle'}[accepted['familyKey']],
                target='body', lookupEvidence=dict(verified=True,scope=('single-seven-angle-acceptance' if cp==55 else 'seven-character-human-boundary-review'))))
    if not r:
        return detail
    d = dict(detail, paths=list(detail['paths']), objects=list(detail.get('objects', [])),
             codeCounts=dict(detail['codeCounts']), suggestions=list(detail.get('suggestions', [])))
    for a in r['assignments']:
        obj = a['objectId']
        if not any(o['id'] == obj for o in d['objects']):
            d['objects'].append(dict(id=obj, type='whole-glyph-collection', count=a['count'],
                                     scope=('同一整字的原特征集合，a/b/g计数原义保持；原范围记录见sourceScopeHistory' if totals.active() and a['feature']!='totalContinuousGroups' else a['scope']), feature=a['feature'],
                                     **({'sourceScopeHistory':a['scope']} if totals.active() and a['feature']!='totalContinuousGroups' else {}),
                                     **({k:a[k] for k in ('memberTypeCounts','countSemanticsVersion')} if a.get('countSemanticsVersion') else {})))
        code = a['code']
        d['paths'].append(dict(code=code, preferred=False, structuralCollection=True,
                              evidence=[dict(rule='whole-glyph-collection-nine-variant-count',
                                             objectId=obj, fourthObjectId=obj, familyTarget='whole-glyph',
                                             attribute=(a['meaning'] + '：总数' + str(a['count']) + '（直'+str(a['memberTypeCounts']['straight'])+'＋曲'+str(a['memberTypeCounts']['curve'])+'；p为五个及以上）' if a.get('countSemanticsVersion') else a['meaning'] + '：' + str(a['count']) + '个（p为五个及以上）'),
                                             status='accepted-rule-machine-application', variants=9)]))
        d['codeCounts'][code] = len(data()['codeMembers'][code])
    options = sorted(r['codes'], key=lambda c: (d['codeCounts'][c], c))[:3]
    d['structuralRecommendations'] = options
    d['suggestions'] += [dict(code=c, allCandidates=d['codeCounts'][c], preferred=False,
                              layer='component') for c in options]
    return d
