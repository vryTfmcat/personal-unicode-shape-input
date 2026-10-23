import hashlib
from pathlib import Path
import tempfile
import unittest

from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v2 import OUT, V1, SNAPSHOT, EXACT, LEAVES, MOON, DUAL
from save_shape_pictorial_review import save_snapshot, validate


class PictorialV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=read(OUT/'拟物收入全量初稿.json')
        cls.rows={r['cp']:r for r in cls.report['records']}
        cls.decisions=cls.report['reviewDecisions']

    def test_source_protection(self):
        self.assertEqual(self.report['protectedHashes'],protect())
        self.assertEqual(hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),self.report['sourceReviewSHA256'])
        self.assertEqual(self.report['sourceReviewSHA256'],'484626a0b677a992dfab997530d5e5d46b4a9362d13deb0507ce8d93808fbe5b')
        old=read(V1/'拟物收入全量初稿.json')
        self.assertEqual([(r['cp'],r['oldBucket'],r['oldCodes']) for r in old['records']],
                         [(r['cp'],r['oldBucket'],r['oldCodes']) for r in self.report['records']])

    def test_explicit_categories_and_series(self):
        for cp,(decision,category) in EXACT.items():
            self.assertEqual(self.decisions[str(cp)]['decision'],decision)
            self.assertEqual(self.rows[cp]['category'],category)
        for cp in LEAVES|MOON:
            self.assertEqual(self.decisions[str(cp)]['decision'],'include')
        for c in '○●':
            self.assertNotIn(str(ord(c)),self.report['latestConfirmations'])
        self.assertEqual(self.rows[ord('🨊')]['category'],'标识牌')
        self.assertEqual(self.rows[0x1F0A1]['category'],'标识牌')
        for c in '♠♣♦':
            self.assertEqual(self.decisions[str(ord(c))]['decision'],'exclude')

    def test_previous_human_decisions_not_silently_overwritten(self):
        for d in read(SNAPSHOT)['decisions']:
            if str(d['cp']) not in self.report['latestConfirmations']:
                self.assertEqual(self.decisions[str(d['cp'])],d)
        self.assertEqual(self.report['reviewSummary']['firstCohortCounts'],{'include':1149,'exclude':8,'uncertain':59})
        self.assertEqual(len(self.report['reviewQueues']['remainingFirst']['cps']),59)

    def test_only_one_dual_exception(self):
        self.assertEqual(self.report['policy']['geometryRetentionExceptions'],[DUAL])
        self.assertEqual([r['cp'] for r in self.rows.values() if r.get('geometryRetention')],[DUAL])
        self.assertNotIn(str(0x1CCA2),self.report['latestConfirmations'])
        self.assertEqual(self.decisions[str(0x1CCA2)]['decision'],'uncertain')
        self.assertEqual(self.rows[DUAL]['geometryRetention']['keepAllOriginalCodes'],self.rows[DUAL]['oldCodes'])
        self.assertTrue(self.rows[DUAL]['geometryRetention']['geometryRouteNeedsBuilding'])
        self.assertFalse(self.rows[DUAL]['geometryRetention']['existingGeometryRouteAvailable'])

    def test_similar_symbols_are_not_automatically_accepted(self):
        cps=self.report['reviewQueues']['symbolic']['cps']
        self.assertEqual(len(cps),32)
        self.assertIn(ord('☭'),cps)
        self.assertIn(ord('☯'),cps)
        self.assertIn(ord('⍾'),cps)
        self.assertNotIn(str(ord('☯')),self.report['latestConfirmations'])
        self.assertEqual(self.decisions[str(ord('⍾'))]['decision'],'uncertain')

    def test_v2_snapshot_roundtrip(self):
        payload={'format':'pictorial-intake-human-review-v1','version':self.report['version'],
            'sourceIndexSHA256':self.report['sourceIndexSHA256'],'scope':self.report['scope'],
            'decisions':list(self.decisions.values()),'allocationChanged':False}
        self.assertEqual(validate(payload,self.report)['queues']['propose']['uncertain'],59)
        with tempfile.TemporaryDirectory() as folder:
            result=save_snapshot(payload,Path(folder))
            self.assertEqual(read(Path(result['path'])),payload)
            self.assertFalse(result['allocationChanged'])


if __name__=='__main__':unittest.main()
