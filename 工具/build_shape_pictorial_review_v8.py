"""Import the user's exported Chrome review verbatim, without deployment."""
import copy
from collections import Counter
from pathlib import Path
import shutil

from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR,read,sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v7 import OUT as V7
from save_shape_pictorial_review import validate

OUT=V7.parent/'20261023-pictorial-intake-review-v8'
VERSION='pictorial-intake-20261023-v8'
EXPORT=Path(r'C:\Users\86137\Downloads\拟物收入审核结果-2026-10-22 (1).json')


def build():
    if OUT.exists():raise FileExistsError('不覆盖已有v8审核合并结果')
    protected=protect()
    previous=read(V7/'拟物收入全量初稿.json')
    exported=read(EXPORT)
    summary=validate(exported,previous)
    report=copy.deepcopy(previous)
    decisions={str(d['cp']):copy.deepcopy(d) for d in exported['decisions']}
    aliases=read(EDITOR/'data/pictorial-category-labels.json').get('aliases',{})
    admitted=[r for r in report['records'] if decisions.get(str(r['cp']),{}).get('decision')=='include']
    old_uncertain={cp for cp,d in previous['reviewDecisions'].items() if d.get('decision')=='uncertain'}
    changes={'oldUncertainNow':dict(Counter(decisions[cp]['decision'] for cp in old_uncertain)),
        'newExplicitEntries':len(set(decisions)-set(previous['reviewDecisions'])),
        'summary':summary,'sourceExportSHA256':sha(EXPORT),
        'noAutomaticDecision':True,'allocationChanged':False,'runtimeDeployed':False}
    report.update(version=VERSION,predecessorVersion=previous['version'],
        lineageVersions=previous['lineageVersions']+[VERSION],
        predecessorReportSHA256=sha(V7/'拟物收入全量初稿.json'),
        reviewDecisions=decisions,latestConfirmations={},protectedHashes=protected,
        sourceReviewSnapshot=str(OUT/'Chrome人工审核原始导出.json'),sourceReviewSHA256=sha(EXPORT))
    second=report['secondReview']
    second['admittedCps']=[r['cp'] for r in admitted]
    second['excludedCps']=[r['cp'] for r in report['records'] if decisions.get(str(r['cp']),{}).get('decision')=='exclude']
    second['initialReviewedCount']=summary['secondReviewed']
    categories=Counter()
    for row in admitted:
        category=decisions[str(row['cp'])].get('category',row['category'])
        categories[aliases.get(category,category)]+=1
    second['categoryCounts']=dict(categories)
    report['reviewSummary']['currentKnownCounts']=summary['explicitDecisions']
    report['uiNotice']='v8已合并Chrome人工导出：3620收入、43不收入、13待讨论；显示修复不替代二审判断，原始导出和备注保留。'
    report['chromeReviewImport']=changes
    assert report['records']==previous['records']
    assert report['secondReview']['boundaryCps']==previous['secondReview']['boundaryCps']
    assert len(admitted)==3620 and protect()==protected
    save(OUT/'拟物收入全量初稿.json',report)
    shutil.copyfile(EXPORT,OUT/'Chrome人工审核原始导出.json')
    assert sha(OUT/'Chrome人工审核原始导出.json')==sha(EXPORT)
    save(OUT/'Chrome审核合并与显示修复.json',changes)
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in report.items() if k!='protectedHashes'})
    print(changes)


if __name__=='__main__':build()
