"""Pin a validated experimental run for editor/Rime review, without approving it."""
import json,hashlib,shutil
from pathlib import Path
from build_shape_experiment import ROOT,EDITOR,PROJECT,read,save,sha
from shape_review_profile import PROFILE,assignments,codes


def prepare():
    run=(PROJECT/Path(read(ROOT/'最新实验.json')['run'])).resolve()
    report=read(run/'全路径独立校验.json')
    if not report.get('passed'):raise ValueError('Full evidence audit required before review publication')
    raw=(EDITOR/'data/shape-experiment.json').read_bytes();data=json.loads(raw)
    if data['id']!=read(ROOT/'最新实验.json')['id'] or data['active']:raise ValueError('Review experiment version/status mismatch')
    assigned=assignments(data)
    frozen=run/'发布核对索引.json'
    if frozen.exists() and frozen.read_bytes()!=raw:raise ValueError('Pinned review index is immutable; use a new run')
    frozen.write_bytes(raw)
    mirror=EDITOR/'data/shape-review'/data['id']/'index.json';mirror.parent.mkdir(parents=True,exist_ok=True)
    mirror.write_bytes(raw)
    manifest={'format':'unicode-shape-review-profile-v1','enabled':True,'purpose':'user-review',
              'experimentId':data['id'],'sourceStage':data['sourceStage'],'indexPath':frozen.relative_to(PROJECT).as_posix(),
              'indexSHA256':hashlib.sha256(raw).hexdigest(),'url':mirror.relative_to(EDITOR).as_posix(),
              'ordinary':len(data['records']),'unclassified':len(data['unclassified']),
              'codedCharacters':len(assigned),'associations':sum(len(codes(r)) for r in assigned.values()),
              'migrationApproved':False,'keyboardBindingsStatus':'provisional-review','schema':'personal_unicode_modes',
              'userAuthorization':'用户要求将现有键位接入编辑器全形模式并部署小狼毫以逐键核对'}
    if PROFILE.exists():shutil.copy2(PROFILE,run/'上一核对版入口.json')
    save(PROFILE,manifest);save(EDITOR/'data/shape-review-profile.json',manifest)
    print(json.dumps(manifest,ensure_ascii=False));return manifest


if __name__=='__main__':prepare()
