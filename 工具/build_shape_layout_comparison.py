"""Build a semantic layout proposal, never an executable allocation table."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/代表字实际查找测试'
OUT=PARENT/'布局对照草案'
ROUTES={
 'O':dict(family='圆／椭圆',a=['均衡比例','圆／椭圆','空心圆主体','尺寸档待定'],b=[['圆／椭圆','空心圆主体','大小','系列档待定']],note='不再在第四位重复“空心”。大小参照未定，不能先给O填c或其它尺寸字母。'),
 'Q':dict(family='圆／椭圆',a=['比例待定','圆／椭圆','尾笔','右下位置'],b=[['圆／椭圆','尾笔','位置','右下']],note='可另保留圆主体大小查法，和O共享入口是可接受的；尾笔路线承担进一步区分。'),
 'ρ':dict(family='圆／椭圆',a=['比例待定','圆／椭圆','连接尾笔','位置待核'],b=[['圆／椭圆','连接尾笔','位置','待核']],note='以已接受圆主体起手；尾笔属性仍须原墨迹对象核验，不把主体一曲当整字一曲。'),
 'ộ':dict(family='圆／椭圆',a=['主体比例','圆／椭圆','下方外点','位置'],b=[['圆／椭圆','外部点块','位置','下方'],['圆／椭圆','外部折线','位置','上方']],note='两条路线分别选定一个附件。折线两个线段不算两个附件，第二至第四位始终描述同一对象。'),
 'D':dict(family='孔线复合',a=['整字比例待定','孔线复合','整字直笔集','数量1'],b=[['孔线复合','整字直笔集','数量','1']],note='默认先看已接受的整字k形族；竖干/半弧可作补充查法，但不能偷偷把第一位改成局部竖干的比例。'),
 '8':dict(family='双环',a=['整字比例待定','双环','孔组','数量2'],b=[['双环','孔组','数量','2']],note='双环主体成立。与ᛒ在本路线相同，仍可能重码；不伪造新候选人数。'),
 'ᛒ':dict(family='双闭叶（本字接受）',a=['整字比例待定','双闭叶','孔组','数量2'],b=[['双闭叶','孔组','数量','2']],note='只使用本字已接受形态与两孔证据；不使用尚未全局接入的5直笔局部修正。双环/双闭叶能否用同键按既有b边界处理，字母仍待冲突检查。'),
 'ȣ':dict(family='回绕候选',a=['整字比例待定','回绕候选','闭孔','数量1'],b=[['回绕候选','闭孔','数量','1']],note='候选路径，不视为整字回绕对象已最终核准；被拒绝的连接区合并不用于草案。'),
 '𞥕':dict(family='回绕（本字接受）',a=['整字比例待定','回绕','整字直笔集','数量4'],b=[['回绕','整字直笔集','数量','4']],note='沿用已复验的整字4直笔证据，不按书写笔顺计数。'),
 '*':dict(family='放射／星芒',a=['整字比例待定','放射／星芒','中心交点','至少5臂'],b=[['放射／星芒','中心交点','臂数类别','至少5']],note='第四位提供臂数类别，不填“居中”占位；若该分支已限定≥5臂，再编码≥5也会重复，届时应允许前缀查询或改选其它有效属性。'),
 '☆':dict(family='放射／星芒',a=['整字比例待定','放射／星芒','空心星形轮廓','尺寸待定'],b=[['放射／星芒','空心星形轮廓','大小','系列档待定']],note='外轮廓星形不等于局部多臂交点。大小系列未核验；这里仅展示语义职责，不宣称新码可用。'),
 '⁂':dict(family='放射／星芒',a=['整字比例待定','放射／星芒','局部交点组','位置'],b=[['放射／星芒','局部上方交点','位置','上方'],['放射／星芒','整字交点组','数量','3']],note='单个交点与交点集合是不同对象。位置路线选一个点，数量路线选整组；不能在同一路径里换对象。'),
}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def api(s):
    with urlopen('http://127.0.0.1:8765/api/shape-overview/'+s,timeout=60) as r:return json.load(r)

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/'原型/键位编辑器/data/structure-count-bindings.json',ROOT/'数据/三模式/规则库/四键实验/人工审议.json',ROOT/'原型/键位编辑器/shape_overview.py',ROOT/'原型/键位编辑器/shape-key-overview.js']
    before={p.relative_to(ROOT).as_posix():digest(p) for p in protected}
    baseline=json.loads((PARENT/'代表字查找基线.json').read_text(encoding='utf-8'))
    boot=api('bootstrap');rows=[]
    for old in baseline['records']:
        ch=old['char'];d=api('detail?allocation=1&cp='+str(old['cp']))
        routes=[dict(code=p['code'],count=d['codeCounts'][p['code']],preferred=p.get('preferred',False),compatibility=p.get('compatibilityOnly',False),structural=p.get('structuralCollection',False),attachment=p.get('subjectAttachment',False)) for p in d['paths']]
        rows.append(dict(char=ch,cp=old['cp'],image=old['image'],current=routes,**ROUTES[ch]))
    data=dict(id='shape-layout-comparison-draft-20261025-v1',date=datetime.now().astimezone().isoformat(),
        status='AI语义布局草案，未确认字母、未生成或切换码表',baseline=boot['structureBindings']['version'],
        attachment=boot.get('subjectAttachments',{}).get('id'),rows=rows,
        candidateCountsAvailable=False,existingProtectedHashes=before,
        invariants=['t/b收入4362字保持','历史确认保持','旧查法/首选/实际部署保持','2083范围及历史84队列保持'],
        plans={
          'A':dict(name='保留比例起手，去掉粗形族乘积',slots=['整字或明确主体的长宽比','主体形族','特征对象与属性合并','属性值'],risk='变动较小，但仍须先判断比例；第三位继续混合对象和属性。'),
          'B':dict(name='主体形族直接起手（建议试验）',slots=['主体形族','特征对象','属性','属性值'],risk='消除起手比例判断，但需要重排字母及验证26键对象/属性容量；仅为完整布局的局部样本。')})
    assert len(rows)==12 and all(len(r['a'])==4 and all(len(x)==4 for x in r['b']) for r in rows)
    assert before=={p.relative_to(ROOT).as_posix():digest(p) for p in protected}
    (OUT/'布局对照草案.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    template=Path(__file__).with_name('shape_layout_comparison_template.html').read_text(encoding='utf-8')
    html=template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
    (OUT/'布局对照草案.html').write_text(html,encoding='utf-8')
    # Historical semantic redesign, superseded by the user's bucket-preserving direction.
    # Regeneration may reproduce its evidence, never replace the current public comparison.
    lines=['# 第一位重构：12字布局对照草案','',data['status'],'',
      '默认建议B：主体形族 → 特征对象 → 属性 → 属性值。A保留比例起手作为对照，不预设其被本人接受。',
      '字母尚未映射；中文四格是四位职责，不是新码。不能删掉旧第一位后把剩余三码拼接当作新四码。',
      '', '|字|现行部分查法及候选|B语义路径|主要限制|','|---|---|---|---|']
    for r in rows:
        old='；'.join(p['code']+' '+str(p['count']) for p in r['current'][:4])
        lines.append('|'+r['char']+'|'+old+'|'+'；'.join(' → '.join(x) for x in r['b'])+'|'+r['note']+'|')
    lines+=['','## 待解决的设计约束','',
      '- 第一位只选择主体形族，整条路径不因选尾笔/竖干改成局部形族；特征对象显式放第二位。主体不明确时先暂缓。',
      '- 第二位可选单个附件或有证据的同类对象组；第三和第四位必须描述同一对象。整字计数必须明写整字集合。',
      '- 同一分支若已限定空心，末位不再重复空心；若前缀仍同时包含空心/实心，填充属性仍可能有用，不全局删除。',
      '- 大小作为可选细分属性，不强迫所有字用大小；稳定参照是同形族/同填充的原字形系列，不能只按截图像素。O与Q可共享主体入口，尾笔路区分Q。',
      '- 四位是容量上限方向；不加无信息占位强凑四位，前缀可查询。是否允许正式短码与输入法选词结束规则须后续另验。',
      '- 旧第一位t/b保持。若最终进入同一模式，新三角/双环形族必须另配不冲突键；草案不占用t/b，也不改已收入4362字。独立预览不是完整冲突解决方案。',
      '- 必须检查全部26键、未知形族、多个可选主体、多部件、整字/局部对象、最多四位容量和真实候选规模；本批12字不能代表已完成全布局。',
      '', '## 下一步','',
      '先请本人比较A/B的起手习惯、圆主体和附件的四格职责、大小是否自然；答案默认空白，草稿只存浏览器。确认方向后才制定新字母表及少量离线候选索引，测覆盖/重码/旧确认/t-b碰撞，再决定是否推广。',
      '本轮不生成任何可执行新码、不修改人工审议或现行运行数据；范围2083/历史84保持。']
    (OUT/'布局对照草案.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(rows=len(rows),protectedUnchanged=True,newCodeTableGenerated=False),ensure_ascii=True))

if __name__=='__main__':build()
