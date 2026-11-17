"""Conservative filled-face eligibility correction; numerical features unchanged."""
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np

from audit_shape_other_collisions import OUTPUT,PROJECT,STATUS_NAMES,sha,summarize,write_review
from shape_stroke_topology_trial import render_locked
from shape_recovery_geometry import angle_has_visible_gap
from shape_lab_features import components


def scope_evidence(mask,total_segments):
    if not total_segments:return dict(filledFace=False,reason='no-traced-segments')
    yy,xx=np.nonzero(mask);w=int(xx.max()-xx.min()+1);h=int(yy.max()-yy.min()+1)
    compact=min(w,h)/max(w,h);density=float(mask.sum()/(w*h))
    parts=[p for p in components(mask,8) if p['area']>=3]
    candidate=len(parts)==1 and compact>=.35 and density>.35
    gap=angle_has_visible_gap({'body':mask}) if candidate else None
    return dict(filledFace=bool(candidate and not gap),inkComponents=len(parts),
                bboxInkFraction=density,minorOverMajor=compact,convexHullGapAtLeast6Percent=gap,
                reason='compact-dense-convex-ink-is-not-evidence-of-visible-strokes')


def worker(row):
    if row['statistics'] is None:return row['cp'],dict(filledFace=False,reason='no-baseline')
    mask=render_locked(row['char'],row['font'])
    return row['cp'],scope_evidence(mask,row['statistics']['totalSegments'])


def build():
    path=OUTPUT/'其他大组分析.json';report=json.loads(path.read_text(encoding='utf-8'))
    if 'scopeEligibilityRevision' in report:raise FileExistsError('适用性修订已完成，不重复写入')
    initial=sha(path);rows=report['records'];index={r['cp']:r for r in rows};changes=[]
    with ProcessPoolExecutor(max_workers=4) as executor:
        for n,(cp,evidence) in enumerate(executor.map(worker,rows),1):
            r=index[cp];r['scopeEvidence']=evidence
            if evidence['filledFace'] and r['status'] not in ('filled-face','error'):
                changes.append(dict(cp=cp,beforeStatus=r['status'],beforeApplicability=r['applicability']))
                r.update(status='filled-face',applicability='filled-face')
            if n%2000==0:print(f'实心面适用性核对 {n}/{len(rows)}',flush=True)
    scopes=[{k:g[k] for k in ('code','cps','membershipFamily','identicalMembershipCodes')} for g in report['groups']]
    report['groups']=summarize(rows,scopes)
    report['statistics']['statusCounts']=dict(Counter(r['status'] for r in rows))
    report['sourceHashes'][str(Path(__file__).resolve().relative_to(PROJECT))]=sha(Path(__file__))
    report['scopeEligibilityRevision']=dict(version='compact-filled-face-gate-v2',
        runTime=datetime.now().astimezone().isoformat(),initialReportSHA256=initial,
        numericalObservationsUnchanged=True,changes=changes,
        evidence='Initial JSONL observations remain in 观测记录.jsonl; correction changes eligibility only.',
        condition='one ink component, minor/major>=.35, bbox ink fraction>.35, convex-hull gap<6%; zero traced segments stay explicit no-line')
    report['uiSourceHashes']=write_review(report)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(changedEligibility=len(changes),statusCounts=report['statistics']['statusCounts']),ensure_ascii=False),flush=True)


if __name__=='__main__':build()
