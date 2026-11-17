import copy
from pathlib import Path
import tempfile
import unittest
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v9 import OUT,V8
from save_shape_pictorial_review import save_snapshot
from audit_shape_historical_buckets import protect


class V9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read(OUT/'拟物收入全量初稿.json')

    def test_income_and_raw_manual_overrides_preserved(self):
        previous=read(V8/'拟物收入全量初稿.json')
        self.assertEqual(self.r['reviewDecisions'],previous['reviewDecisions'])
        self.assertEqual(self.r['protectedHashes'],protect())
        self.assertEqual(self.r['secondReview']['boundaryCps'],previous['secondReview']['boundaryCps'])
        self.assertEqual(len(self.r['secondReview']['admittedCps']),3620)
        self.assertEqual(sum(self.r['secondReview']['categoryCounts'].values()),3620)
        self.assertEqual(self.r['categoryPlacementSummary']['remainingAdmittedUnknown'],0)

    def test_specific_placements_only_for_admitted(self):
        rows={r['cp']:r for r in self.r['records']}
        for char,category in (('𓁞','人物与神形'),('𓆟','鱼类')):
            self.assertEqual(rows[ord(char)]['category'],category)
        for p in self.r['categoryPlacements']:
            self.assertEqual(self.r['reviewDecisions'][str(p['cp'])]['decision'],'include')
        self.assertEqual(len(self.r['categoryPlacements']),2320)

    def test_completed_series_no_longer_waiting(self):
        counts=self.r['categoryPlacementSummary']['pendingQueues']
        self.assertEqual(counts['egyptPeople'],0)
        self.assertEqual(counts['egyptFish'],0)
        self.assertEqual(counts['egyptAnimals'],0)
        self.assertEqual(counts['egyptAnimalParts'],241)
        self.assertTrue(all(q['onlyUnresolved'] for q in self.r['discoveryQueues'].values()))

    def test_save_placement_version(self):
        r=self.r
        payload={'format':'pictorial-intake-human-review-v1','version':r['version'],
            'sourceIndexSHA256':r['sourceIndexSHA256'],'scope':r['scope'],
            'decisions':copy.deepcopy(list(r['reviewDecisions'].values())),'allocationChanged':False}
        with tempfile.TemporaryDirectory() as folder:
            receipt=save_snapshot(payload,Path(folder))
            self.assertEqual(read(Path(receipt['path'])),payload)


if __name__=='__main__':unittest.main()
