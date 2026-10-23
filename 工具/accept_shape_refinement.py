"""Apply the user-approved 262 changes and retire the wedge-only bucket constraint."""
import copy,gzip,json,re,shutil
from pathlib import Path
from datetime import datetime
from collections import Counter
import numpy as np

PROJECT=Path(__file__).resolve().parents[1]
LAB=PROJECT/'数据/三模式/规则库';ROOT=LAB/'人工核对';ACTIVE='abcdefghijklmnopqrstuvw'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)

def main():
    source=Path(read(ROOT/'最新人工核对.json')['run'])
    proposal=LAB/'邻域优化/运行/20261015-140139'
    if read(proposal/'摘要.json').get('acceptedRun'):
        print('Already applied',read(proposal/'摘要.json')['acceptedRun']);return
    assert Path(read(proposal/'摘要.json')['source'])==source,'主分组已变化，必须重新核对建议'
    old=read(source/'全部收纳.json');current=read(proposal/'候选分组.json');a={r['cp']:r for r in old['characters']};b={r['cp']:r for r in current['characters']}
    changes=read(proposal/'迁移建议.json');accepted={c['cp'] for c in changes}
    assert len(accepted)==len(changes)==262 and a.keys()==b.keys()
    assert {cp for cp in a if a[cp]['primary']!=b[cp]['primary']}==accepted
    for c in changes:assert a[c['cp']]['primary']==c['before'] and b[c['cp']]['primary']==c['after']
    rules=read(source/'人工约束.json');wedge=rules.pop('wedgeFamily');wedges=set(wedge['members'])
    run=ROOT/'运行'/datetime.now().strftime('%Y%m%d-%H%M%S');run.mkdir(parents=True)
    for r in current['characters']:
        cp=r['cp']
        if cp in accepted:r.update(status='reviewed-neighbor-confirmed',shapeAssignmentLocked=True,reviewReason='用户于2026-10-16接受262项近邻迁移建议')
        if cp in wedges:
            r['tags']=list(dict.fromkeys(r.get('tags',[])+['wedge-strokes']))
            r.update(status='optimized-draft-frozen' if a[cp]['status']=='reviewed-wedge-family' else 'pending-shape-features-unlocked',shapeAssignmentLocked=False,
                reviewReason='楔笔专桶硬约束已取消；当前归属暂保留，后续仅按图形参与优化')
    rules.update(version='shape-only-wedge-unlocked-v1',date='2026-10-16',source=str(source),
        ordinaryBuckets=list(ACTIVE),wedgeTag={'members':sorted(wedges),'tag':'wedge-strokes','blocks':wedge['blocks'],'affectsAssignment':False},
        shapePolicy={'oExclusive':False,'wedgeMustCoLocate':False,'crossScriptGrouping':True,'groupBy':'轮廓、比例、结构、部件布局与疏密'},
        acceptedRefinement={'source':str(proposal),'count':262,'members':sorted(accepted),'preserveOnOrdinaryRebuild':True})
    counts=Counter(r['primary'] for r in current['characters'] if r['primary'])
    assert all(500<=counts[k]<=2000 for k in ACTIVE)
    assert all(a[cp]==b[cp] for cp in a if a[cp]['primary'] in ('x','y','z'))
    assert all(a[cp]['primary']==b[cp]['primary'] for cp in wedges)
    save(run/'全部收纳.json',current);save(run/'人工约束.json',rules)
    save(run/'冻结分组.json',{'version':rules['version'],'capacity':{'plannedLower':500,'plannedUpper':2000},'characters':[r for r in current['characters'] if r['primary'] not in ('y','z')]})
    model=read(source/'模型.json')
    with gzip.open(model['qualityRecords'],'rt',encoding='utf-8') as f:qa=list(map(json.loads,f))
    with np.load(model['featureCache']) as f:
        visual=(f['pixels']-np.array(model['pixelMean'],dtype='float32'))@np.array(model['basis'],dtype='float32')/model['visualScale']
        structural=(f['stats']-np.array(model['structureMean']))/np.array(model['structureScale'])*np.array(model['structureWeights'])
        matrix=np.concatenate([visual,structural,f['hog']*model['hogMultiplier']],1).astype('float32')
    indices={q['cp']:i for i,q in enumerate(qa)}
    centres=np.array([matrix[[indices[r['cp']] for r in current['characters'] if r['primary']==k and r['cp'] in indices]].mean(0) for k in ACTIVE])
    model.update(centres=centres.tolist(),manualRules=str(run/'人工约束.json'),capacity={'plannedLower':500,'plannedUpper':2000,'assigned':sum(counts[k] for k in ACTIVE),'observed':sum(r['primary'] in list(ACTIVE) and r['cp'] in indices for r in current['characters'])})
    save(run/'模型.json',model)
    summary={'date':'2026-10-16','run':str(run),'source':str(source),'acceptedProposal':str(proposal),'primaryChanged':262,'scopeRecords':len(b),'counts':dict(counts),'assigned':sum(counts.values()),'pending':sum(not r['primary'] for r in current['characters']),'oPure':False,'wedgeConstraintActive':False,'wedgeTagCount':len(wedges),'effectiveCodebooksChanged':False,'rimePublished':False,'newFontsRetrained':False}
    save(run/'摘要.json',summary);save(run/'接受迁移记录.json',changes)
    for filename in ('全部桶预览.html','单层分桶核对.html'):
        page=(proposal/'优化后全部桶预览.html').read_text(encoding='utf-8').replace('优化后桶分类草稿','当前桶分类').replace('只作核对，未替换主分组。','262项迁移已接受；o楔笔专属限制已取消，现有楔笔归属暂保留。').replace('桶分类局部优化核对.html','迁移接受记录.html')
        (run/filename).write_text(page,encoding='utf-8')
    page=(proposal/'桶分类局部优化核对.html').read_text(encoding='utf-8').replace('桶分类局部优化建议','已接受的262项迁移').replace('当前主分组未覆盖。','已设为当前主分组。o的专属限制现已取消。').replace('优化后全部桶预览.html','全部桶预览.html')
    (run/'迁移接受记录.html').write_text(page,encoding='utf-8')
    shutil.copytree(proposal/'全部字符预览',run/'全部字符预览')
    # Preserve portable font source used by the existing font repair workflow.
    shutil.copytree(source/'字体全面检查-20261014',run/'字体全面检查-20261014',ignore=shutil.ignore_patterns('修改前*','*.woff2','字体修正对照.png'))
    fontpage=(run/'字体全面检查-20261014/全部桶字体核对.html')
    fontpage.write_text((run/'全部桶预览.html').read_text(encoding='utf-8').replace('迁移接受记录.html','../迁移接受记录.html'),encoding='utf-8')
    target=LAB/'首次优化/运行/20261012-171242/全部字符预览'
    backup=run/'更新前MD备份';backup.mkdir()
    for p in (run/'全部字符预览').glob('*.md'):
        if (target/p.name).exists():shutil.copy2(target/p.name,backup/p.name)
        shutil.copy2(p,target/p.name)
    save(target.parent/'预览来源.json',{'source':str(run),'updated':'2026-10-16','note':'已接受262项迁移，取消o专属硬约束'})
    report={'ok':True,'identities':len(b),'acceptedMoves':262,'xyzUnchanged':True,'wedgePrimaryUnchangedThisStep':True,'wedgeConstraintRemoved':True,'ordinaryMin':min(counts[k] for k in ACTIVE),'ordinaryMax':max(counts[k] for k in ACTIVE),'acceptedAssignmentsLocked':all(b[cp].get('shapeAssignmentLocked') for cp in accepted)}
    for p in (run/'全部字符预览').glob('*.md'):
        assert p.read_bytes()==(target/p.name).read_bytes()
        if p.name!='a-w.md':assert '\n' not in p.read_text(encoding='utf-8') and '\r' not in p.read_text(encoding='utf-8')
    save(run/'校验报告.json',report)
    for name in ('最新人工核对.json','现行人工约束.json'):
        if (ROOT/name).exists():shutil.copy2(ROOT/name,run/('修改前-'+name))
    save(ROOT/'现行人工约束.json',rules)
    save(ROOT/'最新人工核对.json',{'run':str(run),'source':str(source),'completed':True,'effectiveCodebooksChanged':False})
    ps=read(proposal/'摘要.json');ps.update(acceptedRun=str(run),acceptedDate='2026-10-16');save(proposal/'摘要.json',ps)
    latest=read(LAB/'邻域优化/最新实验.json');latest.update(applied=True,acceptedRun=str(run));save(LAB/'邻域优化/最新实验.json',latest)
    print(json.dumps(dict(report,run=str(run)),ensure_ascii=False))

if __name__=='__main__':main()
