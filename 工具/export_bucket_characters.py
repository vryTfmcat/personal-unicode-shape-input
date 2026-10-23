"""Export each ordinary bucket as literal characters on one line, without metadata."""
import json
from collections import Counter
from pathlib import Path
from reserved_shape_buckets import ROOT
from shape_bucket_scope import ACTIVE


def main():
    run=Path(json.loads((ROOT/'最新分桶.json').read_text(encoding='utf-8'))['run'])
    book=json.loads((run/'冻结分组.json').read_text(encoding='utf-8'))
    folder=run/'全部字符预览';folder.mkdir(exist_ok=True)
    counts={};exported=[]
    for key in ACTIVE:
        rows=sorted((r for r in book['characters'] if r['primary']==key),key=lambda r:r['cp'])
        chars=''.join(r['char'] for r in rows)
        if any(c in chars for c in '\r\n\u2028\u2029'):
            raise ValueError(f'{key}桶含换行字符，不能静默删字')
        path=folder/(key+'.md');path.write_bytes(chars.encode('utf-8'))
        assert path.read_bytes().decode('utf-8')==chars
        assert len(chars)==len(rows)
        counts[key]=len(rows);exported.extend(r['cp'] for r in rows)
    assert len(exported)==len(set(exported))
    assert len(list(folder.glob('*.md')))==len(ACTIVE)
    assert not any((folder/(key+'.md')).exists() for key in 'xyz')
    print(json.dumps({'folder':str(folder),'files':len(ACTIVE),'characters':len(exported),'counts':counts,
        'headers':False,'newlines':False,'aliasesDuplicated':False},ensure_ascii=False))


if __name__=='__main__':main()
