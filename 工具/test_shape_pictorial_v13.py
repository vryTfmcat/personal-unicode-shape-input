import copy
import tempfile
import unittest
from pathlib import Path
from collections import Counter
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v12 import OUT as V12
from build_shape_pictorial_review_v13 import OUT
from save_shape_pictorial_review import validate,save_snapshot


class V13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=read(OUT/'拟物收入全量初稿.json')
        cls.rows={r['cp']:r for r in cls.report['records']}

    def test_admission_and_identity_preserved(self):
        old=read(V12/'拟物收入全量初稿.json');new=self.report
        self.assertEqual(old['reviewDecisions'],new['reviewDecisions'])
        self.assertEqual(old['protectedHashes'],new['protectedHashes'])
        self.assertEqual(old['secondReview']['boundaryCps'],new['secondReview']['boundaryCps'])
        self.assertEqual([(r['cp'],r['oldBucket'],r['oldCodes']) for r in old['records']],
                         [(r['cp'],r['oldBucket'],r['oldCodes']) for r in new['records']])
        self.assertFalse(new['allocationChanged']);self.assertFalse(new['runtimeDeployed'])

    def test_bucket_partition_and_category_repairs(self):
        allocation=self.report['draftFirstKeyAllocations']
        self.assertEqual(len({r['cp'] for r in allocation}),3827)
        self.assertEqual(Counter(r['firstKey'] for r in allocation),{'t':3653,'b':174})
        self.assertEqual(len(self.report['bucketAudit']['categoryRepairs']),69)
        for char in '⛻✆🚰🛅':
            self.assertEqual(next(r['firstKey'] for r in allocation if r['cp']==ord(char)),'b')
        for char,target in [('🌭','食物与饮品'),('🌽','食物与饮品'),('🍥','食物与饮品'),
                            ('🖱','工具与日常物品'),('🚒','交通工具'),('🐽','动物部位')]:
            self.assertEqual(self.rows[ord(char)]['category'],target)
        # Prior explicit category overrides remain user-owned, even when flagged.
        self.assertEqual(self.report['reviewDecisions'][str(ord('💂'))]['category'],'人脸与表情')

    def test_unapproved_boundaries_stay_unapproved(self):
        qs=self.report['discoveryQueues'];decisions=self.report['reviewDecisions']
        self.assertEqual(len(qs['tToBBoundary']['cps']),218)
        self.assertEqual(self.report['bucketAudit']['boundaryInTByCategory']['棋牌符号'],209)
        self.assertIn(ord('🚾'),qs['bBadges']['cps'])
        self.assertEqual(decisions[str(ord('🚾'))]['decision'],'exclude')
        self.assertEqual(len(qs['bInterface']['cps']),40)
        for cp in qs['bInterface']['cps']:self.assertNotIn(str(cp),decisions)
        for char in '♥♡♀♂♠♣♦○●':
            self.assertNotIn(ord(char),qs['bBadges']['cps']+qs['bInterface']['cps'])

    def test_bucket_override_saves_and_rejects_invalid_keys(self):
        r=self.report
        payload={'format':'pictorial-intake-human-review-v1','version':r['version'],
                 'sourceIndexSHA256':r['sourceIndexSHA256'],'scope':r['scope'],
                 'allocationChanged':False,'decisions':[{'cp':ord('♔'),'char':'♔','decision':'include','firstKey':'b'}]}
        with tempfile.TemporaryDirectory() as folder:
            receipt=save_snapshot(payload,Path(folder));self.assertTrue(receipt['saved'])
        payload['decisions'][0]['firstKey']='auto';validate(payload,r)
        payload['decisions'][0]['firstKey']='x'
        with self.assertRaises(ValueError):validate(payload,r)


if __name__=='__main__':unittest.main()
