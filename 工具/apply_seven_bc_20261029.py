"""Reproduce the approved four-character BC overlay; no bulk matrix migration."""
import sys,json,copy,hashlib,argparse
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
REL='数据/三模式/规则库/四键实验/键位试验/20261027-structure-count-bindings-v10/七组合接入-20261029'
OUT=ROOT/REL
FIELD='jointBCSevenAcceptance20261029Batch1'
RAW='已经审核这7个组合，都可以采用，比较自然容易记忆，可以进行推进旧码替换'
PLAN={56:(['eesw','eeci'],{'ebii':'eeci'}),7897:(['ifgb','ifmg'],{'iokg':'ifmg'}),272:(['inmt'],{'ikjt':'inmt','ikqt':'inmt'}),120123:(['iegt','iezv'],{'ikit':'iegt','ikiv':'iezv'})}
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    details=read(OUT/'接入前四字详情.json');briefs=read(OUT/'接入前全字.json')
    examples=read(ROOT/'数据/三模式/规则库/四键实验/键位试验/20261029-二三位联合设计/键义矩阵/代表字可输入候选与边界.json')
    descriptions={'eesw':('同一主体两孔中唯一较小孔','上','原9扰动面积/长边同序；仅此锁定字，未设通用可辨阈值'),
        'eeci':('主体全体共同圆弧类孔组','纵向','本人接受该字共同圆弧孔组；不将包围框当圆弧分类器'),
        'ifgb':('主体外全部分离附件组','两个','排除圆主体；两件外附件，不计全字墨块'),
        'ifmg':('全部外附件恰一点一折组','正置','类型由BC表达；g复用原组墨并集主轴，非成员中心排列'),
        'inmt':('整字直曲混合连续组总集合','三个','直2＋曲1；t数同集合3，不是手写3笔'),
        'iegt':('整字全部真实闭孔组','三个','锁定图三白区，独立于失败的骨架模型'),
        'iezv':('整字显式中央单孔','大','单孔长49/整字60；不依D重选孔')}
    records={};sources={}
    for cp,(codes,replacements) in PLAN.items():
        d=details[str(cp)];objects={o['id']:o for o in d['objects']};old={p['code']:p for p in d['paths']}
        assert set(replacements)<=set(old)
        assert not set(replacements)&set(briefs[str(cp)]['preferredCodes'])
        routes=[]
        for code in codes:
            ex=next(e for e in examples if e['canonical']==code)
            assert ex['cp']==cp
            oid=ex['selectedObjectIds'][0];assert oid in objects
            original=next((p for c,p in old.items() if replacements.get(c)==code),None)
            if original:assert all(e['objectId']==e['fourthObjectId']==oid for e in original['evidence'])
            members=ex['memberIds'];assert all(m in objects for m in members)
            co,dm,note=descriptions[code]
            parent='body:b:body' if cp==56 else 'reviewed-ộ-circle-subject' if cp==7897 else 'accepted-120123:k:body' if cp==120123 else 'whole-glyph'
            e=dict(rule='accepted.joint_BC.locked_single_character',objectId=oid,fourthObjectId=oid,
                familyTarget=parent,BC=code[1:3],BCMeaning=co,fixedDMeaning=dm,attribute=note,
                members=members,objectMode=objects[oid].get('objectMode',objects[oid].get('kind','whole-glyph-collection')),
                firstBucketReferenceObjectId=parent,status='human-accepted-single-character-combination',
                approvalScope='本字锁定对象与七条组合；非全库选择器完成')
            if code=='iezv':e.update(sizeReferenceObjectId=parent,referenceScope='whole-glyph',relativeSize=49/60)
            if code=='eesw':e.update(comparisonDomainIds=ex['comparisonDomainIds'],comparisonMetrics=['hole-area','hole-longest-side'],comparisonRuleScope='locked-nine-variant-order-only')
            if code=='ifmg':e['directionMode']='group-ink-principal-axis'
            if code=='eeci':e['directionMode']='member-centres'
            if code in ['ifgb','iegt','inmt']:e.update(quantityFeature={'ifgb':'externalMembers','iegt':'closedHoles','inmt':'totalContinuousGroups'}[code],count={'ifgb':2,'iegt':3,'inmt':3}[code])
            routes.append(dict(code=code,preferred=False,jointBC=True,semanticVersion='joint-bc-seven-20261029-v1',evidence=[e]))
        if cp==272:
            assert old['ikjt']['evidence'][0]['objectId']==old['ikqt']['evidence'][0]['objectId']
            obj=objects[routes[0]['evidence'][0]['objectId']]
            assert obj['count']==3 and obj['memberTypeCounts']=={'straight':2,'curve':1}
        preview=d['preview'];sheet=ROOT/'原型/键位编辑器'/preview['url'];sources[str(sheet.relative_to(ROOT))]=sha(sheet)
        records[str(cp)]=dict(cp=cp,char=chr(cp),beforeCodes=briefs[str(cp)]['codes'],preferredCodes=briefs[str(cp)]['preferredCodes'],
            newCodes=codes,retiredCanonicalCodes=list(replacements),replacements=replacements,
            afterCodes=sorted((set(briefs[str(cp)]['codes'])-set(replacements))|set(codes)),paths=routes,
            compatibilityPaths=[dict(copy.deepcopy(old[c]),compatibilityOnly=True,retiredCanonical=True,replacedBy=replacements[c],semanticVersion='before-joint-bc-seven-20261029') for c in replacements],
            objects=list(objects.values()),lockedGlyph=dict(source=sheet.relative_to(ROOT).as_posix(),sha256=sha(sheet),crop=[preview['x'],preview['y'],64,64]),
            familyAndBucketUnchanged=True)
    return dict(id='joint-bc-seven-20261029-v1',decision='accepted',date='2026-10-29',userResponseRaw=RAW,
        authorizationSource='总控二三位联合组合设计简报末节及本人七条明确批准；本专项唯一公共写入',
        approvedCodes=[c for cp,(cs,_) in PLAN.items() for c in cs],excludedUnapprovedCodes=['eecb','eehi','izec'],
        records=records,sourceHashes=sources,baselineDetails=REL+'/接入前四字详情.json',baselineDetailsSHA256=sha(OUT/'接入前四字详情.json'),
        oldRuntimeVersion='structure-count-bindings-v10',countSemanticsVersion='whole-continuous-total-v1',
        compatibilityPolicy='六条旧路退出本字规范推荐；仅compatibility=1精确四码可达，不反向注入默认查询/结构层',
        globalClassifierCompleted=False,firstAndFourthMeaningsUnchanged=True,preferredCodesChanged=False)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    candidate=build();path=ROOT/'数据/三模式/规则库/四键实验/人工审议.json';manual=read(path)
    if FIELD in manual:
        assert manual[FIELD]==candidate;print('已按冻结输入重现七组合确认，当前相同');return
    (OUT/'七组合接入候选.json').write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.apply:
        baseline=read(OUT/'接入前人工审议.json');assert manual==baseline,'人工审议有并发修改'
        expected=read(OUT/'修改前SHA.json')['数据/三模式/规则库/四键实验/人工审议.json'];assert sha(path)==expected
        manual[FIELD]=candidate;path.write_text(json.dumps(manual,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        assert all(read(path)[k]==v for k,v in baseline.items());print('仅追加七组合人工审议字段')
    else:print('已生成限定四字候选；未写人工审议')
if __name__=='__main__':main()
