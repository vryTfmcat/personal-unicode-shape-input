"""Accept the reviewed 703 shape-only moves, keeping the refreshed feature model."""
import copy,json,re,shutil
from pathlib import Path
from datetime import datetime
from collections import Counter

PROJECT=Path(__file__).resolve().parents[1];LAB=PROJECT/'数据/三模式/规则库';ROOT=LAB/'人工核对'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)

def main():
    proposal=LAB/'邻域优化/运行/20261016-165346';ps=read(proposal/'摘要.json')
    if ps.get('acceptedRun'):print('Already accepted',ps['acceptedRun']);return
    source=Path(read(ROOT/'最新人工核对.json')['run']);assert Path(ps['source'])==source
    before=read(source/'全部收纳.json');after=read(proposal/'候选分组.json');changes=read(proposal/'迁移建议.json');confirmed={c['cp'] for c in changes}
    a={r['cp']:r for r in before['characters']};b={r['cp']:r for r in after['characters']}
    assert len(changes)==len(confirmed)==703 and a.keys()==b.keys()
    assert {cp for cp in a if a[cp]['primary']!=b[cp]['primary']}==confirmed
    assert all(a[cp]==b[cp] for cp in a if a[cp].get('shapeAssignmentLocked') or a[cp]['primary'] in ('x','y','z'))
    for cp in confirmed:b[cp].update(status='reviewed-shape-confirmed',shapeAssignmentLocked=True,reviewReason='用户接受本轮703项按图形迁移')
    run=ROOT/'运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    counts=Counter(r['primary'] for r in after['characters'] if r['primary']);assert all(500<=counts[k]<=2000 for k in 'abcdefghijklmnopqrstuvw')
    rules=read(source/'人工约束.json');assert 'wedgeFamily' not in rules and rules['shapePolicy']['oExclusive'] is False
    rules.update(date='2026-10-16',version='shape-only-wedge-703-confirmed-v1',source=str(source))
    rules['acceptedShapeRefinements']=rules.get('acceptedShapeRefinements',[])+[{'source':str(proposal),'count':703,'members':sorted(confirmed),'preserveOnOrdinaryRebuild':True}]
    save(run/'全部收纳.json',after);save(run/'人工约束.json',rules);save(run/'接受迁移记录.json',changes)
    save(run/'冻结分组.json',{'version':rules['version'],'capacity':{'plannedLower':500,'plannedUpper':2000},'characters':[r for r in after['characters'] if r['primary'] not in ('y','z')]})
    model=read(proposal/'候选模型.json');model['manualRules']=str(run/'人工约束.json');save(run/'模型.json',model)
    summary={'date':'2026-10-16','run':str(run),'source':str(source),'acceptedProposal':str(proposal),'primaryChanged':703,'scopeRecords':len(b),'counts':dict(counts),'assigned':sum(counts.values()),'pending':sum(not r['primary'] for r in after['characters']),'oPure':False,'wedgeConstraintActive':False,'effectiveCodebooksChanged':False,'rimePublished':False,'letters':'abcdefghijklmnopqrstuvwxyz','capacity':{'plannedLower':500,'plannedUpper':2000},'representatives':{k:[{'cp':r['cp'],'char':r['char']} for r in after['characters'] if r['primary']==k][:12] for k in 'abcdefghijklmnopqrstuvw'}}
    save(run/'摘要.json',summary)
    shutil.copytree(proposal/'全部字符预览',run/'全部字符预览')
    page=(proposal/'优化后全部桶预览.html').read_text(encoding='utf-8').replace('o取消专属限制后的图形优化草稿','当前图形分桶：703项迁移已接受').replace('尚未替换主分组','已设为当前主分组').replace('桶分类局部优化核对.html','迁移接受记录.html')
    (run/'全部桶预览.html').write_text(page,encoding='utf-8')
    record=(proposal/'桶分类局部优化核对.html').read_text(encoding='utf-8').replace('o取消专属限制后的图形优化草稿','已接受的703项图形迁移').replace('尚未替换主分组','已设为当前主分组').replace('优化后全部桶预览.html','全部桶预览.html')
    (run/'迁移接受记录.html').write_text(record,encoding='utf-8')
    # Retain the searchable inspector, with current assignments and matching native wedge glyphs.
    inspector=(source/'单层分桶核对.html').read_text(encoding='utf-8');m=re.search(r'const data=(.*?);const \$=',inspector,re.S);olddata=json.loads(m.group(1));extra={r['cp']:r for r in olddata['rows']};display=[]
    for r in after['characters']:d=dict(extra[r['cp']]);d.update(r);display.append(d)
    payload=json.dumps({'summary':summary,'rows':display},ensure_ascii=True,separators=(',',':'));inspector=inspector[:m.start(1)]+payload+inspector[m.end(1):]
    inspector=inspector.replace('当前桶分类：已接受262项迁移','当前桶分类：再接受703项图形迁移')
    native=re.search(r'@font-face\{font-family:WedgeReviewedNative;.*?\}',page,re.S).group(0)
    stack=re.search(r'\.chars\{font-family:(.*?);font-size:',page).group(1)
    inspector=inspector.replace('</style>',native+'.char.portable-fonts{font-family:WedgeReviewedNative,'+stack+'!important;}</style>',1)
    (run/'单层分桶核对.html').write_text(inspector,encoding='utf-8')
    (run/'约束与接受说明.md').write_text('本轮703项迁移已接受：702个楔笔字符移出o，✺从d进入o，o余614字。已接受的262项与x/y/z不变。楔笔标签不约束分桶。当前模型使用刷新后的1315字原生字形，其中196字新纳入特征缓存；小狼毫和正式码本未发布。\n',encoding='utf-8')
    fontdir=run/'字体全面检查-20261014';fontdir.mkdir();(fontdir/'全部桶字体核对.html').write_text(page.replace('迁移接受记录.html','../迁移接受记录.html'),encoding='utf-8')
    target=LAB/'首次优化/运行/20261012-171242/全部字符预览';backup=run/'更新前MD备份';backup.mkdir()
    for p in (run/'全部字符预览').glob('*.md'):
        if (target/p.name).exists():shutil.copy2(target/p.name,backup/p.name)
        shutil.copy2(p,target/p.name);assert p.read_bytes()==(target/p.name).read_bytes()
    save(target.parent/'预览来源.json',{'source':str(run),'updated':'2026-10-16','note':'已接受703项图形迁移，o不专属于楔笔族'})
    report={'ok':True,'identities':len(b),'acceptedMoves':703,'previous262Unchanged':True,'xyzUnchanged':True,'oExclusive':False,'oCount':counts['o'],'ordinaryMin':min(counts[k] for k in 'abcdefghijklmnopqrstuvw'),'ordinaryMax':max(counts[k] for k in 'abcdefghijklmnopqrstuvw'),'confirmedShapeAssignments':sum(bool(r.get('shapeAssignmentLocked')) for r in after['characters'])}
    save(run/'校验报告.json',report)
    for filename in ('最新人工核对.json','现行人工约束.json'):
        if (ROOT/filename).exists():shutil.copy2(ROOT/filename,run/('修改前-'+filename))
    save(ROOT/'现行人工约束.json',rules);save(ROOT/'最新人工核对.json',{'run':str(run),'source':str(source),'completed':True,'effectiveCodebooksChanged':False})
    ps.update(acceptedRun=str(run),acceptedDate='2026-10-16',applied=True);save(proposal/'摘要.json',ps)
    latest=read(LAB/'邻域优化/最新实验.json');latest.update(applied=True,acceptedRun=str(run));save(LAB/'邻域优化/最新实验.json',latest)
    print(json.dumps(dict(report,run=str(run)),ensure_ascii=False))

if __name__=='__main__':main()
