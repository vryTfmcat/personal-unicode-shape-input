"""Snapshot the accepted visual buckets and display order into editor research data."""
import hashlib,json
from pathlib import Path
from mode_codebooks import atomic_json

PROJECT=Path(__file__).resolve().parents[1];DATA=PROJECT/'数据/三模式';STAGE=DATA/'shape-stage.json'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    run=Path(read(DATA/'规则库/人工核对/最新人工核对.json')['run']);rows=read(run/'全部收纳.json')['characters'];order=read(run/'桶内图形顺序.json')['orders']
    buckets={a:order[a] if a in order else [r['cp'] for r in rows if r['primary']==a] for a in 'abcdefghijklmnopqrstuvwxyz'}
    missing=[r['cp'] for r in rows if not r['primary']];seen=[cp for b in buckets.values() for cp in b]+missing
    assert len(seen)==len(set(seen))==len(rows)==159345
    stage={'format':'unicode-shape-stage-v1','version':1,'id':'shape-stage-'+run.name,'date':'2026-10-16','title':'图形分桶阶段版 · 2026-10-16',
        'source':run.relative_to(PROJECT).as_posix(),'sourceSha256':hashlib.sha256((run/'全部收纳.json').read_bytes()).hexdigest(),'orderSha256':hashlib.sha256((run/'桶内图形顺序.json').read_bytes()).hexdigest(),
        'buckets':buckets,'unclassified':missing,'aliases':{str(r['cp']):r['aliases'] for r in rows if r['aliases']},'reviewed':[r['cp'] for r in rows if r.get('shapeAssignmentLocked')],
        'tags':{'wedge-strokes':read(run/'人工约束.json')['wedgeTag']['members']},
        'counts':{a:len(v) for a,v in buckets.items()},'statistics':{'identities':len(rows),'ordinary':sum(len(buckets[a]) for a in 'abcdefghijklmnopqrstuvw'),'unclassified':len(missing),'reviewed':sum(bool(r.get('shapeAssignmentLocked')) for r in rows)},
        'policy':{'ordinary':'abcdefghijklmnopqrstuvw','capacity':[500,2000],'x':'组合与附加标记','y':'排除文字收纳','z':'中文与汉字构件','oExclusive':False,'primaryOnlyCapacity':True,'displayOrder':'visual-nearest-path-v1','xOrder':'codepoint','remainingKeys':[None,None,None],'rimePublished':False},
        'milestones':[{'acceptedMoves':262},{'acceptedMoves':703},{'nativeGlyphsRefreshed':1315,'newGlyphFeatures':196},{'shapeSorted':28223,'adjacentDistanceReduction':0.35991033561175634}],
        'deferredProblems':['局部相似尚未形成整族一致：星形符号分散，○/O与0仍分桶。','特征优先级尚未明确：整体轮廓与内部细节没有清晰层次。','每桶500～2000字的容量约束会牺牲部分自然形族的相似性。']}
    atomic_json(STAGE,stage);atomic_json(PROJECT/'原型/键位编辑器/data/shape-stage.json',stage)
    # Preserve existing effective codes byte-for-byte; add only a research data manifest.
    path=PROJECT/'原型/键位编辑器/data/mode-data.json';base=read(path)
    base['shapeStage']={k:stage[k] for k in ('format','id','date','title','statistics')};base['shapeStage']['url']='data/shape-stage.json';atomic_json(path,base)
    print(json.dumps({'stage':stage['id'],'counts':stage['counts'],'statistics':stage['statistics']},ensure_ascii=False))

if __name__=='__main__':main()
