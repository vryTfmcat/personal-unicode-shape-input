import sys
import tempfile
import unittest
from pathlib import Path
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v17 import OUT, SNAPSHOT
from save_shape_pictorial_review import save_snapshot

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '原型/键位编辑器'))
import shape_overview as so


class V17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = read(OUT / '拟物收入全量初稿.json')
        cls.o = so.get_overview()
        cls.intake = so.exclusive_intake()

    def test_latest_review_preserved_with_only_authorized_provisional_admissions(self):
        provisional = set(self.r['stageClosure17']['provisionalEgyptianCps'])
        self.assertEqual(len(provisional), 140)
        for d in read(SNAPSHOT)['decisions']:
            current = self.r['reviewDecisions'][str(d['cp'])]
            self.assertEqual(current.get('note'), d.get('note'))
            self.assertEqual(current.get('decision'), 'include' if d['cp'] in provisional else d.get('decision'))
        self.assertEqual(self.r['bucketSplit']['admittedCounts'], {'t': 3630, 'b': 732})
        self.assertEqual(self.r['latestReviewSummary']['exclude'], 70)
        self.assertFalse(self.r['stageClosure17']['explicitBucketOverrides'])
        self.assertNotIn('roundFlowers', self.r['discoveryQueues'])
        self.assertNotIn('bInterface', self.r['discoveryQueues'])

    def test_all_geometry_prefixes_exclude_all_admissions(self):
        keys = self.intake.keys()
        prefixes = set(self.o.layers.entries) | set(so.cleanup_additions()) | set(so.centre_additions())
        for prefix in prefixes:
            members = self.o.allocation_members(prefix)
            if prefix not in ('t', 'b'):
                self.assertFalse(members.keys() & keys, prefix)
        for key in ('t', 'b'):
            expected = {cp for cp, row in self.intake.items() if row['firstKey'] == key}
            self.assertEqual(set(self.o.allocation_members(key)), expected)

    def test_every_position_and_reserved_collection_exclude_admissions(self):
        for pos in range(1, 5):
            for key in so.LETTERS:
                if pos == 1 and key in ('t', 'b'):
                    continue
                self.assertFalse(set(self.o.key_members(pos, key, True)) & self.intake.keys(), (pos, key))
        badges = set(self.o.collections['z']) & self.intake.keys()
        self.assertEqual(len(badges), 15)
        self.assertFalse(set(self.o.allocation_members('z')) & badges)

    def test_details_queries_and_historical_original_are_consistent(self):
        for cp in (0x273F, 0x1F237, self.r['stageClosure17']['provisionalEgyptianCps'][0]):
            row = self.o.detail(cp, True)
            self.assertTrue(row['pictorialIntake'])
            self.assertFalse(row['paths'])
            result = self.o.query({'text':[f'U+{cp:X}'], 'allocation':['1']})
            self.assertEqual(result['total'], 1)
            self.assertFalse(result['rows'][0]['codes'])
        cp = next(cp for cp in self.intake if self.o.rows.get(cp, {}).get('codes'))
        self.assertTrue(self.o.brief(cp)['codes'])
        self.assertFalse(self.o.brief(cp, True)['codes'])
        self.assertEqual(self.o.query({'position':['1'], 'key':['b'], 'allocation':['1']})['total'], 732)

    def test_new_snapshot_can_be_saved(self):
        r = self.r
        payload = dict(format='pictorial-intake-human-review-v1', version=r['version'],
                       sourceIndexSHA256=r['sourceIndexSHA256'], scope=r['scope'],
                       allocationChanged=False, decisions=list(r['reviewDecisions'].values()))
        with tempfile.TemporaryDirectory() as folder:
            receipt = save_snapshot(payload, Path(folder))
        self.assertEqual(receipt['summary']['explicitDecisions']['include'], 4362)


if __name__ == '__main__':
    unittest.main()
