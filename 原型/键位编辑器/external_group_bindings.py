"""One accepted exterior group; g retains its existing upright direction meaning."""
import copy
import functools
import hashlib
import json
import continuous_total_semantics as totals
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FIELD='externalGroupUprightAcceptance20261027Batch1'
NOTICE='规范码iokg：仅ộ的第3位k选排除圆主体后的两个外附件组；第4位g仍为正置，描述该组墨迹并集长轴，不编码附件类型。原k全字墨组与旧路/首选保留；后置okgi只是投影。'
D_NOTICE='最新澄清：本人认可ikq前三位，询问第四位计数。q选整字曲连续组集合，u表示1个成员、b表示2个成员；不是手写总笔画、主体数量或原始短线段总数。现模型2直组＋1曲组与本人“两笔写成”分开。此前ikqu拒绝历史保留，最新尚未授权恢复ikqu或新增ikqb。'


@functools.lru_cache(maxsize=1)
def curve_restore_policy():
    a=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8')).get('dStrokeCurveRestoreAcceptance20261027')
    if not a:return None
    assert a['decision']=='accepted' and a['cp']==272 and a['restoredOnly']==['ikqu']
    assert a['canonical']=='ikqu' and a['projection']=='kqui'
    assert not a['tRequest']['implemented'] and not a['tRequest']['publicConditionalRuleApproved']
    p=(ROOT/a['proofReport']).resolve()
    assert p.is_relative_to(ROOT.resolve()) and hashlib.sha256(p.read_bytes()).hexdigest()==a['proofSHA256']
    proof=json.loads(p.read_text(encoding='utf-8'))
    source=(ROOT/proof['sourceReport']).resolve()
    assert source.is_relative_to(ROOT.resolve()) and hashlib.sha256(source.read_bytes()).hexdigest()==proof['sourceSHA256']
    assert proof['record']['statistics']['curveStrokes']==1 and proof['record']['status']=='stable'
    assert a['object']['feature']=='curveStrokes' and a['object']['count']==1
    return a


def curve_restore_active():
    return bool(curve_restore_policy()) and not totals.active()


def count_members(code):
    return {272} if code=='ikqu' and curve_restore_active() else set()


def codes():
    return (['iokg'] if policy() else [])+(['ikqu'] if curve_restore_active() else [])


@functools.lru_cache(maxsize=1)
def policy():
    a=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8')).get(FIELD)
    if not a:return None
    assert a['decision']=='accepted' and a['cp']==7897
    assert (a['canonical'],a['projection'])==('iokg','okgi')
    assert a['preferredCodes']==['epki'] and not a['withdrawnCodes']
    assert a['rejectedCodes']==['iokl'] and a['typeEncoding'] is False
    o=a['object']
    assert o['kind']=='part-group' and o['memberCount']==2
    assert o['directionMode']=='group-ink-principal-axis'
    assert o['parentSubjectObjectId']=='reviewed-ộ-circle-subject'
    assert set(o['members'])=={'reviewed-ộ-external-caret','reviewed-ộ-external-dot'}
    p=(ROOT/a['proofReport']).resolve()
    assert p.is_relative_to(ROOT.resolve()) and hashlib.sha256(p.read_bytes()).hexdigest()==a['proofSHA256']
    proof=json.loads(p.read_text(encoding='utf-8'))
    assert proof['cp']==7897 and len(proof['variants'])==9
    assert proof['selected']['object']==o
    for v in proof['variants']:
        angle=v['orientationDegrees']
        assert v['anisotropy']>1.5 and min(angle,abs(angle-90),180-angle)<=12
        assert v['excludedSubject'] and v['completeInkPartition'] and 'g' in v['properties']
    assert not a['clarificationDStroke']['restoreIkquAuthorized']
    assert not a['perception8']['newCodes'] and a['perception8']['noThreshold']
    return a


def brief(row,cp):
    a=policy()
    if not a:return row
    if cp==7897:
        return dict(row,codes=sorted(set(row['codes'])|{'iokg'}),externalGroupBinding=a['id'])
    if cp==272 and totals.active():
        return dict(row,roundRefinementNote='当前全局总数：2直＋1曲＝3，使用ikjt/ikqt；旧ikjb/ikqu接受、拒绝与恢复仅保留历史。')
    if cp==272 and curve_restore_active():
        return dict(row,codes=sorted(set(row['codes'])|{'ikqu'}),curveCountRestoration=curve_restore_policy()['id'],
                    roundRefinementNote='原三条k路和ioma保持，ikqu已获后续明确授权恢复；旧拒绝记录仅为历史，ikqt组合入口仍待审。')
    # Perception/clarification are detail notes, not route or ownership changes.
    return row


def members(prefix,entries):
    for code,cp in [('iokg',7897),('ikqu',272)]:
        if code in codes() and prefix and code.startswith(prefix):entries[cp]=min(entries.get(cp,4),1)
    return entries


