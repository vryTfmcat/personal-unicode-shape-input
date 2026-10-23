"""Generate a readable review of trial generalization without changing routes."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from shape_experiment_features import render, bounds
from shape_keyboard_trial import load
from build_shape_keyboard_full import save


CONFIRMED = set('◯○o◦⬤●•∙□◻◽▫■◼◾▪☆★∥=∴∵𐎊𝍫﹦𝌆BI4∞8')
FAMILY = {'l': '线条', 'o': '圆形', 's': '四边形', 'b': '双环',
          'h': '分叉', 'a': '角折', 'm': '复合', 'd': '点群',
          'u': '其他既有形族', 'c': '开放弧', 'r': '星芒', None: '未绑定'}


def build(run, note):
    index = load(run / '发布核对索引.json')
    FAMILY.update({k: v['meaning'] for k, v in index['definitions']['families'].items()})
    changes = load(run / '补充入口与排除清单.json')
    primary = load(run / '主族修正提案.json')
    rows = {r['cp']: r for r in index['records']}
    details = {}
    for shard in sorted((run / 'details').glob('*.json')):
        for r in load(shard)['records']:
            details[r['cp']] = r
    assert set(rows) == set(details)
    categories = [
        ('A', '细长不等于直线', '单长直线', '（[⌠⎧⏠⁀┃ㄧ',
         '程序先收紧', '细长和各向异性不能证明直线。括号、弧段、带钩笔画应先排除整字直线入口；真正长直线可保留。无需逐字决定机器阈值。'),
        ('B', '平行线组与复合主体', '平行线组', '☷≣〓ᚓᚔ𐏒𐎐🬰',
         '需要判断边界', '单独多条平行线可查线组；带连接主干、楔形或其他结构时，宜保留复合主入口，只把线组作为补充。看图判断哪些仍自然。'),
        ('C', '圆轮廓推广', '圆轮廓明确', '⚫🔴🌑⯃𖧹',
         '需要判断边界', '外轮廓近圆可有圆入口；但月面、内部图案及彩色图标不等于纯实心圆。此处分别判断圆入口和实心属性，不把二者一起确认。'),
        ('D', '点块与小方形双入口', '小方轮廓', '',
         '需要判断入口', '只问完整可见小方块能否同时作为点块和方形检索；不把局部方形块自动当作整字。已确认的▪／◾不重复提问。'),
        ('E', '双环范围明显偏宽', '沿用双环', '🕶🛩⥈⧟༔៖ⴻɃ',
         '程序先收紧', '双环新增入口共有大量复杂字形。两个检测孔洞只是必要线索，不足以决定双环：先限制为两个主导闭合环，排除偶然孔洞、附属孔洞和带大量结构的整字。眼镜或两环连杆等自然补充入口可单独保留讨论。'),
        ('F', '4字形原型推广', '已核对角折', '４',
         '对照观察', '全角４沿用4的角折／分叉取形，不再从四边形查找；这里只展示新增推广样本，不重复确认4。'),
    ]
    groups = []
    inventory = []
    for key, title, needle, hints, action, question in categories:
        population = [r for r in changes if any(needle in b for b in r['basis'])]
        pool = {r['cp']: r for r in population if r['char'] not in CONFIRMED}
        selected = []
        for char in hints:
            if ord(char) in pool and ord(char) not in selected:
                selected.append(ord(char))
        for cp in sorted(pool, key=lambda cp: (not pool[cp]['oldReviewed'], cp)):
            if len(selected) >= 8:
                break
            if cp not in selected:
                selected.append(cp)
        groups.append(dict(id=key, title=title, count=len(population), action=action,
                           question=question, selected=selected, type='routes'))
        for r in population:
            inventory.append(dict(group=key, **r))

    def matching(kind):
        out = []
        for cp, r in details.items():
            objects = {o['id']: o for o in r['objects']}
            found = []
            for p in r['paths']:
                code = p['code']
                if len(code) != 4:
                    continue
                for e in p['evidence']:
                    o = objects[e['objectId']]
                    if ((kind == 'fill' and code[-1] in 'ef' and o['kind'] == 'body') or
                        (kind == 'size' and code[1] in 'os' and code[-1] in 'vczx' and o['kind'] == 'body') or
                        (kind == 'group' and o['kind'] == 'part-group' and code[-1] in 'bthiws')):
                        found.append(code)
            if found:
                out.append({'cp': cp, 'char': r['char'], 'codes': sorted(set(found))})
        return out

    for key, title, kind, hints, question in [
        ('G', '空心与实心的推广对象', 'fill', '⊙⊕⊗◉◎◍◐◑▣▤▥', '有内部线条、阴影或孔洞时不能仅按外轮廓判实心。只判断整体主体的空心／实心入口，不判断颜色。'),
        ('H', '圆方大小分档推广', 'size', 'Ｏｏ０0O◉◎▣▢▤▥', '参考系列已确认；这里检查其他圆方字形是否有自然的整体尺寸查法。大小按锁定字体与字号测量，不按Unicode名称，也不把内部孔洞大小当整体大小。'),
        ('J', '组数量与排列推广', 'group', '≡☰☱☷∷⁙⁝⋮⋯', '成员数量和成员中心排列是组属性，不改原单线方向。分散点、短划与带连接主干的字形要分开判断。')]:
        population = matching(kind)
        pool = {r['cp']: r for r in population if r['char'] not in CONFIRMED}
        selected = [ord(c) for c in hints if ord(c) in pool][:8]
        for cp in sorted(pool):
            if len(selected) >= 8:
                break
            if cp not in selected:
                selected.append(cp)
        groups.append(dict(id=key, title=title, count=len(population), action='需要判断对象／入口',
                           question=question, selected=selected, type=kind))
        inventory.extend(dict(group=key, **r) for r in population)

    assets = note.parent / '全形推广核对图-2026-10-21'
    assets.mkdir(exist_ok=True)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 18)
    selected_records = []
    for g in groups:
        image = Image.new('RGB', (1040, 320), 'white')
        draw = ImageDraw.Draw(image)
        for i, cp in enumerate(g['selected']):
            r = details[cp]
            source = r['font']
            mask, _ = render(chr(cp), source['path'], source.get('index', 0))
            x0, y0, x1, y1 = bounds(mask)
            crop = mask[y0:y1, x0:x1]
            ratio = min(90 / crop.shape[0], 180 / crop.shape[1])
            glyph = Image.fromarray(255 - crop.astype('uint8') * 255).resize(
                (max(1, round(crop.shape[1] * ratio)), max(1, round(crop.shape[0] * ratio))), Image.Resampling.NEAREST)
            x, y = i % 4 * 260, i // 4 * 160
            identity = f"{g['id']}{i + 1}"
            draw.text((x + 12, y + 8), f'{identity} U+{cp:04X}', font=font, fill='black')
            image.paste(glyph, (x + 12, y + 45))
            selected_records.append({'id': identity, 'cp': cp, 'font': source, 'group': g['id']})
        image.save(assets / f"{g['id']}.png")
        if g['id'] == 'H':
            actual = Image.new('RGB', (1040, 320), 'white')
            pen = ImageDraw.Draw(actual)
            for i, cp in enumerate(g['selected']):
                source = details[cp]['font']
                mask, extent = render(chr(cp), source['path'], source.get('index', 0))
                x0, y0, x1, y1 = bounds(mask)
                crop = mask[y0:y1, x0:x1]
                scale = extent * 96 / max(crop.shape)
                glyph = Image.fromarray(255 - crop.astype('uint8') * 255).resize(
                    (max(1, round(crop.shape[1] * scale)), max(1, round(crop.shape[0] * scale))), Image.Resampling.NEAREST)
                x, y = i % 4 * 260, i // 4 * 160
                pen.text((x + 12, y + 8), f'H{i + 1} U+{cp:04X}', font=font, fill='black')
                actual.paste(glyph, (x + 12, y + 45))
            actual.save(assets / 'H-size.png')

    text = ['---', 'title: 全形规则推广核对稿', 'date: 2026-10-21',
            'status: 机器推广待审，未修改现行发布', 'tags: [Unicode, 全形, 核对]', '---',
            '', '# 全形规则推广核对稿', '',
            '依据[[全形键位集中核对稿-2026-10-19#2026-10-21续：已确认入口落实与全量校验]]及独立运行`20261021-reviewed-entries-v2`生成。本文是AI整理的机器推广核对材料，不是用户确认结果。已确认样本只作依据，不重复列入待答。', '',
            '## 先看结论', '',
            '- 程序需先收紧两处：细长笔画不能直接等同直线；检测出两个孔洞不能直接等同自然双环。当前数据仍保留原机器结果供核对，本次没有改规则或重算发布。',
            '- 优先看B、C、D组的入口边界；G、H、J组只需判断所指对象和查法是否自然。A、E组的明显误收由程序处理，不要求逐字批准。',
            '- 每个编号可写“自然／不自然／保留原主入口，仅补充／看不清／暂不决定”，空白不视为同意。',
            '- 图像使用数据原记录的锁定字体，统一黑色墨迹并放大比较形状；归一化图的大小不能用来决定尺寸档位。H组另有同字号图。表内“整体／内部目标”区分取形对象，不能把内部构件尺寸读成整字尺寸。', '',
            '## 显示颜色说明', '',
            '截图中其他实心符号随深色界面显示为白色，而◾仍深色，最可能是它采用了emoji／符号字体回退，未跟随正文颜色。未读取实际渲染字体，故不把具体字体原因写成已核实事实。前次仅解释实心含义，没有解释这个显示差异，现作更正。', '',
            'Unicode允许用U+FE0E请求文本样式，例如“◾︎”（U+25FE U+FE0E）；实际支持由软件和字体决定。这里只给显示示例，不把选择符加入单字符码本。核对图统一用原锁定字体黑白栅格，避免颜色干扰。依据：[Unicode Emoji FAQ](https://unicode.org/faq/emoji_dingbats.html)。', '',
            '## 全量范围', '',
            f'形族入口增删涉及{len(changes):,}个不同字符，主族变化提案{len(primary):,}个；六类规则统计可能交叉，不应相加当作字符总数。全量清单保存在工程运行内`规则推广核对清单.json`，本文抽取代表及风险样本。属性组G／H／J统计本版所有命中的字符（含内部目标），不全是相对基线新增。', '',
            '| 组 | 规则／属性 | 命中字符 | 本文样本 |', '| --- | --- | ---: | ---: |']
    for g in groups:
        text.append(f"| {g['id']} | {g['title']} | {g['count']:,} | {len(g['selected'])} |")
    for g in groups:
        text += ['', f"## {g['id']} {g['title']}", '', f"处理方式：**{g['action']}**。{g['question']}", '',
                 f"![[全形推广核对图-2026-10-21/{g['id']}.png]]", '']
        if g['id'] == 'H':
            text += ['下图才是统一96字号的实际相对大小；上图仅看形状。中、小等属性还需按表内所指整体或内部构件分别理解。', '',
                     '![[全形推广核对图-2026-10-21/H-size.png]]', '']
        text += [
                 '| 编号 | 字符／码位 | 当前机器入口或属性 | 提醒 | 我的判断 |', '| --- | --- | --- | --- | --- |']
        for i, cp in enumerate(g['selected']):
            r = details[cp]
            amendment = next((a for a in changes if a['cp'] == cp), None)
            before = FAMILY.get(r.get('baselineFamilyKey'), r.get('baselineFamilyKey'))
            after = FAMILY.get(r['familyKey'], r['familyKey'])
            if g['type'] == 'routes':
                added = '、'.join(FAMILY.get(f, f) for f, _ in amendment['added']) or '无'
                removed = '、'.join(FAMILY.get(f, f) for f, _ in amendment['removed']) or '无'
                desc = f'新增{added}；排除{removed}；主族{before}→{after}'
            else:
                objects = {o['id']: o for o in r['objects']}
                codes = []
                for p in r['paths']:
                    c = p['code']
                    if len(c) != 4:
                        continue
                    for e in p['evidence']:
                        o = objects[e['objectId']]
                        target = '整体' if e.get('familyTarget') == 'body' else '内部目标' + str(e.get('familyTarget', ''))
                        if g['type'] == 'fill' and c[-1] in 'ef' and o['kind'] == 'body':
                            codes.append(c + ('空心' if c[-1] == 'e' else '实心') + '〔' + target + '〕')
                        elif g['type'] == 'size' and c[1] in 'os' and c[-1] in 'vczx' and o['kind'] == 'body':
                            codes.append(c + {'v': '大', 'c': '中', 'x': '小', 'z': '极小'}[c[-1]] + f"〔{target}, em={o.get('extentEm', 0):.3f}〕")
                        elif g['type'] == 'group' and o['kind'] == 'part-group' and c[-1] in 'bthiws':
                            codes.append(c + {'b': '两个', 't': '三个', 'h': '左右排列', 'i': '上下排列', 'w': '尖端向上', 's': '尖端向下'}[c[-1]])
                desc = '、'.join(sorted(set(codes)))
            warn = '涉及旧确认；本版改变不等于迁移已获批准' if r.get('oldReviewed') else '机器候选，未人工确认'
            glyph = chr(cp).replace('|', '&#124;')
            text.append(f"| {g['id']}{i + 1} | {glyph} U+{cp:04X} | {desc} | {warn} |  |")
    old_changes = [r for r in primary if r['oldReviewed']]
    text += ['', '## 旧确认保护与后续处理', '',
             f'本版主族提案中有{len(old_changes)}项涉及旧确认字符，列在下表。历史确认文件没有改变；独立候选改变仍需审核。', '',
             '| 字符／码位 | 主族提案 | 我的判断 |', '| --- | --- | --- |']
    for r in old_changes:
        text.append(f"| {r['char']} U+{r['cp']:04X} | {FAMILY.get(r['beforeFamily'], r['beforeFamily'])}→{FAMILY.get(r['afterFamily'], r['afterFamily'])} |  |")
    text += ['', '程序下一步应先收紧A、E两类，再生成前后差异；B等边界按用户判断处理。没有确认前不删除原入口、不切换编辑器、不部署小狼毫。', '',
             '本稿及核对清单不构成规则确认来源；用户填写后的判断需回写既有`人工审议.json`，避免形成第二套权威决定。', '']
    note.write_text('\n'.join(text), encoding='utf-8')
    save(run / '规则推广核对清单.json', {'experimentId': index['id'], 'status': 'machine-review-not-approved',
         'groups': groups, 'uniqueRouteChangeCharacters': len(changes), 'primaryChanges': primary,
         'routeChanges': changes, 'inventory': inventory, 'renderedSamples': selected_records})
    assert len(selected_records) == sum(len(g['selected']) for g in groups)
    assert all(chr(r['cp']) not in CONFIRMED for r in selected_records)
    assert all((assets / f"{g['id']}.png").exists() for g in groups)
    print(json.dumps({'groups': [(g['id'], g['count'], len(g['selected'])) for g in groups],
                      'samples': len(selected_records), 'primaryChanges': len(primary),
                      'oldReviewedPrimaryChanges': len(old_changes), 'note': str(note)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--note', type=Path, required=True)
    args = parser.parse_args()
    build(args.run, args.note)
