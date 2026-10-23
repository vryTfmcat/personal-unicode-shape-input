"""No identity loss or forced primary labels when clearing the retained buckets."""
import hashlib
from pathlib import Path
import sys
import unittest

PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'工具'),str(PROJECT/'原型/键位编辑器')]
from shape_overview import cleanup_draft,cleanup_records,cleanup_additions,get_overview
from audit_shape_historical_buckets import assert_protected_snapshot


class CleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=cleanup_draft();cls.records=cleanup_records();cls.overview=get_overview()

    def test_partition_without_forcing_396(self):
        d=self.report
        self.assertEqual(len(self.records),443)
        self.assertEqual(d['allocated'],{'r':4,'u':42,'v':1})
        self.assertEqual(d['pendingPrimary'],396)
        self.assertEqual(sum(d['allocated'].values())+d['pendingPrimary'],443)
        self.assertTrue(all(r['draftBucket'] not in {'b','g','j','t'} for r in self.records.values()))
        self.assertEqual(d['pendingWithReliableSupplement'],93)

    def test_old_source_codes_and_human_confirmations_unchanged(self):
        self.assertTrue(assert_protected_snapshot(self.report['protectedHashes']))
        for cp,r in self.records.items():
            old=self.overview.rows[cp]
            self.assertEqual(r['legacyFirstAlias'],old['bucket'])
            self.assertEqual(set(r['oldCodes']),set(old['codes']))
            self.assertFalse(r['historicalConfirmationMigrated'])
        self.assertEqual(sum(r['historicalFirstKeyConfirmed'] for r in self.records.values()),10)

    def test_recovery_not_misreported_as_primary_assignment(self):
        d=self.report
        self.assertEqual(d['recoveredCharacters'],138)
        self.assertEqual(d['newCharacterCodePairs'],506)
        self.assertEqual(d['withAnyPathsAfter'],139)
        self.assertEqual(sum(bool(r['newCodes']) for r in self.records.values()),138)
        for r in self.records.values():
            if r['primaryPending']:
                self.assertIsNone(r['draftFamily'])

    def test_same_object_fourth_and_nine_variant_evidence(self):
        for r in self.records.values():
            objects={o['id']:o for o in r['objects']}
            for path in r['paths']:
                for evidence in path['evidence']:
                    self.assertEqual(evidence['objectId'],evidence['fourthObjectId'])
                    self.assertIn(evidence['objectId'],objects)
                if path['code']!='ulki':self.assertEqual(len(r['stabilityChecks']),9)
            if r['draftBucket']=='u':
                self.assertIn('ulki',r['newCodes'])
                self.assertFalse(any(c.startswith('ulk') and c!='ulki' for c in r['newCodes']))

    def test_draft_keys_freed_legacy_keys_accessible(self):
        v=self.overview
        keys={(k['position'],k['key']):k for k in v.allocation_keys()}
        for key,count in [('b',161),('g',161),('j',5),('t',27)]:
            self.assertEqual(v.query({'prefix':[key],'allocation':['1']})['total'],0)
            self.assertEqual(v.query({'prefix':[key]})['total'],count)
            self.assertEqual(keys[1,key]['count'],0)
            self.assertFalse(keys[1,key]['assigned'])
        self.assertEqual(v.query({'prefix':['u'],'allocation':['1']})['total'],42)
        self.assertEqual(v.query({'prefix':['u']})['total'],73)
        self.assertEqual(v.query({'prefix':['v'],'allocation':['1']})['total'],1)
        self.assertEqual(v.query({'prefix':['v']})['total'],16)

    def test_all_paths_details_counts_and_all_layer_members_visible(self):
        v=self.overview
        for cp,row in self.records.items():
            detail=v.detail(cp,True)
            codes={p['code'] for p in detail['paths']}
            self.assertTrue(set(row['oldCodes'])<=codes)
            self.assertEqual(set(row['oldCodes'])|set(row['newCodes']),codes)
        for code in ['ulki','chvc','eowe','rteg']:
            q=v.query({'prefix':[code],'allocation':['1']})
            self.assertEqual(q['total'],sum(q['groups'].values()))
        self.assertEqual(v.query({'prefix':['ulki'],'allocation':['1']})['total'],42)

    def test_pending_queue_and_coverage_separate(self):
        v=self.overview
        self.assertEqual(v.query({'cleanup':['pending'],'allocation':['1']})['total'],396)
        self.assertEqual(v.query({'cleanup':['reviewed'],'allocation':['1']})['total'],10)
        self.assertEqual(v.query({'queue':['first'],'allocation':['1']})['total'],6578)
        self.assertEqual(v.query({'queue':['first']})['total'],6716)
        self.assertEqual(v.query({'queue':['unclassified'],'allocation':['1']})['total'],5220)
        self.assertFalse(self.report['runtimeDeployed'])
        self.assertFalse(self.report['fullGeneratorChanged'])


if __name__=='__main__':unittest.main()
