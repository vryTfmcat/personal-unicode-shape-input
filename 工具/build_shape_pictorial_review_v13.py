"""Create approved t/b intake buckets and audit classification and recall boundaries."""
import copy
from collections import Counter
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR,read,sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v12 import OUT as V12,SPLIT_CATEGORIES
from build_shape_pictorial_review_v11 import emoji_records
from save_shape_pictorial_review import validate

OUT=V12.parent/'20261023-pictorial-intake-review-v13'
VERSION='pictorial-intake-20261023-v13'
SNAPSHOT=V12/'人工审核保存/网页审核原始结果-2b922157bb48b4c216aa6a467ac83e1f6a5e7794553650721a14ff1b81a17de2.json'
FIXES={
 '食物与饮品':'🌭🌽🍖🍗🍤🍥', '植物':'🌾',
 '人物与动作':'🎅🤶🤽', '动物':'🐃', '动物部位':'🐽🪶🪽',
 '工具与日常物品':'🎐🎒🎣🏏💎📡🔉🕩🖄🖋🖱🥌🧯🧴🧸🪤🪭',
 '交通工具':'🚅🚒🚞🚠🛱', '自然物象':'𜱤',
 '标识':'⛻✆🚰🛅',
}
INSECTS=set(map(ord,'🐛🐜🐞🦋🦗🦟🪰🪲'))
FISH=set(map(ord,'🐟🐠🦈'))
BORDER=set(map(ord,'🛉🛊💮🌐🎑🗱🗲💂🛀'))


