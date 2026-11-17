"""Regression checks for frozen preferences, full-cohort burden and exclusion safety."""
import json
import unittest
from collections import Counter
import audit_shape_chvc_post_intake as trial


class SelectionTests(unittest.TestCase):
    def test_explicit_preference_cannot_be_replaced_by_smaller_group(self):
        self.assertEqual(trial.choose(['chmw'],[{'code':'chmd'}],['chmw','chmd']),(['chmw'],False))

    def test_no_unavailable_code_can_be_recommended(self):
        self.assertEqual(trial.choose([],[{'code':'chmd'}],['chvc']),([],False))

    def test_unknown_does_not_remove_fallback(self):
        self.assertEqual(trial.choose([],[],['chvc']),([],False))

    def test_character_weighted_burden_includes_full_fallback(self):
        result=trial.burden([10,10,1554])
        self.assertEqual(result['totalCandidateExposure'],1574)
        self.assertEqual(result['mean'],524.667)
        self.assertEqual(result['median'],10)
        self.assertEqual(result['maximum'],1554)


class SavedExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=trial.overview.read(trial.OUTPUT/'诊断与结构推荐.json')
        cls.view=trial.overview.Overview()
        cls.counts={g['code']:g['count'] for g in cls.view.collision_groups(4,True)}

    def test_exact_current_cohort_and_tb_exclusion(self):
        cps=[r['cp'] for r in self.r['records']]
        self.assertEqual(len(cps),len(set(cps)))
        self.assertEqual(set(cps),set(self.view.allocation_members('chvc')))
        self.assertFalse(set(cps)&trial.overview.exclusive_intake().keys())
        self.assertEqual(len(cps),1554)

    def test_all_old_preferences_and_all_recommended_paths_retained(self):
        for r in self.r['records']:
            current=self.view.brief(r['cp'],True)
            self.assertEqual(r['legacyCodes'],current['codes'])
            self.assertEqual(r['beforePreferred'],current['preferredCodes'])
            if r['beforePreferred']:
                self.assertEqual(r['afterPreferred'],r['beforePreferred'])
            self.assertIn(r['afterCode'],r['legacyCodes'])
            self.assertIn(r['cp'],self.view.allocation_members(r['afterCode']))

    def test_fresh_proofs_bound_to_existing_objects_and_nine_variants(self):
        for r in self.r['records']:
            if not r['newRecommendation']:continue
            detail=self.view.chunk(self.view.rows[r['cp']]['detailUrl'])[r['cp']]
            path=next(p for p in detail['paths'] if p['code']==r['afterCode'])
            original={(e['objectId'],e['rule']) for e in path['evidence']}
            proof=r['freshEvidence']
            self.assertTrue(proof['evidence'])
            self.assertTrue({(e['objectId'],e['rule']) for e in proof['evidence']}<=original)
            self.assertEqual(len(r['freshChecks']),9)
            self.assertLess(r['afterBurden'],r['beforeBurden'])

    def test_counts_are_global_and_comparison_includes_every_character(self):
        for r in self.r['records']:
            self.assertEqual(r['beforeBurden'],self.counts[r['beforeCode']])
            self.assertEqual(r['afterBurden'],self.counts[r['afterCode']])
        self.assertEqual(self.r['before'],trial.burden([r['beforeBurden'] for r in self.r['records']]))
        self.assertEqual(self.r['after'],trial.burden([r['afterBurden'] for r in self.r['records']]))
        self.assertEqual(self.r['rawChvcBefore'],self.r['rawChvcAfter'])

    def test_protected_sources_and_no_unapproved_integration(self):
        self.assertEqual(self.r['protectedHashes'],trial.snapshot())
        self.assertFalse(self.r['runtimeIntegrated'])
        self.assertFalse(self.r['runtimeDeployed'])
        self.assertFalse(self.r['newBindings'])
        self.assertFalse(self.r['humanIndividuallyConfirmed'])
        overlay=trial.overview.read(trial.OUTPUT/'新增推荐覆盖层.json')
        self.assertFalse(overlay['active'])
        self.assertEqual({r['cp'] for r in overlay['records']},
                         {r['cp'] for r in self.r['records'] if r['newRecommendation']})


if __name__=='__main__':unittest.main()
