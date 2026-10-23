import unittest,json
from pathlib import Path
from shape_bucket_scope import Scripts,collection,full_scope,ACTIVE
from reserved_shape_buckets import ROOT


class ScopeTests(unittest.TestCase):
    def test_known_characters(self):
        rows,_=full_scope();lookup={r['cp']:r for r in rows}
        for cp in (0x4e00,0x2e80,0x2f00,0x31c0,0x2ff0,0x328c):self.assertEqual(lookup[cp]['collection'],'z')
        for cp in (0xac00,0xc729,0x17000,0x183df,0x18b00,0x3042,0x30a2):self.assertEqual(lookup[cp]['collection'],'y')
        for cp in (0x3105,0x1b170,0xf40,0x1000,0xa000,0x25cb,0x2630,0x1f600):self.assertIsNone(lookup[cp]['collection'])

    def test_completed_draft(self):
        latest=ROOT/'最新分桶.json'
        if not latest.exists():self.skipTest('draft not generated')
        run=Path(json.loads(latest.read_text(encoding='utf-8'))['run']);summary=json.loads((run/'摘要.json').read_text(encoding='utf-8'))
        allrows=json.loads((run/'全部收纳.json').read_text(encoding='utf-8'))['characters'];lookup={r['cp']:r for r in allrows}
        expected,_=full_scope();self.assertEqual(len(lookup),len(expected));self.assertEqual(len(lookup),len(allrows))
        counts={k:0 for k in 'abcdefghijklmnopqrstuvwxyz'}
        for r in expected:
            actual=lookup[r['cp']];self.assertEqual(actual['char'],r['char'])
            if r['collection']:self.assertEqual(actual['primary'],r['collection']);self.assertEqual(actual['aliases'],[])
            else:
                self.assertTrue(actual['primary'] is None or actual['primary'] in ACTIVE)
                self.assertTrue(all(k in ACTIVE for k in actual['aliases']))
            if actual['primary']:counts[actual['primary']]+=1
        self.assertEqual(counts['x'],0)
        for k in ACTIVE:self.assertTrue(summary['capacity']['plannedLower']<=counts[k]<=summary['capacity']['plannedUpper'])
        self.assertEqual(counts,summary['counts'])


if __name__=='__main__':unittest.main()
