"""Prepare closed-family policy questions; never apply proposals to active data."""
import hashlib
import json
import sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'原型/键位编辑器'))
import shape_structure_bindings as binding


def build():
    out=binding.active_report_path().parent
    manual=PROJECT/'数据/三模式/规则库/四键实验/人工审议.json'
    protected=[binding.PATH,binding.active_report_path(),manual,PROJECT/'原型/键位编辑器/data/pictorial-exclusive-allocation.json']
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes={str(p.relative_to(PROJECT)):digest(p) for p in protected}
    rows=json.loads((out/'闭合形族边界代表字.json').read_text(encoding='utf-8'))
    by={r['char']:r for r in rows}
    groups=[dict(key='o',label='圆／椭圆',chars='OQ',current='Q已确认按完整圆环主体保留o；主体计数与含尾笔的整字计数分开。',proposal='完整圆／椭圆主体优先o，不仅凭闭孔认定圆。'),
      dict(key='s',label='四边形',chars='□◇',current='当前第二位s。',proposal='四边形主体仍按s查，不因有孔批量加入k。'),
      dict(key='t',label='三角',chars='△',current='当前第二位t；4已确认是k。',proposal='按主体形态判断t；4内部孔近三角，不据此自动改成三角形族。'),
      dict(key='b',label='双环',chars='8∞',current='当前8、∞为b；旧p例字也列∞，两族存在重叠。',proposal='两个可辨环构成主体时优先b；任意两个孔不自动当双环。'),
      dict(key='p',label='不规则回环',chars='♧',current='当前♧为p；旧定义边界仍宽泛。',proposal='明确的回绕、结绕或多叶回环形态用p，不把所有非圆闭轮廓都叫回环。'),
      dict(key='k',label='有孔拓扑',chars='4DP',current='本批三字已确认进入k，未扩充其它成员。',proposal='建议k承接混合闭轮廓或有孔复合结构，与现有专门形族分工。'),
      dict(key='negative',label='有外轮廓但没有闭孔／开口',chars='●■▲CU',current='●／■／▲仍分别按圆／方／三角；C、U为开口形。',proposal='这些原字形没有可见闭孔，不符合k的有孔条件。形状轮廓与孔洞拓扑分开。')]
    for g in groups:g['records']=[by[c] for c in g['chars']]
    questions=[dict(id='K1',title='k是否作为所有非圆有孔字的并行入口？',
      issue='当前k的文字边界会同时覆盖□、△、8、∞、♧；是否让k承担这个宽泛查法，尚未确认。',
      recommendation='建议专门形族优先：o圆、s四边、t三角、b双环、p回环各自保留；k主要承接4／D／P这类混合闭轮廓或有孔复合结构。不会只凭有孔就批量给□／△／8／∞／♧新增k。这里按主体判断形族，不按任意孔或圆形构件判断：Q仍是圆主体，8仍是双环主体。此一般边界尚待本次审核。',
      options=['采用建议：专门形族优先，k限有孔复合／混合闭轮廓','k作所有非圆有孔字的并行入口，原形族也保留','暂不确定，补充具体边界']),
      dict(id='K2',title='b、p与k如何分工？',
      issue='旧例字把∞同时列入双环b和不规则回环p；如果p仍等于任意不规则闭合，D／P又会与k混在一起。',
      recommendation='建议b看两个可辨环组成的主体（8／∞）；p看回绕、结绕、多叶回环等明显形态（如♧）；k看混合闭轮廓或孔线复合（4／D／P）。多孔不直接等于多环。有独立证据的备选查法可并存，旧码不批量删除，首选不自动重排。',
      options=['采用建议：b双环、p回环形态、k有孔复合，允许可靠备选','b与p完全并列，不区分主要查法；k只作另一拓扑入口','暂不确定，补充具体分工'])]
    data=dict(reviewDate='2026-10-25',status='proposal-awaiting-human-review',activeVersion=binding.data()['version'],
      groups=groups,questions=questions,protectedHashes=hashes,
      note='只审核规则，不自动确认示例以外的字，不改现有成员或首选。讨论主要查法，不要求强制单一归类。')
    policy=binding.closed_family_policy()
    if policy:
        data['status']='accepted-policy-members-unchanged'
        data['acceptance']=policy
    stem='闭合形族边界确认' if policy else '闭合形族边界待审'
    (out/(stem+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page=Path(__file__).with_name('closed_family_boundary_review_template.html').read_text(encoding='utf-8')
    (PROJECT/'原型/键位编辑器/closed-family-boundary-review.html').write_text(page.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
    lines=['# k与闭合形族的边界'+('已确认' if policy else '待审'),'',data['note'],'',('K1、K2规则已接受；成员与首选未改变。' if policy else '本页为建议，未修改现行规则。')+'审核入口：http://127.0.0.1:8765/closed-family-boundary-review.html','']
    for q in questions:lines.extend(['## '+q['id']+' '+q['title'],'',q['issue'],'',q['recommendation'],'']+['- '+x for x in q['options']]+[''])
    (out/(stem+'.md')).write_text('\n'.join(lines),encoding='utf-8')
    assert hashes=={str(p.relative_to(PROJECT)):digest(p) for p in protected}
    print(json.dumps(dict(questions=2,glyphs=len(rows),activeChanges=0),ensure_ascii=False))


if __name__=='__main__':build()
