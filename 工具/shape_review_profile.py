"""One immutable review index shared by editor and Rime, separate from approvals."""
import hashlib,json
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
PROFILE=PROJECT/'数据/三模式/全形核对版.json'


def codes(record):
    found={record['bucket']}
    for route in record.get('familyRoutes',[]):found.add(route['bucket']+route['familyKey'])
    for path in record.get('codes',[]):
        for length in range(1,len(path)+1):found.add(path[:length])
    return sorted(found,key=lambda c:(len(c),c))


def load():
    if not PROFILE.exists():return None
    manifest=json.loads(PROFILE.read_text(encoding='utf-8'))
    if not manifest.get('enabled'):return None
    path=(PROJECT/manifest['indexPath']).resolve()
    if not path.is_relative_to(PROJECT):raise ValueError('Review index outside engineering tree')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['indexSHA256']:raise ValueError('Review index fingerprint mismatch')
    data=json.loads(raw)
    if data['id']!=manifest['experimentId'] or data['active']:raise ValueError('Review index version/status mismatch')
    return manifest,data


def assignments(data):
    result={r['cp']:r for r in data['records']}
    if len(result)!=28223:raise ValueError('Review ordinary coverage mismatch')
    for key,points in data['collections'].items():
        for cp in points:
            if cp in result:raise ValueError('Duplicate review identity')
            result[cp]={'cp':cp,'bucket':key,'familyId':None,'familyKey':None,'codes':[],'familyRoutes':[],'collection':True}
    if set(result)&set(data['unclassified']):raise ValueError('Pending characters received invented codes')
    if len(result)+len(data['unclassified'])!=159345:raise ValueError('Review total coverage mismatch')
    return result
