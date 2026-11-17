"""Prepare scope triage and a small human review; never write active bindings."""
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
EDITOR = PROJECT / '原型/键位编辑器'
OUT = PROJECT / '数据/三模式/规则库/四键实验/键位试验/20261024-structure-count-bindings-v3'
REPORT = OUT / '大组结构键位分配.json'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    manual_path = PROJECT/'数据/三模式/规则库/四键实验/人工审议.json'
    if json.loads(manual_path.read_text(encoding='utf-8')).get('scopeBoundaryAcceptance20261024Batch1'):
        raise RuntimeError('首批7字已确认；v3待审材料保持冻结，禁止覆盖structure-scope-review.html确认结果。现行核验使用verify_shape_release.py。')
    protected = [REPORT, EDITOR/'data/structure-count-bindings.json',
                 PROJECT/'数据/三模式/规则库/四键实验/人工审议.json',
                 EDITOR/'data/pictorial-exclusive-allocation.json', PROJECT/'数据/三模式/全形核对版.json']
    before = {str(p.relative_to(PROJECT)): sha(p) for p in protected}
    d = json.loads(REPORT.read_text(encoding='utf-8'))
    rows = [r for r in d['records'] if r['eligible'] and not r['codes']]
    assert len(rows) == 2090
    by = {r['char']:r for r in d['records']}
    labels = {'local':'含局部／补充对象问题', 'proof':'含整体验证缺口', 'shape':'其余形族／对象边界问题'}
    triage=[]
    for r in rows:
        reasons=sorted({x for rej in r['scopeRejections'] for x in rej['reasons']})
        group=('local' if any('局部／补充' in x for x in reasons) else
               'proof' if any('验证' in x or '待核' in x for x in reasons) else 'shape')
        triage.append(dict(cp=r['cp'],char=r['char'],group=group,reasons=reasons,
                           oldCodes=r['oldCodes'],oldPreferredCodes=r['oldPreferredCodes']))
    questions=[
      dict(id='A',chars='4',title='4：整字交叉还是复合形？',
           fact='锁定原图有闭孔及伸出的交叉直笔。观测为1个交叉点、3条直连续笔；旧ch依据标为局部，不是整字证明。',
           question='您按整字查4时，更自然的是哪一种第二位形族？',
           recommendation='建议交叉x作为独立整字候选；含闭孔不自动排除交叉。原ch局部入口保留。仍须验证该整字路线后才生成新计数码。',
           options=['整字交叉x','整字复合形m','只保留现有局部查法，暂不新增','需要其它查法，回对话说明']),
      dict(id='B',chars='ft',title='f／t：曲笔与横笔相交能否走整字交叉？',
           fact='两字原图都有曲直相交；观测均为1个交叉点、1直连续笔及1曲连续笔。它们不符合ajqu整字单曲笔，这项既有排除不再审核。',
           question='是否接受两字各自增加整字交叉x查法？本题只审f和t。',
           recommendation='建议两字均走整字交叉x候选；曲笔不会使真实交叉消失。不能因此自动将旧ch局部路线升级。',
           options=['两字均接受整字交叉x','仅f接受整字交叉x','仅t接受整字交叉x','两字整字均按复合形m','暂不新增整字路线']),
      dict(id='C',chars='DQP',title='D／Q／P：圆形主体不等于整字都是圆',
           fact='D是直边加弧边的闭轮廓；Q有圆形主体和尾笔；P是竖笔与上部闭孔。旧D含竖脊／半弧局部入口，Q的io对象是圆环主体。整字计数不能直接套到这些局部对象。',
           question='第二位o继续限圆／椭圆整体，还是允许这些复合字形直接承接全字计数？',
           recommendation='建议o保持圆／椭圆边界：D、Q、P的整字复合形m另行验证；Q仍保留圆环主体查法。此方案不删除旧io入口，也不改变主体的旧属性。',
           options=['按建议：o保留圆义，三字整字复合m另验','允许Q按圆形族o承接全字计数，D/P另验','允许D/Q/P均按闭轮廓o承接全字计数','逐字另定，回对话说明']),
      dict(id='D',chars='ᶔ',title='ᶔ：原分叉形族与原图不一致',
           fact='本字U+1D94原图呈相连弯曲结构；九扰动观测0分叉、0交叉、2角、3曲连续笔。旧ch却有整体验证标记，这与本次观测冲突。',
           question='您按这个完整字形查找时，更自然的是复合形、波形还是钩弯？',
           recommendation='建议先按复合形m候选验证，保留旧ch查法；不要以旧verified标记直接派生整字分叉计数。波形w可由您判断是否更自然。',
           options=['整字复合形m','整字波形w','整字钩弯j','暂不新增，继续核查','其它，回对话说明'])]
    for q in questions:
        q['records']=[{k:by[ch][k] for k in ('cp','char','preview','statistics','oldCodes','oldPreferredCodes','wholeRouteFacts','scopeRejections')} for ch in q['chars']]
        assert all(by[ch]['eligible'] and not by[ch]['codes'] for ch in q['chars'])
    counts=Counter(r['group'] for r in triage)
    assert sum(counts.values())==2090 and len({r['cp'] for r in triage})==2090
    output=dict(createdAt=datetime.now().astimezone().isoformat(),sourceSHA256=sha(REPORT),
      status='proposal-only-awaiting-human-boundaries',counts=dict(counts),groupLabels=labels,
      grouping='按local、proof、shape优先分流，互斥且覆盖2090字；同一字可有其它交叉原因，分组不是最终分类结论。',
      humanQuestions=questions,humanSampleCharacters=7,autoAppliedChanges=0,records=triage,protectedHashes=before)
    (OUT/'整字范围待核分流.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    template=(Path(__file__).with_name('shape_scope_review_template.html')).read_text(encoding='utf-8')
    slim={k:output[k] for k in ('sourceSHA256','counts','groupLabels','grouping','humanQuestions')}
    manual=json.loads((PROJECT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    slim['acceptance']=manual.get('scopeBoundaryAcceptance20261024Batch1')
    page=template.replace('__DATA__',json.dumps(slim,ensure_ascii=False).replace('</','<\\/'))
    (EDITOR/'structure-scope-review.html').write_text(page,encoding='utf-8')
    lines=['# 整字范围首批人工边界审阅','','本轮只审4个问题、7字；原型页面： http://127.0.0.1:8765/structure-scope-review.html',
      '',output['grouping'],'',f'分流：{dict(counts)}。程序队列不要求逐字人工审。','',
      '以下均为AI建议，未形成新确认，未修改候选、原首选或第二位定义。回答仅适用于这些例字，不能自动外推到整批同类字符。']
    for q in questions:
        lines += ['',f"## {q['id']} · {q['title']}",'',q['fact'],'',q['question'],'',q['recommendation'],'']+[f"- {x}" for x in q['options']]
    lines+=['','原始字形：同目录整字范围首批原字形.png。完整旧码、观测与路线证据见分流JSON及网页。',
      '未选项保持待核；网页只保存本机草稿，复制答复发回当前对话后再写入既有人工审议。下一步先验证经确认的7字整字路线，再以差异实验决定具体新码。']
    (OUT/'人工边界首批审阅.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    assert before == {str(p.relative_to(PROJECT)):sha(p) for p in protected}
    print(json.dumps(dict(counts=counts,questions=len(questions),characters=7,activeChanges=0),ensure_ascii=False))


if __name__=='__main__':
    build()
