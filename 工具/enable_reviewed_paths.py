"""Promote only the already approved batches; no machine-created detail codes."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

APPROVED=('01','02','03','05','06')

def promote(project, book):
    data=Path(project)/'数据/三模式'
    spec=importlib.util.spec_from_file_location('shape_audit',Path(project)/'工具/audit_shape_rules.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    all_batches=[(p.name,json.loads(p.read_text(encoding='utf-8-sig'))) for p in sorted(data.glob('全形圆族试验-*.json'))]
    report=audit.audit(all_batches)
    # Follow the audit's declared conflict list; status approval is checked independently below.
    if report.get('errors') or report.get('conflicts'):
        raise ValueError('键义检查失败，请先解决冲突')
    result=copy.deepcopy(book);count=0;chars=set()
    for suffix in APPROVED:
        name=f'全形圆族试验-{suffix}.json';batch=json.loads((data/name).read_text(encoding='utf-8-sig'))
        if batch.get('status')!='approved-candidate':raise ValueError(name+' 尚未确认')
        for item in batch['characters']:
            if item.get('status',batch['status'])!='approved-candidate':continue
            cp=int(item['codepoint'].replace('U+',''),16);identity=f'u-{cp:04x}'
            paths=item.get('codes') or [{'code':item.get('proposedCode') or item['code'],'basis':item.get('description') or ' · '.join(x for x in (item.get('feature',''),item.get('detail','')) if x) or '已核对批次中的字形路径','status':item.get('status',batch['status'])}]
            current=result['shapeOverrides'].setdefault(identity,{'coarse':paths[0]['code'][:2], 'detail':None,'status':'reviewed',
                'mode':'shape','ruleVersion':'reviewed-paths-v1','reference':'已确认批次；各路径保留具体依据'})
            current.setdefault('paths',[])
            for path in paths:
                if path.get('status',item.get('status',batch['status']))!='approved-candidate':continue
                code=path['code'];font=item.get('font') or batch.get('reference') or ', '.join(f['font'] for f in batch.get('fonts',[]))
                if not isinstance(font,str):font=json.dumps(font,ensure_ascii=False)
                candidate={'code':code,'basis':path.get('basis') or item.get('description') or '已核对批次中的字形路径，见 '+name,
                    'font':font,'ruleVersion':batch.get('layoutVersion','game-layout-v1'),'status':'reviewed','enabled':True,'sourceBatch':name}
                existing=next((x for x in current['paths'] if x['code']==code),None)
                if existing is None:current['paths'].append(candidate);count+=1
            chars.add(identity)
    return result, {'characters':len(chars),'newPaths':count,'batches':list(APPROVED)}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    path=project/'数据/三模式/codebooks.json';book=json.loads(path.read_text(encoding='utf-8-sig'))
    result,report=promote(project,book)
    import mode_codebooks as books
    base=json.loads(books.BASE_PATH.read_text(encoding='utf-8-sig'));books.validate_codebooks(result,base)
    if args.apply:
        folder=path.parent/'备份';folder.mkdir(exist_ok=True)
        import uuid
        (folder/('before-reviewed-paths-'+uuid.uuid4().hex+'.json')).write_bytes(path.read_bytes())
        books.atomic_json(path,result)
    print(json.dumps(report,ensure_ascii=False))
