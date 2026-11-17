import tempfile
import unittest
from pathlib import Path
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v15 import OUT as V15
from build_shape_pictorial_review_v16 import OUT, SNAPSHOT, FLOWERS, FLOWER_CANDIDATES
from save_shape_pictorial_review import save_snapshot


class V16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = read(OUT / '拟物收入全量初稿.json')

    def test_original_admissions_exclusions_notes_and_codes_preserved(self):
        r = self.r
        for d in read(SNAPSHOT)['decisions']:
            current = r['reviewDecisions'][str(d['cp'])]
            self.assertEqual(current.get('decision'), d.get('decision'))
            self.assertEqual(current.get('note'), d.get('note'))
        old = read(V15 / '拟物收入全量初稿.json')
        self.assertEqual(r['protectedHashes'], old['protectedHashes'])
        self.assertEqual([(x['cp'], x['oldCodes'], x['oldBucket']) for x in r['records']],
                         [(x['cp'], x['oldCodes'], x['oldBucket']) for x in old['records']])

    def test_confirmations_and_egyptian_pending(self):
        r = self.r
        for key in ('tToBBoundary', 'categoryRepairs13', 'egyptAnimalParts'):
            self.assertNotIn(key, r['discoveryQueues'])
            self.assertIn(key, r['archivedDiscoveryQueues'])
        audit = r['queueCleanup16']
        self.assertEqual(len(audit['confirmedBoundaryCps']), 4)
        self.assertEqual(len(audit['confirmedRepairCps']), 69)
        for cp in audit['confirmedBoundaryCps'] + audit['confirmedRepairCps']:
            self.assertTrue(r['reviewDecisions'][str(cp)]['secondReviewed'])
        self.assertEqual(len(audit['egyptianPendingCps']), 140)
        for cp in audit['egyptianPendingCps']:
            d = r['reviewDecisions'][str(cp)]
            self.assertEqual(d['category'], '象形·形象待辨')
            self.assertNotIn('decision', d)
            self.assertIn(cp, r['discoveryQueues']['pictorialUnresolved']['cps'])

    def test_flower_candidates_are_not_automatically_admitted(self):
        r = self.r
        alloc = {x['cp']: x for x in r['draftFirstKeyAllocations']}
        for cp in FLOWERS:
            self.assertEqual((alloc[cp]['category'], alloc[cp]['firstKey']), ('花', 'b'))
        for cp in FLOWER_CANDIDATES:
            self.assertNotIn(cp, alloc)
        self.assertEqual(r['latestReviewSummary']['include'], 4198)
        self.assertEqual(r['latestReviewSummary']['exclude'], 64)
        self.assertEqual(r['bucketSplit']['admittedCounts'], {'t': 3489, 'b': 709})

    def test_new_version_and_category_only_reviews_can_be_saved(self):
        r = self.r
        data = dict(format='pictorial-intake-human-review-v1', version=r['version'],
                    sourceIndexSHA256=r['sourceIndexSHA256'], scope=r['scope'],
                    allocationChanged=False, decisions=list(r['reviewDecisions'].values()))
        with tempfile.TemporaryDirectory() as folder:
            receipt = save_snapshot(data, Path(folder))
        self.assertTrue(receipt['saved'])
        self.assertEqual(receipt['summary']['secondReviewed'], 74)


if __name__ == '__main__':
    unittest.main()
