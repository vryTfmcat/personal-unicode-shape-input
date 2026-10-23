import itertools,unittest
import numpy as np
from optimize_shape_buckets import flow_assign,align
from shape_quality_v2 import describe,skeleton


class OptimizationTests(unittest.TestCase):
    def test_flow_matches_brute_force(self):
        cost=np.array([[.9,.1,.4],[.8,.2,.5],[.7,.3,.6],[.6,.4,.7],[.5,.5,.8]])
        labels=flow_assign(cost,1,2);best=float('inf')
        for assignment in itertools.product(range(3),repeat=5):
            counts=np.bincount(assignment,minlength=3)
            if np.all(counts>=1) and np.all(counts<=2):best=min(best,sum(cost[i,j] for i,j in enumerate(assignment)))
        self.assertAlmostEqual(sum(cost[i,j] for i,j in enumerate(labels)),best)
        with self.assertRaises(ValueError):flow_assign(cost,2,2)

    def test_alignment_is_a_permutation(self):
        old=np.tile(np.arange(23),4);new=(old+7)%23
        aligned,mapping=align(new,old);self.assertTrue(np.array_equal(aligned,old))
        self.assertEqual(len(set(mapping)),23)

    def test_contour_hole_and_skeleton(self):
        ring=np.zeros((64,64),dtype='float32');ring[8:56,8:56]=1;ring[12:52,12:52]=0
        structure,hog=describe(ring,0.)
        self.assertAlmostEqual(structure[2],1/6);self.assertAlmostEqual(structure[3],1/8)
        self.assertEqual(len(structure),24);self.assertEqual(len(hog),128)
        self.assertTrue(np.isfinite(structure).all());self.assertAlmostEqual(np.linalg.norm(hog),1.,places=5)
        line=np.zeros((32,32),dtype=bool);line[3:29,15:18]=True
        sk=skeleton(line);self.assertLess(sk.sum(),line.sum());self.assertGreater(sk.sum(),10)
        weak=np.zeros((64,64),dtype='float32');weak[30,30]=.05
        stats,hog=describe(weak,0.)
        self.assertTrue(np.isfinite(stats).all());self.assertTrue(np.isfinite(hog).all())


if __name__=='__main__':unittest.main()
