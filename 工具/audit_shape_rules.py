"""Audit every trial batch against previously recorded third/fourth key meanings."""
from __future__ import annotations
import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / '数据' / '三模式'
REPORT = PROJECT / '理论' / '全形后两位键义比对.md'

# These are broader/narrower concepts, not automatically equivalent functions.
RELATED = (
    ('orientation.axis_aligned', 'orientation.horizontal'),
    ('orientation.axis_aligned', 'orientation.vertical'),
    ('orientation.tilted', 'orientation.up_left'),
    ('orientation.tilted', 'orientation.up_right'),
    ('orientation.up_left', 'position.up_left'),
    ('orientation.up_right', 'position.up_right'),
)
RELATED_THIRD = (
    ('outline.half', 'fill.half'),
    ('outline.quarter', 'fill.quarter'),
    ('outline.gap', 'blank.quarter'),
    ('component.hook', 'component.corner'),
)


def audit(batches: list[tuple[str, dict]]) -> dict:
    bindings = []
    errors = []
    for source, batch in batches:
        rules = batch.get('rules', batch)
        functions = batch.get('functionIds', {})
        confirmed = batch.get('status') == 'approved-candidate' and not batch.get('layoutTrial')
        positions = [(p, field) for p, field in ((1, 'first'), (2, 'second'), (3, 'third'), (4, 'fourth'))
                     if p >= 3 or field in functions]
        for position, field in positions:
            meanings = rules.get(field, {})
            declared = functions.get(field, {})
            if not isinstance(meanings, dict) or not isinstance(declared, dict):
                errors.append({'type': 'invalid_rules', 'source': source, 'position': position})
                continue
            if set(meanings) != set(declared):
                errors.append({'type': 'missing_function_ids', 'source': source,
                               'position': position, 'keys': sorted(set(meanings) ^ set(declared))})
            for key, meaning in meanings.items():
                function = declared.get(key)
                if len(key) != 1 or key not in 'abcdefghijklmnopqrstuvwxyz' or not isinstance(meaning, str) or not isinstance(function, str) or not function.strip():
                    errors.append({'type': 'invalid_binding', 'source': source, 'position': position, 'key': key})
                    continue
                binding_confirmed = confirmed or (position == 4 and batch.get('layoutApproval', {}).get('status') == 'approved' and not batch.get('layoutTrial'))
                bindings.append({'position': position, 'key': key, 'function': function,
                                 'meaning': meaning, 'source': source, 'confirmed': binding_confirmed})
        for row in batch.get('characters', []):
            primary = row.get('proposedCode', row.get('code'))
            codes = [primary] if primary is not None else []
            if 'codes' in row:
                entries = row['codes']
                if not isinstance(entries, list) or not entries:
                    errors.append({'type': 'invalid_aliases', 'source': source, 'char': row.get('char')})
                    continue
                codes = []
                for entry in entries:
                    if not isinstance(entry, dict) or not isinstance(entry.get('basis'), str) or not entry['basis'].strip():
                        errors.append({'type': 'alias_without_basis', 'source': source, 'char': row.get('char')})
                    if isinstance(entry, dict):
                        codes.append(entry.get('code'))
                        target = entry.get('fourthTarget')
                        if not isinstance(target, str) or not target.strip():
                            errors.append({'type': 'alias_without_target', 'source': source, 'char': row.get('char')})
                        code = entry.get('code')
                        if isinstance(code, str) and len(code) == 4:
                            function = functions.get('fourth', {}).get(code[3], '')
                            size_target = target in ('overall-size', 'component-size')
                            if function and function.startswith('size.') != size_target:
                                errors.append({'type': 'alias_target_mismatch', 'source': source,
                                               'char': row.get('char'), 'code': code, 'target': target})
                valid_strings = [code for code in codes if isinstance(code, str)]
                if len(valid_strings) != len(set(valid_strings)):
                    errors.append({'type': 'duplicate_alias', 'source': source, 'char': row.get('char')})
                if primary is not None and primary not in codes:
                    errors.append({'type': 'primary_not_in_aliases', 'source': source, 'char': row.get('char')})
            for code in codes:
                if not isinstance(code, str) or len(code) != 4 or any(c not in 'abcdefghijklmnopqrstuvwxyz' for c in code):
                    errors.append({'type': 'invalid_code', 'source': source, 'char': row.get('char')})
                    continue
                for position, field in positions:
                    if code[position-1] not in rules.get(field, {}):
                        errors.append({'type': 'undeclared_code_key', 'source': source,
                                       'char': row.get('char'), 'code': code, 'position': position, 'key': code[position-1]})
    by_key, by_function = defaultdict(list), defaultdict(list)
    for row in bindings:
        by_key[row['position'], row['key']].append(row)
        by_function[row['position'], row['function']].append(row)
    for (position, key), rows in sorted(by_key.items()):
        if len({r['function'] for r in rows}) > 1:
            errors.append({'type': 'key_conflict', 'position': position, 'key': key,
                           'bindings': rows})
    for (position, function), rows in sorted(by_function.items()):
        if len({r['key'] for r in rows}) > 1:
            errors.append({'type': 'function_duplicate', 'position': position,
                           'function': function, 'bindings': rows})
    cross_position = []
    for key in sorted({r['key'] for r in bindings}):
        if (3, key) in by_key and (4, key) in by_key:
            cross_position.append({'key': key, 'third': by_key[3, key], 'fourth': by_key[4, key]})
    manual = []
    for position, pairs in ((3, RELATED_THIRD), (4, RELATED)):
        for first, second in pairs:
            if (position, first) in by_function and (position, second) in by_function:
                manual.append({'position': position, 'functions': [first, second],
                               'bindings': by_function[position, first] + by_function[position, second]})
    scope_review = [{'source': source, 'notes': batch['scopeReview']}
                    for source, batch in batches if batch.get('scopeReview')]
    return {'ok': not errors, 'errors': errors, 'bindings': bindings,
            'crossPositionReuse': cross_position, 'manualReview': manual,
            'scopeReview': scope_review}