def build():
    if OUT.exists():raise FileExistsError('不覆盖已有v13分桶结果')
    protected=protect();previous=read(V12/'拟物收入全量初稿.json');snapshot=read(SNAPSHOT)
    assert sha(SNAPSHOT)==SNAPSHOT.stem.split('-')[-1]
    validate(snapshot,previous)
    decisions={str(d['cp']):copy.deepcopy(d) for d in snapshot['decisions']}
    assert decisions==previous['reviewDecisions']
    result=copy.deepcopy(previous)
    result.update(version=VERSION,predecessorVersion=previous['version'],
        lineageVersions=previous['lineageVersions']+[VERSION],
        predecessorReportSHA256=sha(V12/'拟物收入全量初稿.json'),
        sourceReviewSnapshot=str(SNAPSHOT),sourceReviewSHA256=sha(SNAPSHOT),
        reviewDecisions=decisions,latestConfirmations={},protectedHashes=protected)
    rows={r['cp']:r for r in result['records']};labels=read(EDITOR/'data/pictorial-category-labels.json')['aliases']
    def category(row):
        c=decisions.get(str(row['cp']),{}).get('category',row['category'])
        return labels.get(c,c)
    targets={ord(c):target for target,chars in FIXES.items() for c in chars}
    for cp,(group,sub) in emoji_records().items():
        if sub=='animal-bird' and cp not in map(ord,'🪶🪽'):targets[cp]='鸟类'
    targets.update({cp:'昆虫' for cp in INSECTS});targets.update({cp:'鱼类' for cp in FISH})
    repairs=[]
    for cp,target in sorted(targets.items()):
        row=rows.get(cp);d=decisions.get(str(cp),{})
        if not row or d.get('decision')!='include' or category(row)==target:continue
        if 'category' in d:
            BORDER.add(cp)
            continue
        repair={'cp':cp,'char':row['char'],'before':row['category'],'after':target,
                'basis':'按完整图像主体修正关键词误归；鸟类、鱼类及真实昆虫归已有专类，不将蜘蛛、蜗牛、蝎子称昆虫'}
        row['category']=target;row['categoryAuditRepair']=repair
        repairs.append(repair)
    result['categoryPlacements'].extend(repairs)
    bcategories=list(SPLIT_CATEGORIES)+['字母标识','界面／情绪图标']
    result['bucketSplit']={'enabled':True,'status':'accepted-independent-intake-draft',
        'firstKeys':{'t':'具体物象','b':'图案／标识'},
        'categoryFirstKeys':{c:'b' for c in bcategories},'defaultFirstKey':'t',
        'humanAuthorization':'好的，新增b桶，然后看看现在的t桶是否分类合理，收录齐全，是否有不必要放在t桶的可以移动到b桶',
        'geometryIndexChanged':False,'runtimeDeployed':False,'secondKeysAssigned':False}
    def bucket(row):return decisions.get(str(row['cp']),{}).get('firstKey') or result['bucketSplit']['categoryFirstKeys'].get(category(row),'t')
    admitted=[r for r in rows.values() if decisions.get(str(r['cp']),{}).get('decision')=='include']
    allocation=[{'cp':r['cp'],'char':r['char'],'firstKey':bucket(r),'category':category(r),
        'reason':'已确认五类分出b，或具体对象分类纠错' if bucket(r)=='b' else '保留具体物象入口',
        'codesAssigned':False} for r in admitted]
    counts=Counter(r['firstKey'] for r in allocation)
    result['bucketSplit'].update(admittedCounts=dict(counts),
        admittedCategoryCounts={key:dict(Counter(r['category'] for r in allocation if r['firstKey']==key)) for key in ('t','b')})
    result['draftFirstKeyAllocations']=allocation
    for row in rows.values():
        if row.get('entryPolicy')=='t-exclusive':row['entryPolicy']='pictorial-bucket-exclusive'
    result['policy'].update(firstKeys=['t','b'],categoryBucketSplitAccepted=True,
        firstKeyMeaning='具体物象',exclusiveAfterIndividualApproval=True)
    result['bucketSplitProposal']['status']='superseded-by-accepted-split'
    result['secondReview']['categoryCounts']=dict(Counter(category(r) for r in admitted))
    queues=result['discoveryQueues']
    border=[r['cp'] for r in admitted if bucket(r)=='t' and (category(r)=='棋牌符号' or r['cp'] in BORDER)]
    queues['tToBBoundary']={'label':'t→b边界核对','cps':border,'onlyFirstKey':'t'}
    queues['categoryRepairs13']={'label':'本次分类纠错对照','cps':[r['cp'] for r in repairs]}
    # New b eligibility is a candidate, not a reversal of the previous t exclusion.
    badge=set(result['reviewQueues']['letters']['cps']);new_icons=set()
    for cp,(group,sub) in emoji_records().items():
        if cp not in rows:continue
        if group=='Symbols' and sub in ('alphanum','currency'):badge.add(cp)
        if group=='Symbols' and sub=='av-symbol' and str(cp) not in decisions:new_icons.add(cp)
    new_icons.update(cp for cp in map(ord,'💢💥💫💦💨🕳🗨🗯💤🗩🗪🗫🗬🗭🗮🗰') if cp in rows and str(cp) not in decisions)
    candidates=[]
    for name,cps,target in (('bBadges',badge,'字母标识'),('bInterface',new_icons,'界面／情绪图标')):
        picked=[]
        for cp in sorted(cps):
            d=decisions.get(str(cp),{})
            if d.get('decision')=='include':continue
            if d.get('decision')=='exclude' and cp!=0x1F6BE:continue
            row=rows[cp];row['bCandidate']={'suggestedCategory':target,'previousTDecision':d.get('decision','pending'),
                'isAdmitted':False,'basis':'新增b范围重新核对；不撤销原t判断、不自动收入'}
            if not d.get('category'):
                before=row['category'];row['category']=target
                result['categoryPlacements'].append({'cp':cp,'char':row['char'],'before':before,'after':target,'basis':'b候选分类提示，非收入'})
            picked.append(cp);candidates.append(cp)
        queues[name]={'label':'b字母标识候选' if name=='bBadges' else 'b界面／情绪图标候选',
                     'cps':picked,'onlyUnresolved':name!='bBadges','allowExcluded':name=='bBadges'}
    remaining={k:sum(decisions.get(str(cp),{}).get('decision','pending') in ('pending','uncertain') for cp in q['cps'])
               for k,q in queues.items() if q.get('onlyUnresolved')}
    result['bucketAudit']={'admitted':len(admitted),'counts':dict(counts),'categoryRepairs':repairs,
        'boundaryInT':len(border),'boundaryInTByCategory':dict(Counter(category(rows[cp]) for cp in border)),
        'additionalBCandidates':len(candidates),'pendingTopics':remaining,'intakeComplete':False,
        'allListedCharactersCheckedForCategoryRouting':len(rows),
        'excludedStillExcluded':60,'admissionDecisionsChanged':False,
        'limitations':['t归类和收入未完成逐字二审；没有以自动扫描宣称全部齐全。',
                      '棋牌符号保留t并列入t→b待核；未擅自迁入b。',
                      '普通圆方、抽象心形及整块几何拼块不自动收入b。',
                      '动物、植物等古文字剩余图像仍保留原7303字入口，不按整区批准。']}
    result['uiNotice']='v13已新增b图案／标识独立收入草案；t保留具体物象。原判断及几何码不变，第二位与部署未更新。'
    assert len(admitted)==3827 and counts=={'t':3653,'b':174}
    assert result['reviewDecisions']==previous['reviewDecisions']
    assert result['secondReview']['boundaryCps']==previous['secondReview']['boundaryCps']
    assert protect()==protected
    save(OUT/'拟物收入全量初稿.json',result)
    save(OUT/'tb分桶与分类核查.json',{'allocation':allocation,'audit':result['bucketAudit'],'split':result['bucketSplit']})
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in result.items() if k!='protectedHashes'})
    print('buckets',dict(counts),'category repairs',len(repairs),'t boundary',len(border),'b candidates',len(candidates))
    print('pending',remaining)


if __name__=='__main__':build()
