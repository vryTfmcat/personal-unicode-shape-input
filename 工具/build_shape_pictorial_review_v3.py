"""Repair lexical false recalls and distinguish category approval from glyph review."""
import argparse
import copy
import json
from collections import Counter

from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_pictorial_review_v2 import OUT as V2
from build_shape_keyboard_full import save

VERSION = 'pictorial-intake-20261022-v3'
OUT = V2.parent/'20261022-pictorial-intake-review-v3'
SNAPSHOT = V2/'人工审核保存/网页审核原始结果-1ae196b1937c08c484911417955e54b45b69e4d8dd65add5bca34452c0316be4.json'
TYPOGRAPHIC = set(range(0x1F670, 0x1F680)) | set(range(0x1F668, 0x1F66C))
CJK_MOON = {0x2E9D, 0x2F49, 0x322A, 0x328A}
MUSIC = {0x1D152, 0x1D153}
LUNAR = set(range(0x1F311, 0x1F31E)) | {0x263D, 0x263E, 0x26B8, 0x2BDD, 0x2BDF}


def build(refresh_generated=False):
    if OUT.exists() and not refresh_generated:
        raise FileExistsError('不覆盖既有v3收入核对稿')
    if OUT.exists():
        assert read(OUT/'拟物收入全量初稿.json')['version']==VERSION
    before = protect()
    previous = read(V2/'拟物收入全量初稿.json')
    assert sha(SNAPSHOT) == '1ae196b1937c08c484911417955e54b45b69e4d8dd65add5bca34452c0316be4'
    snapshot = read(SNAPSHOT)
    result = copy.deepcopy(previous)
    result.update(version=VERSION, predecessorVersion=previous['version'],
        lineageVersions=['pictorial-intake-20261022-v1',previous['version'],VERSION],
        predecessorReportSHA256=sha(V2/'拟物收入全量初稿.json'),
        sourceReviewSnapshot=str(SNAPSHOT), sourceReviewSHA256=sha(SNAPSHOT), protectedHashes=before)
    rows = {r['cp']: r for r in result['records']}
    decisions = {str(r['cp']): dict(r) for r in snapshot['decisions']}
    corrections = {}

    def change(cp, decision, category, reason):
        r = rows[cp]
        old = decisions.get(str(cp), {})
        corrections[str(cp)] = {'decision': decision, 'category': category, 'basis': reason,
            'beforeDecision': old.get('decision', 'pending'), 'beforeCategory': r['category']}
        decisions[str(cp)] = {'cp': cp, 'char': chr(cp), 'decision': decision,
            **({'note': old['note']} if 'note' in old else {})}
        r.update(category=category, decisionSource=reason, classificationStatus='本轮确认／程序误收修正',
            confirmationKind='本轮排除或分类修正', correctionReason=reason)

    for cp in TYPOGRAPHIC:
        change(cp, 'exclude', '文字标点／抽象纹样',
            '本人排除&连字、引号、问叹号、粗斜线、棋盘格等字形及同类几何纹样；Unicode区块称Ornamental不等于拟物装饰')
    for cp in CJK_MOON:
        change(cp, 'exclude', '中文及汉字构件',
            '月字部首、括号汉字或带圈汉字，不是天体图像；名称含MOON只表示汉字月的语义')
    for cp in MUSIC:
        change(cp, 'exclude', '乐谱记号',
            'MUSICAL SYMBOL MOON NOTEHEAD WHITE/BLACK：乐谱中的白／黑月形符头，不是天体月相')
    for cp in (0x1CCA2, 0x1CCA3):
        change(cp, 'include', '游戏图标', '本人确认左右向车厢收入游戏图标；没有扩大此前仅右向的双入口许可')
    mooncake = 0x1F96E
    change(mooncake, decisions[str(mooncake)]['decision'], '食物与饮品',
        '本人指出MOON CAKE是月饼；纠正先匹配MOON导致的自然物象误分类，不新增或撤回原收入判断')
    q = result['reviewQueues']
    original_remaining = q['remainingFirst']['cps']
    q['remainingFirst']['cps'] = [cp for cp in original_remaining if decisions.get(str(cp), {}).get('decision') == 'uncertain']
    q['decoration']['cps'] = [cp for cp in q['decoration']['cps'] if cp not in TYPOGRAPHIC]
    q['decoration']['label'] = '物象装饰（排除文字纹样）'
    q['moon']['cps'] = sorted(LUNAR & rows.keys())
    q['moon']['label'] = '月相与占星标志'
    q['games']['cps'] = sorted(set(q['games']['cps']) | {0x1CCA2, 0x1CCA3})
    q['dual'] = {'label': '双入口许可（仅右向）', 'cps': [0x1CCA3]}
    q['exclusionRepairs'] = {'label': '本轮误收排除对照', 'cps': sorted(TYPOGRAPHIC | CJK_MOON | MUSIC)}
    for r in rows.values():
        r['similarityTopics'] = [key for key, value in q.items() if r['cp'] in value['cps']]
    result['reviewDecisions'] = decisions
    result['latestConfirmations'] = corrections
    result['latestChanges'] = [{'cp': int(cp), 'char': chr(int(cp)), **d} for cp,d in corrections.items()]
    result['categoryReviewAcceptance'] = {
        'humanClarification': '分类范围已确认，没有逐字修改全部选项',
        'acceptedScopeKeys': ['symbolic','traffic','boards','games','decoration','moon','fragments','letters','dual'],
        'reviewedCountsAtV2': {k: len(previous['reviewQueues'][k]['cps']) for k in ('symbolic','traffic','boards','games','decoration','moon','fragments','letters','dual')},
        'doesNotApproveAllMembers': True,
        'excludedDecorativeForms': sorted(TYPOGRAPHIC),
        'secondKeyLettersAssigned': False,
    }
    result['repairSummary'] = {'exclusions': len(TYPOGRAPHIC|CJK_MOON|MUSIC),
        'lexicalMoonFalseRecallsRemoved': sorted(set(previous['reviewQueues']['moon']['cps']) - set(q['moon']['cps'])),
        'mooncakeReclassifiedWithoutDecisionChange': True, 'bothCarsInGameTopic': True,
        'categoryApprovalIsNotCharacterApproval': True}
    result['reviewSummary']['original97Remaining'] = len(q['remainingFirst']['cps'])
    result['reviewSummary']['currentKnownCounts'] = dict(Counter(d['decision'] for d in decisions.values()))
    first = [r for r in rows.values() if r['proposal'] == 'propose']
    result['reviewSummary']['firstCohortCounts'] = dict(Counter(decisions.get(str(r['cp']), {}).get('decision','pending') for r in first))
    result['reviewSummary']['latestDecisionChanges'] = sum(d['beforeDecision'] != d['decision'] for d in corrections.values())
    result['uiNotice'] = 'v3已保存分类范围确认；不等于逐字全票通过。已排除中文、月形符头及文字纹样误收，月饼归食物，两向车厢归游戏图标。'
    result['limitations'] += ['分类范围已确认，但未逐字选择的成员保持未审核，不自动判收入。',
        '物象装饰不包括&连字、引号、问叹号、粗斜线、棋盘／方格等文字与抽象纹样。',
        '月相列表按实际月相／占星符号身份维护，不再按名称含MOON全量召回。']
    assert len(rows) == len(previous['records'])
    assert all((r['oldBucket'],r['oldCodes']) == (o['oldBucket'],o['oldCodes']) for r,o in zip(result['records'],previous['records']))
    assert all(decisions[str(d['cp'])] == d for d in snapshot['decisions'] if str(d['cp']) not in corrections)
    assert before == protect()
    save(OUT/'拟物收入全量初稿.json',result)
    save(OUT/'分类确认与误收修正.json',{'categoryAcceptance':result['categoryReviewAcceptance'],
        'corrections':corrections,'summary':result['repairSummary']})
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in result.items() if k!='protectedHashes'})
    save(OUT/'验收.json',{'passed':True,'oldSnapshotsPreserved':True,'unrelatedDecisionsUnchanged':True,
        'protectedInputsUnchanged':before==protect(),'allocationChanged':False,'runtimeDeployed':False})
    print(json.dumps({'reviewSummary':result['reviewSummary'],'repairs':result['repairSummary'],
        'queues':{k:len(v['cps']) for k,v in q.items()}},ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-generated',action='store_true')
    build(parser.parse_args().refresh_generated)
