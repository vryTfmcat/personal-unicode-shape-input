"""Merge preserved human review with explicit category decisions, without migration."""
import argparse
import copy
import csv
import hashlib
import json
import re
from collections import Counter

from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import OUT as V1, EDITOR, read, sha
from build_shape_keyboard_full import save

VERSION = 'pictorial-intake-20261022-v2'
OUT = V1.parent/'20261022-pictorial-intake-review-v2'
SNAPSHOT = V1/'人工审核保存/网页审核原始结果-484626a0b677a992dfab997530d5e5d46b4a9362d13deb0507ce8d93808fbe5b.json'
SYMBOLS = set(map(ord, '☭⚒⚔⚕⚖⚗⚙⚛⚜☤☥☦☧☨☩☪☫☬☮☯☸✝✞✟✠✡⛤⛥⛦⛧⍾⚓'))
TRAFFIC = set(map(ord, '⛍⛐⚠⛔⛕⛖⛗⛘⛙⛚⛛⛜⛝⛞⛟⛠⛡⛣⛨🚸🚫🚳🚭🚯🚱🚷🚻🚹🚺🚼♿'))
LETTERS = set(map(ord, '🚾🏧🅿🆘🆔🆕🆖🆗🆙🆚🆒🆓🈁🈂'))
MOON = set(range(0x1F311, 0x1F31A))
LEAVES = set(range(0x1F650, 0x1F660))
DUAL = 0x1CCA3
EXACT = {
    ord('☭'): ('include', '象征标志'), ord('⛍'): ('include', '交通指示牌'),
    ord('🔗'): ('include', '工具与日常物品'), ord('🕨'): ('include', '工具与日常物品'),
    0x1CC50: ('include', '游戏图标'), 0x1CC53: ('include', '游戏图标'),
    DUAL: ('include', '游戏图标'), 0x1CDF4: ('exclude', '碎片／抽象拼块'),
    ord('🚾'): ('exclude', '字母标识'), ord('🙐'): ('include', '装饰'), ord('🙘'): ('include', '装饰'),
}


