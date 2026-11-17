"""Apply approved zodiac intake and seven category repairs to the saved review."""
import copy
from collections import Counter
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v14 import OUT as V14
from save_shape_pictorial_review import validate

OUT = V14.parent / '20261024-pictorial-intake-review-v15'
VERSION = 'pictorial-intake-20261024-v15'
SNAPSHOT = V14 / '人工审核保存/网页审核原始结果-1b9f364626e7e21ce8d748c8e282116f0105e808c0eb04b3e50762e47981b78a.json'
ZODIAC = list(range(0x2648, 0x2654)) + [0x26CE]
REPAIRS = {
    0x1F39E: ('工具与日常物品', 't'),
    0x1F6A8: ('标识', 'b'),
    0x1FAC6: ('身体部位', 't'),
    0x1F54F: ('象征标志', 'b'),
    0x1FA70: ('工具与日常物品', 't'),
    0x1F3DC: ('自然物象', 'b'),
    0x1F491: ('人物与动作', 't'),
}


def build():
    if OUT.exists():
        raise FileExistsError('不覆盖已有v15核对结果')
    previous = read(V14 / '拟物收入全量初稿.json')
    snapshot = read(SNAPSHOT)
    assert sha(SNAPSHOT) == SNAPSHOT.stem.split('-')[-1]
    validate(snapshot, previous)
    protected = protect()
    result = copy.deepcopy(previous)
    decisions = {str(d['cp']): copy.deepcopy(d) for d in snapshot['decisions']}
    assert Counter(d.get('decision') for d in decisions.values()) == {'include': 4185, 'exclude': 77}
    result.update(version=VERSION, predecessorVersion=previous['version'],
        lineageVersions=previous['lineageVersions'] + [VERSION],
        predecessorReportSHA256=sha(V14 / '拟物收入全量初稿.json'),
        sourceReviewSnapshot=str(SNAPSHOT), sourceReviewSHA256=sha(SNAPSHOT),
        reviewDecisions=decisions, latestConfirmations={}, protectedHashes=protected)
    rows = {r['cp']: r for r in result['records']}
    approved = {cp: ('星座', 'b') for cp in ZODIAC}
    approved.update(REPAIRS)
    approved[0x1FA8E] = ('工具与日常物品', 't')
    changes = []
    for cp, (category, key) in approved.items():
        before = copy.deepcopy(decisions.get(str(cp)))
        decision = decisions.setdefault(str(cp), {'cp': cp, 'char': chr(cp)})
        decision.update(decision='include', category=category, firstKey=key)
        result['latestConfirmations'][str(cp)] = {
            'decision': 'include', 'category': category, 'firstKey': key,
            'basis': '本人确认星座入b、宝箱入t及七项分类修正'}
        row = rows[cp]
        result['categoryPlacements'].append({'cp': cp, 'char': chr(cp),
            'before': row['category'], 'after': category, 'basis': '本人2026-10-24明确确认'})
        row['category'] = category
        changes.append({'cp': cp, 'before': before, 'after': copy.deepcopy(decision)})
    labels = read(EDITOR / 'data/pictorial-category-labels.json')
    mapping = result['bucketSplit']['categoryFirstKeys']
    mapping['星座'] = 'b'
    def category(row):
        value = decisions.get(str(row['cp']), {}).get('category', row['category'])
        return labels['aliases'].get(value, value)
    admitted = [r for r in rows.values() if decisions.get(str(r['cp']), {}).get('decision') == 'include']
    allocation = []
    for row in admitted:
        d = decisions[str(row['cp'])]
        c = category(row)
        key = d.get('firstKey') if d.get('firstKey') in ('t', 'b') else mapping.get(c, 't')
        allocation.append({'cp': row['cp'], 'char': row['char'], 'category': c,
                           'firstKey': key, 'codesAssigned': False})
    counts = Counter(r['firstKey'] for r in allocation)
    result['draftFirstKeyAllocations'] = allocation
    result['bucketSplit'].update(admittedCounts=dict(counts),
        admittedCategoryCounts={k: dict(Counter(r['category'] for r in allocation if r['firstKey'] == k)) for k in ('t', 'b')})
    result['secondReview'].update(admittedCps=[r['cp'] for r in admitted],
        categoryCounts=dict(Counter(category(r) for r in admitted)))
    pending = [cp for cp in result['discoveryQueues']['egyptAnimalParts']['cps']
               if decisions.get(str(cp), {}).get('decision', 'pending') in ('pending', 'uncertain')]
    result['latestReviewSummary'] = {
        'include': len(admitted), 'exclude': sum(d.get('decision') == 'exclude' for d in decisions.values()),
        'uncertain': 0, 'categoryOnly': 0,
        'secondReviewed': sum(d.get('secondReviewed') is True for d in decisions.values())}
    result['bucketAudit15'] = {'approvedChanges': changes, 'zodiacCps': ZODIAC,
        'counts': dict(counts), 'egyptianPartsPending': len(pending),
        'runtimeDeployed': False, 'originalReviewPreserved': True}
    result['uiNotice'] = 'v15合并最新逐字审核；本人确认13个星座收入b，宝箱收入t，七项分类修正。140个埃及部位相关候选仍待辨。'
    assert len(admitted) == 4198 and counts == {'t': 3493, 'b': 705}
    assert result['latestReviewSummary']['exclude'] == 64 and len(pending) == 140
    assert protect() == protected
    save(OUT / '拟物收入全量初稿.json', result)
    save(OUT / '星座收入与七项分类修正.json', result['bucketAudit15'])
    save(EDITOR / 'data/pictorial-intake-review.json', {k: v for k, v in result.items() if k != 'protectedHashes'})
    print(result['latestReviewSummary'])
    print(dict(counts))


if __name__ == '__main__':
    build()
