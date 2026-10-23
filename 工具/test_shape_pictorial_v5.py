from pathlib import Path
import tempfile
import unittest
from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import read
from build_shape_pictorial_review_v5 import OUT,V4
from save_shape_pictorial_review import save_snapshot


class PictorialV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=read(OUT/'拟物收入全量初稿.json')

    def test_geometry_exception_revoked(self):
        r=self.report
        self.assertEqual(r['policy']['geometryRetentionExceptions'],[])
        self.assertTrue(r['policy']['exclusiveAfterIndividualApproval'])
        self.assertNotIn('dual',r['reviewQueues'])
        self.assertFalse(any(row.get('geometryRetention') for row in r['records']))
        for row in r['records']:
            if row['cp'] in (0x1CCA2,0x1CCA3):
                self.assertEqual(row['entryPolicy'],'t-exclusive')
                self.assertEqual(row['category'],'游戏图标')
                self.assertEqual(r['reviewDecisions'][str(row['cp'])]['decision'],'include')

    def test_previous_work_preserved(self):
        previous=read(V4/'拟物收入全量初稿.json')
        self.assertEqual(self.report['reviewDecisions'],previous['reviewDecisions'])
        self.assertEqual(self.report['ornamentalBlockAcceptance'],previous['ornamentalBlockAcceptance'])
        self.assertEqual([(r['cp'],r['oldBucket'],r['oldCodes']) for r in self.report['records']],
                         [(r['cp'],r['oldBucket'],r['oldCodes']) for r in previous['records']])
        self.assertEqual(self.report['protectedHashes'],protect())

    def test_current_snapshot_save(self):
        r=self.report
        payload={'format':'pictorial-intake-human-review-v1','version':r['version'],
            'sourceIndexSHA256':r['sourceIndexSHA256'],'scope':r['scope'],
            'decisions':list(r['reviewDecisions'].values()),'allocationChanged':False}
        with tempfile.TemporaryDirectory() as folder:
            result=save_snapshot(payload,Path(folder))
            self.assertEqual(read(Path(result['path'])),payload)
            self.assertFalse(result['runtimeDeployed'])


if __name__=='__main__':unittest.main()
