"""Geometry controls plus user-sample consistency, never human confirmation.

The two source-hash guards apply to the pinned 20261024-turn-junction-samples-v2
fixtures (seven samples and the chvc 1554 comparison), before structure bindings
and 20261025 manual/attachment/query changes. They are historical reproducibility
checks, not current-release gates. Keep their expected hashes and failures intact;
use verify_shape_release.py for the selected runtime. Other geometry controls
still exercise the current default detector.
"""
import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from audit_shape_historical_buckets import protect
from build_shape_turn_samples import PROJECT, sha
from shape_stroke_topology_trial import analyze

RESULT=PROJECT/'数据/三模式/规则库/四键实验/键位试验/20261024-turn-junction-samples-v2/七例转折与分段结果.json'


def fixture(kind):
    im=Image.new('1',(192,192));d=ImageDraw.Draw(im)
    paths={'line':[[(25,96),(165,96)]],
           'angle':[[(35,30),(35,155),(155,155)]],
           'zigzag':[[(30,30),(155,30),(155,155),(30,155)]],
           'T':[[(25,35),(165,35)],[(95,35),(95,170)]],
           'X':[[(25,25),(165,165)],[(25,165),(165,25)]],
           'H':[[(40,20),(40,170)],[(150,20),(150,170)],[(40,95),(150,95)]]}
    for path in paths.get(kind,[]):d.line(path,fill=1,width=12)
    if kind=='arc':d.arc((25,25,165,165),0,180,fill=1,width=12)
    if kind=='circle':d.ellipse((25,25,165,165),outline=1,width=12)
    return np.array(im,dtype=bool)


class StrokeTopologyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads(RESULT.read_text(encoding='utf-8'))

    def test_straight_and_corner_controls(self):
        for name,corners,total in [('line',0,1),('angle',1,2),('zigzag',2,3)]:
            with self.subTest(name=name):
                s=analyze(fixture(name))['statistics']
                self.assertEqual(s['corners'],corners)
                self.assertEqual(s['straightSegments'],total)
                self.assertEqual(s['totalSegments'],total)
                self.assertEqual(s['forks']+s['crosses'],0)

    def test_fork_cross_and_two_separated_junctions(self):
        for name,forks,crosses,total in [('T',1,0,3),('X',0,1,4),('H',2,0,5)]:
            with self.subTest(name=name):
                s=analyze(fixture(name))['statistics']
                self.assertEqual((s['forks'],s['crosses'],s['totalSegments']),(forks,crosses,total))
                self.assertEqual(s['corners'],0)

    def test_smooth_arc_and_closed_curve_not_corners(self):
        for name in ('arc','circle'):
            with self.subTest(name=name):
                s=analyze(fixture(name))['statistics']
                self.assertEqual((s['corners'],s['forks'],s['crosses']),(0,0,0))
                self.assertEqual((s['curveSegments'],s['totalSegments']),(1,1))

    def test_rotation_and_mirror_controls(self):
        for name in ('line','angle','zigzag','T','X','H','arc','circle'):
            mask=fixture(name);expected=analyze(mask)['statistics']
            for transformed in (np.rot90(mask),np.rot90(mask,2),mask[:,::-1]):
                with self.subTest(name=name):
                    self.assertEqual(analyze(transformed)['statistics'],expected)

    def test_all_user_specified_counts_nine_variants(self):
        self.assertEqual(self.report['baselineMatched'],7)
        self.assertEqual(self.report['allNineMatched'],7)
        for r in self.report['records']:
            self.assertFalse(r['baselineMismatch'])
            self.assertEqual(len(r['variants']),9)
            self.assertTrue(all(not v['mismatch'] for v in r['variants']))
            self.assertTrue(all(not v['baselineCountDifferences'] for v in r['transformations']))

    def test_latest_santali_correction_and_segment_paths(self):
        r=next(r for r in self.report['records'] if r['cp']==0x1C64)
        self.assertEqual(r['userExpected'],dict(forks=1,corners=1,straightSegments=3,curveSegments=1,totalSegments=4))
        for r in self.report['records']:
            result=r['baseline'];s=result['statistics']
            self.assertEqual(s['totalSegments'],s['straightSegments']+s['curveSegments']+s['uncertainSegments'])
            self.assertEqual(len(result['segments']),s['totalSegments'])
            for segment in result['segments']:
                self.assertGreater(len(segment['points']),1)
                self.assertGreater(segment['metrics'].get('pathLength',1),0)

    def test_original_and_shared_sources_unchanged(self):
        self.assertEqual(protect(),self.report['protectedHashes'])
        for path,digest in self.report['sourceHashes'].items():
            self.assertEqual(sha(PROJECT/path),digest,path)
        for r in self.report['records']:
            self.assertEqual(sha(Path(r['font']['path'])),r['fontSHA256'])

    def test_diagnostic_partition_keeps_every_unstable_character(self):
        from audit_shape_turn_cohort import partition
        toy=[dict(cp=1,statistics={'corners':1},stableAcrossThreeSizes=True),
             dict(cp=2,statistics={'corners':1},stableAcrossThreeSizes=True),
             dict(cp=3,statistics=None,stableAcrossThreeSizes=False)]
        p=partition(toy,['corners'])
        self.assertEqual(p['cohort'],3)
        self.assertEqual(p['groups'],2)
        self.assertEqual(p['medianCharacterGroup'],2)
        self.assertEqual(p['maximumGroup'],2)
        self.assertEqual({cp for g in p['largestGroups'] for cp in g['cps']},{1,2,3})

    def test_full_comparison_does_not_change_candidate_membership(self):
        path=RESULT.parent/'当前chvc全组结构比较.json'
        report=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(report['statistics']['cohort'],1554)
        self.assertEqual(report['currentCandidateCountBefore'],1554)
        self.assertEqual(report['currentCandidateCountAfter'],1554)
        self.assertEqual(report['codesAdded']+report['codesRemoved']+report['tBReentry'],0)
        cps=[r['cp'] for r in report['records']]
        self.assertEqual(len(set(cps)),1554)
        self.assertEqual(report['statistics']['stableThreeSizes']+report['statistics']['unstableThreeSizes'],1554)
        for r in report['records']:
            self.assertIn('chvc',r['originalCodes'])
        for path,digest in report['sourceHashes'].items():
            self.assertEqual(sha(PROJECT/path),digest,path)
        self.assertEqual(protect(),report['protectedHashes'])


if __name__=='__main__':unittest.main()
