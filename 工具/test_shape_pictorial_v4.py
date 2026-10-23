from pathlib import Path
import tempfile
import unittest
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR,read
from build_shape_pictorial_review_v4 import OUT,SNAPSHOT,FLORAL,ROCKETS,EXCLUDED
from save_shape_pictorial_review import save_snapshot


class PictorialV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=read(OUT/'拟物收入全量初稿.json')
        cls.rows={r['cp']:r for r in cls.report['records']}

    def test_full_block_explicit_partition(self):
        self.assertEqual((len(FLORAL),len(ROCKETS),len(EXCLUDED)),(24,4,20))
        self.assertEqual(FLORAL|ROCKETS|EXCLUDED,set(range(0x1F650,0x1F680)))
        self.assertFalse(FLORAL&ROCKETS or FLORAL&EXCLUDED or ROCKETS&EXCLUDED)
        for cps,decision,category in ((FLORAL,'include','装饰'),(ROCKETS,'include','物品／火箭'),(EXCLUDED,'exclude','文字标点／抽象纹样')):
            for cp in cps:
                self.assertEqual(self.report['reviewDecisions'][str(cp)]['decision'],decision)
                self.assertEqual(self.rows[cp]['category'],category)

    def test_queues_and_unrelated_choices(self):
        self.assertEqual(set(self.report['reviewQueues']['decoration']['cps']),FLORAL)
        self.assertEqual(set(self.report['reviewQueues']['rockets']['cps']),ROCKETS)
        for r in read(SNAPSHOT)['decisions']:
            if r['cp'] not in FLORAL|ROCKETS|EXCLUDED:
                self.assertEqual(self.report['reviewDecisions'][str(r['cp'])],r)
        self.assertEqual(self.report['reviewSummary']['currentKnownCounts'],{'include':1258,'exclude':41,'uncertain':58})
        self.assertEqual(self.report['policy']['geometryRetentionExceptions'],[0x1CCA3])

    def test_sources_and_saved_snapshot(self):
        self.assertEqual(self.report['protectedHashes'],protect())
        current=read(EDITOR/'data/pictorial-intake-review.json')
        if current['version']==self.report['version']:
            self.assertEqual(current['records'],self.report['records'])
        else:
            self.assertIn(self.report['version'],current['lineageVersions'])
            expected=[]
            for r in self.report['records']:
                category=r['category']
                if current.get('classificationRepairs'):
                    from build_shape_pictorial_review_v7 import face_category,EXTRA_SIGNS
                    correction=face_category(r['cp'],r['name']) if category=='人脸与表情' else None
                    if correction:category=correction[0]
                    if r['cp'] in EXTRA_SIGNS:category='象征标志'
                expected.append((r['cp'],category,r['oldCodes']))
            self.assertEqual([(r['cp'],r['category'],r['oldCodes']) for r in current['records']],expected)
        payload={'format':'pictorial-intake-human-review-v1','version':self.report['version'],
            'sourceIndexSHA256':self.report['sourceIndexSHA256'],'scope':self.report['scope'],
            'decisions':list(self.report['reviewDecisions'].values()),'allocationChanged':False}
        with tempfile.TemporaryDirectory() as folder:
            result=save_snapshot(payload,Path(folder))
            self.assertEqual(read(Path(result['path'])),payload)
            self.assertFalse(result['runtimeDeployed'])


if __name__=='__main__':unittest.main()