def project_layout(batches: list[tuple[str, dict]], layout: dict) -> tuple[list, list]:
    """Preview a complete key permutation by function, without mutating batches."""
    reverse = {}
    for key, entry in layout['fourth'].items():
        function = entry['function']
        if len(key) != 1 or key not in 'abcdefghijklmnopqrstuvwxyz' or function in reverse:
            raise ValueError('布局必须一键一义，同一功能不能占用多个字母')
        reverse[function] = key
    projected = copy.deepcopy(batches)
    changes = []
    for (source, original), (_, batch) in zip(batches, projected):
        old_functions = original['functionIds']['fourth']
        mapping = {key: reverse.get(function, key) for key, function in old_functions.items()}
        if len(set(mapping.values())) != len(mapping):
            raise ValueError(f'{source}：布局与未迁移功能发生字母冲突')
        rules = batch.get('rules', batch)
        rules['fourth'] = {mapping[key]: meaning for key, meaning in rules['fourth'].items()}
        batch['functionIds']['fourth'] = {mapping[key]: function for key, function in old_functions.items()}
        batch['layoutTrial'] = True
        for row in batch.get('characters', []):
            field = 'proposedCode' if 'proposedCode' in row else 'code'
            targets = [(row, field)] if field in row else []
            targets += [(entry, 'code') for entry in row.get('codes', [])]
            seen = set()
            for target, key in targets:
                old = target[key]
                new = old[:3] + mapping[old[3]]
                target[key] = new
                if old != new and row.get('primaryReference', True) and (old, new) not in seen:
                    changes.append({'source': source, 'char': row.get('char'), 'before': old, 'after': new})
                seen.add((old, new))
    return projected, changes


