"""Render all paths in a trial batch with each letter's position-specific meaning."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from audit_shape_rules import DATA, PROJECT

OUTPUT = PROJECT / '理论' / '批次逐码说明'
FIRST = {'o':'圆类轮廓', 'c':'曲弧', 'u':'直臂U形', 'j':'钩弯', 'p':'回环', 'a':'角折'}
SECOND = {'e':'空心', 'f':'实心', 'g':'开放', 'i':'内含构件', 'x':'穿出主体', 'p':'部分填充'}
TARGETS = {'arc-side':'弧身所在侧／凸出方向', 'opening-direction':'开口朝向',
           'primary-orientation':'所选主体的取向', 'primary-position':'所选主体的参考点位置',
           'corner-position':'整个角折的角点位置', 'overall-size':'整体尺寸',
           'component-size':'构件尺寸', 'region-position':'区域位置',
           'component-position':'构件位置', 'component-orientation':'构件朝向／排列方向'}


def annotated_paths(batch: dict) -> list[dict]:
    rules = batch.get('rules', batch)
    definitions = [batch.get('first', FIRST), batch.get('second', SECOND),
                   rules['third'], rules['fourth']]
    result = []
    for char in batch['characters']:
        if not char.get('primaryReference', True): continue
        code = char.get('proposedCode', char.get('code'))
        entries = char.get('codes', [{'code':code, 'basis':char.get('description', ''), 'fourthTarget':None}])
        for entry in entries:
            code = entry['code']
            if not isinstance(code, str) or len(code) != 4:
                raise ValueError('详注只接受已声明的四字母批次码')
            positions = []
            for position, (key, meanings) in enumerate(zip(code, definitions), 1):
                if key not in meanings: raise ValueError(f'{code} 第{position}位 {key} 缺少键义')
                positions.append({'position':position, 'letter':key, 'meaning':meanings[key]})
            target = entry.get('fourthTarget')
            label = TARGETS.get(target, '见取形依据；该旧批次尚未单独标记对象')
            if target in ('component-position', 'component-orientation', 'component-size'):
                label = rules['third'][code[2]] + '的' + {
                    'component-position':'位置', 'component-orientation':'朝向／排列方向',
                    'component-size':'尺寸'}[target]
            if entry.get('fourthReference'):
                label += '（参考：' + entry['fourthReference'] + '）'
            result.append({'char':char['char'], 'codepoint':char['codepoint'], 'code':code,
                           'positions':positions, 'fourthTarget':label,
                           'objects':{position:entry.get(field) for position,field in
                                      ((1,'firstObject'),(2,'secondObject'),(3,'thirdObject'))},
                           'basis':entry.get('basis') or char.get('description') or '见批次规则与参考字体',
                           'referenceFont':char.get('referenceFont', char.get('font', batch.get('reference', '见批次字体资料'))),
                           'status':entry.get('status', batch.get('status', 'trial'))})
    return result


def cell(text):
    return str(text).replace('|', '\\|').replace('\n', '<br>')


def render(batch: dict) -> str:
    paths = annotated_paths(batch)
    confirmed = batch.get('status') == 'approved-candidate'
    lines = ['# 批次逐码说明', '', f"状态：{'本批候选已核对' if confirmed else '本批候选待核对'}。共 {len({r['char'] for r in paths})} 字、{len(paths)} 条路径。",
             '', '每条码按四个位置分别读取。同字母跨位可以有不同含义；第四位的描述对象单独标注。'
             '多条路径都是检索入口，不把默认展示码当成唯一分配。', '',
             '此表解释批次规则，不表示小狼毫已启用正式四码查询。', '']
    for char in dict.fromkeys(r['char'] for r in paths):
        rows = [r for r in paths if r['char'] == char]
        lines += [f"## {char} · {rows[0]['codepoint']}", '', '参考字体：' + cell(rows[0]['referenceFont']), '',
                  '| 码 | 第一位·主形 | 第二位·状态 | 第三位·取形特点 | 第四位·补充 | 第四位描述对象 | 取形依据 |',
                  '|---|---|---|---|---|---|---|']
        for row in rows:
            parts = [f"`{p['letter']}`＝{cell(p['meaning'])}" +
                     ('<br>对象：'+cell(row['objects'][p['position']]) if row['objects'].get(p['position']) else '')
                     for p in row['positions']]
            lines.append('| `' + row['code'] + '` | ' + ' | '.join(parts) + ' | ' + cell(row['fourthTarget']) + ' | ' + cell(row['basis']) + ' |')
        lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=Path)
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    if args.all == bool(args.batch): parser.error('请选择 --all 或 --batch 路径之一')
    files = sorted(DATA.glob('全形*试验-*.json')) if args.all else [args.batch]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in files:
        batch = json.loads(path.read_text(encoding='utf-8'))
        number = re.search(r'-(\d+)\.json$', path.name)
        name = f'第{number.group(1)}批逐码说明.md' if number else path.stem+'逐码说明.md'
        target = OUTPUT/name
        target.write_text(render(batch), encoding='utf-8')
        print(str(target))


if __name__ == '__main__': main()
