import copy
import struct
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from shape_lab_features import components,describe,font_cmap
from shape_lab_features import extract,inventory
from shape_lab_rules import family,views,strategies,FIXED_REQUIRED
from shape_strategy_lab import aliases,palette,score,cluster_vectors


def fixture(kind):
    im=Image.new('L',(40,40));draw=ImageDraw.Draw(im)
    if kind=='circle':draw.ellipse((0,0,39,39),outline=255,width=3)
    elif kind=='square':draw.rectangle((0,0,39,39),outline=255,width=3)
    elif kind=='triangle':draw.polygon([(20,0),(39,39),(0,39)],fill=255);draw.polygon([(20,8),(33,35),(7,35)],fill=0)
    return dict(observed=True,**describe(np.array(im)>96,40,40))


class LabTests(unittest.TestCase):
    def test_topology_and_geometry(self):
        for shape,key in [('circle','o'),('square','s'),('triangle','t')]:
            f=fixture(shape);self.assertEqual(f['holes'],1);self.assertEqual(family(f),key)
        diagonal=np.eye(3,dtype=bool)
        self.assertEqual(len(components(diagonal,8)),1)
        self.assertEqual(len(components(diagonal,4)),3)

    def test_shared_suffix_and_identity_independence(self):
        mapping,_=palette()
        self.assertEqual({k:mapping[k]['function'] for k in FIXED_REQUIRED},FIXED_REQUIRED)
        f=fixture('circle');objects=views(f,mapping)
        for spec in strategies():
            a=aliases(f,objects,spec,0)
            self.assertEqual({p['code'][-1] for p in a},{v['suffix'] for v in objects})
            changed=copy.deepcopy(f);changed.update(char='A',unicodeName='ARBITRARY',block='OTHER')
            self.assertEqual(a,aliases(changed,views(changed,mapping),spec,0))
            doubled=aliases(f,objects+objects,spec,0)
            self.assertEqual([p['code'] for p in a],[p['code'] for p in doubled])
            self.assertAlmostEqual(sum(1/len(a) for _ in a),1)

    def test_missing_never_invents_fourth(self):
        f={'observed':False};mapping,_=palette()
        self.assertIsNone(views(f,mapping)[0]['suffix'])
        for spec in strategies():self.assertEqual(aliases(f,views(f,mapping),spec),[])

    def test_arc_does_not_become_hook(self):
        from PIL import ImageFont
        path=Path('C:/Windows/Fonts/seguisym.ttf')
        if not path.exists():self.skipTest('reference font unavailable')
        coverage,name=font_cmap(path)
        fonts=[{'path':str(path),'index':0,'family':name,'coverage':coverage,'font':ImageFont.truetype(str(path),48)}]
        for char in ('C','Ϲ'):self.assertEqual(family(extract(char,fonts)),'c')

    def test_weights_and_deterministic_clusters(self):
        metrics={'balance':10,'memory':20,'visual':30,'observedFraction':1}
        self.assertEqual(score(metrics,{'balance':1,'memory':0,'visual':0}),10)
        for invalid in ({'balance':0,'memory':0,'visual':0},{'balance':float('nan'),'memory':1,'visual':1}):
            with self.assertRaises(ValueError):score(metrics,invalid)
        matrix=np.random.default_rng(42).normal(size=(40,74)).astype('float32')
        a,model=cluster_vectors(matrix,3);b,_=cluster_vectors(matrix,3)
        self.assertTrue(np.array_equal(a,b));self.assertEqual(len(model['centres']),3)

    def test_font_cmap_rejects_last_resort(self):
        path=Path('C:/Windows/Fonts/segoeui.ttf')
        if not path.exists():self.skipTest('system font unavailable')
        coverage,_=font_cmap(path);self.assertIn(ord('O'),coverage)
        data=bytearray(path.read_bytes());count=struct.unpack_from('>H',data,4)[0]
        head=next(struct.unpack_from('>I',data,12+16*i+8)[0] for i in range(count) if data[12+16*i:16+16*i]==b'head')
        flags=struct.unpack_from('>H',data,head+16)[0];struct.pack_into('>H',data,head+16,flags|0x4000)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            modified=Path(folder)/'LastResort.ttf';modified.write_bytes(data)
            self.assertEqual(font_cmap(modified)[0],set())


if __name__=='__main__':unittest.main()
