"""Render the accepted attachment rule and explicitly staged geometry results."""
import base64
import json
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]


def build():
    manual=json.loads((PROJECT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8'))
    policy=manual['subjectAttachmentAcceptance20261025'];path=PROJECT/policy['proofReport']
    report=json.loads(path.read_text(encoding='utf-8'));out=path.parent
    data=dict(date=report['date'],attachmentDiagram='data:image/png;base64,'+base64.b64encode((out/'ộ主体与附件原墨迹.png').read_bytes()).decode(),policy=policy,repairs=report['repairs'],radial=report['radial'],attachment=report['attachment'],
        diagram='data:image/png;base64,'+base64.b64encode((out/'原图继承环与连接区候选.png').read_bytes()).decode())
    template=Path(__file__).with_name('subject_followup_template.html').read_text(encoding='utf-8')
    page=template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
    (out/'主体附件与连接区结果.html').write_text(page,encoding='utf-8')
    (PROJECT/'原型/键位编辑器/p-family-object-verification.html').write_text(page,encoding='utf-8')
    text='''# 主体附件绑定、切口和连接区处理

## 已接入的规则与查法

第二位选有证据的主体；第三位t/y分别选择该主体外的点块/线状构件；第四位只描述同一附件的位置、大小或已验证的同类附件组数量。折线也可为y，不把折线的两个线段误记成两个构件。a/b/g/j/q原整字集合不改，未将圆主体1曲直接写成ioqu。

本批仅ộ：iots=圆主体+下方外点；ioyw=圆主体+上方外部折线。仅增2条附件对象路径，原首选epki和全部旧码保留。主体对象圆bbox和两附件bbox来自原墨迹；九扰动位置均成立，第三第四位objectId相同。现行o键位浏览排除4/D/P已确认非圆主体；ộ从当前p形族浏览中退出、进入o。直接旧码仍可兼容查询，并明确标兼容，不改v14或部署。

## 局部计数处理

ρ：不再细化切断后的像素边界，继承原图去尾后的闭环骨架；九次均主体0角0叉0直1曲1孔，切口假支杈问题在此对象计数方法中消除。

ᛒ：短连接桥仅在两尺度真实墨迹四出口成立、闭环图秩保持时归入连接核心；九次均4角、0三叉、1四臂点、5直0曲、2孔。它是可复验的局部修正候选，尚未替换全局计数器或v5旧数据，也未新增b计数入口。

ȣ：同样的合并在加粗图成立、其它图不成立，九次计数不一致，因此候选被拒绝，原有1直3曲、2三叉、1孔和p候选保持。不能为了得到预想笔数而强并。

默认analyze(mask)行为保持；修正只能通过显式graph_transform进入。H/T/X/O/⊟共45个负对照观测均不变。

## 2/r与3/r

2/r选主体放射/星芒外形，3/r选同一局部交点至少五臂，显示名澄清为“局部放射交点（≥5臂）”。☆/★可有星形轮廓，但不自动有3/r。*的单中心qrr通常缺少额外区分，⁂多个交点的位置属性仍有用。

实查现行成员：2/r 3304、3/r 1315、交集764；这是入口重叠，不代表764字逐字几何已确认。保留两键和旧码，未批准批量删除r路径；后续可以降低无新增对象信息的重复路径推荐优先级。

本次结构计数v5仍1518字/122码/3230路径，另有2条主体附件路径；2,083字范围待核与历史84字缺口不变。未重建全码表、部署、改实体原码或推送。
'''
    (out/'主体附件与连接区处理结论.md').write_text(text,encoding='utf-8')
    print('subject followup page and conclusion rendered')


if __name__=='__main__':build()
