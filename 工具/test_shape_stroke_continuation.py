"""Conservation, continuation, actual-hole and same-cohort checks.

test_original_inputs_and_public_files_unchanged is pinned to the sourceHashes
and protectedHashes in 20261024-stroke-continuation-trial-v1. It checks that
historical experiment, not the later v5/attachment/bucket-order runtime. Preserve
its expected hashes and failure evidence; verify_shape_release.py is the current
release gate. The remaining controls retain their geometry meaning.
"""
import json
import unittest
from collections import Counter

import numpy as np
from PIL import Image,ImageDraw

from shape_stroke_topology_trial import analyze
from shape_stroke_continuation_trial import analyze_continuation,MIN_OPPOSITE_ANGLE
from test_shape_stroke_topology_trial import fixture
from build_shape_continuation_trial import PROJECT,OUTPUT,SOURCE,FIELDS,NEW_FIELDS,sha,protect


class ContinuationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((OUTPUT/'分类数据.json').read_text(encoding='utf-8'))
        cls.old=json.loads((SOURCE/'分类数据.json').read_text(encoding='utf-8'))

    def test_straight_through_is_not_y_branch(self):
        for name,strokes in [('T',2),('X',2),('H',3),('line',1),('angle',2),('zigzag',3)]:
            m=fixture(name);base=analyze(m);r=analyze_continuation(m,base)
            with self.subTest(name=name):
                self.assertEqual(r['statistics']['strokeCount'],strokes)
                self.assertEqual(r['statistics']['loops'],0)
                self.assertTrue(r['topologyAgrees'])

    def test_closed_and_open_curves_have_distinct_topology(self):
        for name,loops in [('arc',0),('circle',1)]:
            m=fixture(name);r=analyze_continuation(m,analyze(m))
            self.assertEqual(r['statistics']['loops'],loops)
            self.assertEqual(r['graphCycleCount'],loops)
        m=fixture('circle');m[15:45,92:100]=False
        r=analyze_continuation(m,analyze(m))
        self.assertEqual(r['statistics']['loops'],0)
        self.assertEqual(r['graphCycleCount'],0)

    def test_segments_belong_to_exactly_one_continuous_stroke(self):
        for name in ('T','X','H','circle','arc','angle'):
            m=fixture(name);base=analyze(m);r=analyze_continuation(m,base)
            ids=[v for s in r['strokes'] for v in s['segmentIds']]
            self.assertEqual(sorted(ids),list(range(len(base['segments']))))
            ports=[tuple(p) for pairing in r['pairings'] for p in pairing['ports']]
            self.assertEqual(len(ports),len(set(ports)))
            for pairing in r['pairings']:self.assertGreaterEqual(min(pairing['angles']),MIN_OPPOSITE_ANGLE)

    def test_orientation_invariance(self):
        for name in ('T','X','H','circle','angle'):
            m=fixture(name);expected=analyze_continuation(m,analyze(m))['statistics']
            for n in (np.rot90(m),np.rot90(m,2),m[:,::-1]):
                self.assertEqual(analyze_continuation(n,analyze(n))['statistics'],expected)

    def test_user_examples_and_nine_observations(self):
        rows={r['cp']:r for r in self.data['records']}
        expected={'ꓬ':dict(strokeCount=3,noThroughForks=1,loops=0),
                  'T':dict(strokeCount=2,straightThroughJunctions=1,loops=0),
                  'Ꚕ':dict(strokeCount=2,curveStrokes=2,curveThroughJunctions=1),
                  '4':dict(loops=1)}
        for char,fields in expected.items():
            r=rows[ord(char)];self.assertEqual(len(r['variants']),9)
            for v in r['variants']:
                for k,value in fields.items():self.assertEqual(v['statistics'][k],value,(char,k))
                self.assertTrue(v['topologyAgrees'])
        self.assertNotEqual(rows[ord('T')]['groupId'],rows[ord('ꓬ')]['groupId'])

    def test_same_1554_and_original_evidence_preserved(self):
        old={r['cp']:r for r in self.old['records']}
        self.assertEqual({r['cp'] for r in self.data['records']},set(old))
        self.assertEqual(len(old),1554)
        for r in self.data['records']:
            p=old[r['cp']]
            self.assertEqual(r['originalCodes'],p['originalCodes'])
            self.assertEqual(r['originalPreferredCodes'],p['originalPreferredCodes'])
            self.assertTrue(all(r['statistics'][k]==v for k,v in p['statistics'].items()))
            if not p['stableAcrossNineVariants']:self.assertFalse(r['stableAcrossNineVariants'])
        self.assertEqual(sum(g['count'] for g in self.data['groups']),1554)
        self.assertEqual(sum(v['count'] for v in self.data['largestPreviousClassSplit']),143)

    def test_original_inputs_and_public_files_unchanged(self):
        self.assertEqual(protect(),self.data['protectedHashes'])
        for p,digest in self.data['sourceHashes'].items():self.assertEqual(sha(PROJECT/p),digest,p)
        self.assertEqual(self.data['newCodes']+self.data['removedPaths']+self.data['tBReentry'],0)


if __name__=='__main__':unittest.main()
