import copy
import tempfile
import unittest
from pathlib import Path
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v11 import OUT as V11
from build_shape_pictorial_review_v12 import OUT,SNAPSHOT,CORRECTIONS
from save_shape_pictorial_review import save_snapshot


class V12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=read(OUT/'拟物收入全量初稿.json')

    def test_preserves_snapshot_except_authorized_corrections(self):
        expected={str(d['cp']):copy.deepcopy(d) for d in read(SNAPSHOT)['decisions']}
        for cp in CORRECTIONS:expected[str(cp)].update(decision='include',category='动物部位')
        self.assertEqual(self.report['reviewDecisions'],expected)
        self.assertEqual(self.report['secondReview']['categoryCounts']['动物部位'],131)
        self.assertEqual(len(self.report['secondReview']['admittedCps']),3827)
        self.assertEqual(sum(self.report['secondReview']['categoryCounts'].values()),3827)

    def test_protects_identity_codes_and_scope(self):
        old=read(V11/'拟物收入全量初稿.json')
        self.assertEqual(old['records'],self.report['records'])
        self.assertEqual(old['protectedHashes'],self.report['protectedHashes'])
        self.assertEqual(old['secondReview']['boundaryCps'],self.report['secondReview']['boundaryCps'])
        self.assertFalse(self.report['allocationChanged'])
        self.assertEqual(self.report['bucketSplitProposal']['status'],'discussion-only-not-applied')

    def test_pending_candidates_and_no_automatic_admission(self):
        summary=self.report['latestReviewSummary']
        self.assertEqual(summary['pendingTopics']['similarSigns'],0)
        self.assertEqual([summary['pendingTopics'][k] for k in
                         ('omittedObjects','omittedSigns','omittedVariants','egyptAnimalParts')],[205,35,59,156])
        self.assertEqual(self.report['policy']['firstKey'],'t')
        self.assertEqual(self.report['bucketSplitProposal']['wouldMove'],170)

    def test_saves_new_version(self):
        r=self.report
        payload={'format':'pictorial-intake-human-review-v1','version':r['version'],
                 'sourceIndexSHA256':r['sourceIndexSHA256'],'scope':r['scope'],
                 'allocationChanged':False,'decisions':list(r['reviewDecisions'].values())}
        with tempfile.TemporaryDirectory() as folder:
            receipt=save_snapshot(payload,Path(folder))
            self.assertEqual(receipt['summary']['explicitDecisions'],{'include':3827,'exclude':60,'note-only':1})


if __name__=='__main__':unittest.main()
