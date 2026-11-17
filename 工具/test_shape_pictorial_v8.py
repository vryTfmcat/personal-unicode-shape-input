import copy
from pathlib import Path
import tempfile
import unittest
from build_shape_pictorial_review import read,sha
from build_shape_pictorial_review_v8 import OUT,V7
from save_shape_pictorial_review import validate,save_snapshot
from audit_shape_historical_buckets import protect


class V8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read(OUT/'拟物收入全量初稿.json')

    def test_exact_human_export_preserved(self):
        source=read(OUT/'Chrome人工审核原始导出.json')
        self.assertEqual(self.r['reviewDecisions'],{str(d['cp']):d for d in source['decisions']})
        self.assertEqual(self.r['sourceReviewSHA256'],sha(OUT/'Chrome人工审核原始导出.json'))
        self.assertEqual(validate(source,read(V7/'拟物收入全量初稿.json'))['explicitDecisions'],
                         {'include':3620,'exclude':43,'uncertain':13})
        self.assertEqual(self.r['records'],read(V7/'拟物收入全量初稿.json')['records'])
        self.assertEqual(self.r['protectedHashes'],protect())

    def test_category_totals_and_no_automatic_second_confirmation(self):
        second=self.r['secondReview']
        self.assertEqual(len(second['admittedCps']),3620)
        self.assertEqual(len(second['excludedCps']),43)
        self.assertEqual(sum(second['categoryCounts'].values()),3620)
        self.assertEqual(second['initialReviewedCount'],0)
        self.assertEqual(len(second['boundaryCps']),7303)
        self.assertEqual(self.r['chromeReviewImport']['oldUncertainNow'],{'include':45,'exclude':2,'uncertain':11})

    def test_snapshot_roundtrip(self):
        r=self.r
        payload={'format':'pictorial-intake-human-review-v1','version':r['version'],
                 'sourceIndexSHA256':r['sourceIndexSHA256'],'scope':r['scope'],
                 'decisions':copy.deepcopy(list(r['reviewDecisions'].values())),'allocationChanged':False}
        with tempfile.TemporaryDirectory() as folder:
            receipt=save_snapshot(payload,Path(folder))
            self.assertEqual(read(Path(receipt['path'])),payload)
            self.assertEqual(receipt['summary']['secondReviewed'],0)


if __name__=='__main__':unittest.main()
