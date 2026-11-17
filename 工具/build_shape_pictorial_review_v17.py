"""Close the t/b intake stage; apply the saved review and provisional Egyptian intake."""
import copy
from collections import Counter
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v16 import OUT as V16, FLOWERS, FLOWER_CANDIDATES
from save_shape_pictorial_review import validate

OUT = V16.parent / '20261024-pictorial-intake-review-v17'
VERSION = 'pictorial-intake-20261024-v17'
SNAPSHOT = V16 / '人工审核保存/网页审核原始结果-eb434783f4f34b8777d0945e52f0693786f92d4a351531ff0c434ee63709d8dd.json'


def build():
    if OUT.exists():
        raise FileExistsError('不覆盖已有v17阶段结果')
    previous = read(V16 / '拟物收入全量初稿.json')
    snapshot = read(SNAPSHOT)
    assert sha(SNAPSHOT) == SNAPSHOT.stem.split('-')[-1]
    validate(snapshot, previous)
    protected = protect()
    r = copy.deepcopy(previous)
    ds = {str(d['cp']): copy.deepcopy(d) for d in snapshot['decisions']}
    r.update(version=VERSION, predecessorVersion=previous['version'],
             lineageVersions=previous['lineageVersions'] + [VERSION],
             predecessorReportSHA256=sha(V16 / '拟物收入全量初稿.json'),
             sourceReviewSnapshot=str(SNAPSHOT), sourceReviewSHA256=sha(SNAPSHOT),
             reviewDecisions=ds, latestConfirmations={}, protectedHashes=protected)
    rows = {x['cp']: x for x in r['records']}
    provisional = previous['queueCleanup16']['egyptianPendingCps']
    assert len(provisional) == 140
    for cp in provisional:
        d = ds.setdefault(str(cp), dict(cp=cp, char=chr(cp)))
        assert d.get('decision', 'pending') == 'pending'
        d.update(decision='include', category='象形·形象待辨', firstKey='t')
        r['latestConfirmations'][str(cp)] = copy.deepcopy(d)
    completed = set(FLOWERS + FLOWER_CANDIDATES + previous['discoveryQueues']['bInterface']['cps'])
    for cp in completed:
        assert ds.get(str(cp), {}).get('decision') in ('include', 'exclude'), cp
        ds[str(cp)]['secondReviewed'] = True
        r['latestConfirmations'][str(cp)] = copy.deepcopy(ds[str(cp)])
    for key in ('roundFlowers', 'bInterface'):
        r['archivedDiscoveryQueues'][key] = r['discoveryQueues'].pop(key)
    aliases = read(EDITOR / 'data/pictorial-category-labels.json')['aliases']
    mapping = r['bucketSplit']['categoryFirstKeys']
    mapping['象形·形象待辨'] = 't'
    allocations, overrides = [], []
    for cp, row in rows.items():
        d = ds.get(str(cp), {})
        if d.get('decision') != 'include':
            continue
        category = aliases.get(d.get('category', row['category']), d.get('category', row['category']))
        first = d.get('firstKey') if d.get('firstKey') in ('t', 'b') else mapping.get(category, 't')
        if first != mapping.get(category, 't'):
            overrides.append(dict(cp=cp, char=chr(cp), category=category, firstKey=first,
                                  categoryDefault=mapping.get(category, 't')))
        allocations.append(dict(cp=cp, char=chr(cp), category=category, firstKey=first,
                                codesAssigned=False, provisional=cp in provisional))
    counts = Counter(x['firstKey'] for x in allocations)
    r['draftFirstKeyAllocations'] = allocations
    r['bucketSplit'].update(admittedCounts=dict(counts), admittedCategoryCounts={
        k: dict(Counter(x['category'] for x in allocations if x['firstKey'] == k)) for k in ('t', 'b')})
    r['secondReview'].update(admittedCps=[x['cp'] for x in allocations],
                            categoryCounts=dict(Counter(x['category'] for x in allocations)))
    r['latestReviewSummary'] = dict(include=len(allocations),
        exclude=sum(d.get('decision') == 'exclude' for d in ds.values()),
        uncertain=sum(d.get('decision') == 'uncertain' for d in ds.values()),
        categoryOnly=sum('decision' not in d for d in ds.values()),
        secondReviewed=sum(d.get('secondReviewed') is True for d in ds.values()))
    r['stageClosure17'] = dict(status='阶段收尾；后续先推进四位键位总览',
        provisionalEgyptianCps=provisional, completedTopicCps=sorted(completed),
        explicitBucketOverrides=overrides, exclusiveAllocation=True, runtimeDeployed=False,
        scope='当前独立全形工作视图；不改历史对照、实体原始码或小狼毫部署；t/b后续细码待编制')
    r['uiNotice'] = 't／b收录阶段暂告一段落；140个埃及形象暂收入t，花和界面／情绪审核已合并。当前独立全形键位采用排他入口；后续细码另行整理，未部署。'
    assert len(allocations) == 4362 and counts == {'t': 3630, 'b': 732}
    assert len(set(x['cp'] for x in allocations)) == len(allocations)
    assert protect() == protected
    save(OUT / '拟物收入全量初稿.json', r)
    save(EDITOR / 'data/pictorial-intake-review.json', {k:v for k,v in r.items() if k != 'protectedHashes'})
    save(EDITOR / 'data/pictorial-exclusive-allocation.json', dict(version=VERSION,
        sourceReportSHA256=sha(OUT / '拟物收入全量初稿.json'),
        sourceReviewSHA256=sha(SNAPSHOT), counts=dict(counts), allocations=allocations,
        provisionalCps=provisional, active=True, runtimeDeployed=False))
    print(r['latestReviewSummary'])
    print(dict(counts), 'explicit overrides:', overrides)


if __name__ == '__main__':
    build()
