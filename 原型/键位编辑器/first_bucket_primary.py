"""Two human-accepted primary-subject hints; never a path membership source."""
import functools
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


@functools.lru_cache(maxsize=1)
def policy():
    manual=json.loads((ROOT/'数据/三模式/规则库/四键实验/人工审议.json').read_text(encoding='utf-8-sig'))
    p=manual.get('firstBucketPrimaryAcceptance20261025')
    if not p or p.get('decision')!='accepted':return None
    report=(ROOT/p['statisticalReport']).resolve()
    if not report.is_relative_to(ROOT.resolve()) or hashlib.sha256(report.read_bytes()).hexdigest()!=p['reportSHA256']:
        raise ValueError('第一位主归属确认的候选证据不匹配')
    assert {r['cp'] for r in p['records']}=={961,7897}
    assert len(p['records'])==2
    for r in p['records']:
        assert r['char']==chr(r['cp']) and r['bucket']=='i' and r['familyKey']=='o'
        assert r['scope']=='circle-subject' and r['pathsUnchanged'] and r['preferredUnchanged']
    return p


def apply(row,cp):
    p=policy()
    r=next((r for r in (p or {}).get('records',[]) if r['cp']==cp),None)
    if not r:return row
    # Applied once after all existing subject/structure interpretation layers.
    assert (row.get('bucket'),row.get('familyKey'))==(r['beforeBucket'],r['beforeFamily'])
    return dict(row,legacyPrimaryBucket=row['bucket'],legacyPrimaryFamily=row['familyKey'],
        bucket=r['bucket'],familyKey=r['familyKey'],primarySubjectScope=r['scope'],
        firstBucketPrimaryAcceptance=p['id'],
        firstBucketPrimaryNote='本字推荐主归属已确认：i闭环·均衡，按圆主体o找。旧e整字路径与原首选保留；主归属不限制其它对象路径的桶，不新增计数或候选。')
