import copy,tempfile,unittest
from pathlib import Path
import numpy as np
from unittest.mock import patch
from balanced_shape_buckets import balanced_assign,fit,boundary_aliases,incremental
from shape_strategy_lab import save


class BucketTests(unittest.TestCase):
    def test_overfull_and_underfull(self):
        rng=np.random.default_rng(17)
        cost=rng.uniform(0,1,(130,26));cost[:,0]-=10
        labels=balanced_assign(cost,4,6);counts=np.bincount(labels,minlength=26)
        self.assertTrue(np.all(counts>=4));self.assertTrue(np.all(counts<=6))
        self.assertEqual(sum(counts),130)
        with self.assertRaises(ValueError):balanced_assign(cost,6,7)

    def test_equal_costs_and_exact_quota(self):
        labels=balanced_assign(np.zeros((104,26),dtype='float32'),4,4)
        self.assertTrue(np.all(np.bincount(labels,minlength=26)==4))
        self.assertEqual(boundary_aliases(np.zeros(26),5),[0,1])

    def test_fit_repeatable(self):
        x=np.random.default_rng(19).normal(size=(130,6)).astype('float32')
        a,centres,_=fit(x,4,6,iterations=2);b,_,_=fit(x,4,6,iterations=2)
        self.assertTrue(np.array_equal(a,b));self.assertTrue(np.isfinite(centres).all())

    def test_frozen_entries_and_capacity_queue(self):
        # A normal update must not rewrite assignments or remove an absent identity.
        row={'cp':65,'char':'A','primary':'a','aliases':['b'],'distance':0.,'font':'fixture','status':'machine-draft-frozen'}
        pending={'cp':66,'char':'B','primary':None,'aliases':[],'status':'pending-glyph'}
        records=[{'cp':65,'char':'A','feature':{'observed':False}}, {'cp':67,'char':'C','feature':{'observed':False}}]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            run=Path(folder);save(run/'冻结分组.json',{'capacity':{'plannedUpper':2},'characters':[row,pending]})
            save(run/'模型.json',{'centres':[[0.]*42]*26})
            rows,_,_=incremental(records,{},run)
        result={r['cp']:r for r in rows};self.assertEqual(result[65],row)
        self.assertEqual(result[66],pending);self.assertIsNone(result[67]['primary'])

    def test_new_assignment_uses_room_and_full_capacity_waits(self):
        from balanced_shape_buckets import LETTERS
        old=[{'cp':65+i,'char':chr(65+i),'primary':k,'aliases':[],'distance':0.,'status':'machine-draft-frozen'} for i,k in enumerate(LETTERS)]
        new={'cp':97,'char':'a','feature':{'observed':True,'font':'fixture'}}
        x=np.zeros((1,42),dtype='float32');model={'centres':[[0.]*42]*26}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            run=Path(folder);save(run/'模型.json',model)
            for upper,expected in [(1,None),(2,'a')]:
                save(run/'冻结分组.json',{'capacity':{'plannedUpper':upper},'characters':old})
                with patch('balanced_shape_buckets.features',return_value=([new],x,model)):
                    rows,_,_=incremental([new],{},run)
                result={r['cp']:r for r in rows};self.assertEqual(result[97]['primary'],expected)
                for r in old:self.assertEqual(result[r['cp']],r)
                if upper==1:self.assertEqual(result[97]['status'],'pending-capacity')


if __name__=='__main__':unittest.main()
