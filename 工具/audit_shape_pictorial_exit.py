"""Measure confirmed t-only exits from pinned geometry candidates, without migration."""
from collections import Counter, defaultdict
import json

from audit_shape_historical_buckets import SOURCE, protect
from build_shape_pictorial_review import read, sha
from build_shape_pictorial_review_v5 import OUT
from build_shape_keyboard_full import save

REPORT = OUT / '拟物收入全量初稿.json'
SNAPSHOT = OUT / '人工审核保存/网页审核原始结果-a8c8167e8efe3d6b737d8de7ef8ea3fa64021b49f043f420659ef79c7ddbf069.json'
FOCUS = ('chvc', 'mdez', 'ajvg', 'cxvc', 'iocv', 'crvg')


def measure(records, decisions):
    admitted = {int(cp) for cp, d in decisions.items() if d['decision'] == 'include'}
    groups = defaultdict(set)
    buckets = defaultdict(set)
    for r in records:
        buckets[r['bucket']].add(r['cp'])
        for code in r['codes']:
            if len(code) == 4:
                groups[code].add(r['cp'])
    rows = []
    for code, cps in groups.items():
        removed = cps & admitted
        rows.append({'code': code, 'before': len(cps), 'removed': len(removed),
                     'after': len(cps - admitted), 'removedCps': sorted(removed)})
    rows.sort(key=lambda r: (-r['before'], r['code']))
    ordinary = {r['cp'] for r in records}
    detailed = {r['cp'] for r in records if r['codes']}
    return {
        'approved': len(admitted), 'ordinaryExits': len(ordinary & admitted),
        'detailedExits': len(detailed & admitted),
        'firstOnlyExits': len((ordinary - detailed) & admitted),
        'outsideOrdinary': len(admitted - ordinary),
        'candidateAssociationsRemoved': sum(r['removed'] for r in rows),
        'fourKeyGroupsBefore': len(rows),
        'fourKeyGroupsAfter': sum(r['after'] > 0 for r in rows),
        'maximumBefore': max((r['before'] for r in rows), default=0),
        'maximumAfter': max((r['after'] for r in rows), default=0),
        'focus': [r for code in FOCUS for r in rows if r['code'] == code],
        'largestBefore': rows[:20],
        'largestAfter': sorted(rows, key=lambda r: (-r['after'], r['code']))[:20],
        'largestReductions': sorted(rows, key=lambda r: (-r['removed'], r['code']))[:20],
        'buckets': [{'key': k, 'before': len(cps), 'removed': len(cps & admitted),
                     'after': len(cps - admitted)} for k, cps in sorted(buckets.items())],
        'allGroups': rows,
    }


def build():
    targets = [OUT / 't排他入口减负试算.json', OUT / 't排他入口减负与剩余核对.md']
    if any(p.exists() for p in targets):
        raise FileExistsError('不覆盖已有试算')
    before = protect()
    report = read(REPORT)
    snapshot = read(SNAPSHOT)
    assert sha(SNAPSHOT) == SNAPSHOT.stem.split('-')[-1]
    decisions = {str(d['cp']): d for d in snapshot['decisions']}
    assert decisions == report['reviewDecisions']
    index = read(SOURCE / '发布核对索引.json')
    assert sha(SOURCE / '发布核对索引.json') == report['sourceIndexSHA256']
    result = measure(index['records'], decisions)
    remaining = [r for r in report['records']
                 if decisions.get(str(r['cp']), {}).get('decision') == 'uncertain']
    result.update(sourceVersion=report['version'], sourceReportSHA256=sha(REPORT),
                  sourceSnapshotSHA256=sha(SNAPSHOT),
                  sourceIndexSHA256=report['sourceIndexSHA256'],
                  remainingByCategory=dict(Counter(r['category'] for r in remaining)),
                  remaining=[{k: r[k] for k in ('cp', 'char', 'name', 'category')} for r in remaining],
                  allocationChanged=False, runtimeDeployed=False,
                  scope='仅固定v14几何索引的逐码候选集合差；未应用结构优先级、中心或粗笔试验，未构造t第二位码')
    assert result['ordinaryExits'] + result['outsideOrdinary'] == result['approved']
    assert result['detailedExits'] + result['firstOnlyExits'] == result['ordinaryExits']
    assert all(r['before'] == r['after'] + r['removed'] for r in result['allGroups'])
    assert protect() == before
    save(targets[0], result)
    lines = ['# t排他入口减负与剩余核对', '',
             '本稿是v5已确认收入字符退出固定v14几何候选的只读试算，不是已迁移结果。',
             '不把未审、待讨论或不收入的字符移出；不据此分配第二位字母。', '',
             f"已收入{result['approved']}字：普通几何桶内{result['ordinaryExits']}字，桶外{result['outsideOrdinary']}字。",
             f"普通桶内有细码{result['detailedExits']}字，仅第一位{result['firstOnlyExits']}字。",
             f"四码字符对应减少{result['candidateAssociationsRemoved']}项；不是去重字符数。",
             f"四码最大候选{result['maximumBefore']}→{result['maximumAfter']}。", '',
             '## 六个原重点大组', '', '| 编码 | 原候选 | 拟移出 | 试算剩余 |',
             '| --- | ---: | ---: | ---: |']
    for r in result['focus']:
        lines.append(f"| {r['code']} | {r['before']} | {r['removed']} | {r['after']} |")
    lines += ['', '## 试算后最大20组', '', '| 编码 | 原候选 | 拟移出 | 试算剩余 |',
              '| --- | ---: | ---: | ---: |']
    for r in result['largestAfter']:
        lines.append(f"| {r['code']} | {r['before']} | {r['removed']} | {r['after']} |")
    lines += ['', '## 剩余待讨论', '',
              '以下只按现有分类聚合，不依据名称或专题范围自动批准。原备注继续保存在网页审核快照。']
    for category, count in sorted(result['remainingByCategory'].items()):
        lines += ['', f'### {category}（{count}字）', '', '| 字符 | 码位 | 名称 |', '| --- | --- | --- |']
        for r in remaining:
            if r['category'] == category:
                lines.append(f"| {r['char']} | U+{r['cp']:04X} | {r['name']} |")
    lines += ['', '## 后续顺序', '',
              '1. 本试算只分离已确认t字；剩余待讨论保持原状，按网页逐字审核。',
              '2. t退出后仍大的几何组，继续查入口证据及更特异的结构优先级，不能指望拟物分桶消除全部重码。',
              '3. t内部第二位先比较类别的候选数量和边界，再拟字母；不把古文字按名称或区块整段迁入。',
              '', '注意：本稿基线是固定v14，不与后续chvc可靠细码、中心、粗笔稳定性试验直接相加。']
    targets[1].write_text('\n'.join(lines) + '\n', encoding='utf-8')
    assert protect() == before
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('remaining', 'allGroups', 'largestBefore', 'largestAfter',
                                   'largestReductions', 'buckets')}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    build()
