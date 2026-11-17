"""Inventory local changes and package only the measured four-round restore dependency set."""
import argparse
import hashlib
import json
import subprocess
import shutil
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]


def category(rel):
    if rel.startswith('实体/') or any(x in rel for x in ['association-graph.json','编码.tsv','人工审议.json','structure-count-bindings.json']):
        return '个人数据或人工确认：本地与私有备份，禁止默认公开'
    if '/测试输出/' in rel or rel.endswith(('.log','.pyc')):return '测试输出与缓存：保留，待确认可重建范围'
    if rel.startswith('数据/') or '/data/' in rel:return '运行输入与实验数据：保留，逐项确认来源和恢复依赖'
    if rel.startswith(('工具/','原型/')) and Path(rel).suffix in ('.py','.js','.cjs','.html','.css'):
        return '源码候选：须逐文件审阅后才可纳入Git白名单'
    if rel.endswith('.md'):return '说明与项目记录：核对权威位置，不自动提交'
    return '其它本地成果：待判定，保留'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--trace-json',required=True)
    parser.add_argument('--archive-dir',required=True)
    args=parser.parse_args();out=Path(args.archive_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    status=subprocess.check_output(['git','-c','core.quotePath=false','status','--porcelain=v1','-z','-uall'],cwd=PROJECT)
    rows=[]
    chunks=status.split(b'\0');i=0
    while i<len(chunks):
        chunk=chunks[i];i+=1
        if not chunk:continue
        state=chunk[:2].decode();rel=chunk[3:].decode('utf-8')
        if 'R' in state or 'C' in state:i+=1
        path=PROJECT/rel
        rows.append(dict(path=rel,status=state,category=category(rel),bytes=path.stat().st_size if path.is_file() else None))
    inventory=dict(createdAt=datetime.now().astimezone().isoformat(),counts=dict(Counter(r['category'] for r in rows)),
        note='仅分类，未执行移动、删除、忽略规则修改、git add/commit/push；源码候选不是公开白名单。',files=rows)
    (out/'未提交成果分类.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
    reads=json.loads(Path(args.trace_json).read_text(encoding='utf-8'))
    paths={PROJECT/rel for rel in reads if (PROJECT/rel).is_file() and '__pycache__' not in rel}
    # Source code is small; include the whole local tool/overview source layer, without traversing entities.
    for base in [PROJECT/'工具',PROJECT/'原型/键位编辑器']:
        paths.update(f for f in base.iterdir() if f.is_file() and f.suffix in ('.py','.js','.cjs','.html','.css','.cmd'))
    paths.update(f for f in (PROJECT/'原型/键位编辑器/fonts').iterdir() if f.is_file())
    for rel in ['DEVELOPMENT.md','Git版本管理.md','README.md']:
        paths.add(PROJECT/rel)
    # Review pages fetch these optional static payloads when available.
    for rel in ['原型/键位编辑器/data/pictorial-intake-review.json']:
        if (PROJECT/rel).is_file():paths.add(PROJECT/rel)
    estimate=sum(f.stat().st_size for f in paths)
    if shutil.disk_usage(out).free < 2*estimate+200*1024*1024:
        raise OSError('可用空间不足以同时保留归档及独立恢复目录，未打包')
    manifest=[];archive=out/'四轮总览恢复包.zip'
    if archive.exists():raise FileExistsError('不覆盖已有恢复包，请选择新的恢复点')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for f in sorted(paths):
            rel=f.relative_to(PROJECT).as_posix()
            if f.is_symlink() or rel.startswith('实体/'):raise ValueError('不打包实体或联接')
            content=f.read_bytes();digest=hashlib.sha256(content).hexdigest()
            z.writestr(rel,content);manifest.append(dict(path=rel,bytes=len(content),sha256=digest))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for r in manifest:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256']
    # Detect writes from another process while the snapshot was being captured.
    assert all(hashlib.sha256((PROJECT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in manifest)
    active=json.loads((PROJECT/'原型/键位编辑器/data/structure-count-bindings.json').read_text(encoding='utf-8'))
    meta=dict(version=active['version'],scope='四轮总览与规则重生成恢复包；含本地人工数据，不得公开',
        independentPhysicalBackup=False,createdAt=datetime.now().astimezone().isoformat(),
        gitHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=PROJECT,text=True).strip(),
        externalRuntime='Python with existing NumPy/Pillow/PyYAML; browser validation uses installed Edge/Playwright',
        fileCount=len(manifest),sourceBytes=sum(r['bytes'] for r in manifest),zipBytes=archive.stat().st_size,files=manifest)
    (out/'恢复清单.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    restored=out/'恢复演练/worktree'
    if restored.exists():raise FileExistsError('不覆盖已有恢复演练目录')
    restored.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        for r in manifest:
            target=(restored/r['path']).resolve()
            assert target.is_relative_to(restored.resolve())
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(r['path']))
            assert hashlib.sha256(target.read_bytes()).hexdigest()==r['sha256']
    print(json.dumps({k:v for k,v in meta.items() if k!='files'}|dict(restored=str(restored)),ensure_ascii=False))


if __name__=='__main__':main()
