"""Revoke the single geometry exception; keep the confirmed ornamental partition."""
import copy
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR,read,sha
from build_shape_pictorial_review_v4 import OUT as V4
from build_shape_keyboard_full import save

VERSION='pictorial-intake-20261022-v5'
OUT=V4.parent/'20261022-pictorial-intake-review-v5'


def build():
    if OUT.exists():raise FileExistsError('不覆盖已有v5核对稿')
    before=protect();previous=read(V4/'拟物收入全量初稿.json');result=copy.deepcopy(previous)
    result.update(version=VERSION,predecessorVersion=previous['version'],
        lineageVersions=previous['lineageVersions']+[VERSION],
        predecessorReportSHA256=sha(V4/'拟物收入全量初稿.json'),protectedHashes=before)
    result['policy']['geometryRetentionExceptions']=[]
    result['policy']['exclusiveAfterIndividualApproval']=True
    result['policy'].pop('exceptionDoesNotApplyToOtherCharacters',None)
    result['policy']['noGeometryExceptions']=True
    result['reviewQueues'].pop('dual',None)
    result['categoryReviewAcceptance']['acceptedScopeKeys']=[k for k in result['categoryReviewAcceptance']['acceptedScopeKeys'] if k!='dual']
    result['geometryExceptionRevocation']={'cp':0x1CCA3,'char':chr(0x1CCA3),
        'humanConfirmed':True,'currentEntryPolicy':'t-exclusive','category':'游戏图标',
        'previousPermissionRevoked':True,'noGeometryRouteToBuild':True,
        'source':'算了，𜲣这种不保存个例了只保留t入口，归入游戏图标，其他任务继续'}
    confirmations={}
    for r in result['records']:
        r.pop('geometryRetention',None)
        r['similarityTopics']=[k for k in r.get('similarityTopics',[]) if k!='dual']
        if r['cp'] in (0x1CCA2,0x1CCA3):
            r.update(entryPolicy='t-exclusive',decisionSource='本人取消右向车厢双入口个例；两向均归游戏图标，只保留t查法',
                confirmationKind='本轮取消几何例外',classificationStatus='本人确认游戏图标及t排他方向',
                correctionReason='不再补建t外几何入口；历史许可仅留作追溯，不用于当前规则')
            confirmations[str(r['cp'])]={'decision':'include','category':'游戏图标','basis':r['decisionSource']}
    result['latestConfirmations']=confirmations
    result['latestChanges']=[result['geometryExceptionRevocation']]
    result['reviewSummary']['latestDecisionChanges']=0
    result['limitations']=[line for line in result['limitations'] if '双入口' not in line]
    result['limitations'].append('当前t采用排他入口，不再保留车厢个例，也不补建其t外几何查法。历史报告的旧许可已被本轮撤销。')
    result['uiNotice']='v5已取消车厢双入口个例；两向车厢均归游戏图标，只保留t查法。花饰区块维持24装饰、4物品火箭、20排除。其它未逐字审核者仍保持未审。'
    assert result['reviewDecisions']==previous['reviewDecisions']
    assert result['ornamentalBlockAcceptance']==previous['ornamentalBlockAcceptance']
    assert all((r['oldBucket'],r['oldCodes'])==(o['oldBucket'],o['oldCodes']) for r,o in zip(result['records'],previous['records']))
    assert protect()==before
    save(OUT/'拟物收入全量初稿.json',result)
    save(OUT/'取消车厢双入口个例.json',result['geometryExceptionRevocation'])
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in result.items() if k!='protectedHashes'})
    save(OUT/'验收.json',{'passed':True,'noGeometryException':True,'ornamentalPartitionPreserved':True,
        'allDecisionsPreserved':True,'protectedInputsUnchanged':protect()==before,'runtimeDeployed':False})
    print('v5: geometry exception revoked; floral24 / rockets4 / excluded20 preserved; no allocation or deployment')
    return result


if __name__=='__main__':build()
