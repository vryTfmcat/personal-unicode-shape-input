"""Audit the frozen 145 identities against current routes without rebuilding codes."""
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '原型/键位编辑器'))
import shape_overview as so

OUT = so.RUNS / '20261024-historical145-current-audit-v1'
COHORT = so.RUNS / '20261021-reviewed145-audit-v1/历史确认145字初核.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect():
    frozen = so.read(COHORT)
    baseline = so.read(so.RUN / '历史确认145字逐字核查.json')
    source = Path(frozen['source'])
    assert digest(source) == frozen['sourceSHA256'], '历史确认源与初核哈希不一致'
    history = {r['cp']: r for r in so.read(source)['characters']}
    overview = so.get_overview()
    cohort = set(frozen['cohortFrozen'])
    assert len(cohort) == 145 == len(baseline['records'])
    assert cohort == {r['cp'] for r in baseline['records']}
    protected = [COHORT, source, so.RUN / '发布核对索引.json',
                 so.RUN / '历史确认145字逐字核查.json',
                 so.PROJECT / '原型/键位编辑器/data/pictorial-exclusive-allocation.json',
                 so.PROJECT / '数据/三模式/全形核对版.json']
    hashes = {str(p): digest(p) for p in protected}
    frozen_history = {r['cp']: r['history'] for r in frozen['records']}
    intake_keys = {(pos, key): set(overview.key_members(pos, key, True))
                   for pos in range(1, 5) for key in so.LETTERS}
    rows = []
    for r in baseline['records']:
        cp = r['cp']
        assert history[cp] == frozen_history[cp], (cp, '历史确认记录变化')
        assert history[cp]['shapeAssignmentLocked']
        brief, detail = overview.brief(cp, True), overview.detail(cp, True)
        codes = sorted(brief['codes'])
        assert codes == sorted(p['code'] for p in detail['paths']), cp
        assert brief['oldReviewed'], cp
        assert overview.query({'text': [f'U+{cp:X}'], 'allocation': ['1']})['total'] == 1
        for code in codes:
            assert cp in overview.allocation_members(code), (cp, code)
        bucket = brief.get('bucket')
        assert bucket and cp in overview.allocation_members(bucket), (cp, '第一位入口缺失')
        status = 't/b正常转入' if brief.get('pictorialIntake') else '保留几何细码' if codes else '几何细码待补'
        if status == 't/b正常转入':
            assert not codes
            for pos in range(1, 5):
                for key in so.LETTERS:
                    if pos == 1 and key == bucket:
                        continue
                    assert cp not in intake_keys[pos, key], (cp, pos, key)
        rows.append(dict(cp=cp, char=chr(cp), status=status, baselineRecovered=r['recovered'],
                         historicalPrimary=history[cp]['primary'], currentBucket=bucket,
                         historyLocked=True, category=r['category'], codes=codes,
                         pictorialCategory=brief.get('category'),
                         provisional=brief.get('provisional', False),
                         identityQueryable=True, firstKeyQueryable=True,
                         detailConsistent=True, amendments=r['amendments']))
    pending = {r['cp'] for r in rows if r['status'] == '几何细码待补'}
    query = overview.query({'queue': ['historical'], 'allocation': ['1']})
    fetched = set()
    for offset in range(0, query['total'], 60):
        page = overview.query({'queue': ['historical'], 'allocation': ['1'], 'offset': [str(offset)]})
        fetched.update(r['cp'] for r in page['rows'])
    assert fetched == pending
    assert hashes == {str(p): digest(p) for p in protected}, '核查期间受保护输入变化'
    return dict(createdAt=datetime.now(timezone.utc).isoformat(), cohortCount=145,
                baseline=dict(recovered=baseline['recovered'], pending=baseline['remaining']),
                counts=dict(Counter(r['status'] for r in rows)),
                pendingCategories=dict(Counter(r['category'] for r in rows if r['cp'] in pending)),
                sourceHistorySHA256=frozen['sourceSHA256'], protectedHashes=hashes,
                validations=dict(historyUnchanged=True, identitiesPreserved=True,
                                 firstKeyPreserved=True, detailsConsistent=True,
                                 pendingQueueExact=True, intakeExclusive=True),
                scope='旧确认仅保护历史第一位；本报告不恢复或确认几何细码，不部署。', records=rows)


def write_report(report):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / '历史145字当前覆盖核查.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 历史145字当前覆盖核查', '', report['scope'], '',
             '当前：' + '；'.join(f'{k} {v} 字' for k, v in report['counts'].items()) + '。', '',
             'v14为52字有细码、93字待补；其中1个原有细码字和9个原待补字转入t／b，故当前为51＋10＋84。', '',
             '84字均可按身份和当前第一位查询，候选与详情一致；未发现页面漏显已有细码或身份丢失。',
             '历史第一位确认源哈希与初核相同；缺少细码不表示历史确认被撤销。', '',
             '以下类别沿用原几何核查的机器原因，不是本轮逐字视觉确认，也不等于应恢复旧入口。', '',
             '| 状态／旧核查原因 | 字数 |', '| --- | ---: |']
    lines += [f'| {k} | {v} |' for k, v in report['pendingCategories'].items()]
    lines += ['', '## 全部145字逐项清单', '', '| 码位 | 字符 | 当前状态 | 历史第一位 | 当前第一位 | 原核查原因／路径 |', '| --- | --- | --- | --- | --- | --- |']
    for r in report['records']:
        reason = '、'.join(r['codes']) or (r['pictorialCategory'] if r['status'] == 't/b正常转入' else r['category'])
        lines.append(f"| U+{r['cp']:04X} | {r['char']} | {r['status']} | {r['historicalPrimary']} | {r['currentBucket']} | {reason} |")
    (OUT / '历史145字当前覆盖核查.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    report = inspect()
    write_report(report)
    print(json.dumps({k: report[k] for k in ('counts', 'pendingCategories', 'validations')}, ensure_ascii=False))
