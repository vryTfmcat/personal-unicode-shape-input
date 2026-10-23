"""Coverage, group boundaries and no-migration contracts for the u similarity scan."""
import hashlib
from pathlib import Path
import sys
import unittest

PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'工具'),str(PROJECT/'原型/键位编辑器')]
from shape_overview import u_expansion,u_expansion_members,get_overview
from audit_shape_historical_buckets import assert_protected_snapshot


class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=u_expansion();cls.overview=get_overview()

    def test_full_ordinary_scope_and_existing42_retained(self):
        d=self.data
        self.assertEqual(d['ordinaryScanned'],28223)
        self.assertEqual(d['groupCounts'],{'原u已保留42字':42,'同一定义稳定新候选':131,
                                         '同形线群但检测不稳定':22,'多段层列扩展候选':28})
        self.assertEqual(len({r['cp'] for r in d['records']}),223)
        self.assertEqual(len(u_expansion_members('new')),181)

    def test_family_completeness_not_identity_based_detection(self):
        d=self.data;rows=d['records']
        self.assertEqual({r['cp'] for r in rows if 0x4DC0<=r['cp']<=0x4DFF},set(range(0x4DC0,0x4E00)))
        self.assertEqual(len(u_expansion_members('six')),22)
        self.assertEqual(len(u_expansion_members('three')),8)
        self.assertEqual(len(u_expansion_members('two')),4)

    def test_stable_vs_unstable_vs_broader_not_conflated(self):
        for r in self.data['records']:
            if r['category']=='同一定义稳定新候选':
                self.assertTrue(r['strictStability']['passed'])
                self.assertEqual(len(r['strictStability']['variants']),9)
            elif r['category']=='同形线群但检测不稳定':
                self.assertIsNotNone(r['strictObject'])
                self.assertFalse(r['strictStability']['passed'])
            elif r['category']=='多段层列扩展候选':
                self.assertIsNone(r['strictObject'])
                self.assertTrue(r['broadObject']['ruleExpansionRequired'])
        bar=next(r for r in self.data['records'] if r['char']=='║')
        self.assertEqual(sum(v['passed'] for v in bar['strictStability']['variants']),6)

    def test_no_automatic_bucket_or_code_changes(self):
        d=self.data
        self.assertFalse(d['bucketsChanged'])
        self.assertTrue(all(not r['migrationApplied'] and not r['newCodeApplied'] for r in d['records']))
        self.assertTrue(assert_protected_snapshot(d['protectedHashes']))
        self.assertEqual(self.overview.query({'prefix':['u'],'allocation':['1']})['total'],42)
        self.assertEqual(self.overview.query({'prefix':['u']})['total'],73)

    def test_browser_query_sets_and_details(self):
        v=self.overview
        for kind,count in [('six',22),('three',8),('two',4),('stable',131),('unstable',22),('broad',28),('new',181)]:
            q=v.query({'uExpansion':[kind],'allocation':['1']})
            self.assertEqual(q['total'],count,kind)
            self.assertTrue(all(r['uExpansionCategory'] for r in q['rows']))
        self.assertIsNotNone(v.detail(ord('≡'),True)['uExpansion'])
        self.assertEqual(self.data['measurementExplanation']['sourceSizes'],[48,96,128])
        self.assertEqual(self.data['measurementExplanation']['normalizedCanvas'],[64,64])


if __name__=='__main__':unittest.main()
