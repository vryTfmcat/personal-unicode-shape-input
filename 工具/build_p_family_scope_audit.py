"""Read-only evidence review of p86 and current scope queue; never assigns codes.

VISUAL_GROUPS is an AI image-by-image audit of the pinned 86 glyphs, not a
character classifier or a set of approved membership exceptions.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[1]
EDITOR = PROJECT / '原型/键位编辑器'
sys.path.insert(0, str(EDITOR))
import shape_structure_bindings as binding


# Numbers refer only to the ascending-codepoint sheet, whose identities are
# separately pinned below. Recommendations never enter effective_definitions.
VISUAL_GROUPS = [
    ('circle', '完整圆／椭圆主体加附笔',
     '可辨圆环主体；附笔使整字不等于单圆。建议优先核查o主体，不能直接把整字计数搬到主体；现图不足以支持p回环。',
     [3,5,6,7,9,11,19,22,23,24,28,35,40,48,49,51,56,57,58,67,73,78,79,82]),
    ('mixed', '单孔混合轮廓／孔线复合',
     '可见闭孔与直边、伸笔或弧边组成复合结构；建议核查k，局部有圆或孔不直接证明整字回环。既有其它查法保留。',
     [1,4,12,14,15,16,17,26,27,30,32,33,36,46,47,52,53,61,64,66,69,70,71,76,77,80,81,83,84]),
    ('triangle', '三角轮廓主体',
     '锁定图主体为倒三角闭轮廓，按已接受专门形族优先原则，建议t；不能因非圆且有孔继续证明p。', [8,50]),
    ('quad', '四边轮廓主体',
     '锁定图主体为四边闭轮廓并有延伸笔；建议核查s主体或k复合对象，当前p缺少回绕证据。', [37]),
    ('double', '两个可辨闭合叶／环',
     '可见两个闭合单元，但部分是角形叶或共享主干；b的环是否包括角形闭叶需人工判断，不能把两孔自动算双环。', [13,18,63,65,72]),
    ('open-top', '上部开口、下部闭环',
     '上方是开口弧／交叉曲笔，下方才是闭环；既不是两个完整闭环，也不能仅凭一个孔认定p。需判断是否具有整体回绕形态。', [2,41,68,86]),
    ('separated', '分离附加部件／多个独立对象',
     '原图有分离点、符号或相邻部件；即使局部有环，也不能不说明对象就用p承接全部整字计数。建议保留旧查法、分开整字与主体。', [20,34,38,39,42,43,44,45,59]),
    ('compound', '多孔或贯通结构，非明确双环',
     '可见横贯、栅格、交叠或闭孔复合；孔数不能代替环数。建议先核查k复合对象或其它整字形族，不据骨架有环直接保留p。', [21,25,29,31,54,55,60,62,75]),
    ('outline', '空心十字外轮廓',
     '看到的是空心十字的外轮廓和内部白区；轮廓闭合不等于书写轨迹回绕。需区分十字主体与孔轮廓对象。', [74]),
    ('turning', '折曲相接的回绕候选',
     '上部角形闭叶接下部开口曲尾，可看出转回形态；是否自然归p仍需本人判断，本轮不宣布通过。', [85]),
    ('curved-turning', '相连曲笔形成的回绕候选',
     '折曲相接形成上下闭合空间，具有回转候选形态；仍需区分回绕与孔线复合，先保留待核，本轮不宣布通过。', [10]),
]
PINNED_CPS = '105 223 24a 3b2 3c1 3d9 7d0 7dc 7e7 a13 c78 10a9 10f5 1586 1587 1588 1589 16d2 1d68 1ed9 222f 2374 2640 26b2 2904 2987 2988 29c3 2a16 2d12 a0b7 a1c9 a321 a396 a50c a527 a57c a5b5 a5b6 a7c1 a8d4 a9eb a9ed a9fb aa66 ab9e 100c9 102ad 10312 10360 10533 10537 10540 10630 10662 10671 10a64 10a84 10b99 10c05 10c16 10c8a 10c98 10c9a 10cd8 10cda 1115b 114d4 115a0 1168b 118e4 11d55 131f6 1455b 169da 16f38 16f9c 1d0bb 1d209 1d52e 1d690 1d780 1d7f0 1e879 1e955 1f718'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sheet(rows, path):
    image = Image.new('RGB', (1120, ((len(rows)+7)//8)*135), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 14)
    for i, r in enumerate(rows):
        p = r['preview']; x = i % 8*140; y = i//8*135
        with Image.open(EDITOR/p['url']) as source:
            glyph = source.crop((p['x'],p['y'],p['x']+64,p['y']+64)).convert('RGB')
        image.paste(glyph.resize((80,80)), (x+28,y+3))
        draw.text((x+4,y+88), f"{i+1}: U+{r['cp']:04X}", fill='black', font=font)
        draw.text((x+4,y+109), f"holes={r['statistics']['loops']}", fill='black', font=font)
    image.save(path)


def build():
    if binding.data().get('pFamilyBoundaryReview'):
        raise RuntimeError('本批已收到答复，86字材料为冻结审核前范围；使用apply_p_family_boundary_batch1.py重生成确认版，不覆盖原审核材料。')
    report_path = binding.active_report_path()
    out = report_path.parent
    protected = [binding.PATH, report_path, PROJECT/'数据/三模式/规则库/四键实验/人工审议.json',
                 EDITOR/'data/pictorial-exclusive-allocation.json', PROJECT/'数据/三模式/全形核对版.json',
                 EDITOR/'shape_structure_bindings.py', EDITOR/'shape_overview.py',
                 EDITOR/'shape-key-overview.js', EDITOR/'shape-key-overview.html']
    before = {str(p.relative_to(PROJECT)):sha(p) for p in protected}
    report = binding.review_report()
    policy = binding.closed_family_policy()
    assert policy['id'] == 'closed-family-policy-20261025'
    rows = sorted([r for r in report['records'] if any(c[1]=='p' for c in r['codes'])], key=lambda r:r['cp'])
    assert [r['cp'] for r in rows] == [int(cp,16) for cp in PINNED_CPS.split()]
    nums = [n for *_, indices in VISUAL_GROUPS for n in indices]
    assert sorted(nums) == list(range(1,87))
    exclusive = json.loads((EDITOR/'data/pictorial-exclusive-allocation.json').read_text(encoding='utf-8'))
    exclusive_cps = {r['cp'] for r in exclusive['allocations']}
    assert not exclusive_cps.intersection(r['cp'] for r in rows)
    groups = []
    for key,title,evidence,indices in VISUAL_GROUPS:
        records=[]
        for n in indices:
            row=rows[n-1]
            record={k:row[k] for k in ('cp','char','preview','codes','oldCodes','oldPreferredCodes','statistics','wholeRouteFacts','scopeRejections')}
            record.update(sheetNumber=n, visualGroup=key, imageObservation=evidence,
                          judgmentAuthor='AI locked-glyph visual audit', status='recommendation-only-not-applied',
                          pCodes=[c for c in row['codes'] if c[1]=='p'])
            records.append(record)
        groups.append(dict(key=key,title=title,evidence=evidence,count=len(records),records=records))
    bycp={r['cp']:r for g in groups for r in g['records']}
    specs=[
        ('P1','ρ','完整圆环加竖笔如何分对象？',
         'ρ有可辨完整圆主体和向下竖笔，接近已接受Q的主体／整字分工；没有明显回绕。',
         ['采用建议：圆主体用o，整字复合另核k；不再用p生成整字计数','仍保留p整字回环，请补充判据','逐字另定或暂缓']),
        ('P2','ȣ','上开下闭，是否算整体回绕？',
         'ȣ上部开口、下部闭环，锁定图仅1孔。不能当两个完整环；可能有整体回绕感，但此前闭孔筛选不能证明它。',
         ['采用建议：保留p候选，但另验整字回绕对象','更自然用k孔线复合，p不承接新整字计数','逐字另定或暂缓']),
        ('P3','ᛒ','两个三角闭叶是否属于b双环？',
         'ᛒ有两个角形闭叶，共享竖干；是两个孔，但不是圆形双环。一般规则未明确环能否含角形叶。',
         ['采用建议：两个可辨闭叶也可构成b主体，逐字另验','b只接受环状回转形，这字用k复合另核','这字保留p，需说明回绕判据','逐字另定或暂缓']),
        ('P4','ộ','主体加分离附标的计数范围',
         'ộ有圆主体、上方分离折形和下方分离点。现有ep代码却是整字集合计数；不能仅凭主体成环就证明整个字符属于p回环。',
         ['采用建议：o仅指圆主体；整字另核，不给p直接承接全字计数','保留p整字，需要明确附标也纳入对象','逐字另定或暂缓']),
        ('P5','𐘰𖧚','贯通造成的多孔是否优先视为复合？',
         '𐘰是竖干横栏形成两孔；𖧚是贯通笔与闭轮廓形成四孔。它们没有仅凭孔数即可证明的双环或回绕。',
         ['采用建议：两字核查k复合；不凭多孔保留p或自动入b','两字分别判断，回对话补充','保留p，需说明回绕判据','暂缓']),
        ('P6','𞥕','一个角形闭叶接开口曲尾，是否属于p？',
         '𞥕上方角形闭叶与下方开口曲尾相接，确有折曲转回形态。它是本批较需要主观取形判断的p候选。',
         ['采用建议：接受本字p回绕形态，计数仍另验','更自然用k孔线复合，p不承接新计数','逐字另定或暂缓']),
        ('P7','𔕛','空心十字的闭合轮廓如何处理？',
         '𔕛是空心十字，机器沿轮廓得到1孔和曲连续笔；这不等于字符书写主体在回绕，也不能把空心十字直接当线条相交模型。',
         ['采用建议：保留原查法，整字与轮廓对象拆开另核，暂不沿p扩展','按k混合闭轮廓另核','仍保留p整字，请补充判据','逐字另定或暂缓']),
    ]
    questions=[dict(id=i,chars=chars,title=title,evidence=evidence,options=opts,
                    records=[bycp[ord(ch)] for ch in chars]) for i,chars,title,evidence,opts in specs]
    scope_cps=set(binding.queues()['scopePending'])
    scope=sorted([r for r in report['records'] if r['cp'] in scope_cps],key=lambda r:r['cp'])
    assert len(scope)==2083 and not scope_cps.intersection(bycp)
    scope_records=[]
    for r in scope:
        reasons=sorted({reason for rejection in r['scopeRejections'] for reason in rejection['reasons']})
        group=('local' if any('局部／补充' in reason for reason in reasons) else
               'proof' if any('验证' in reason or '待核' in reason for reason in reasons) else 'shape')
        families=sorted({x['prefix'][1] for x in r['scopeRejections']})
        closed=bool(set(families).intersection('ostbp'))
        scope_records.append(dict(cp=r['cp'],char=r['char'],group=group,closedFamilyRelated=closed,
            closedHoles=r['statistics']['loops'],originalRejectedFamilies=families,reasons=reasons,
            nextAction=('先核查局部与整字对象，禁止借用全字计数' if group=='local' else
                        '补独立整体验证；旧verified与锁定图矛盾时保留原入口待核' if group=='proof' else
                        '按现行边界逐字确定形族与对象；有孔不自动入k'),
            preview=r['preview'],oldCodes=r['oldCodes'],oldPreferredCodes=r['oldPreferredCodes'],
            wholeRouteFacts=r['wholeRouteFacts'],status='triaged-still-pending'))
    pscope=[r for r in scope_records if 'p' in r['originalRejectedFamilies']]
    assert len(pscope)==6 and not exclusive_cps.intersection(scope_cps)
    p_pending_observations={
        0x1478:'锁定图为P状孔线主体加上方和左侧分离点；局部闭孔不证明整字回环。优先拆开附点与主体范围。',
        0x247D:'锁定图为(10)，括号、1和0是多个对象；0的圆环不能代表完整字符是p。原nrkh／spkh首选保留。',
        0xA549:'锁定图为圆环加竖笔、两侧四个分离点；建议分开圆主体与整字，不能因主体有孔升级p整字计数。',
        0x10B9C:'锁定图为四个分离圆环加中央点；四孔不是双环主体，也不是单一回绕对象，先核查多对象范围。',
        0x10C93:'锁定图为完整菱形轮廓；优先核查s四边主体。旧观测四角不足属于几何证据缺口，不应改用p绕过。',
        0x1D956:'锁定图为箭头加横栏竖笔，围出一个局部闭孔；有孔不能证明回绕，原局部路线不能升为整字p。',
    }
    assert set(p_pending_observations)=={r['cp'] for r in pscope}
    for r in pscope:
        r['visualObservation']=p_pending_observations[r['cp']]
        r['judgmentAuthor']='AI locked-glyph visual audit'
        r['nextAction']='按明确矛盾继续保留待核，不沿p扩展；'+r['nextAction']
    audit=dict(date='2026-10-25',version=report['version'],policyID=policy['id'],
        sourceSHA256=sha(report_path),status='AI-visual-audit-awaiting-human-representatives',
        counts=dict(pCharacters=86,pRoutes=sum(len(r['pCodes']) for r in bycp.values()),
                    visualGroups={g['key']:g['count'] for g in groups},humanQuestions=len(questions),
                    humanCharacters=sum(len(q['records']) for q in questions),membersChanged=0),
        limits='86字为AI逐字锁定原图核查，不是本人逐字确认。分组是建议，不是运行分类器。所有现有码和首选保留，未自动移入k/o/b。',
        groups=groups,questions=questions,protectedHashes=before)
    triage=dict(date='2026-10-25',version=report['version'],sourceSHA256=sha(report_path),
        counts=dict(total=len(scope),groups=dict(Counter(r['group'] for r in scope_records)),
                    closedFamilyRelated=sum(r['closedFamilyRelated'] for r in scope_records),
                    withClosedHoles=sum(r['closedHoles']>0 for r in scope_records),oldPRejected=6,resolved=0),
        grouping='local→proof→shape互斥覆盖全部2083字；闭合形族相关与有孔是交叉标签，不可相加。仅分流，未解决或移出队列。',
        pRelatedRecords=pscope,records=scope_records,protectedHashes=before)
    (out/'p族86字边界核查.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'范围待核2083字续查分流.json').write_text(json.dumps(triage,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sheet(rows,out/'p族86字锁定原图.png')
    sheet([r for r in scope if r['cp'] in p_pending_observations],out/'p相关待核6字锁定原图.png')
    lines=['# p族86字边界核查与2083字续查','',audit['limits'],'',
           '审阅页：http://127.0.0.1:8765/p-family-scope-review.html','',
           f"86字、{audit['counts']['pRoutes']}条p结构入口，7题8字。没有任何一字在本轮被自动确认为符合p或迁移到其它形族。",'']
    for g in groups:
        lines.extend(['## '+g['title']+f"（{g['count']}字）",'',g['evidence'],'',''.join(r['char'] for r in g['records']),''])
    lines+=['## 本人审核范围','', '只审核P1—P7所列8字；其它78字暂不自动外推。选项默认空白，答复回本对话后才进入既有人工审议。','']
    for q in questions:
        lines += [q['id']+' '+q['chars']+'：'+q['title'],q['evidence']]+['- '+x for x in q['options']]+['']
    lines+=['## 2083字已继续分流','',json.dumps(triage['counts'],ensure_ascii=False),triage['grouping'],
            '旧p待核6字：'+''.join(r['char'] for r in pscope)+'。均仍待核，未沿用“有孔即回环”放行。',
            '全量身份、旧入口／首选、原因与下一动作在同目录JSON；历史84字缺口不计入已解决。']
    (out/'p族86字核查与下一批范围.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    page=Path(__file__).with_name('p_family_scope_review_template.html').read_text(encoding='utf-8')
    payload=dict(audit=audit,scope={k:v for k,v in triage.items() if k not in ('records','protectedHashes')})
    (EDITOR/'p-family-scope-review.html').write_text(page.replace('__DATA__',json.dumps(payload,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
    assert before=={str(p.relative_to(PROJECT)):sha(p) for p in protected}
    receipt=dict(passed=True,identityCount=86,questions=7,humanCharacters=8,pRoutes=audit['counts']['pRoutes'],
        scopeCount=2083,scopeGroups=triage['counts']['groups'],protectedInputsUnchanged=True,tbOverlap=0,
        membersChanged=0,humanDecisionsWritten=0,historicalGapResolved=0)
    (out/'p族范围核查验收.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    build()