def build(refresh_generated=False):
    if OUT.exists() and not refresh_generated:
        raise FileExistsError('不覆盖已生成的v2收入核对稿')
    if OUT.exists():
        assert read(OUT/'拟物收入全量初稿.json')['version']==VERSION
    before = protect()
    original = read(V1/'拟物收入全量初稿.json')
    snapshot = read(SNAPSHOT)
    assert sha(SNAPSHOT) == '484626a0b677a992dfab997530d5e5d46b4a9362d13deb0507ce8d93808fbe5b'
    records = copy.deepcopy(original['records'])
    by_cp = {r['cp']: r for r in records}
    decisions = {r['cp']: dict(r) for r in snapshot['decisions']}
    for r in records:
        r['previousCategory'] = r['category']
        if r['humanReviewed']:
            decisions.setdefault(r['cp'], {'cp': r['cp'], 'char': r['char'],
                'decision': 'include' if r['proposal'] == 'confirmed' else 'exclude'})
        if r['cp'] in decisions:
            r['decisionSource'] = '原网页逐字审核' if not r['humanReviewed'] else '原例直接确认'
    baseline = copy.deepcopy(decisions)
    accepted = {}
    topics = {key: set() for key in ('symbolic', 'traffic', 'boards', 'games', 'decoration', 'moon', 'fragments', 'letters', 'dual')}

    def confirm(cp, decision, category, basis):
        if cp not in by_cp:
            return
        previous = decisions.get(cp, {})
        decisions[cp] = {'cp': cp, 'char': chr(cp), 'decision': decision,
            **({'note': previous['note']} if 'note' in previous else {})}
        accepted[cp] = {'decision': decision, 'category': category, 'basis': basis}
        by_cp[cp].update(category=category, decisionSource=basis,
            confirmationKind='本轮点名确认' if cp in EXACT else '本轮类属确认的有限系列推广')

    for r in records:
        cp, name, block = r['cp'], r['name'], r['block']
        if cp in SYMBOLS:
            topics['symbolic'].add(cp)
            r['category'] = '象征标志'
        if cp in TRAFFIC:
            topics['traffic'].add(cp)
            r['category'] = '交通指示牌'
        if (block in ('Chess Symbols', 'Playing Cards') or 0x2654 <= cp <= 0x265F
                or 0x2680 <= cp <= 0x2685 or cp in (0x1F3B2, 0x1F3B4)):
            topics['boards'].add(cp)
            confirm(cp, 'include', '标识牌', '本人确认棋子、纸牌、骰子收入；分类为标识牌')
        elif block in ('Mahjong Tiles', 'Domino Tiles'):
            topics['boards'].add(cp)
            r['category'] = '标识牌'
        if (block.startswith('Symbols for Legacy Computing') and re.search(
                r'ALIEN|ROCKET SHIP|ATOMIC BOMB|SNAKE HEAD|ENERGY WAVE|RACING CAR|ROCKET BOOSTER|ROLLER COASTER CAR|MOON LANDER|POINTING FROG', name)):
            topics['games'].add(cp)
            r['category'] = '游戏图标'
        if block == 'Ornamental Dingbats':
            topics['decoration'].add(cp)
            r['category'] = '装饰'
        if cp in LEAVES:
            confirm(cp, 'include', '装饰', '本人确认叶饰、藤叶饰可收入装饰；同系列方向与粗细变体推广')
        if cp in MOON:
            topics['moon'].add(cp)
            confirm(cp, 'include', '自然物象／月相', '本人确认月相可收入；仅推广九个月相图像，不包含普通圆与占星标记')
        elif 'MOON' in name:
            topics['moon'].add(cp)
        if (block.startswith('Symbols for Legacy Computing') and re.search(r'HALF|QUADRANT|SEGMENT|TYPE PIECE|RUNNER FRAME', name)):
            topics['fragments'].add(cp)
            r['category'] = '碎片／抽象拼块'
        if cp in LETTERS:
            topics['letters'].add(cp)
            r['category'] = '字母标识'
    for cp, (decision, category) in EXACT.items():
        confirm(cp, decision, category, '本轮本人点名确认')
    topics['dual'].update((DUAL, 0x1CCA2))
    by_cp[DUAL]['geometryRetention'] = {'mode': 'dual-exception',
        'humanAccepted': True, 'keepOriginalBucket': by_cp[DUAL]['oldBucket'],
        'keepAllOriginalCodes': by_cp[DUAL]['oldCodes'],
        'existingGeometryRouteAvailable': bool(by_cp[DUAL]['oldBucket'] or by_cp[DUAL]['oldCodes']),
        'geometryRouteNeedsBuilding': not bool(by_cp[DUAL]['oldBucket'] or by_cp[DUAL]['oldCodes']),
        'reason': '本人允许该字收入t，同时保留t以外的几何查法；仅此个例，不泛化到同族。该字旧版全局未分类，无现成普通主桶或几何细码；几何入口待补建，不能冒称已有两套码。'}
    for r in records:
        r['classificationStatus'] = ('本人确认分类' if r['cp'] in accepted else
            '同类分类提案，仍需核对' if any(r['cp'] in cps for cps in topics.values()) else '原分类提示')
        r['similarityTopics'] = [key for key, cps in topics.items() if r['cp'] in cps]
    remaining = [r['cp'] for r in snapshot['decisions'] if r.get('decision') == 'uncertain'
        and decisions[r['cp']]['decision'] == 'uncertain']
    queues = {'remainingFirst': {'label': '首批剩余待讨论', 'cps': remaining, 'onlyUnresolved': True}}
    labels = {'symbolic': '象征标志及专业记号', 'traffic': '交通／公共指示牌', 'boards': '标识牌／棋牌骰子',
        'games': '游戏图标同类', 'decoration': '装饰同类', 'moon': '月相与占星边界',
        'fragments': '碎片与拼块边界', 'letters': '字母标识边界', 'dual': '车厢双入口个例'}
    for key, cps in topics.items():
        queues[key] = {'label': labels[key], 'cps': sorted(cps)}
    changes = [{'cp': cp, 'char': chr(cp), 'before': baseline.get(cp, {}).get('decision', 'pending'),
        'after': d['decision'], 'basis': d['basis']} for cp, d in accepted.items()
        if baseline.get(cp, {}).get('decision') != d['decision']]
    policy = copy.deepcopy(original['policy'])
    policy.update({'geometryRetentionExceptions': [DUAL], 'exceptionDoesNotApplyToOtherCharacters': True,
        'symbolicSignsAcceptedAsCategory': True, 'decorationAcceptedAsCategory': True,
        'gameIconsAcceptedAsCategory': True, 'secondKeysAssigned': False})
    result = {**copy.deepcopy(original), 'version': VERSION, 'predecessorVersion': original['version'],
        'records': records, 'policy': policy, 'reviewDecisions': {str(cp): d for cp, d in decisions.items()},
        'latestConfirmations': {str(cp): d for cp, d in accepted.items()}, 'reviewQueues': queues,
        'sourceReviewSnapshot': str(SNAPSHOT), 'sourceReviewSHA256': sha(SNAPSHOT),
        'predecessorReportSHA256': sha(V1/'拟物收入全量初稿.json'),
        'reviewSummary': {'originalExplicitDecisions': 1216,
            'originalExplicitCounts': dict(Counter(r['decision'] for r in snapshot['decisions'])),
            'original97Remaining': len(remaining), 'latestDecisionChanges': len(changes),
            'currentKnownCounts': dict(Counter(d['decision'] for d in decisions.values())),
            'firstCohortCounts': dict(Counter(decisions[r['cp']]['decision'] for r in snapshot['decisions']))},
        'latestChanges': changes, 'protectedHashes': before,
        'limitations': original['limitations'] + ['象征标志等同类清单只作候选召回；未逐字确认者不自动收入。',
            '保留原网页审核及本轮确认来源；双入口只明确批准U+1CCA3，其余仍按排他方向。',
            '界面分类名称不是第二位键盘字母；本轮没有生成t编码或移除几何路径。']}
    assert [r['cp'] for r in records] == [r['cp'] for r in original['records']]
    assert all((r['oldBucket'], r['oldCodes']) == (o['oldBucket'], o['oldCodes']) for r,o in zip(records,original['records']))
    assert all(decisions[cp] == d for cp,d in baseline.items() if cp not in accepted)
    assert protect() == before
    save(OUT/'拟物收入全量初稿.json', result)
    save(OUT/'原首批剩余待讨论.json', {'records': [by_cp[cp] for cp in remaining]})
    save(OUT/'本轮确认与变更.json', {'confirmations': result['latestConfirmations'], 'changes': changes,
        'retentionException': by_cp[DUAL]['geometryRetention']})
    with (OUT/'拟物审核合并清单.tsv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['码位', '字符', '分类', '判断', '确认／审核来源', '分类状态', '双入口例外'])
        for r in records:
            writer.writerow([f"U+{r['cp']:04X}", r['char'], r['category'], decisions.get(r['cp'], {}).get('decision', 'pending'),
                r.get('decisionSource', '未逐字审核'), r['classificationStatus'], bool(r.get('geometryRetention'))])
    save(EDITOR/'data/pictorial-intake-review.json', {k:v for k,v in result.items() if k!='protectedHashes'})
    save(OUT/'验收.json', {'passed': True, 'preservedOriginalSnapshot': sha(SNAPSHOT)==result['sourceReviewSHA256'],
        'unapprovedDecisionsUnchanged': True, 'protectedInputsUnchanged': protect()==before,
        'allocationChanged': False, 'runtimeDeployed': False})
    print(json.dumps({'reviewSummary': result['reviewSummary'], 'queues': {k:len(v['cps']) for k,v in queues.items()}}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-generated',action='store_true')
    build(parser.parse_args().refresh_generated)
