import copy
import tempfile
import unittest
from pathlib import Path
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v14 import OUT as V14
from build_shape_pictorial_review_v15 import OUT, SNAPSHOT, REPAIRS, ZODIAC
from save_shape_pictorial_review import save_snapshot


class V15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = read(OUT / '拟物收入全量初稿.json')

    def test_exact_authorized_changes_only(self):
        expected = {str(d['cp']): copy.deepcopy(d) for d in read(SNAPSHOT)['decisions']}
        approved = {cp: ('星座', 'b') for cp in ZODIAC}
        approved.update(REPAIRS)
        approved[0x1FA8E] = ('工具与日常物品', 't')
        for cp, (category, first) in approved.items():
            expected.setdefault(str(cp), {'cp': cp, 'char': chr(cp)}).update(
                decision='include', category=category, firstKey=first)
        self.assertEqual(self.r['reviewDecisions'], expected)
        self.assertEqual(len(self.r['latestConfirmations']), 21)
        self.assertEqual(self.r['latestReviewSummary'], {
            'include': 4198, 'exclude': 64, 'uncertain': 0,
            'categoryOnly': 0, 'secondReviewed': 1})

    def test_categories_and_buckets(self):
        self.assertEqual(self.r['bucketSplit']['admittedCounts'], {'t': 3493, 'b': 705})
        self.assertEqual(self.r['bucketSplit']['admittedCategoryCounts']['b']['星座'], 13)
        alloc = {r['cp']: r for r in self.r['draftFirstKeyAllocations']}
        self.assertTrue(all(alloc[cp]['firstKey'] == 'b' for cp in ZODIAC))
        for cp, (category, key) in REPAIRS.items():
            self.assertEqual((alloc[cp]['category'], alloc[cp]['firstKey']), (category, key))
        self.assertEqual(alloc[0x1FA8E]['firstKey'], 't')

    def test_pending_codes_and_notes_untouched(self):
        old = read(V14 / '拟物收入全量初稿.json')
        self.assertEqual(self.r['protectedHashes'], old['protectedHashes'])
        self.assertEqual(self.r['secondReview']['boundaryCps'], old['secondReview']['boundaryCps'])
        self.assertEqual([(r['cp'], r['oldCodes'], r['oldBucket']) for r in old['records']],
                         [(r['cp'], r['oldCodes'], r['oldBucket']) for r in self.r['records']])
        self.assertEqual(self.r['bucketAudit15']['egyptianPartsPending'], 140)
        for d in read(SNAPSHOT)['decisions']:
            if 'note' in d:
                self.assertEqual(self.r['reviewDecisions'][str(d['cp'])]['note'], d['note'])

    def test_saver_accepts_new_category_and_version(self):
        r = self.r
        data = {'format': 'pictorial-intake-human-review-v1', 'version': r['version'],
                'sourceIndexSHA256': r['sourceIndexSHA256'], 'scope': r['scope'],
                'allocationChanged': False, 'decisions': list(r['reviewDecisions'].values())}
        with tempfile.TemporaryDirectory() as folder:
            receipt = save_snapshot(data, Path(folder))
        self.assertEqual(receipt['summary']['explicitDecisions'], {'include': 4198, 'exclude': 64})


if __name__ == '__main__':
    unittest.main()
