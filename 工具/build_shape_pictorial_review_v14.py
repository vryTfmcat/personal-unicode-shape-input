"""Expand b under explicit approval and explain Egyptian part-related candidates."""
import copy
import re
from collections import Counter
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR,read,sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v13 import OUT as V13
from save_shape_pictorial_review import validate

OUT=V13.parent/'20261023-pictorial-intake-review-v14'
VERSION='pictorial-intake-20261023-v14'
SNAPSHOT=V13/'人工审核保存/网页审核原始结果-a5bd99797199ce4de9acc5f23abd6b596821107f33e7b1343e1f27a81e430329.json'
MOVED_CATEGORIES=('自然物象','人脸与表情','棋牌符号')
EXACT={0x1312E:'牛肋骨的示意图',0x1312F:'带肉的腿骨',
       0x13132:'肠的示意图，开口在右下',0x13133:'肠的示意图，开口在左上',
       0x13134:'肠的示意图，开口在左下',0x13135:'肠的示意图，开口在右上'}
TERMS=[(r'ribs?','肋骨'),(r'leg[- ]bone','腿骨'),(r'intestine','肠'),
 (r'flesh|piece of meat|haunch','肉块'),(r'folded piece of cloth','折叠布条'),
 (r'excrement','粪便'),(r'feathers?','羽毛'),(r'egg','鸟蛋'),(r'thigh','大腿'),
 (r'windpipe','气管'),(r'lungs?','肺'),(r'heart','心脏'),(r'horns?','角'),
 (r'palm branch','棕榈枝'),(r'sun disk','太阳圆盘'),(r'fire-drill','取火钻'),
 (r'tusk','长牙'),(r'jawbone','颌骨'),(r'tongue','舌'),(r'ear','耳'),
 (r'hindquarters','后躯'),(r'paw|claw|talon','爪'),(r'foreleg','前肢'),
 (r'hoof','蹄'),(r'water skin','皮囊'),(r'skin','兽皮'),(r'udder','乳房'),(r'tail','尾'),
 (r'wood','木块'),(r'standard','仪式用支架'),(r'cup|basin|vase','杯／盆／瓶'),
 (r'flowers?','花'),(r'papyrus','纸莎草'),(r'vertebrae?|vertebra','椎骨'),
 (r'spine','脊柱'),(r'spinal cord','脊髓'),(r'pustule','脓疱'),(r'gland','腺体'),
 (r'placenta','胎盘'),(r'liver','肝'),(r'fang','獠牙'),(r'mat|bag|woven','席／袋／编织物'),
 (r'falcon','隼'),(r'owl','猫头鹰'),(r'lion','狮'),(r'leopard','豹'),
 (r'bovid|ox|cow','牛类'),(r'goat','山羊'),(r'cobra','眼镜蛇'),(r'duckling','雏鸭'),
 (r'staff','杖'),(r'spear','矛'),(r'tiller','船舵'),(r'eye','眼'),
 (r'loop','环线'),(r'oval','椭圆'),(r'circle','圆'),(r'rectangle|rectangular','长方形'),
 (r'cone|conical','锥形'),(r'triangles?','三角形')]


def explain(row):
    desc=row['egyptianReference'].get('appearance','')
    if row['cp'] in EXACT:
        return {'zh':EXACT[row['cp']],'kind':'中文辅助释义','hasOfficialDescription':True,'admissionEvidence':False}
    if not desc:
        return {'zh':'官方未提供本字的图形描述；只有目录分组，具体所画对象待辨',
                'kind':'资料缺口','hasOfficialDescription':False,'admissionEvidence':False}
    terms=[]
    for pattern,zh in TERMS:
        if re.search(r'\b(?:'+pattern+r')\b',desc,re.I) and zh not in terms:terms.append(zh)
    return {'zh':'、'.join(terms[:7]) if terms else '官方有图形描述，但本轮尚无可靠中文辅助释义',
            'kind':'官方描述关键词的中文辅助','hasOfficialDescription':True,'admissionEvidence':False}


