import copy
import hashlib
import tempfile
from pathlib import Path
import unittest
import zipfile

from audit_shape_historical_buckets import PROJECT, protect
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v6 import OUT, V5
from save_shape_pictorial_review import save_snapshot, validate


class PictorialV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(OUT / '拟物收入全量初稿.json')

    def payload(self):
        r = self.report
        return {'format': 'pictorial-intake-human-review-v1', 'version': r['version'],
                'sourceIndexSHA256': r['sourceIndexSHA256'], 'scope': r['scope'],
                'decisions': copy.deepcopy(list(r['reviewDecisions'].values())), 'allocationChanged': False}

    def test_original_choices_and_boundary_preserved(self):
        previous = read(V5 / '拟物收入全量初稿.json')
        self.assertEqual(self.report['records'], previous['records'])
        self.assertEqual(self.report['reviewDecisions'], previous['reviewDecisions'])
        s = self.report['secondReview']
        self.assertEqual((len(s['admittedCps']), len(s['excludedCps']), len(s['boundaryCps'])), (1258, 41, 7303))
        self.assertEqual(s['initialReviewedCount'], 0)
        self.assertEqual(sum(s['categoryCounts'].values()), 1258)
        self.assertEqual(len(s['categoryCounts']), 21)
        self.assertEqual(self.report['protectedHashes'], protect())

    def test_archive_restorable_and_originals_untouched(self):
        import json
        archive = self.report['secondReview']['archive']
        target = PROJECT / archive['relativePath']
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), archive['sha256'])
        with zipfile.ZipFile(target) as z:
            self.assertIsNone(z.testzip())
            manifest = json.loads(z.read('归档清单.json'))
            for name, digest in manifest.items():
                self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(), digest)
                if '/键位试验/' in name:
                    self.assertEqual(hashlib.sha256((PROJECT / name).read_bytes()).hexdigest(), digest)

    def test_round_two_category_and_note_roundtrip(self):
        payload = self.payload()
        row = payload['decisions'][0]
        row.update(category='装饰', secondReviewed=True, note='二审备注')
        with tempfile.TemporaryDirectory() as folder:
            result = save_snapshot(payload, Path(folder))
            self.assertEqual(read(Path(result['path'])), payload)
            self.assertEqual(result['summary']['secondReviewed'], 1)
        old = read(V5 / '拟物收入全量初稿.json')
        payload.update(version=old['version'])
        with self.assertRaises(ValueError):
            validate(payload, old)

    def test_invalid_second_review_fields_rejected(self):
        for fields in ({'category':'不存在的类别'}, {'secondReviewed':'true'}, {'secondReviewed':1}):
            payload = self.payload()
            payload['decisions'][0].update(fields)
            with self.assertRaises(ValueError):
                validate(payload, self.report)


if __name__ == '__main__':
    unittest.main()
