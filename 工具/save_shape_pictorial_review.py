"""Append-only storage for explicit browser review, never an allocation writer."""
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json

from build_shape_pictorial_review import EDITOR, OUT, read


def validate(data, report):
    if not isinstance(data, dict) or data.get('format') != 'pictorial-intake-human-review-v1':
        raise ValueError('不是拟物审核结果')
    if data.get('version') != report['version'] or data.get('sourceIndexSHA256') != report['sourceIndexSHA256']:
        raise ValueError('审核来源版本不匹配')
    if data.get('allocationChanged') is not False or not isinstance(data.get('decisions'), list):
        raise ValueError('仅允许保存未迁移的审核草稿')
    if data.get('scope') != report['scope']:
        raise ValueError('审核范围不匹配')
    rows = {r['cp']: r for r in report['records']}
    categories = {row['category'] for row in report['records']}
    labels = EDITOR / 'data/pictorial-category-labels.json'
    if labels.is_file():
        categories.update(read(labels).get('aliases', {}).values())
    decisions = {}
    for r in data['decisions']:
        if not isinstance(r, dict):
            raise ValueError('审核条目格式无效')
        cp = r.get('cp')
        if type(cp) is not int or cp not in rows or cp in decisions or r.get('char') != chr(cp):
            raise ValueError('审核包含未知／重复字符或字符与码位不一致')
        if 'decision' in r and r['decision'] not in ('include', 'exclude', 'uncertain'):
            raise ValueError('审核判断无效')
        if 'note' in r and (not isinstance(r['note'], str) or len(r['note']) > 2000):
            raise ValueError('审核备注无效')
        allowed = {'cp', 'char', 'decision', 'note'}
        if report.get('secondReview', {}).get('enabled'):
            allowed |= {'category', 'secondReviewed'}
            if 'category' in r and (not isinstance(r['category'], str) or r['category'] not in categories):
                raise ValueError('二审类别无效')
            if 'secondReviewed' in r and type(r['secondReviewed']) is not bool:
                raise ValueError('二审确认状态无效')
        if set(r) - allowed:
            raise ValueError('审核含未知字段')
        decisions[cp] = r
    groups = {}
    for queue in ('propose', 'confirmed', 'boundary', 'exclude'):
        members = [r for r in report['records'] if r['proposal'] == queue]
        counts = Counter(decisions.get(r['cp'], {}).get('decision', 'pending') for r in members)
        groups[queue] = {'total': len(members), **{k: counts[k] for k in ('include', 'exclude', 'uncertain', 'pending')}}
    return {'explicitEntries': len(decisions), 'explicitDecisions': dict(Counter(r.get('decision', 'note-only') for r in decisions.values())), 'queues': groups,
            'secondReviewed': sum(r.get('secondReviewed') is True for r in decisions.values())}


def save_snapshot(data, output=None):
    if not isinstance(data, dict):
        raise ValueError('不是拟物审核结果')
    folder_root = OUT
    if data.get('version') == 'pictorial-intake-20261022-v7':
        folder_root = OUT.parent/'20261022-pictorial-intake-review-v7'
    elif data.get('version') == 'pictorial-intake-20261022-v6':
        folder_root = OUT.parent/'20261022-pictorial-intake-review-v6'
    elif data.get('version') == 'pictorial-intake-20261022-v5':
        folder_root = OUT.parent/'20261022-pictorial-intake-review-v5'
    elif data.get('version') == 'pictorial-intake-20261022-v4':
        folder_root = OUT.parent/'20261022-pictorial-intake-review-v4'
    elif data.get('version') == 'pictorial-intake-20261022-v3':
        folder_root = OUT.parent/'20261022-pictorial-intake-review-v3'
    elif data.get('version') == 'pictorial-intake-20261022-v2':
        folder_root = OUT.parent/'20261022-pictorial-intake-review-v2'
    elif data.get('version') != 'pictorial-intake-20261022-v1':
        raise ValueError('审核来源版本不匹配')
    report = read(folder_root/'拟物收入全量初稿.json')
    summary = validate(data, report)
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    digest = hashlib.sha256(payload).hexdigest()
    folder = output if output is not None else folder_root/'人工审核保存'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/f'网页审核原始结果-{digest}.json'
    try:
        with target.open('xb') as f:
            f.write(payload)
    except FileExistsError:
        if target.read_bytes() != payload:
            raise ValueError('既有审核快照校验不一致，停止保存')
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    return {'saved': True, 'path': str(target.resolve()), 'sha256': digest,
        'savedAt': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'summary': summary, 'snapshotOnly': True, 'allocationChanged': False, 'runtimeDeployed': False}
