"""Thick real forks pass without admitting solid convex medial-axis forks."""
import unittest
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

from shape_experiment_features import observe,render
from shape_recovery_geometry import visible_fork


def convex_hull(points):
    points=sorted(set(points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves=[]
    for seq in (points,points[::-1]):
        out=[]
        for p in seq:
            while len(out)>=2 and cross(out[-2],out[-1],p)<=0:out.pop()
            out.append(p)
        halves.append(out[:-1])
    return halves[0]+halves[1]


class ThickForkTests(unittest.TestCase):
    def test_t_y_cross_f_all_nine(self):
        fonts={}
        for char in 'TY+F':
            for size in (48,96,128):
                for weight in (-1,0,1):
                    f=observe(*render(char,'C:/Windows/Fonts/seguisym.ttf',0,size=size,weight=weight,fonts=fonts))
                    proofs=[visible_fork(f,j,(3,4)) for j in f['junctionObjects']]
                    self.assertTrue(any(proofs),(char,size,weight))
                    if char=='T' and weight==1:
                        p=next(p for p in proofs if p)
                        self.assertTrue(p['thickStrokeConcavityProof'])
                        self.assertTrue(all(v['exitsFromSameConnectedInk'] for v in p['thickStrokeConcavityProof']))

    def test_solid_convex_font_controls_stay_rejected(self):
        fonts={}
        for char in '▲▼■●◆':
            for size in (48,96,128):
                for weight in (-1,0,1):
                    f=observe(*render(char,'C:/Windows/Fonts/seguisym.ttf',0,size=size,weight=weight,fonts=fonts))
                    self.assertFalse(any(visible_fork(f,j,(3,4)) for j in f['junctionObjects']),(char,size,weight))

    def test_200_solid_convex_polygons_stay_rejected(self):
        rng=np.random.default_rng(20261022)
        for n in range(200):
            hull=convex_hull([tuple(map(int,p)) for p in rng.integers(3,61,size=(8,2))])
            im=Image.new('1',(64,64));ImageDraw.Draw(im).polygon(hull,fill=1)
            f=observe(np.array(im,dtype=bool))
            self.assertFalse(any(visible_fork(f,j,tuple(range(3,17))) for j in f['junctionObjects']),n)

    def test_j_hook_has_no_fork(self):
        f=observe(*render('J','C:/Windows/Fonts/segoeui.ttf',0))
        self.assertFalse(any(visible_fork(f,j,(3,4)) for j in f['junctionObjects']))

    def test_fixed_cohort_and_frozen_inputs(self):
        import audit_shape_thick_fork as audit
        report_path=audit.OUTPUT/'粗笔分叉误拒复核.json'
        if not report_path.is_file():self.skipTest('audit not built')
        r=audit.load(report_path);s=r['statistics']
        self.assertEqual(s['cohort'],1562)
        self.assertEqual((s['stableBefore'],s['stableAfter'],s['newlyStable']),(620,762,142))
        self.assertEqual(s['improvedCharacters'],228)
        self.assertEqual(s['stableAfter']+s['remainingUnstable'],1562)
        self.assertEqual(r['protectedHashes'],audit.protect())
        for name,digest in r['sourceSHA256'].items():
            self.assertEqual(hashlib.sha256((audit.PROJECT/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(r['geometryCodeSHA256'],hashlib.sha256((audit.PROJECT/'工具/shape_recovery_geometry.py').read_bytes()).hexdigest())
        for row in r['records']:
            self.assertGreaterEqual(row['afterPositiveVariants'],row['beforePositiveVariants'])
            self.assertEqual(len(row['variants']),9)
            self.assertFalse(row['oldPreferencesChanged'])
        t=next(x for x in r['records'] if x['char']=='T')
        self.assertEqual((t['beforePositiveVariants'],t['afterPositiveVariants']),(6,9))


if __name__=='__main__':unittest.main()
