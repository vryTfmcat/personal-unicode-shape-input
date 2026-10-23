"""Pinned full-run and read-only HTTP contract checks for the unified overview."""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.parse import quote
from http.server import ThreadingHTTPServer

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / '原型/键位编辑器'), str(PROJECT / '工具')]
import shape_overview
from serve import GraphStore, handler_factory


class OverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected = [PROJECT / '数据/三模式/全形核对版.json',
                         PROJECT / '原型/键位编辑器/data/shape-review-profile.json',
                         PROJECT / '数据/三模式/规则库/四键实验/人工审议.json',
                         shape_overview.RUN / '发布核对索引.json']
        cls.hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.protected]
        cls.overview = shape_overview.get_overview()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_factory(GraphStore()))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        assert cls.hashes == [hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.protected]

    def request(self, path, method='GET'):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=30)
        conn.request(method, '/api/shape-overview/' + quote(path, safe='/?=&.'))
        response = conn.getresponse()
        status, body = response.status, response.read()
        conn.close()
        return status, body

    def test_104_keys_and_empty_keys(self):
        self.assertEqual(len(self.overview.keys), 104)
        for p in range(1, 5):
            keys = [k for k in self.overview.keys if k['position'] == p]
            self.assertEqual({k['key'] for k in keys}, set(shape_overview.LETTERS))
        self.assertTrue(any(not k['assigned'] for k in self.overview.keys))
        z = next(k for k in self.overview.keys if k['position'] == 3 and k['key'] == 'z')
        self.assertEqual(z['meaning'], '连接横笔组')

    def test_chvc_structure_trial_is_lossless_and_separate(self):
        report=shape_overview.chvc_trial()
        self.assertEqual(report['capacity']['preferSpecific'],418)
        self.assertEqual(len(shape_overview.chvc_members('all')),1562)
        self.assertEqual(len(shape_overview.chvc_members('centre')),101)
        self.assertEqual(report['comparisons']['combined']['maxGroup'],1188)
        q=self.overview.query({'chvcTrial':['preferred']})
        self.assertEqual(q['total'],418)
        self.assertTrue(all(r['chvcPriority']['preferredCodes'] for r in q['rows']))
        self.assertEqual(self.overview.query({'prefix':['chvc']})['total'],1562)
        self.assertEqual(self.overview.detail(ord('E'))['chvcTrial']['preferredCodes'],['chzt'])
        self.assertEqual(self.overview.detail(ord('F'))['chvcTrial']['preferredCodes'],['chzb'])
        self.assertTrue(any(p['code']=='chmw' and p['preferred'] for p in self.overview.detail(ord('T'))['paths']))
        trial_row=next(r for r in report['records'] if r['preferredCodes'] and r['preferredCodes']!=r['oldPreferredCodes'])
        cp=trial_row['cp']
        self.assertEqual(self.overview.brief(cp,True)['preferredCodes'],trial_row['preferredCodes'])
        self.assertEqual(self.overview.brief(cp,False)['preferredCodes'],trial_row['oldPreferredCodes'])
        self.assertEqual([p['code'] for p in self.overview.detail(cp,True)['paths'] if p['preferred']],trial_row['preferredCodes'])
        self.assertEqual(self.request('query?chvcTrial=bogus')[0],400)

    def test_coverage_queues_are_separate(self):
        self.assertEqual(self.overview.bootstrap['queueCounts'], dict(first=6716, prior=4621,
                         withdrawn=33, historical=93, affected=3, unclassified=5220))
        self.assertTrue(set(self.overview.queues['prior']) <= set(self.overview.queues['first']))
        self.assertFalse(set(self.overview.queues['unclassified']) & set(self.overview.rows))
        self.assertEqual({chr(cp) for cp in self.overview.queues['affected']}, set('𐏓𒌋𐎓'))

    def test_all_prefix_counts_and_layers(self):
        expected = {'chvc':1562,'mdez':1183,'ajvg':1160,'cxvc':1011,'iocv':1009,
                    'crvg':831,'chzt':17,'chzb':17,'ioym':12}
        for code, count in expected.items():
            q = self.overview.query({'prefix':[code]})
            self.assertEqual(q['total'], count, code)
            self.assertEqual(sum(q['groups'].values()), count, code)
        for length in range(1, 5):
            groups = self.overview.collision_groups(length)
            self.assertEqual(len(groups), self.overview.capacity['prefixDistribution'][str(length)]['occupied'])

    def test_short_codes_do_not_break_keymap(self):
        short = [(r,c) for r in self.overview.rows.values() for c in r['codes'] if len(c)==3]
        self.assertTrue(short)
        for r, code in short[:10]:
            self.assertIn(r['cp'], self.overview.layers.entries[code])

    def test_detail_objects_and_original_codes(self):
        q = self.overview.detail(ord('Q'))
        self.assertTrue({'iose','iosc','ioym'} <= {p['code'] for p in q['paths']})
        self.assertTrue(all(e['objectId'] == e['fourthObjectId'] for p in q['paths'] for e in p['evidence']))
        self.assertIn('chzt', self.overview.detail(ord('E'))['codeCounts'])
        self.assertIn('chzb', self.overview.detail(ord('F'))['codeCounts'])

    def test_pagination_and_unclassified_search(self):
        a=self.overview.query({'prefix':['chvc']})
        b=self.overview.query({'prefix':['chvc'],'offset':['60']})
        self.assertEqual(len(a['rows']),60)
        self.assertFalse({r['cp'] for r in a['rows']} & {r['cp'] for r in b['rows']})
        cp=self.overview.unclassified[0]
        q=self.overview.query({'text':[f'U+{cp:X}']})
        self.assertEqual([r['cp'] for r in q['rows']],[cp])
        self.assertEqual(self.overview.query({'prefix':['y']})['total'],19996)

    def test_http_read_only_and_allowlist(self):
        self.assertEqual(self.request('bootstrap')[0],200)
        self.assertEqual(self.request('query?prefix=chzt')[0],200)
        for path in ['query?prefix=abcde','query?position=5&key=z','detail?cp=-1',
                     'collisions?length=9']:
            self.assertEqual(self.request(path)[0],400,path)
        for path in ['../../人工审议.json','asset?id=../../人工审议.json','publish']:
            self.assertEqual(self.request(path)[0],404,path)
        self.assertEqual(self.request('bootstrap','PUT')[0],404)
        self.assertEqual(self.request('bootstrap','POST')[0],404)

    def test_assets_and_bootstrap_versions(self):
        for name in ['Q','D','EF']:
            status, data = self.request('asset?id='+name)
            self.assertEqual(status,200)
            self.assertTrue(data.startswith(b'\x89PNG'))
        status, data = self.request('bootstrap')
        boot=json.loads(data)
        self.assertEqual(boot['sha256'],shape_overview.INDEX_SHA)
        self.assertNotEqual(boot['id'],boot['deployed']['experimentId'])


if __name__ == '__main__':
    unittest.main()
