from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from build_shape_pictorial_review import EDITOR,read,sha


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read(EDITOR/'data/pictorial-glyph-previews.json')

    def test_every_preview_preserves_shape_and_fits_original_bounds(self):
        hashes={}
        self.assertEqual(len(self.r['previews']),2924)
        self.assertEqual(self.r['statistics'],{'tiny':2749,'normal':168,'large':7})
        for cp,p in self.r['previews'].items():
            root=ET.parse(EDITOR/p['url']).getroot()
            x,y,w,h=map(float,root.attrib['viewBox'].split())
            x0,y0,x1,y1=p['bounds']
            self.assertLessEqual(x,x0)
            self.assertLessEqual(y,-y1)
            self.assertGreaterEqual(x+w+1e-5,x1)
            self.assertGreaterEqual(y+h+1e-5,-y0)
            self.assertTrue(root[0].attrib['d'])
            self.assertFalse(p['geometryChanged'])
            if p['sourceFont'] not in hashes:hashes[p['sourceFont']]=sha(EDITOR/'fonts'/p['sourceFont'])
            self.assertEqual(p['sourceFontSHA256'],hashes[p['sourceFont']])

    def test_reported_examples_and_review_unchanged(self):
        for cp in (0x13BF9,0x13BFA,0x13BFC,0x13BFD,0x137C1):
            self.assertEqual(self.r['previews'][str(cp)]['problem'],'tiny')
        self.assertEqual(self.r['previews'][str(0x13BFB)]['problem'],'normal')
        rows={str(r['cp']):r for r in read(EDITOR/'data/pictorial-intake-review.json')['records']}
        self.assertTrue(all(rows[cp]['font']['file']==p['sourceFont'] for cp,p in self.r['previews'].items()))
        self.assertFalse(self.r['allocationChanged'])


if __name__=='__main__':unittest.main()