def markdown(result: dict) -> str:
    has_prefix = any(row['position'] < 3 for row in result['bindings'])
    lines = ['# '+('全形四位键义比对' if has_prefix else '全形后两位键义比对'), '',
             '每个新批次先与全部已确认及试验键义比对。同一键位不允许一字母多功能，'
             '同一功能使用多个字母也会报错。第三、第四位之间的字母复用单独列出，'
             '不会自动改动已确认编码。', '',
             '功能 ID 是明确登记的概念；工具能检查已声明的功能重复，不能自动判断所有语义相似。'
             '新增功能仍需人工审查。', '',
             '已确认状态指用户接受的字母分配；比例／尺寸的数值阈值仍是测量试验依据。', '',
             '同一字符可有多个检索码；每个码必须注明取形依据。'
             '逐个检查所有备选码，不只检查展示码；同一字符同一码不重复登记。', '',
             f"检查结果：{'通过' if result['ok'] else '未通过'}；同位冲突／重复／格式问题 {len(result['errors'])} 项。", '']
    if result.get('layoutTrial'):
        lines += ['本报告是统一布局试验：原批次、有效字符编码及小狼毫词典未修改；'
                  '新的字母分配不自动继承历史确认状态。', '']
    if has_prefix:
        lines += ['本报告仅对声明了前两位功能ID的候选方案检查前两位。旧批次尚未登记前两位功能ID，'
                  '因此旧／新前缀差异须同时查阅影响报告，不能把本检查当成已完成旧表迁移。', '']
    for position in ((1, 2, 3, 4) if has_prefix else (3, 4)):
        lines += [f'## 第{position}位已占用键义', '', '| 字母 | 功能 | 状态 | 来源 |', '|---|---|---|---|']
        groups = defaultdict(list)
        for row in result['bindings']:
            if row['position'] == position: groups[row['key'], row['function']].append(row)
        for (key, function), rows in sorted(groups.items()):
            confirmed = any(r['confirmed'] for r in rows)
            meaning = next((r['meaning'] for r in rows if r['confirmed']), rows[0]['meaning'])
            if function.startswith(('size.', 'proportion.')):
                meaning = meaning.split('：', 1)[0]
            lines.append(f"| `{key}` | {meaning} | {'已确认' if confirmed else '试验'} | {'、'.join(sorted({r['source'] for r in rows}))} |")
        used = {key for key, _ in groups}
        lines += ['', '未占用：`' + ' '.join(c for c in 'abcdefghijklmnopqrstuvwxyz' if c not in used) + '`', '']
    lines += ['## 同位冲突和功能重复', '', '```json', json.dumps(result['errors'], ensure_ascii=False, indent=2), '```', '',
              '## 跨位字母复用提醒', '', '| 字母 | 第三位 | 第四位 |', '|---|---|---|']
    for item in result['crossPositionReuse']:
        lines.append('| `' + item['key'] + '` | ' + '／'.join(sorted({r['meaning'] for r in item['third']})) + ' | ' + '／'.join(sorted({r['meaning'] for r in item['fourth']})) + ' |')
    lines += ['', '## 相近功能的人工检查', '',
              '以下包含泛义与细义、位置与倾向的关系；不同功能 ID 不代表已经证明互不重叠。', '']
    for item in result['manualReview']:
        lines.append(f"- 第{item['position']}位：" + ' ↔ '.join(item['functions']) + '：' + '、'.join(sorted({r['key'] + '＝' + r['meaning'] for r in item['bindings']})))
    lines += ['', '## 新样本适用范围检查', '']
    for item in result.get('scopeReview', []):
        lines.append('- ' + item['source'] + '：' + '；'.join(item['notes']))
    lines += ['', '## 后续批次必做', '',
              '1. 在批次 JSON 中声明第三、第四位键义及 `functionIds`；同一概念沿用同一 ID。',
              '2. 运行本工具，冲突未解决时不提交候选批次；已确认键义优先保留。',
              '3. 用户看到新字符表时，同时列出本批沿用键、新增键、冲突检查结果及相近功能提醒。',
              '4. 功能优先级、比对对象和省略的信息仍需明确说明，不能仅以无字母冲突为通过依据。', '']
    lines += ['5. 每次出稿逐码标注四位字母及含义、第四位描述对象、取形依据；'
              '运行 `python 工具/render_shape_batch.py --batch 批次.json` 生成详表，不能只给裸码。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, help='Additional future batch to compare before recording it')
    parser.add_argument('--layout', type=Path, help='Preview a fourth-position layout without changing recorded batches')
    parser.add_argument('--report', type=Path, help='Write a separate proposal report, preserving the current report')
    args = parser.parse_args()
    paths = sorted(DATA.glob('全形*试验-*.json'))
    if args.candidate and args.candidate.resolve() not in {p.resolve() for p in paths}:
        paths.append(args.candidate)
    batches = [(p.name, json.loads(p.read_text(encoding='utf-8'))) for p in paths]
    changes = []
    if args.layout:
        batches, changes = project_layout(batches, json.loads(args.layout.read_text(encoding='utf-8')))
    result = audit(batches)
    result.update(layoutTrial=bool(args.layout), codeChanges=changes)
    report = args.report or (REPORT if not args.layout else REPORT.with_name('全形后两位键义比对-游戏布局试验.md'))
    data_report = DATA / (report.stem+'.json' if args.report else ('全形键义比对-游戏布局试验.json' if args.layout else '全形键义比对.json'))
    report.write_text(markdown(result), encoding='utf-8')
    data_report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'ok': result['ok'], 'issues': len(result['errors']),
                      'crossPositionReuse': len(result['crossPositionReuse']),
                      'manualReview': len(result['manualReview']), 'changedCharacters': len(changes),
                      'report': str(report)}, ensure_ascii=False))
    if not result['ok']: raise SystemExit(1)


if __name__ == '__main__': main()
