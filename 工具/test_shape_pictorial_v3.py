from collections import Counter
import hashlib
from pathlib import Path
import tempfile
import unittest

from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read
from build_shape_pictorial_review_v3 import OUT, SNAPSHOT, TYPOGRAPHIC, CJK_MOON, MUSIC, LUNAR
from save_shape_pictorial_review import save_snapshot, validate


class PictorialV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=read(OUT/'拟物收入全量初稿.json')
        cls.rows={r['cp']:r for r in cls.report['records']}
        cls.decisions=cls.report['reviewDecisions']

    def test_scope_approval_not_all_character_approval(self):
        acceptance=self.report['categoryReviewAcceptance']
        self.assertTrue(acceptance['doesNotApproveAllMembers'])
        self.assertEqual(len(acceptance['acceptedScopeKeys']),9)
        self.assertNotIn(str(ord('☮')),self.decisions)
        self.assertNotIn(str(ord('☯')),self.decisions)
        self.assertEqual(self.decisions[str(ord('⍾'))]['decision'],'uncertain')

    def test_text_and_abstract_ornaments_excluded(self):
        self.assertEqual(len(TYPOGRAPHIC),20)
        for cp in TYPOGRAPHIC:
            self.assertEqual(self.decisions[str(cp)]['decision'],'exclude')
            self.assertNotIn(cp,self.report['reviewQueues']['decoration']['cps'])
        for cp in range(0x1F650,0x1F660):
            self.assertEqual(self.decisions[str(cp)]['decision'],'include')
            self.assertIn(cp,self.report['reviewQueues']['decoration']['cps'])

    def test_cjk_and_music_are_not_celestial_objects(self):
        for cp in CJK_MOON|MUSIC:
            self.assertEqual(self.decisions[str(cp)]['decision'],'exclude')
            self.assertNotIn(cp,self.report['reviewQueues']['moon']['cps'])
        self.assertEqual(self.rows[0x2F49]['category'],'中文及汉字构件')
        self.assertEqual(self.rows[0x1D152]['category'],'乐谱记号')
        self.assertEqual(set(self.report['reviewQueues']['moon']['cps']),LUNAR)

    def test_mooncake_category_only_and_game_cars(self):
        self.assertEqual(self.rows[0x1F96E]['category'],'食物与饮品')
        self.assertEqual(self.decisions[str(0x1F96E)]['decision'],'include')
        for cp in (0x1CCA2,0x1CCA3):
            self.assertEqual(self.decisions[str(cp)]['decision'],'include')
            self.assertEqual(self.rows[cp]['category'],'游戏图标')
            self.assertIn(cp,self.report['reviewQueues']['games']['cps'])
        self.assertNotIn('geometryRetention',self.rows[0x1CCA2])
        self.assertEqual(self.report['policy']['geometryRetentionExceptions'],[0x1CCA3])
        self.assertTrue(self.rows[0x1CCA3]['geometryRetention']['geometryRouteNeedsBuilding'])

    def test_unrelated_choices_and_protected_sources_preserved(self):
        self.assertEqual(self.report['protectedHashes'],protect())
        self.assertEqual(hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),self.report['sourceReviewSHA256'])
        for d in read(SNAPSHOT)['decisions']:
            if str(d['cp']) not in self.report['latestConfirmations']:
                self.assertEqual(self.decisions[str(d['cp'])],d)
        self.assertEqual(self.report['reviewSummary']['firstCohortCounts'],{'include':1150,'exclude':8,'uncertain':58})
        self.assertEqual(Counter(d['decision'] for d in self.decisions.values()),{'include':1250,'exclude':41,'uncertain':58})
        current=read(EDITOR/'data/pictorial-intake-review.json')
        if current['version']==self.report['version']:
            self.assertEqual(current['records'],self.report['records'])
        else:
            self.assertIn(self.report['version'],current['lineageVersions'])
            self.assertEqual([(r['cp'],r['oldBucket'],r['oldCodes']) for r in current['records']],
                             [(r['cp'],r['oldBucket'],r['oldCodes']) for r in self.report['records']])

    def test_save_v3_roundtrip_is_not_deployment(self):
        payload={'format':'pictorial-intake-human-review-v1','version':self.report['version'],
            'sourceIndexSHA256':self.report['sourceIndexSHA256'],'scope':self.report['scope'],
            'decisions':list(self.decisions.values()),'allocationChanged':False}
        self.assertEqual(validate(payload,self.report)['queues']['propose']['uncertain'],58)
        with tempfile.TemporaryDirectory() as folder:
            result=save_snapshot(payload,Path(folder))
            self.assertEqual(read(Path(result['path'])),payload)
            self.assertFalse(result['runtimeDeployed'])


if __name__=='__main__':unittest.main()
