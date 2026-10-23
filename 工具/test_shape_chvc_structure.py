"""Object scope, stable buckets, and fixed-cohort safeguards."""
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

import audit_shape_chvc_structure as trial
from shape_experiment_features import observe, render


class StructuralTests(unittest.TestCase):
    def feature(self,char):
        return trial.measurements(observe(*render(char,'C:/Windows/Fonts/seguisym.ttf',0)))

    def test_connected_ink_is_not_stroke_count(self):
        for c,n in [('E',3),('F',2)]:
            f=self.feature(c)
            self.assertEqual(f['exactPartCount'],1)
            self.assertEqual(f['bars']['memberCount'],n)
            self.assertEqual(f['values']['bars'],str(n))

    def test_holes_have_explicit_whole_ink_scope(self):
        mask=np.zeros((64,64),bool)
        mask[5:25,5:25]=True; mask[8:22,8:22]=False
        mask[35:55,35:55]=True;mask[38:52,38:52]=False
        f=trial.measurements(observe(mask))
        self.assertEqual(f['exactHoleCount'],2)
        self.assertEqual(f['exactPartCount'],2)

    def test_unknown_is_not_absence(self):
        f=self.feature('T')
        self.assertEqual(f['values']['attachments'],trial.UNKNOWN)
        self.assertEqual(f['values']['bars'],trial.UNKNOWN)
        self.assertTrue(f['visibleForks'])
        self.assertEqual(f['visibleForks'][0]['positionKey'],'w')

    def test_round_tail_partition(self):
        mask,extent=render('Q','C:/Windows/Fonts/seguisym.ttf',0)
        self.assertIsNotNone(trial.cycle_subject(observe(mask,extent)))
        # This pilot's extension gate is deliberately narrower than legacy Q lookup.
        mask[60:64,54:58]=True
        q=trial.measurements(observe(mask,extent));o=self.feature('O')
        self.assertTrue(any(a['kind']=='尾' for a in q['attachments']))
        self.assertFalse(any(a['kind']=='尾' for a in o['attachments']))

    def test_unstable_measurements_keep_unknown(self):
        obs=[{'values':{'parts':str(n)}} for n in (1,1,2)]
        self.assertEqual(trial.stable_value(obs,'parts'),trial.UNKNOWN)
        self.assertEqual(trial.count_band(4),'4+')

    def test_partition_does_not_hide_unknowns(self):
        rows=[{'cp':n,'char':chr(65+n),'stableFeatures':{'holes':v}} for n,v in enumerate(['0','0',trial.UNKNOWN])]
        p=trial.partition(rows,['holes'])
        self.assertEqual(p['cohort'],3)
        self.assertEqual(sum(g['count'] for g in p['largestGroups']),3)
        self.assertEqual(p['maxGroup'],2)

    @unittest.skipUnless((trial.OUTPUT/'chvc结构细分与优先级试验.json').is_file(),'full audit not yet built')
    def test_full_audit_invariants(self):
        r=trial.load(trial.OUTPUT/'chvc结构细分与优先级试验.json')
        self.assertEqual(len({v['cp'] for v in r['records']}),1562)
        for x in r['records']:
            self.assertEqual(len(x['checks']),9)
            if x['preferredCodes']:
                self.assertIn(x['preferredCodes'][0],[c['code'] for c in x['choices']])
                self.assertTrue(x['demotedCodes'])
            if x['withdrawnTrialCodes']:
                self.assertIsNotNone(x['negativeCertificate'])
                self.assertTrue(all(v['negative'] for v in x['checks']))
            self.assertTrue(x['legacyChvcRetained'])
        self.assertFalse(r['runtimeDeployed'])
        self.assertFalse(r['newBindings'])
        self.assertEqual(r['capacity']['preferSpecific']+r['capacity']['unresolvedFallback']+
                         r['capacity']['withdrawnWithNegativeCertificate'],1562)
        from audit_shape_historical_buckets import assert_protected_snapshot
        self.assertTrue(assert_protected_snapshot(r['protectedHashes']))


if __name__=='__main__':unittest.main()
