"""Place admitted Egyptian images in concrete categories, leaving only unresolved candidates."""
import copy
from collections import Counter
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR,read,sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v8 import OUT as V8

OUT=V8.parent/'20261023-pictorial-intake-review-v9'
VERSION='pictorial-intake-20261023-v9'
SNAPSHOT=V8/'人工审核保存/网页审核原始结果-c35b635ad72ab9c4502636d0d48b4ffce926e9430d134993000a68afee3cbd09.json'
GROUPS={'A':'人物与动作','B':'人物与动作','C':'人物与神形',
        'E':'动物','F':'动物部位','G':'鸟类','H':'动物部位',
        'I':'动物','K':'鱼类','L':'昆虫'}
ALIASES={'象形·人物与动作':'人物与动作','象形·人物与复合形象':'人物与神形',
         '象形·动物':'动物','象形·动物部位':'动物部位','象形·鸟类':'鸟类',
         '象形·鸟类部位':'动物部位','象形·昆虫':'昆虫','象形·鱼类':'鱼类',
         '象形·植物':'植物','象形·物品与标志':'象征标志'}


def build():
    if OUT.exists():raise FileExistsError('不覆盖已有v9归类结果')
    protected=protect();previous=read(V8/'拟物收入全量初稿.json');snapshot=read(SNAPSHOT)
    assert sha(SNAPSHOT)==SNAPSHOT.stem.split('-')[-1]
    decisions={str(d['cp']):copy.deepcopy(d) for d in snapshot['decisions']}
    assert decisions==previous['reviewDecisions']
    result=copy.deepcopy(previous)
    result.update(version=VERSION,predecessorVersion=previous['version'],
        lineageVersions=previous['lineageVersions']+[VERSION],
        predecessorReportSHA256=sha(V8/'拟物收入全量初稿.json'),
        sourceReviewSnapshot=str(SNAPSHOT),sourceReviewSHA256=sha(SNAPSHOT),
        reviewDecisions=decisions,latestConfirmations={},protectedHashes=protected)
    placements=[]
    for row in result['records']:
        if decisions.get(str(row['cp']),{}).get('decision')!='include':continue
        group=row.get('egyptianReference',{}).get('group')
        category=GROUPS.get(group)
        if not category:continue
        placements.append({'cp':row['cp'],'char':row['char'],'before':row['category'],'after':category,
            'basis':'已收入后的具体对象归类；Unicode17官方外形组只确定类别，不新增收入',
            'manualCategoryOverridePreserved':'category' in decisions[str(row['cp'])]})
        row.update(category=category,placementSource='v9已收入字具体归类',
            categoryBeforePlacement=row['category'])
    result['categoryPlacements']=placements
    labels=read(EDITOR/'data/pictorial-category-labels.json')
    save(OUT/'归类前名称映射.json',labels)
    labels['aliases'].update(ALIASES)
    labels['placementBasis']='本人要求将已审核收入字移动到具体类别；保留旧类名和人工覆盖，不改变收入判断。'
    result['archivedDiscoveryQueues']=copy.deepcopy(result['discoveryQueues'])
    result['discoveryQueues'].pop('categoryRepairs',None)
    for q in result['discoveryQueues'].values():q['onlyUnresolved']=True
    admitted=[r for r in result['records'] if decisions.get(str(r['cp']),{}).get('decision')=='include']
    categories=Counter()
    for r in admitted:
        category=decisions[str(r['cp'])].get('category',r['category'])
        categories[labels['aliases'].get(category,category)]+=1
    result['secondReview']['categoryCounts']=dict(categories)
    result['categoryPlacementSummary']={'placed':len(placements),
        'byTarget':dict(Counter(r['after'] for r in placements)),
        'remainingAdmittedUnknown':categories['象形·形象待辨'],
        'pendingQueues':{k:sum(decisions.get(str(cp),{}).get('decision','pending') in ('pending','uncertain')
            for cp in q['cps']) for k,q in result['discoveryQueues'].items()},
        'admissionDecisionsChanged':False,'runtimeDeployed':False}
    result['uiNotice']='v9已将收入的象形图像放入人物、神形、动物、鸟、鱼、昆虫及部位等具体分类；候选专题只保留未决定者。'
    assert result['reviewDecisions']==previous['reviewDecisions']
    assert len(admitted)==3620 and categories['象形·形象待辨']==0
    assert result['secondReview']['boundaryCps']==previous['secondReview']['boundaryCps']
    assert protect()==protected
    save(OUT/'拟物收入全量初稿.json',result)
    save(OUT/'已收入字归类与待审队列整理.json',{'placements':placements,'summary':result['categoryPlacementSummary']})
    save(EDITOR/'data/pictorial-category-labels.json',labels)
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in result.items() if k!='protectedHashes'})
    print(result['categoryPlacementSummary']);print(dict(categories))


if __name__=='__main__':build()