def key_members(position,key,entries):
    return set(entries)|{cp for code,cp in [('iokg',7897),('ikqu',272)] if code in codes() and code[position-1]==key}


def detail(row,cp,burden):
    a=policy()
    # Frozen structure records keep their original counts; current details must
    # show the same accepted union as query, including all existing ikqu peers.
    if curve_restore_active() and 'ikqu' in row.get('codeCounts',{}):
        row=copy.deepcopy(row)
        row['codeCounts']['ikqu']=burden('ikqu')
        for suggestion in row.get('suggestions',[]):
            if suggestion['code']=='ikqu':suggestion['allCandidates']=burden('ikqu')
    if not a or cp not in (56,272,7897):return row
    row=copy.deepcopy(row)
    if cp==56:
        row['currentFeedbackNote']='本人对8的孔间自然印象为“上小下大”。仅保存本字形态确认，不推出面积阈值，不派ebie/ebif；ebii纵向路及原旧路/空首选保持。'
    elif cp==272:
        restore=curve_restore_policy() if curve_restore_active() else None
        if totals.active():
            row['currentFeedbackNote']='当前全局直曲总数：Đ为2直＋1曲＝总数3，j含直入口ikjt、q含曲入口ikqt；C/D为同一整字总集合。旧ikjb/ikqu的接受、拒绝与恢复记录保留历史，旧数量路不再注入当前视图；不是手写3笔。'
            row['roundRefinementNote']='Đ现为ikab／ikgu／ikjt／ikqt＋ioma，空首选保持；iocv／iosc仍撤。'
            row['countSemanticsVersion']=totals.MODE
        elif restore:
            o=copy.deepcopy(restore['object']);row['objects'].append(o)
            for old in row['objects']:
                if old.get('type')=='whole-glyph-collection' and old['id']!=o['id']:
                    old['scope']='原三路确认的整字集合；q恢复由后续单字确认独立叠加'
            row['paths'].append(dict(code='ikqu',preferred=False,acceptedCountRestoration=restore['id'],evidence=[dict(
                rule='accepted.restore_whole_curve_collection',objectId=o['id'],fourthObjectId=o['id'],familyTarget='whole-glyph',
                attribute='q选整字曲连续组集合；u表示该集合1个成员，非总笔画/主体/原始短线段数量',status='human-accepted-restoration-existing-count')]))
            row['codeCounts']['ikqu']=burden('ikqu')
            row['currentFeedbackNote']='ikqu已按后续明确授权恢复：q选整字曲连续组集合，u表示1个成员；不是手写总笔画或主体数。现模型2直组＋1曲组。旧拒绝保留为历史；ikqt所求2直1曲与当前q/t三曲有冲突，仍待审，未派ikqt/ikqb。'
            row['curveCountRestoration']=restore['id']
            row['roundRefinementNote']='Đ保留ikab／ikgu／ikjb及ioma，撤iocv／iosc；后续仅恢复ikqu。'
        else:
            row['currentFeedbackNote']=D_NOTICE
            row['roundRefinementNote']='Đ仍仅接受ikab／ikgu／ikjb，保留ioma，撤iocv／iosc。'+D_NOTICE
    else:
        objects={o['id']:o for o in row['objects']}
        proof=json.loads((ROOT/a['proofReport']).read_text(encoding='utf-8'))
        for m in proof['selected']['members']:
            o=objects[m['objectId']]
            assert o['bbox']==m['bbox'] and o['area']==m['area']
        assert objects[a['object']['parentSubjectObjectId']]['bbox']==proof['selected']['subjectBBox']
        assert {p['code'] for p in row['paths']}==set(a['beforeCodes'])
        assert {p['code'] for p in row['paths'] if p['preferred']}=={'epki'}
        o=copy.deepcopy(a['object']);row['objects'].append(o)
        row['paths'].append(dict(code='iokg',preferred=False,externalGroupBinding=a['id'],evidence=[dict(
            rule='accepted.external_group.upright',third='k',objectId=o['id'],fourthObjectId=o['id'],
            familyTarget='reviewed-ộ-circle-subject',familyId='family.round-outline',
            directionMode='group-ink-principal-axis',members=o['members'],typeEncoding=False,
            attribute='仅该外附件组墨迹并集长轴正置；沿用g方向义，不编码成员类型',status='human-accepted-single-character-binding')]))
        row['codeCounts']['iokg']=burden('iokg')
        row.update(externalGroupBinding=a['id'],currentFeedbackNote=NOTICE)
    return row


def key_definition(position,key,item):
    if policy() and position==3 and key=='k':
        item.update(condition=(item.get('condition','')+' '+NOTICE).strip(),
                    lookupException=dict(char='ộ',code='iokg',scope='single-character-external-group',gMeaningUnchanged=True))
    return item
