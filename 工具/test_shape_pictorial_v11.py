import unittest
from collections import Counter
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_pictorial_review_v10 import OUT as V10
from build_shape_pictorial_review_v11 import OUT, EXPORT


class V11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(OUT/'拟物收入全量初稿.json')
        cls.rows = {r['cp']:r for r in cls.report['records']}

    def test_latest_export_preserved(self):
        exported = read(OUT/'Chrome最新人工审核原始导出.json')
        self.assertEqual(sha(EXPORT),sha(OUT/'Chrome最新人工审核原始导出.json'))
        self.assertEqual(self.report['reviewDecisions'],{str(d['cp']):d for d in exported['decisions']})
        self.assertEqual(Counter(d.get('decision') for d in exported['decisions']),{'include':3629,'exclude':54})

    def test_identity_codes_and_boundary_protected(self):
        previous = read(V10/'拟物收入全量初稿.json')
        self.assertEqual(self.report['protectedHashes'],previous['protectedHashes'])
        self.assertEqual(self.report['secondReview']['boundaryCps'],previous['secondReview']['boundaryCps'])
        self.assertEqual([(r['cp'],r['oldCodes'],r['oldBucket']) for r in previous['records']],
                         [(r['cp'],r['oldCodes'],r['oldBucket']) for r in self.report['records']])

    def test_candidates_are_not_reviewed_or_admitted(self):
        topics = ('omittedObjects','omittedSigns','omittedVariants')
        all_cps = [cp for key in topics for cp in self.report['discoveryQueues'][key]['cps']]
        self.assertEqual(len(all_cps),400)
        self.assertEqual(len(set(all_cps)),400)
        self.assertFalse(set(map(str,all_cps)) & self.report['reviewDecisions'].keys())
        for cp in all_cps:
            self.assertFalse(self.rows[cp]['omissionCandidate']['humanAccepted'])
        for char in '☃☕⛵🚑🦏🫁🫶☠🩱☖✿':self.assertIn(ord(char),all_cps)
        for char in '♥♡♀♂♠♣♦🚾𜷴○●🙨🙴':self.assertNotIn(ord(char),all_cps)
        self.assertEqual(sum(self.rows[cp]['proposal']=='exclude' for cp in all_cps),28)

    def test_label_and_counts(self):
        counts = self.report['secondReview']['categoryCounts']
        self.assertEqual(counts['标识'],6)
        self.assertNotIn('标识分类',counts)
        self.assertEqual(sum(counts.values()),3629)
        self.assertEqual(len(self.report['secondReview']['admittedCps']),3629)
        aliases = read(EDITOR/'data/pictorial-category-labels.json')['aliases']
        for old in ('标识分类','安全标识','交通指示牌'):self.assertEqual(aliases[old],'标识')


if __name__ == '__main__':unittest.main()
