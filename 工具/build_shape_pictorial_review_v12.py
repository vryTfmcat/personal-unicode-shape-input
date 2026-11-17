"""Preserve the new review, apply two explicit corrections, and record a split proposal."""
import copy
from collections import Counter
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v11 import OUT as V11
from save_shape_pictorial_review import validate

OUT = V11.parent/'20261023-pictorial-intake-review-v12'
VERSION = 'pictorial-intake-20261023-v12'
SNAPSHOT = V11/'人工审核保存/网页审核原始结果-37847a3d7881032ab6a3cb55786b30423269aebc432b3ea71ee106954ab80d0c.json'
CORRECTIONS = (0x13B68,0x13B9A)
SPLIT_CATEGORIES = ('碎片／抽象拼块','游戏图标','装饰','象征标志','标识')


def build():
    if OUT.exists():raise FileExistsError('不覆盖已有v12结果')
    protected = protect()
    previous = read(V11/'拟物收入全量初稿.json')
    snapshot = read(SNAPSHOT)
    assert sha(SNAPSHOT) == SNAPSHOT.stem.split('-')[-1]
    validate(snapshot,previous)
    decisions = {str(d['cp']):copy.deepcopy(d) for d in snapshot['decisions']}
    assert not set(previous['reviewDecisions']) - decisions.keys()
    changes = [{'before':previous['reviewDecisions'].get(cp),'after':d}
               for cp,d in decisions.items() if previous['reviewDecisions'].get(cp) != d]
    assert len(changes) == 206
    assert Counter(d.get('decision') for d in decisions.values()) == {'include':3825,'exclude':62,None:1}
    corrected = []
    for cp in CORRECTIONS:
        d = decisions[str(cp)]
        assert d['decision'] == 'exclude'
        before = copy.deepcopy(d)
        d.update(decision='include',category='动物部位')
        corrected.append({'before':before,'after':copy.deepcopy(d),
                          'basis':'本人明确回复：U+13B68、U+13B9A收入动物部位'})
    result = copy.deepcopy(previous)
    result.update(version=VERSION,predecessorVersion=previous['version'],
                  lineageVersions=previous['lineageVersions']+[VERSION],
                  predecessorReportSHA256=sha(V11/'拟物收入全量初稿.json'),
                  sourceReviewSnapshot=str(SNAPSHOT),sourceReviewSHA256=sha(SNAPSHOT),
                  reviewDecisions=decisions,protectedHashes=protected,
                  latestConfirmations={str(cp):{'decision':'include','category':'动物部位',
                       'basis':'本人纠正误点'} for cp in CORRECTIONS})
    labels = read(EDITOR/'data/pictorial-category-labels.json')['aliases']
    admitted = []
    counts = Counter()
    for row in result['records']:
        d = decisions.get(str(row['cp']),{})
        if d.get('decision') == 'include':
            admitted.append(row['cp'])
            category = d.get('category',row['category'])
            counts[labels.get(category,category)] += 1
    result['secondReview'].update(admittedCps=admitted,categoryCounts=dict(counts))
    result['latestReviewSummary'] = {'include':3827,'exclude':60,'uncertain':0,'categoryOnly':1,
        'browserChanges':len(changes),'explicitCorrections':2,'secondReviewed':0,
        'pendingTopics':{key:sum(decisions.get(str(cp),{}).get('decision','pending') in ('pending','uncertain')
            for cp in q['cps']) for key,q in result['discoveryQueues'].items()}}
    result['bucketSplitProposal'] = {'status':'discussion-only-not-applied','suggestedFirstKey':'b',
        'suggestedMeaning':'图案／标识','currentFirstKey':'t',
        'categories':{k:counts[k] for k in SPLIT_CATEGORIES},'wouldMove':sum(counts[k] for k in SPLIT_CATEGORIES),
        'wouldRemainInT':len(admitted)-sum(counts[k] for k in SPLIT_CATEGORIES),
        'letterBadges':'如🚾另行审核，不自动推翻此前明确不收入决定',
        'geometryBoundary':'不整段收纳纯几何拼块；仅将明确作为图案或图标查找者列入提案',
        'allocationChanged':False,'runtimeDeployed':False}
    result['displayIncident'] = {
        'page':'https://symbl.cc/en/1CDF4/',
        'observedTranslatedDOM':{'htmlClass':'translated-ltr','displayedText':'👎','displayedCodepoint':'U+1F44E',
                                  'wrapper':'font[dir=auto] inside font[dir=auto]'},
        'observedUntranslatedDOM':{'htmlClass':None,'element':'span#char-node','displayedText':'𜷴',
                                    'displayedCodepoint':'U+1CDF4','fontFamily':'u1cc00'},
        'officialChart':'https://www.unicode.org/charts/PDF/Unicode-16.0/U160-1CC00.pdf',
        'finding':'该案例自动翻译替换了符号文字，不是U+1CDF4本来表示拇指向下；不外推所有显示问题均同因',
        'localMitigation':'审核页及字形增加translate=no和notranslate标记；不更改第三方页面或浏览器设置'}
    result['uiNotice'] = 'v12已合并最新审核，并按本人确认将U+13B68、U+13B9A收入动物部位；分桶仍为讨论提案。'
    assert len(admitted) == 3827 and counts['动物部位'] == 131
    assert result['secondReview']['boundaryCps'] == previous['secondReview']['boundaryCps']
    assert protect() == protected
    save(OUT/'拟物收入全量初稿.json',result)
    save(OUT/'最新人工审核与误点修正.json',{'sourceSHA256':sha(SNAPSHOT),'browserChanges':changes,'corrections':corrected})
    save(OUT/'分桶讨论与显示问题核查.json',{'proposal':result['bucketSplitProposal'],'displayIncident':result['displayIncident']})
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in result.items() if k!='protectedHashes'})
    print(result['latestReviewSummary']);print(result['bucketSplitProposal'])


if __name__ == '__main__':build()
