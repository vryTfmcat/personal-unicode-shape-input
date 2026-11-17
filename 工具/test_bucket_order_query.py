"""Checks preserve canonical candidates and disambiguate registered short paths."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'原型/键位编辑器'))
import shape_overview as so
import bucket_order_query as order


class BucketOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.o=so.get_overview()

    def back(self,prefix,length=4,text=''):
        return self.o.query(dict(allocation=['1'],order=['back'],prefix=[prefix],routeLength=[str(length)],text=[text]))

    def test_all_full_routes_keep_exact_candidate_sets(self):
        idx=order.index(self.o,True,4)
        for rotated,entries in idx['routes'].items():
            canonical=rotated[-1]+rotated[:-1]
            self.assertEqual({cp:t for c,cp,t in entries},self.o.allocation_members(canonical),canonical)
        self.assertGreater(len(idx['routes']),100)

    def test_cross_bucket_union_has_no_duplicate_characters(self):
        idx=order.index(self.o,True,4)
        expected={cp for rotated,entries in idx['routes'].items() if rotated.startswith('oq') for c,cp,t in entries}
        q=self.back('oq')
        self.assertEqual(q['total'],len(expected))
        self.assertEqual(len(q['rows']),len({r['cp'] for r in q['rows']}))
        self.assertIn(ord('O'),expected)
        self.assertEqual(self.back('oqui',text='O')['total'],0 if so.count_bc.policy() else 1)
        original=self.o.query(dict(allocation=['1'],prefix=['ioqu']))
        self.assertEqual([r['cp'] for r in self.back('oqui')['rows']],
                         [r['cp'] for r in original['rows']])

    def test_short_codes_do_not_absorb_four_code_descendants(self):
        idx=order.index(self.o,True,3)
        for rotated,entries in idx['routes'].items():
            canonical=rotated[-1]+rotated[:-1]
            self.assertTrue(all(canonical in self.o.brief(cp,True)['codes'] for c,cp,t in entries))
        self.assertEqual(self.back('rrq',3,'*')['total'],1)
        self.assertEqual(self.back('rrq',4,'*')['total'],0)

    def test_intake_history_and_preferences_stay_separate(self):
        intake=set(so.exclusive_intake())
        for length in (3,4):
            idx=order.index(self.o,True,length)
            self.assertFalse(intake & set(idx['prefixes']['']))
        before=self.o.brief(ord('ộ'),True)['preferredCodes'][:]
        self.back('otsi',text='ộ')
        self.assertEqual(before,self.o.brief(ord('ộ'),True)['preferredCodes'])
        with self.assertRaises(ValueError):self.o.query(dict(order=['back'],allocation=['0'],prefix=['oqui']))
        with self.assertRaises(ValueError):self.back('oqui',3)

if __name__=='__main__':unittest.main()
