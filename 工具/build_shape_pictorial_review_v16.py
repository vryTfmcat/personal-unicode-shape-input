"""Apply the user's queue confirmations and separate round floral patterns in b."""
import copy
from collections import Counter
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v15 import OUT as V15
from save_shape_pictorial_review import validate

OUT = V15.parent / '20261024-pictorial-intake-review-v16'
VERSION = 'pictorial-intake-20261024-v16'
SNAPSHOT = V15 / '人工审核保存/网页审核原始结果-6c66d5215e5f18fde39a2e6f82c05a123d6b62a385fbbea01bf063a3d49cebc9.json'
# Round petal patterns; stems, bouquets and realistic plant pictures stay in plants.
FLOWERS = [0x273F, 0x2740, 0x2741, 0x1F4AE]
FLOWER_CANDIDATES = [0x273B, 0x273C, 0x273D, 0x273E, 0x2743,
                     0x2749, 0x274A, 0x274B, 0x1F3F5, 0x1F3F6]


def build():
    if OUT.exists():
        raise FileExistsError('不覆盖已有v16核对结果')
    previous = read(V15 / '拟物收入全量初稿.json')
    snapshot = read(SNAPSHOT)
    assert sha(SNAPSHOT) == SNAPSHOT.stem.split('-')[-1]
    validate(snapshot, previous)
    protected = protect()
    result = copy.deepcopy(previous)
    decisions = {str(d['cp']): copy.deepcopy(d) for d in snapshot['decisions']}
    result.update(version=VERSION, predecessorVersion=previous['version'],
                  lineageVersions=previous['lineageVersions'] + [VERSION],
                  predecessorReportSHA256=sha(V15 / '拟物收入全量初稿.json'),
                  sourceReviewSnapshot=str(SNAPSHOT), sourceReviewSHA256=sha(SNAPSHOT),
                  reviewDecisions=decisions, latestConfirmations={}, protectedHashes=protected)
    rows = {r['cp']: r for r in result['records']}
    mapping = result['bucketSplit']['categoryFirstKeys']
    aliases = read(EDITOR / 'data/pictorial-category-labels.json')['aliases']

    def category(cp):
        value = decisions.get(str(cp), {}).get('category', rows[cp]['category'])
        return aliases.get(value, value)

    def first_key(cp):
        value = decisions.get(str(cp), {}).get('firstKey')
        return value if value in ('t', 'b') else mapping.get(category(cp), 't')

    def pending(cp):
        return decisions.get(str(cp), {}).get('decision', 'pending') in ('pending', 'uncertain')

    queues = result['discoveryQueues']
    boundary = [cp for cp in queues['tToBBoundary']['cps']
                if decisions.get(str(cp), {}).get('decision') == 'include' and first_key(cp) == 't']
    repairs = queues['categoryRepairs13']['cps']
    assert len(boundary) == 4 and len(repairs) == 69
    for cp in set(boundary + repairs):
        assert decisions[str(cp)]['decision'] == 'include'
        decisions[str(cp)]['secondReviewed'] = True
        result['latestConfirmations'][str(cp)] = copy.deepcopy(decisions[str(cp)])
    for key in ('tToBBoundary', 'categoryRepairs13'):
        result['archivedDiscoveryQueues'][key] = copy.deepcopy(queues.pop(key))

    egypt = [cp for cp in queues['egyptAnimalParts']['cps'] if pending(cp)]
    assert len(egypt) == 140
    for cp in egypt:
        rows[cp]['category'] = '象形·形象待辨'
        decisions.setdefault(str(cp), {'cp': cp, 'char': chr(cp)})['category'] = '象形·形象待辨'
        result['latestConfirmations'][str(cp)] = copy.deepcopy(decisions[str(cp)])
    result['archivedDiscoveryQueues']['egyptAnimalParts'] = copy.deepcopy(queues.pop('egyptAnimalParts'))
    queues['pictorialUnresolved'] = {
        'label': '象形形象待辨', 'onlyUnresolved': True,
        'description': '尚未辨认的象形图形，包含原埃及部位相关待辨项；原目录与图形说明保留，不自动收入。',
        'cps': [cp for cp in rows if category(cp) == '象形·形象待辨' and pending(cp)]}

    mapping['花'] = 'b'
    for cp in FLOWERS + FLOWER_CANDIDATES:
        rows[cp]['category'] = '花'
        d = decisions.setdefault(str(cp), {'cp': cp, 'char': chr(cp)})
        d.update(category='花', firstKey='b')
        result['latestConfirmations'][str(cp)] = copy.deepcopy(d)
    queues['roundFlowers'] = {
        'label': '花：相似花纹待审', 'onlyUnresolved': True, 'allowExcluded': True,
        'description': '圆形花瓣纹样候选。保留原不收入决定供重新核对；归到花不等于已收入。带茎叶的写实花朵仍归植物。',
        'cps': FLOWER_CANDIDATES}
    allocation = [dict(cp=cp, char=chr(cp), category=category(cp), firstKey=first_key(cp), codesAssigned=False)
                  for cp in rows if decisions.get(str(cp), {}).get('decision') == 'include']
    result['draftFirstKeyAllocations'] = allocation
    counts = Counter(r['firstKey'] for r in allocation)
    result['bucketSplit'].update(admittedCounts=dict(counts), admittedCategoryCounts={
        key: dict(Counter(r['category'] for r in allocation if r['firstKey'] == key)) for key in ('t', 'b')})
    result['secondReview'].update(admittedCps=[r['cp'] for r in allocation],
                                 categoryCounts=dict(Counter(r['category'] for r in allocation)))
    result['latestReviewSummary'] = {
        'include': len(allocation), 'exclude': sum(d.get('decision') == 'exclude' for d in decisions.values()),
        'uncertain': sum(d.get('decision') == 'uncertain' for d in decisions.values()),
        'categoryOnly': sum('decision' not in d for d in decisions.values()),
        'secondReviewed': sum(d.get('secondReviewed') is True for d in decisions.values())}
    result['queueCleanup16'] = {'confirmedBoundaryCps': boundary, 'confirmedRepairCps': repairs,
        'egyptianPendingCps': egypt, 'flowerMovedCps': FLOWERS, 'flowerCandidateCps': FLOWER_CANDIDATES,
        'boundaryOnlyUnresolved': True, 'runtimeDeployed': False}
    result['uiNotice'] = '已确认项退出待辨入口；埃及部位未决项并入象形形象待辨。b新增花；相似花纹保留原判断待审。'
    assert len(allocation) == 4198 and counts == {'t': 3489, 'b': 709}
    assert protect() == protected
    save(OUT / '拟物收入全量初稿.json', result)
    save(OUT / '待辨整理与花分类.json', result['queueCleanup16'])
    save(EDITOR / 'data/pictorial-intake-review.json', {k: v for k, v in result.items() if k != 'protectedHashes'})
    print(result['latestReviewSummary'])
    print(dict(counts))


if __name__ == '__main__':
    build()
