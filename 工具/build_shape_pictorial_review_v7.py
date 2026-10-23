"""Repair semantic retrieval collisions and expose related glyphs without admission."""
import copy
from collections import Counter, defaultdict
import re
import shutil

from audit_shape_historical_buckets import protect
from build_shape_keyboard_full import save
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_pictorial_review_v6 import OUT as V6

OUT = V6.parent / '20261022-pictorial-intake-review-v7'
VERSION = 'pictorial-intake-20261022-v7'
SNAPSHOT = V6 / '人工审核保存/网页审核原始结果-49c31c00d29b7db8f495712ba2b7aca28596baa5727c13b13cbbb1e5e9593e06.json'
UNIKEMET = EDITOR / '测试输出/pictorial-intake-review/Unikemet-17.0.0.txt'
EXTRA_SIGNS = set(map(ord, '☢☣♲♳♴♵♶♷♸♹♺♻♼♽⚚🕉🛐'))


def face_category(cp, name):
    if cp == 0x1F48B:
        return '身体部位', 'KISS MARK是嘴唇印记，不是整张人脸；归身体部位，不称解剖器官'
    if re.search(r'\b(?:MOUSE|COW|TIGER|RABBIT|CAT|DRAGON|HORSE|MONKEY|DOG|PIG|FROG|HAMSTER|WOLF|BEAR|PANDA|LION|UNICORN|FOX|GIRAFFE|ZEBRA)\b', name):
        return '动物', '动物面孔及动物表情按对象归动物，不因FACE归人脸'
    if name.startswith('CLOCK FACE '):
        return '工具与日常物品', '钟面属于计时物品，不因FACE归人脸'
    if cp in range(0x1F31A, 0x1F31F) or cp == 0x1F32C:
        return '自然物象', '日月及风的拟人图像按主体归自然物象'
    if cp in (0x1F486, 0x1F645, 0x1F646, 0x1F64E, 0x1F926):
        return '人物与动作', '包含完整人物姿态或动作，不因FACE归单独人脸'
    if cp == 0x1F48F:
        return '人物与场景', '两人接吻场景，不是单独人脸'
    return None


def unikemet(path):
    data = defaultdict(dict)
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        scalar, prop, value = line.split('\t', 2)
        data[int(scalar[2:], 16)][prop] = value.strip()
    return data