def build():
    if OUT.exists():raise FileExistsError('不覆盖已有v14核对结果')
    protected=protect();previous=read(V13/'拟物收入全量初稿.json');snapshot=read(SNAPSHOT)
    assert sha(SNAPSHOT)==SNAPSHOT.stem.split('-')[-1];validate(snapshot,previous)
    decisions={str(d['cp']):copy.deepcopy(d) for d in snapshot['decisions']}
    changes=[d for cp,d in decisions.items() if previous['reviewDecisions'].get(cp)!=d]
    assert len(changes)==8
    assert Counter(d.get('decision') for d in decisions.values())=={'include':3835,'exclude':60,None:1}
    result=copy.deepcopy(previous)
    result.update(version=VERSION,predecessorVersion=previous['version'],
        lineageVersions=previous['lineageVersions']+[VERSION],
        predecessorReportSHA256=sha(V13/'拟物收入全量初稿.json'),
        sourceReviewSnapshot=str(SNAPSHOT),sourceReviewSHA256=sha(SNAPSHOT),
        reviewDecisions=decisions,latestConfirmations={},protectedHashes=protected)
    labels=read(EDITOR/'data/pictorial-category-labels.json');labels['aliases']['字母标识']='字符标识'
    labels['characterBadgeBasis']='本人确认b增加字符标识类别，原43个b字母标识候选全部收入；不推广到其它普通文字。'
    mapping=result['bucketSplit']['categoryFirstKeys']
    mapping.update({c:'b' for c in MOVED_CATEGORIES});mapping['字符标识']='b'
    rows={r['cp']:r for r in result['records']};confirmations=[]
    for cp in previous['discoveryQueues']['bBadges']['cps']:
        before=copy.deepcopy(decisions.get(str(cp)))
        d=decisions.setdefault(str(cp),{'cp':cp,'char':chr(cp)})
        d.update(decision='include',category='字符标识',firstKey='b')
        result['latestConfirmations'][str(cp)]={'decision':'include','category':'字符标识','firstKey':'b',
            'basis':'本人明确确认原b字母标识候选全体收入字符标识类'}
        confirmations.append({'cp':cp,'before':before,'after':copy.deepcopy(d)})
        row=rows[cp];old=row['category'];row['category']='字符标识'
        result['categoryPlacements'].append({'cp':cp,'char':chr(cp),'before':old,'after':'字符标识','basis':'本人确认新类别'})
        row['bCandidate']['isAdmitted']=True
    assert len(confirmations)==43
    def category(row):
        c=decisions.get(str(row['cp']),{}).get('category',row['category'])
        return labels['aliases'].get(c,c)
    moved=[]
    for row in rows.values():
        d=decisions.get(str(row['cp']),{})
        if d.get('decision')=='include' and category(row) in MOVED_CATEGORIES:
            moved.append(row['cp'])
            if d.get('firstKey')=='t':
                d['firstKey']='b';result['latestConfirmations'][str(row['cp'])]={'firstKey':'b','basis':'本人确认整类迁往b'}
        if row.get('egyptianReference',{}).get('group') in ('F','H'):
            row['egyptianExplanation']=explain(row)
    admitted=[r for r in rows.values() if decisions.get(str(r['cp']),{}).get('decision')=='include']
    allocation=[{'cp':r['cp'],'char':r['char'],'category':category(r),
        'firstKey':(decisions[str(r['cp'])].get('firstKey') if decisions[str(r['cp'])].get('firstKey') in ('t','b') else mapping.get(category(r),'t')),
        'codesAssigned':False} for r in admitted]
    counts=Counter(r['firstKey'] for r in allocation)
    result['draftFirstKeyAllocations']=allocation
    result['bucketSplit'].update(admittedCounts=dict(counts),
        admittedCategoryCounts={k:dict(Counter(r['category'] for r in allocation if r['firstKey']==k)) for k in ('t','b')})
    result['secondReview'].update(admittedCps=[r['cp'] for r in admitted],categoryCounts=dict(Counter(category(r) for r in admitted)))
    partq=result['discoveryQueues']['egyptAnimalParts']
    partq['label']='埃及部位相关字形待辨'
    partq['description']='F／H是古埃及字形目录分组，不是现代写实部位图。包括肋骨、肠、肉块、羽毛，以及器物和复合图形；中文为图形描述辅助，不表示已收入。'
    result['discoveryQueues']['bBadges'].update(label='字符标识本次收入',allowExcluded=False,onlyUnresolved=True)
    pending=[rows[cp] for cp in partq['cps'] if decisions.get(str(cp),{}).get('decision','pending') in ('pending','uncertain')]
    result['latestReviewSummary']={'include':3878,'exclude':59,'uncertain':0,'browserNewIncludes':8,
        'newlyConfirmedBadges':43,'categoryOnly':1,'secondReviewed':0}
    result['bucketAudit14']={'counts':dict(counts),'movedCategories':{c:sum(category(r)==c for r in admitted) for c in MOVED_CATEGORIES},
        'movedCps':moved,'badgeConfirmations':confirmations,'egyptianPartsPending':len(pending),
        'egyptianPartsPendingByGroup':dict(Counter(r['egyptianReference']['group'] for r in pending)),
        'pendingWithoutOfficialDescription':sum(not r['egyptianExplanation']['hasOfficialDescription'] for r in pending),
        'explanationScope':'形状描述，不是文字读音、词义或本人可识别性确认；缺描述不猜造器官',
        'examples':{str(cp):rows[cp]['egyptianExplanation'] for cp in EXACT},'runtimeDeployed':False}
    result['uiNotice']='v14按本人确认将自然物象、人脸与表情、棋牌符号迁b；43个字符标识全部收入。埃及部位候选增加中文图形说明，未自动收入。'
    assert len(admitted)==3878 and counts=={'t':3279,'b':599}
    assert len(pending)==148
    assert Counter(d.get('decision') for d in decisions.values())=={'include':3878,'exclude':59,None:1}
    assert result['secondReview']['boundaryCps']==previous['secondReview']['boundaryCps']
    assert protect()==protected
    save(OUT/'拟物收入全量初稿.json',result)
    save(OUT/'b扩展及埃及部位说明.json',{'audit':result['bucketAudit14'],'latestReview':result['latestReviewSummary']})
    save(EDITOR/'data/pictorial-category-labels.json',labels)
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in result.items() if k!='protectedHashes'})
    print(result['latestReviewSummary']);print({k:v for k,v in result['bucketAudit14'].items() if k not in ('movedCps','badgeConfirmations','examples')})


if __name__=='__main__':build()
