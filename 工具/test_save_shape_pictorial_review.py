import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_shape_pictorial_review import OUT, read
from save_shape_pictorial_review import save_snapshot, validate
from audit_shape_historical_buckets import protect


class SavePictorialReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(OUT/'拟物收入全量初稿.json')

    def payload(self):
        return {'format':'pictorial-intake-human-review-v1','version':self.report['version'],
            'sourceIndexSHA256':self.report['sourceIndexSHA256'],'scope':self.report['scope'],
            'allocationChanged':False,'exportedAt':'2026-10-22T12:00:00Z',
            'decisions':[{'cp':ord('🔗'),'char':'🔗','decision':'include','note':'保留原始备注'}]}

    def test_roundtrip_idempotent_and_no_migration(self):
        data=self.payload();before=protect()
        with tempfile.TemporaryDirectory() as folder:
            result=save_snapshot(data,Path(folder));again=save_snapshot(data,Path(folder))
            self.assertEqual(result['path'],again['path'])
            self.assertEqual(read(Path(result['path'])),data)
            self.assertEqual(hashlib.sha256(Path(result['path']).read_bytes()).hexdigest(),result['sha256'])
            self.assertTrue(result['snapshotOnly']);self.assertFalse(result['allocationChanged'])
            self.assertEqual(result['summary']['queues']['propose']['include'],1)
        self.assertEqual(before,protect())

    def test_new_snapshot_never_overwrites_old(self):
        data=self.payload()
        with tempfile.TemporaryDirectory() as folder:
            first=save_snapshot(data,Path(folder));old=Path(first['path']).read_bytes()
            data['decisions'][0]['decision']='uncertain'
            second=save_snapshot(data,Path(folder))
            self.assertNotEqual(first['path'],second['path'])
            self.assertEqual(Path(first['path']).read_bytes(),old)

    def test_invalid_inputs_rejected(self):
        mutations=[lambda d:d.update(version='bad'),lambda d:d.update(sourceIndexSHA256='bad'),
            lambda d:d.update(allocationChanged=True),lambda d:d.update(scope={}),
            lambda d:d['decisions'].append(copy.deepcopy(d['decisions'][0])),
            lambda d:d['decisions'][0].update(cp=True),lambda d:d['decisions'][0].update(cp=9999999),
            lambda d:d['decisions'][0].update(char='x'),lambda d:d['decisions'][0].update(decision='yes'),
            lambda d:d['decisions'][0].update(note='x'*2001),lambda d:d['decisions'][0].update(path='../unsafe')]
        for mutate in mutations:
            d=self.payload();mutate(d)
            with self.assertRaises(ValueError):validate(d,self.report)

    def test_preserved_user_snapshot_is_complete(self):
        p=OUT/'人工审核保存/网页审核原始结果-484626a0b677a992dfab997530d5e5d46b4a9362d13deb0507ce8d93808fbe5b.json'
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'484626a0b677a992dfab997530d5e5d46b4a9362d13deb0507ce8d93808fbe5b')
        summary=validate(read(p),self.report)
        self.assertEqual(summary['explicitEntries'],1216)
        self.assertEqual(summary['queues']['propose'],{'total':1216,'include':1113,'exclude':6,'uncertain':97,'pending':0})


if __name__=='__main__':unittest.main()