def build():
    if OUT.exists():
        raise FileExistsError('不覆盖已有v7核对稿')
    protected = protect()
    previous = read(V6 / '拟物收入全量初稿.json')
    snapshot = read(SNAPSHOT)
    assert sha(SNAPSHOT) == SNAPSHOT.stem.split('-')[-1]
    report = copy.deepcopy(previous)
    report.update(version=VERSION, predecessorVersion=previous['version'],
                  lineageVersions=previous['lineageVersions']+[VERSION],
                  predecessorReportSHA256=sha(V6/'拟物收入全量初稿.json'),
                  sourceReviewSnapshot=str(SNAPSHOT), sourceReviewSHA256=sha(SNAPSHOT),
                  protectedHashes=protected)
    decisions = {str(d['cp']): copy.deepcopy(d) for d in snapshot['decisions']}
    report['reviewDecisions'] = decisions
    rows = report['records']
    repairs = []
    for row in rows:
        correction = face_category(row['cp'], row['name']) if row['category']=='人脸与表情' else None
        if correction:
            category, basis = correction
            repairs.append({'cp':row['cp'], 'char':row['char'], 'before':row['category'], 'after':category, 'basis':basis,
                            'manualCategoryPreserved':'category' in decisions.get(str(row['cp']), {})})
            row.update(previousCategory=row['category'], category=category, correctionReason=basis)
    official = unikemet(UNIKEMET)
    queues = {k:{'label':label, 'cps':[]} for k,label in (
        ('categoryRepairs','分类修正对照'), ('similarSigns','标志同类候选'),
        ('nearC002','𓁞近支／鹰首神形'), ('egyptPeople','埃及人物／神形系列'),
        ('egyptFish','𓆟鱼类系列'), ('egyptAnimals','同区块动物／鸟／爬虫／昆虫'),
        ('egyptAnimalParts','动物及鸟类部位'))}
    queues['categoryRepairs']['cps'] = [r['cp'] for r in repairs]
    references = {
        'unikemetVersion':'17.0.0', 'sourceUrl':'https://www.unicode.org/Public/17.0.0/ucd/Unikemet.txt',
        'sha256':sha(UNIKEMET), 'explanatoryUrl':'https://www.unicode.org/reports/tr57/',
        'meaning':'kEH_Cat及kEH_Desc只作检索与外形提示，不代替字形判断；不使用语义功能推定收入。'}
    for row in rows:
        cp = row['cp']
        if row['category']=='象征标志' or cp in EXTRA_SIGNS:
            queues['similarSigns']['cps'].append(cp)
            row['candidateBasis']='与现有象征／专业标志的类别关联；不是几何相似度结论，仍需看图确认'
            if cp in EXTRA_SIGNS:
                row.update(previousCategory=row['category'], category='象征标志')
        meta = official.get(cp)
        if not meta:
            continue
        catalog = meta.get('kEH_Cat','')
        group = catalog.split('-')[0]
        row['egyptianReference'] = {'catalog':catalog, 'group':group,
            'unikemet':meta.get('kEH_UniK',''), 'appearance':meta.get('kEH_Desc',''),
            'blockScope':'原区块' if cp < 0x13460 else '扩展A区块'}
        if catalog.startswith('C-09-'):
            queues['nearC002']['cps'].append(cp)
        if group in ('A','B','C'):
            queues['egyptPeople']['cps'].append(cp)
        if group=='K':
            queues['egyptFish']['cps'].append(cp)
        if group in ('E','G','I','L'):
            queues['egyptAnimals']['cps'].append(cp)
        if group in ('F','H'):
            queues['egyptAnimalParts']['cps'].append(cp)
    report['discoveryQueues'] = queues
    admitted = [r for r in rows if decisions.get(str(r['cp']),{}).get('decision')=='include']
    report['secondReview']['categoryCounts'] = dict(Counter(decisions.get(str(r['cp']),{}).get('category',r['category']) for r in admitted))
    report['secondReview']['initialReviewedCount'] = sum(d.get('secondReviewed') is True for d in decisions.values())
    report['classificationRepairs'] = repairs
    report['egyptianSources'] = references
    report['latestConfirmations'] = {}
    report['uiNotice'] = 'v7修正人脸类的动物、唇印、钟面、自然物象和人物动作；新增标志及埃及系列候选，不自动收入。'
    report['discoverySummary'] = {k:{'total':len(q['cps']),
        'visible':sum(decisions.get(str(cp),{}).get('decision')!='exclude' for cp in q['cps']),
        'originalBlock':sum(cp<0x13460 for cp in q['cps']) if k.startswith('egypt') or k=='nearC002' else None}
        for k,q in queues.items()}
    assert report['reviewDecisions'] == {str(d['cp']):d for d in snapshot['decisions']}
    assert len(rows)==len(previous['records']) and len(admitted)==1258
    assert report['secondReview']['boundaryCps']==previous['secondReview']['boundaryCps']
    assert protect()==protected
    save(OUT/'拟物收入全量初稿.json',report)
    shutil.copyfile(UNIKEMET,OUT/'Unikemet-17.0.0.txt')
    save(OUT/'分类修正与同类候选.json',{'repairs':repairs,'queues':queues,'summary':report['discoverySummary'],'sources':references})
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in report.items() if k!='protectedHashes'})
    save(OUT/'验收.json',{'passed':True,'allDecisionsAndNotesPreserved':True,'admitted':1258,
         'protectedSourcesUnchanged':protect()==protected,'allocationChanged':False,'runtimeDeployed':False})
    print(report['discoverySummary'])
    print('category repairs',len(repairs))


if __name__=='__main__':
    build()
