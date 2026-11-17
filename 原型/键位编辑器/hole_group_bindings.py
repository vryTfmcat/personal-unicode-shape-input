"""Accepted single-character hole-group direction, current view only."""
import copy
import functools
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELD = 'holeGroupDirectionAcceptance20261027Batch1'
NOTICE = '规范码第3位i：方向分支看孔组成员中心连线，位置／尺寸分支仍看单孔。当前仅8新增ebii；不自动给其它字派码。后置biie只是同一码投影。'
COUNT_FIELD = 'roundSubjectClosureAcceptance20261028Batch1'
COUNT_NOTICE = '规范码第3位i：方向／数量看显式孔组，位置／尺寸看选定单孔。仅𝔻的ikit：i选整字三个真实闭孔组成的孔组，t数该组3孔；不是直曲总数3或手写三笔。ikiv仍选中央单孔的相对尺寸。不自动给其它字派i+t。'


@functools.lru_cache(maxsize=1)
def count_policy():
    a=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8')).get(COUNT_FIELD)
    if not a:return None
    assert a['decision']=='accepted' and set(a['records'])=={'120123','66580'}
    record=a['records']['120123'];group=record['holeGroupObject']
    path=(ROOT/a['proofReport']).resolve()
    assert path.is_relative_to(ROOT.resolve()) and hashlib.sha256(path.read_bytes()).hexdigest()==a['proofSHA256']
    proof=json.loads(path.read_text(encoding='utf-8'))
    assert proof['cp']==120123 and proof['holeCount']==3 and proof['pixelMatch']
    assert group['kind']==group['objectMode']=='hole-group'
    assert group['members']==[m['objectId'] for m in proof['members']]
    assert group['count']==group['memberCount']==len(group['members'])==3
    e=record['holeGroupEvidence']
    assert e['objectId']==e['fourthObjectId']==group['id']
    assert e['quantityFeature']=='closedHoles' and e['count']==3
    return dict(id=a['id'],cp=120123,object=group,proof=proof)


def validate_count_members(objects):
    a=count_policy();assert a
    by={o['id']:o for o in objects}
    for member in a['proof']['members']:
        obj=by[member['objectId']]
        assert obj['kind']=='hole' and obj['bbox']==member['bbox'] and obj['area']==member['area']


@functools.lru_cache(maxsize=1)
def policy():
    a = json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8')).get(FIELD)
    if not a:
        return None
    assert a['decision'] == 'accepted' and a['cp'] == 56
    assert (a['canonical'], a['projection']) == ('ebii', 'biie')
    assert len(a['beforeCodes']) == 8 and not a['preferredCodes'] and not a['withdrawnCodes']
    obj = a['object']
    assert obj['kind'] == obj['objectMode'] == 'hole-group'
    assert obj['members'] == ['body:b:hole-0', 'body:b:hole-1']
    assert obj['directionMode'] == 'member-centres'
    path = (ROOT/a['proofReport']).resolve()
    assert path.is_relative_to(ROOT.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == a['proofSHA256']
    proof = json.loads(path.read_text(encoding='utf-8'))
    assert proof['cp'] == 56 and proof['directionMode'] == 'member-centres'
    assert [m['objectId'] for m in proof['members']] == obj['members']
    assert [m['centroid'] for m in proof['members']] == obj['memberCentres']
    (x0,y0),(x1,y1) = obj['memberCentres']
    angle = math.degrees(math.atan2(abs(x1-x0),abs(y1-y0)))
    assert abs(angle-obj['angleFromVerticalDegrees']) < 1e-10 and angle < 12
    assert len(proof['variants']) == 9
    assert all(v['holeCount'] == 2 and v['centroidAngleFromVertical'] < 12 for v in proof['variants'])
    return a


def brief(row, cp):
    a = policy()
    if not a or cp != 56:
        return row
    return dict(row, codes=sorted(set(row['codes'])|{'ebii'}),
                holeGroupBinding=a['id'], holeGroupNote=NOTICE)


def members(prefix, entries):
    if policy() and prefix and 'ebii'.startswith(prefix):
        entries[56] = min(entries.get(56,4),1)
    return entries


def key_members(position, key, entries):
    if policy() and 'ebii'[position-1] == key:
        return set(entries)|{56}
    return entries


def detail(row, cp, burden):
    a = policy()
    if not a or cp != 56:
        return row
    row = copy.deepcopy(row)
    objects = {o['id']:o for o in row['objects']}
    proof = json.loads((ROOT/a['proofReport']).read_text(encoding='utf-8'))
    for m in proof['members']:
        o = objects[m['objectId']]
        assert o['kind'] == 'hole' and o['bbox'] == m['bbox'] and o['area'] == m['area']
    assert {p['code'] for p in row['paths']} == set(a['beforeCodes'])
    assert not any(p['preferred'] for p in row['paths'])
    obj = copy.deepcopy(a['object'])
    row['objects'].append(obj)
    row['paths'].append(dict(code='ebii',preferred=False,holeGroupBinding=a['id'],evidence=[dict(
        rule='accepted.hole_group.direction',third='i',objectId=obj['id'],fourthObjectId=obj['id'],
        familyTarget='body',familyId='family.double-loop',objectMode='hole-group',
        directionMode='member-centres',members=obj['members'],
        attribute='两孔组成员中心连线纵向；位置／尺寸旧分支仍选单孔',status='human-accepted-single-character-binding')]))
    row['codeCounts']['ebii'] = burden('ebii')
    row.update(holeGroupBinding=a['id'],holeGroupNote=NOTICE)
    return row


def key_definition(position, key, item):
    if policy() and position == 3 and key == 'i':
        item.update(meaning='多闭孔：单孔属性／孔组方向',
                    condition=(item.get('condition','')+' '+NOTICE).strip(),
                    objectModes={'position/size':'single-hole','direction':'hole-group'},
                    acceptedGroupCodes=['ebii'])
    if count_policy() and position==3 and key=='i':
        item.update(meaning='多闭孔：单孔属性／孔组方向或数量',
                    condition=(item.get('condition','')+' '+COUNT_NOTICE).strip(),
                    objectModes={'position/size':'single-hole','direction':'hole-group','quantity':'hole-group'},
                    acceptedGroupCodes=['ebii','ikit'])
    if count_policy() and position==4 and key=='t':
        item.update(condition=(item.get('condition','')+' i+t仅本字𝔻的ikit数整字闭孔组的3孔，C/D同组；不改j/q直曲总数。').strip(),
                    acceptedHoleQuantityCode='ikit')
    return item
