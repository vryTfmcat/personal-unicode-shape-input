"""Merge the latest human review and audit omitted pictographs, without admission."""
import copy
import shutil
from collections import Counter
from pathlib import Path
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v10 import OUT as V10
from save_shape_pictorial_review import validate, save_snapshot

OUT = V10.parent / '20261023-pictorial-intake-review-v11'
VERSION = 'pictorial-intake-20261023-v11'
EXPORT = Path('C:/Users/86137/Downloads/拟物收入审核结果-2026-10-22 (2).json')
EMOJI = EDITOR / '测试输出/pictorial-intake-review/emoji-test-17.0.txt'
SOURCE_URL = 'https://www.unicode.org/Public/17.0.0/emoji/emoji-test.txt'


def emoji_records():
    group = subgroup = ''
    result = {}
    for line in EMOJI.read_text(encoding='utf-8').splitlines():
        if line.startswith('# group: '):
            group = line[9:]
        elif line.startswith('# subgroup: '):
            subgroup = line[12:]
        elif line and not line.startswith('#'):
            code, status = line.partition('#')[0].split(';')
            cps = code.split()
            if len(cps) == 1 and status.strip() != 'component':
                result[int(cps[0], 16)] = (group, subgroup)
    return result


def emoji_target(cp, group, sub):
    # Source groups retrieve candidates only; this function never changes decisions.
    if group == 'Smileys & Emotion':
        if sub.startswith('face-') or sub == 'cat-face':
            return {0x1F480:'身体部位', 0x2620:'身体部位', 0x1F4A9:'工具与日常物品',
                    0x1F47E:'游戏图标'}.get(cp, '动物' if sub == 'cat-face' else '人脸与表情')
        if cp == 0x1F48C:
            return '工具与日常物品'
    if group == 'People & Body':
        return '身体部位' if (sub.startswith('hand') or sub == 'body-parts' or cp in (0x1F463,0x1FAC6)) else '人物与动作'
    if group == 'Animals & Nature':
        if sub == 'animal-bird':return '鸟类'
        if sub == 'animal-marine':return '鱼类' if cp == 0x1F421 else '动物'
        if sub == 'animal-bug':return '动物' if cp == 0x1F9A0 else '昆虫'
        if sub.startswith('animal'):return '动物'
        return '自然物象' if cp in (0x1FAB9,0x1FABA) else '植物'
    if group == 'Food & Drink':
        if sub == 'dishware':return '工具与日常物品'
        return '自然物象' if cp == 0x1F9CA else '食物与饮品'
    if group == 'Travel & Places':
        if sub == 'place-map':return '工具与日常物品'
        if sub == 'place-geographic':return '自然物象'
        if sub.startswith('place-'):return '工具与日常物品' if cp in (0x1F9F1,0x1F488) else '建筑与场所'
        if sub == 'transport-ground':
            if cp in (0x1F689,0x1F6E3,0x1F6E4):return '建筑与场所'
            if cp in (0x1F6D1,0x1F6A7):return '标识'
            return '工具与日常物品' if cp in (0x26FD,0x1F6A8,0x1F6A5,0x1F6A6) else '交通工具'
        if sub.startswith('transport-'):return '交通工具'
        if sub == 'time':return '工具与日常物品'
        if cp in (0x26A1,0x2744,0x2603):return '自然物象'
    if group == 'Activities':
        if cp == 0x2728:return None
        return '棋牌符号' if cp == 0x1F004 else '工具与日常物品'
    if group == 'Objects':
        if sub == 'music' and cp not in (0x1F39A,0x1F39B):return None
        if cp == 0x1F4B9:return None  # Chart dominated by a currency character.
        if cp == 0x1FA78:return '身体部位'
        return '工具与日常物品'
    if group == 'Symbols':
        if sub == 'transport-sign' and cp != 0x1F3E7:return '标识'
        if sub == 'warning' and cp != 0x1F51E:return '标识'
        if sub in ('religion','zodiac'):return '象征标志'
        if cp in (0x2695,0x269C,0x267B,0x1F531,0x1F530):return '象征标志'
        if cp == 0x1F4DB:return '标识'
    if group == 'Flags':return '工具与日常物品'
    return None


