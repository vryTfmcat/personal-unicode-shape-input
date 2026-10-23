"""Export independent ordered candidate digests for the editor parity check."""
import hashlib,json
from pathlib import Path
from mode_codebooks import base_data,effective_data,candidate_index,BOOK_PATH
from shape_review_profile import load,assignments,codes
from build_shape_experiment import save


def verify():
    manifest,review=load();book=json.loads(BOOK_PATH.read_text(encoding='utf-8'))
    data=effective_data(base_data(),book);index=candidate_index(data)
    expected={}
    for cp,r in assignments(review).items():
        for code in codes(r):expected.setdefault(code,[]).append(cp)
    hashes={}
    for code,points in expected.items():
        actual=[ord(c['char']) for c in index['shape'][code]]
        assert actual==points and len(points)==len(set(points)),code
        hashes[code]=hashlib.sha256(','.join(map(str,points)).encode()).hexdigest()
    assert set(expected)==set(index['shape'])
    result={'experimentId':review['id'],'passed':True,'prefixes':len(hashes),'associations':sum(len(v) for v in expected.values()),
            'codedCharacters':len(assignments(review)),'hashes':hashes}
    run=Path(manifest['indexPath']).parent
    from shape_review_profile import PROJECT
    target=PROJECT/run/'候选顺序校验.json';save(target,result)
    print(json.dumps({k:v for k,v in result.items() if k!='hashes'},ensure_ascii=False));print(str(target))


if __name__=='__main__':verify()
