import copy
from pathlib import Path
import tempfile
import unittest
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v7 import OUT,SNAPSHOT,unikemet
from save_shape_pictorial_review import save_snapshot


class V7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=read(OUT/'拟物收入全量初稿.json')
        cls.rows={r['cp']:r for r in cls.r['records']}

    def test_specific_repairs_and_unaffected_human_faces(self):
        for char,category in (('🐱','动物'),('😸','动物'),('💋','身体部位'),('🕐','工具与日常物品'),
                              ('🌞','自然物象'),('💆','人物与动作'),('💏','人物与场景'),('😀','人脸与表情')):
            self.assertEqual(self.rows[ord(char)]['category'],category)
        self.assertEqual(len(self.r['classificationRepairs']),66)

    def test_candidate_groups_complete_and_official_version_pinned(self):
        meta=unikemet(OUT/'Unikemet-17.0.0.txt')
        queues=self.r['discoveryQueues']
        for key,groups in (('egyptPeople',{'A','B','C'}),('egyptFish',{'K'}),
                           ('egyptAnimals',{'E','G','I','L'}),('egyptAnimalParts',{'F','H'})):
            expected={cp for cp,v in meta.items() if cp in self.rows and v.get('kEH_Cat','').split('-')[0] in groups}
            self.assertEqual(set(queues[key]['cps']),expected)
        self.assertIn(ord('𓁞'),queues['nearC002']['cps'])
        self.assertIn(ord('𓆟'),queues['egyptFish']['cps'])
        self.assertEqual(self.r['egyptianSources']['unikemetVersion'],'17.0.0')
        self.assertIn(ord('☢'),queues['similarSigns']['cps'])
        for char in '♥♡♀♂♠♣♦🚾':
            self.assertNotIn(ord(char),queues['similarSigns']['cps'])

    def test_no_new_admission_or_loss_of_original_notes(self):
        snapshot=read(SNAPSHOT)
        self.assertEqual(self.r['reviewDecisions'],{str(d['cp']):d for d in snapshot['decisions']})
        self.assertEqual(sum(d.get('decision')=='include' for d in self.r['reviewDecisions'].values()),1258)
        self.assertEqual(len(self.r['secondReview']['boundaryCps']),7303)
        self.assertEqual(self.r['protectedHashes'],protect())
        self.assertFalse(self.r['allocationChanged'])

    def test_save_new_categories_roundtrip(self):
        r=self.r
        payload={'format':'pictorial-intake-human-review-v1','version':r['version'],
            'sourceIndexSHA256':r['sourceIndexSHA256'],'scope':r['scope'],
            'decisions':copy.deepcopy(list(r['reviewDecisions'].values())),'allocationChanged':False}
        payload['decisions'][0].update(category='动物',secondReviewed=True)
        with tempfile.TemporaryDirectory() as d:
            receipt=save_snapshot(payload,Path(d))
            self.assertEqual(read(Path(receipt['path'])),payload)


if __name__=='__main__':unittest.main()
