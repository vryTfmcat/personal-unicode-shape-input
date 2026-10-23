import json
import copy
import tempfile
from pathlib import Path
from mode_codebooks import validate_codebooks,effective_data,candidate_index,query_candidates,BOOK_PATH,BASE_PATH
from enable_reviewed_paths import promote
from build_mode_rime import build

def main():
    project=Path(__file__).resolve().parents[1]
    base=json.loads(BASE_PATH.read_text(encoding='utf-8-sig'));book=json.loads(BOOK_PATH.read_text(encoding='utf-8-sig'))
    enabled,report=promote(project,book);validate_codebooks(enabled,base)
    index=candidate_index(effective_data(base,enabled))
    assert any(r['char']=='○' for r in query_candidates(index,'oesc',['shape']))
    assert any(r['char']=='(' for r in query_candidates(index,'cgva',['shape']))
    assert any(r['char']=='(' for r in query_candidates(index,'cgud',['shape']))
    assert any(r['char']=='(' for r in query_candidates(index,'cgv',['shape']))
    assert len({r['id'] for r in query_candidates(index,'cg',['shape'])})==len(query_candidates(index,'cg',['shape']))
    assert not query_candidates(index,'opba',['shape']), '第四批仍是试验，不能发布'
    before=effective_data(base,book);after=effective_data(base,enabled)
    assert [c['blockCode'] for c in before['characters']]==[c['blockCode'] for c in after['characters']]
    assert [c['personal'] for c in before['characters']]==[c['personal'] for c in after['characters']]
    bad=copy.deepcopy(enabled);bad['shapeOverrides']['u-25cb']['paths'][0]['code']='bad'
    try:validate_codebooks(bad,base)
    except ValueError:pass
    else:raise AssertionError('非法路径未拒绝')
    with tempfile.TemporaryDirectory() as folder:
        result=build(enabled,Path(folder))
        shape=(Path(folder)/'unicode_shape.dict.yaml').read_text()
        assert '○\toesc\t' in shape and '(\tcgva\t' in shape and '(\tcgv\t' in shape
        assert '◐\topba\t' not in shape
    print('已确认路径、两/三/四码、去重、未确认排除、Rime词典与原码本不变检查通过',report)

if __name__=='__main__':main()
