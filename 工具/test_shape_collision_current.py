"""Regression and independent membership checks for the post-t/b experiment."""
import copy
import json
import unittest
from pathlib import Path

from audit_shape_collision_current import OUTPUT, PROJECT, burden, digest, merge_observations, overview
from audit_shape_historical_buckets import protect


class CurrentCollisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((OUTPUT / '当前重码诊断与建议.json').read_text(encoding='utf-8'))
        cls.o = overview.Overview()
        cls.records = cls.report['records']

    def test_full_cohort_and_exclusive_intake(self):
        cps = [r['cp'] for r in self.records]
        self.assertEqual(len(cps), len(set(cps)))
        self.assertEqual(set(cps), set(self.o.allocation_members('chvc')))
        self.assertFalse(set(cps) & set(overview.exclusive_intake()))

    def test_candidate_counts_use_global_memberships(self):
        counts = {g['code']: g['count'] for g in self.o.collision_groups(4, True)}
        for r in self.records:
            for prefix in ('baseline', 'recommended'):
                code = r[prefix + 'Code']
                self.assertEqual(counts[code], r[prefix + 'Burden'])
                self.assertIn(r['cp'], self.o.allocation_members(code))

    def test_no_codes_or_preferences_lost(self):
        for r in self.records:
            brief = self.o.brief(r['cp'], True)
            self.assertEqual(brief['codes'], r['originalCodes'])
            self.assertEqual(brief['preferredCodes'], r['originalPreferredCodes'])
            if r['frozenPreference']:
                self.assertFalse(r['newRecommendation'])

    def test_all_new_recommendations_have_same_object_evidence(self):
        for r in self.records:
            if not r['newRecommendation']:
                continue
            self.assertEqual(r['freshVariantChecks'], 9)
            self.assertFalse(r['negativeCertificate'])
            self.assertLess(r['recommendedBurden'], r['baselineBurden'])
            detail = self.o.detail(r['cp'], True)
            path = next(p for p in detail['paths'] if p['code'] == r['recommendedCode'])
            for proof in r['evidence']:
                evidence = next(e for e in path['evidence'] if e['objectId'] == proof['objectId'] and e['rule'] == proof['rule'])
                self.assertEqual(evidence['objectId'], evidence['fourthObjectId'])

    def test_protected_and_shared_inputs_unchanged(self):
        self.assertEqual(protect(), self.report['protectedHashes'])
        for name, sha in self.report['sourceHashes'].items():
            self.assertEqual(digest(PROJECT / name), sha, name)

    def test_metrics_replay(self):
        self.assertEqual(burden([r['baselineBurden'] for r in self.records]), self.report['statistics']['baseline'])
        self.assertEqual(burden([r['recommendedBurden'] for r in self.records]), self.report['statistics']['experiment'])
        self.assertTrue(all(r['recommendedBurden'] <= r['baselineBurden'] for r in self.records))

    def test_merge_does_not_mutate_history(self):
        old = {'checks': [dict(size=s, weight=w, visibleForks=[]) for s in (48,96,128) for w in (-1,0,1)]}
        snapshot = copy.deepcopy(old)
        thick = {'variants': [dict(size=c['size'], weight=c['weight'], proofs=[{'armCount':3}]) for c in old['checks']]}
        merged = merge_observations(old, thick)
        self.assertEqual(old, snapshot)
        self.assertTrue(all(c['visibleForks'] for c in merged))
        thick['variants'][0]['size'] = 49
        with self.assertRaises(AssertionError):
            merge_observations(old, thick)


if __name__ == '__main__':
    unittest.main()
