"""Apply the user's category merges without changing admission decisions."""
import copy
from collections import Counter
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_keyboard_full import save
from build_shape_pictorial_review_v9 import OUT as V9

OUT = V9.parent / '20261023-pictorial-intake-review-v10'
VERSION = 'pictorial-intake-20261023-v10'
RENAMES = {'安全标识': '标识分类', '交通指示牌': '标识分类',
           '标识牌': '棋牌符号', '自然物象／月相': '自然物象'}
MOVES = {0x1F3C7: '人物与动作', 0x1F46A: '人物与动作',
         0x1F48F: '人物与动作', 0x1F3D5: '建筑与场所'}


def build():
    if OUT.exists():
        raise FileExistsError('不覆盖已有v10结果')
    protected = protect()
    previous = read(V9 / '拟物收入全量初稿.json')
    result = copy.deepcopy(previous)
    labels = read(EDITOR / 'data/pictorial-category-labels.json')
    result.update(version=VERSION, predecessorVersion=previous['version'],
                  lineageVersions=previous['lineageVersions'] + [VERSION],
                  predecessorReportSHA256=sha(V9 / '拟物收入全量初稿.json'),
                  latestConfirmations={}, protectedHashes=protected)
    changes = []
    for row in result['records']:
        before = row['category']
        after = MOVES.get(row['cp'], RENAMES.get(before, before))
        if before != after:
            row['category'] = after
            changes.append({'cp': row['cp'], 'char': row['char'],
                            'before': before, 'after': after,
                            'basis': '本人2026-10-23确认的分类改名、合并与逐字移动'})
    result['categoryPlacements'].extend(changes)
    result['categoryMergeChanges'] = changes
    labels['aliases'].update(RENAMES)
    labels['basis'] = '本人确认：安全标识改为标识分类，标识牌改为棋牌符号，月相并入自然物象；不新增收入。'
    categories = Counter()
    for row in result['records']:
        decision = result['reviewDecisions'].get(str(row['cp']), {})
        if decision.get('decision') == 'include':
            category = decision.get('category', row['category'])
            categories[labels['aliases'].get(category, category)] += 1
    result['secondReview']['categoryCounts'] = dict(categories)
    result['uiNotice'] = 'v10已按确认合并分类并移动🏇、👪、💏、🏕；收入判断、备注及待看图范围不变。'
    assert result['reviewDecisions'] == previous['reviewDecisions']
    assert sum(categories.values()) == 3620
    assert {k: categories[k] for k in ('人物与动作', '建筑与场所', '自然物象', '棋牌符号', '标识分类')} == {
        '人物与动作': 907, '建筑与场所': 42, '自然物象': 71, '棋牌符号': 204, '标识分类': 6}
    assert not any(categories[k] for k in ('人物与场景', '自然物象／月相', '安全标识', '标识牌'))
    assert protect() == protected
    save(OUT / '归类前名称映射.json', read(EDITOR / 'data/pictorial-category-labels.json'))
    save(OUT / '拟物收入全量初稿.json', result)
    save(OUT / '分类合并与逐字移动.json', {'changes': changes, 'admittedCategoryCounts': dict(categories),
                                        'admissionDecisionsChanged': False, 'runtimeDeployed': False})
    save(EDITOR / 'data/pictorial-category-labels.json', labels)
    save(EDITOR / 'data/pictorial-intake-review.json', {k: v for k, v in result.items() if k != 'protectedHashes'})
    print(dict(categories))


if __name__ == '__main__':
    build()
