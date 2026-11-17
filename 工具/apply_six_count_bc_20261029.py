"""Exact accepted six-character migration plus two negative BC boundaries."""
import sys,json,copy,hashlib,argparse
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
REL='数据/三模式/规则库/四键实验/键位试验/20261027-structure-count-bindings-v10/六字计数接入-20261029'
OUT=ROOT/REL
FIELD='jointCountSixAcceptance20261029Batch1'
BOUNDARY='jointBCNegativeBoundariesAcceptance20261029Batch1'
ID='joint-count-six-20261029-v1'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    source=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261029-二三位联合设计/后续计数迁移评估/首批六字精确迁移方案.json'
    plan=read(source);assert plan['mappedOldRelations']==13 and plan['newUniqueRelations']==11
    before=read(OUT/'接入前全字.json');details=read(OUT/'接入前八字详情.json');records={};hashes={}
    meaning={'na':'整字仅直连续组总集合','nc':'整字仅曲连续组总集合','nm':'整字直曲混合连续组总集合','qa':'整字角点集合','qb':'整字三叉点集合','qg':'整字四叉点集合'}
    dmeaning={'u':'一个','b':'两个','t':'三个','y':'四个','p':'五个及以上'}
    for cp in [79,68,84,69,936,55]:
        rows=[r for r in plan['routeLoads'] if r['cp']==cp];d=details[str(cp)];oldpaths={p['code']:p for p in d['paths']};objects={o['id']:o for o in d['objects']}
        replacements={r['old']:r['new'] for r in rows};assert set(replacements)<=set(oldpaths)
        assert not set(replacements)&set(before[str(cp)]['preferredCodes'])
        newpaths={}
        for r in rows:
            o=objects[r['objectId']];assert o['type']=='whole-glyph-collection' and o['count']==r['count']
            assert any(e['objectId']==e['fourthObjectId']==o['id'] for e in oldpaths[r['old']]['evidence'])
            e=dict(rule='accepted.joint_BC.certified_whole_collection',objectId=o['id'],fourthObjectId=o['id'],familyTarget='whole-glyph',BC=r['BC'],BCMeaning=meaning[r['BC']],
                fixedDMeaning=dmeaning[r['new'][3]],attribute=f"{meaning[r['BC']]}：数量{r['count']}；直{r['straight']}曲{r['curve']}是整字背景，不把点集成员当线件或手写笔画",
                feature=r['feature'],count=r['count'],quantityUnit={'corners':'几何角点','forks':'三叉交点','crosses':'四叉交点','totalContinuousGroups':'直曲连续组'}[r['feature']],
                memberTypeCounts={'straight':r['straight'],'curve':r['curve']} if r['feature']=='totalContinuousGroups' else None,variants=9,
                status='human-accepted-combination-reusing-certified-count',approvalScope='本六字组合及精确旧码替换；非全库分类器或逐字计数重验')
            newpaths[r['new']]=dict(code=r['new'],preferred=False,jointBC=True,structuralCollection=True,semanticVersion=ID,evidence=[e])
        preview=d['preview'];sheet=ROOT/'原型/键位编辑器'/preview['url'];hashes[sheet.relative_to(ROOT).as_posix()]=sha(sheet)
        records[str(cp)]=dict(cp=cp,char=chr(cp),bucket=before[str(cp)]['bucket'],familyKey=before[str(cp)]['familyKey'],beforeCodes=before[str(cp)]['codes'],preferredCodes=before[str(cp)]['preferredCodes'],
            afterCodes=sorted((set(before[str(cp)]['codes'])-set(replacements))|set(newpaths)),newCodes=sorted(newpaths),retiredCanonicalCodes=sorted(replacements),replacements=replacements,
            paths=list(newpaths.values()),compatibilityPaths=[dict(copy.deepcopy(oldpaths[c]),compatibilityOnly=True,retiredCanonical=True,replacedBy=replacements[c],semanticVersion='before-'+ID) for c in sorted(replacements)],
            objects=list(objects.values()),lockedGlyph=dict(source=sheet.relative_to(ROOT).as_posix(),sha256=sha(sheet),crop=[preview['x'],preview['y'],64,64]))
    assert sum(len(r['retiredCanonicalCodes']) for r in records.values())==13 and sum(len(r['newCodes']) for r in records.values())==11
    raw='可以采纳，目前看不出有什么问题，现有的规则限制还不明确（每个二三组合码虽然有具体含义但没有整体的对比，放在整个四万多个字符和676种组合中是否合适还不确定），可以先大规模的把字符分配一下进行测试后续再判断是否合适，有哪些问题需要修改'
    a=dict(id=ID,decision='accepted',date='2026-10-29',userResponseRaw=raw,authorizationSource='二三位联合组合设计简报：本人采纳六字与边界，转向大规模试分配；总控明确13旧关系→11新关系',
        records=records,sourceReport=source.relative_to(ROOT).as_posix(),sourceSHA256=sha(source),baselineDetails=REL+'/接入前八字详情.json',baselineDetailsSHA256=sha(OUT/'接入前八字详情.json'),
        sourceHashes=hashes,preferredChanged=False,AChanged=False,DMeaningChanged=False,globalClassifierCompleted=False,oldRuntime='joint-bc-seven-20261029-v1')
    bounds=[]
    for cp,bc,text in [(66,'ec','B的孔含直边/角形，不属于共同圆弧孔组'),(ord('ȱ'),'fm','ȱ为短横加点，短横不是折形，排除点折外附件组')]:
        d=details[str(cp)];p=d['preview'];sheet=ROOT/'原型/键位编辑器'/p['url']
        bounds.append(dict(cp=cp,char=chr(cp),BC=bc,decision='exclude',reason=text,lockedGlyph=dict(source=sheet.relative_to(ROOT).as_posix(),sha256=sha(sheet),crop=[p['x'],p['y'],64,64]),newCodes=[],positiveAlternativeNotInferred=True))
    boundary=dict(id='joint-bc-negative-boundaries-20261029-v1',decision='accepted',date='2026-10-29',userResponseRaw=raw,authorizationSource='总控确认承接上一轮B/ec与ȱ/fm两项审核边界',records=bounds,
        noNewFgForQDot=True,noRuntimeRouteChange=True,scope='锁定本字负例；不由排除自动推断其它正类')
    return a,boundary
def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args();a,b=build();path=ROOT/'数据/三模式/规则库/四键实验/人工审议.json';manual=read(path)
    if FIELD in manual:assert manual[FIELD]==a and manual[BOUNDARY]==b;print('六字及边界已从冻结来源重现');return
    (OUT/'接入候选.json').write_text(json.dumps({FIELD:a,BOUNDARY:b},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.apply:
        assert manual==read(OUT/'接入前人工审议.json');assert sha(path)==read(OUT/'修改前SHA.json')['数据/三模式/规则库/四键实验/人工审议.json']
        manual.update({FIELD:a,BOUNDARY:b});path.write_text(json.dumps(manual,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('仅追加六字及两边界确认字段')
    else:print('生成候选，未改运行确认')
if __name__=='__main__':main()
