import copy
import unittest
from build_shape_pictorial_review import EDITOR, read
from save_shape_pictorial_review import validate


class CategoryLabelTests(unittest.TestCase):
    def test_rename_keeps_source_members_and_accepts_new_saved_label(self):
        report = read(EDITOR / 'data/pictorial-intake-review.json')
        labels = read(EDITOR / 'data/pictorial-category-labels.json')['aliases']
        self.assertEqual(labels, {'交通指示牌': '安全标识'})
        records = [r for r in report['records'] if r['category'] == '交通指示牌']
        self.assertTrue(records)
        cp = records[0]['cp']
        payload = {'format': 'pictorial-intake-human-review-v1', 'version': report['version'],
                   'sourceIndexSHA256': report['sourceIndexSHA256'], 'scope': report['scope'],
                   'allocationChanged': False,
                   'decisions': [{'cp': cp, 'char': chr(cp), 'category': '安全标识',
                                  'note': '保留备注', 'secondReviewed': True, 'decision': 'include'}]}
        self.assertEqual(validate(payload, report)['secondReviewed'], 1)
        old = copy.deepcopy(payload)
        old['decisions'][0]['category'] = '交通指示牌'
        self.assertEqual(validate(old, report)['secondReviewed'], 1)


if __name__ == '__main__':
    unittest.main()