EXTRAS = {
    '身体部位':'🖒🖓🖘🖙🖚🖛🖜🖝🖞🖟🖠🖡🖢🖣',
    '工具与日常物品':'✇✑📾🕫🕬🖈🖧🖩🖭🖵🖷🖹🖺🖻🗅🗆🗇🗈🗉🗊🗋🗌🗍🗎🗏🗐🗠🏱🏲🥆',
    '棋牌符号':'☖☗⛁⛃⛉⛊',
    '自然物象':'⛇☈',
    '装饰':'✾✿❀❁🏶',
    '建筑与场所':'⛯⛼🛓',
    '人物与动作':'🤻',
    '食物与饮品':'⛾',
    '标识':'⛕⛖⛗⛘⛙⛚⛜⛠⛡⛨🕲🛇🛉🛊⌘',
    '象征标志':'☤☥☧☫☬⚚🕏',
}


def build():
    if OUT.exists():raise FileExistsError('不覆盖已有v11核对结果')
    protected = protect()
    previous = read(V10/'拟物收入全量初稿.json')
    snapshot = read(EXPORT)
    validate(snapshot, previous)
    receipt = save_snapshot(snapshot)
    result = copy.deepcopy(previous)
    decisions = {str(d['cp']):copy.deepcopy(d) for d in snapshot['decisions']}
    assert not set(previous['reviewDecisions']) - decisions.keys()
    changes = [{'before':previous['reviewDecisions'].get(cp), 'after':d}
               for cp,d in decisions.items() if previous['reviewDecisions'].get(cp) != d]
    assert len(changes) == 27
    result.update(version=VERSION, predecessorVersion=previous['version'],
                  lineageVersions=previous['lineageVersions']+[VERSION],
                  predecessorReportSHA256=sha(V10/'拟物收入全量初稿.json'),
                  sourceReviewSnapshot=receipt['path'], sourceReviewSHA256=receipt['sha256'],
                  reviewDecisions=decisions, latestConfirmations={}, protectedHashes=protected)
    labels = read(EDITOR/'data/pictorial-category-labels.json')
    labels['aliases'].update({'交通指示牌':'标识', '安全标识':'标识', '标识分类':'标识'})
    labels['basis'] = '本人2026-10-23纠正：类名是标识，不是标识分类；其它已确认归类保持不变。'
    rows = {r['cp']:r for r in result['records']}
    placements = []
    for row in rows.values():
        if row['category'] == '标识分类':
            placements.append({'cp':row['cp'],'char':row['char'],'before':row['category'],
                               'after':'标识','basis':'本人纠正分类名称'})
            row['category'] = '标识'
    queues = {k:{'label':label,'onlyUnresolved':True,'cps':[]} for k,label in (
        ('omittedObjects','遗漏候选：具体图像'),
        ('omittedSigns','遗漏候选：标识与象征'),
        ('omittedVariants','遗漏候选：非Emoji同类'))}
    found = {}
    emoji = emoji_records()
    for cp,(group,sub) in emoji.items():
        if cp not in rows or str(cp) in decisions:continue
        target = emoji_target(cp,group,sub)
        if target:
            found[cp] = (target,'omittedSigns' if group == 'Symbols' else 'omittedObjects',
                         {'group':group,'subgroup':sub,'source':'Unicode emoji-test 17.0'})
    for target,chars in EXTRAS.items():
        for cp in map(ord,chars):
            if cp in rows and str(cp) not in decisions and cp not in found:
                found[cp] = (target,'omittedVariants',{'source':'与已收入的物品、手势、棋牌、花饰或标识同类；仍需逐字看图'})
    for cp,(target,queue,source) in sorted(found.items()):
        row = rows[cp]
        audit = {'suggestedCategory':target,'originalProposal':row['proposal'],
                 'originalCategory':row['category'],'queue':queue,**source,
                 'humanAccepted':False}
        row['omissionCandidate'] = audit
        if row['category'] != target:
            placements.append({'cp':cp,'char':row['char'],'before':row['category'],
                               'after':target,'basis':'查漏分类建议，不改变收入判断'})
            row['category'] = target
        queues[queue]['cps'].append(cp)
    result['categoryPlacements'].extend(placements)
    result['discoveryQueues'].update(queues)
    admitted = [r for r in rows.values() if decisions.get(str(r['cp']),{}).get('decision') == 'include']
    counts = Counter()
    for row in admitted:
        category = decisions[str(row['cp'])].get('category',row['category'])
        counts[labels['aliases'].get(category,category)] += 1
    result['secondReview'].update(admittedCps=[r['cp'] for r in admitted],
                                 categoryCounts=dict(counts))
    statuses = Counter(d.get('decision') for d in decisions.values())
    assert statuses == {'include':3629,'exclude':54}
    assert len(result['secondReview']['boundaryCps']) == 7303
    result['latestReviewSummary'] = {'counts':dict(statuses),'changedEntries':len(changes),
                                    'uncertain':0,'rawExportSHA256':sha(EXPORT)}
    result['omissionAudit'] = {
        'emojiSourceURL':SOURCE_URL,'emojiSourceSHA256':sha(EMOJI),
        'singleCodepointEmojiChecked':len(emoji),
        'singleCodepointEmojiNotInReview':[{ 'cp':cp,'group':g,'subgroup':s} for cp,(g,s) in emoji.items() if cp not in rows],
        'byQueue':{k:len(q['cps']) for k,q in queues.items()},
        'bySuggestedCategory':dict(Counter(v[0] for v in found.values())),
        'oldAutomaticExclusionsRecalled':sum(rows[cp]['proposal']=='exclude' for cp in found),
        'reviewedEntriesReproposed':0,
        'egyptianStillUndecidedByGroup':dict(Counter(r['egyptianReference']['group'] for r in rows.values()
              if r.get('egyptianReference') and str(r['cp']) not in decisions)),
        'limitations':['只检查现有码表中的单码位身份，不扩展组合Emoji或ZWJ序列。',
                      'Unicode分组和名称用于查漏，不代替实际字形审核；没有自动收入。',
                      '埃及文字其余部位、植物、器具仍须逐字看图，未整段收入。',
                      '普通圆方、抽象心形、文字标识、标点乐谱及纯拼块不因Emoji身份收入。']}
    result['uiNotice'] = 'v11已保存最新审核，初审待讨论清零；类名改为标识，新增查漏候选不自动收入。'
    assert protect() == protected
    assert result['reviewDecisions'] == {str(d['cp']):d for d in snapshot['decisions']}
    save(OUT/'拟物收入全量初稿.json',result)
    shutil.copyfile(EXPORT,OUT/'Chrome最新人工审核原始导出.json')
    shutil.copyfile(EMOJI,OUT/'emoji-test-17.0.txt')
    save(OUT/'人工审核变化与查漏.json',{'humanChanges':changes,'audit':result['omissionAudit'],
        'candidates':[{'cp':cp,'char':rows[cp]['char'],'name':rows[cp]['name'],**rows[cp]['omissionCandidate']} for cp in sorted(found)]})
    save(EDITOR/'data/pictorial-category-labels.json',labels)
    save(EDITOR/'data/pictorial-intake-review.json',{k:v for k,v in result.items() if k!='protectedHashes'})
    print(result['latestReviewSummary']);print(result['omissionAudit']);print(dict(counts))


if __name__ == '__main__':build()
