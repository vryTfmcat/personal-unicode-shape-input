"""Archive intake history and expose admitted categories for a separate second review."""
import copy
import json
from collections import Counter
from pathlib import Path
import shutil
import zipfile

from audit_shape_historical_buckets import PROJECT, protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_pictorial_review_v5 import OUT as V5
from build_shape_keyboard_full import save

OUT = V5.parent / '20261022-pictorial-intake-review-v6'
VERSION = 'pictorial-intake-20261022-v6'
SNAPSHOT = V5 / '人工审核保存/网页审核原始结果-a8c8167e8efe3d6b737d8de7ef8ea3fa64021b49f043f420659ef79c7ddbf069.json'


def archive_history():
    files = sorted({p for n in range(1, 6)
                    for p in (V5.parent / f'20261022-pictorial-intake-review-v{n}').rglob('*')
                    if p.is_file()})
    files += [EDITOR / f'pictorial-intake-review.{ext}' for ext in ('html', 'js', 'css')]
    manifest = {str(p.relative_to(PROJECT)).replace('\\', '/'): sha(p) for p in files}
    target = OUT / '归档备份/拟物收入初审-v1至v5.zip'
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, str(p.relative_to(PROJECT)).replace('\\', '/'))
        z.writestr('归档清单.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        import hashlib
        assert all(hashlib.sha256(z.read(name)).hexdigest() == digest
                   for name, digest in manifest.items())
    save(OUT / '归档备份/归档清单.json', {'files': manifest, 'zipSHA256': sha(target),
         'sourceFilesPreserved': True, 'restorable': True})
    shutil.copyfile(target, EDITOR / 'data/pictorial-intake-archive.zip')
    return {'relativePath': str(target.relative_to(PROJECT)), 'sha256': sha(target),
            'fileCount': len(files), 'downloadUrl': 'data/pictorial-intake-archive.zip'}


def build():
    if OUT.exists():
        raise FileExistsError('不覆盖已有v6二审稿')
    protected = protect()
    previous = read(V5 / '拟物收入全量初稿.json')
    snapshot = read(SNAPSHOT)
    assert sha(SNAPSHOT) == SNAPSHOT.stem.split('-')[-1]
    assert {str(d['cp']): d for d in snapshot['decisions']} == previous['reviewDecisions']
    backup = archive_history()
    report = copy.deepcopy(previous)
    report.update(version=VERSION, predecessorVersion=previous['version'],
                  lineageVersions=previous['lineageVersions'] + [VERSION],
                  predecessorReportSHA256=sha(V5 / '拟物收入全量初稿.json'),
                  sourceReviewSnapshot=str(SNAPSHOT), sourceReviewSHA256=sha(SNAPSHOT),
                  protectedHashes=protected)
    decisions = report['reviewDecisions']
    admitted = [r for r in report['records'] if decisions.get(str(r['cp']), {}).get('decision') == 'include']
    excluded = [r['cp'] for r in report['records'] if decisions.get(str(r['cp']), {}).get('decision') == 'exclude']
    boundary = [r['cp'] for r in report['records'] if r['proposal'] == 'boundary']
    report['secondReview'] = {
        'enabled': True, 'defaultQueue': 'admitted', 'admittedCps': [r['cp'] for r in admitted],
        'excludedCps': excluded, 'boundaryCps': boundary, 'boundaryOriginalCount': len(boundary),
        'initialReviewedCount': 0, 'categoryCounts': dict(Counter(r['category'] for r in admitted)),
        'archive': backup, 'oldProcessArchived': True,
        'hideExplicitExclusions': True, 'preserveOriginalDecisions': True,
    }
    report['latestConfirmations'] = {}
    report['uiNotice'] = '二次审核：按当前收入后的具体类别查看；初审收入不等于二审已确认。明确不收入者已从当前列表移出，历史资料已归档备份。'
    assert report['reviewDecisions'] == previous['reviewDecisions']
    assert len(admitted) == 1258 and len(excluded) == 41 and len(boundary) == 7303
    assert protect() == protected
    save(OUT / '拟物收入全量初稿.json', report)
    save(EDITOR / 'data/pictorial-intake-review.json', {k: v for k, v in report.items() if k != 'protectedHashes'})
    save(OUT / '验收.json', {'passed': True, 'archiveVerified': True, 'admitted': len(admitted),
         'hiddenExclusions': len(excluded), 'boundaryOriginalCount': len(boundary),
         'initialSecondReviewed': 0, 'allocationChanged': False, 'runtimeDeployed': False})
    print(json.dumps(report['secondReview'], ensure_ascii=False)[:400])


if __name__ == '__main__':
    build()
