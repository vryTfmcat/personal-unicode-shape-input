import unittest
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v9 import OUT as V9
from build_shape_pictorial_review_v10 import OUT, MOVES


class V10Tests(unittest.TestCase):
    def test_only_categories_change(self):
        old = read(V9 / '拟物收入全量初稿.json')
        new = read(OUT / '拟物收入全量初稿.json')
        self.assertEqual(new['reviewDecisions'], old['reviewDecisions'])
        self.assertEqual(new['secondReview']['boundaryCps'], old['secondReview']['boundaryCps'])
        self.assertEqual(new['protectedHashes'], old['protectedHashes'])
        self.assertEqual([(r['cp'], r['oldCodes']) for r in old['records']],
                         [(r['cp'], r['oldCodes']) for r in new['records']])
        rows = {r['cp']: r for r in new['records']}
        for cp, category in MOVES.items():
            self.assertEqual(rows[cp]['category'], category)
        counts = new['secondReview']['categoryCounts']
        self.assertEqual(sum(counts.values()), 3620)
        for category, count in {'人物与动作':907, '建筑与场所':42, '自然物象':71,
                                '棋牌符号':204, '标识分类':6}.items():
            self.assertEqual(counts[category], count)

    def test_actual_browser_save(self):
        report = read(OUT / '拟物收入全量初稿.json')
        saved = read(OUT / '人工审核保存/网页审核原始结果-05d3da7d7c47bc67bf24ee30c751c5aa94984b587693e865fb4a4b0c20efabfe.json')
        self.assertEqual({str(r['cp']):r for r in saved['decisions']}, report['reviewDecisions'])


if __name__ == '__main__':
    unittest.main()
