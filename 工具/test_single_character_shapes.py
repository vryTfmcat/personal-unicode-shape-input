"""Exact non-count shape approvals: no mirrored brace or unstable count expansion."""
import hashlib
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
import shape_structure_bindings as structural

class SingleCharacterShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview()
        cls.a=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')['singleCharacterShapeAcceptance20261026Batch1']
        cls.candidate=so.read(ROOT/cls.a['candidateReport'])

    def test_left_brace_one_whole_object_and_only_one_new_code(self):
        a=self.a['records']['123'];row=self.o.brief(123,True);d=self.o.detail(123,True)
        self.assertEqual((row['bucket'],row['familyKey']),('f','w'))
        self.assertEqual(set(row['codes']),set(a['beforeCodes'])|{'fweg'})
        self.assertEqual(row['preferredCodes'],[])
        self.assertEqual({p['code'] for p in d['paths']},set(row['codes']))
        p=next(p for p in d['paths'] if p['code']=='fweg');e=p['evidence'][0]
        self.assertEqual(e['objectId'],e['fourthObjectId'])
        self.assertIn(e['objectId'],{o['id'] for o in d['objects']})
        self.assertEqual(e['familyTarget'],'body')
        self.assertNotIn(123,self.o.allocation_members('fwei'))
        self.assertNotIn(125,self.o.allocation_members('fweg'))
        self.assertEqual(self.o.brief(125,True),self.o.brief(125,False)|{'reason':self.o.brief(125,True)['reason']})
        self.assertEqual((self.o.brief(123,False)['bucket'],self.o.brief(123,False)['familyKey']),('a','j'))
        self.assertNotIn('fweg',self.o.brief(123,False)['codes'])
        for c in a['beforeCodes']:self.assertIn(123,self.o.allocation_members(c))

    def test_double_leaf_exact_removal_and_counts_stay_unstable(self):
        a=self.a['records']['42951'];row=self.o.brief(42951,True);d=self.o.detail(42951,True)
        self.assertEqual((row['bucket'],row['familyKey']),('i','b'))
        self.assertEqual(set(row['codes']),{'ibis','ibiv','ibiw','ibma','ibmd'})
        self.assertEqual(row['preferredCodes'],[])
        self.assertNotIn(42951,self.o.key_members(2,'o',True))
        self.assertIn(42951,self.o.key_members(2,'o',False))
        self.assertEqual({p['code'] for p in d['paths']},set(row['codes']))
        self.assertTrue(next(r for r in d['familyRoutes'] if r['familyKey']=='b')['primary'])
        self.assertFalse(any(r['familyKey']=='o' for r in d['familyRoutes']))
        for c in a['withdrawnCurrentCodes']:self.assertNotIn(42951,self.o.allocation_members(c))
        self.assertEqual(set(self.o.brief(42951,False)['codes']),set(a['beforeCodes']))
        record=next(r for r in structural.review_report()['records'] if r['cp']==42951)
        self.assertEqual(record['status'],'unstable');self.assertFalse(record['eligible']);self.assertEqual(record['codes'],[])
        self.assertEqual(min(d['codeCounts'].values()),103)

    def test_authority_pins_structure_unchanged_and_both_query_orders(self):
        p=ROOT/self.a['candidateReport']
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),self.a['candidateSHA256'])
        self.assertEqual(hashlib.sha256((ROOT/structural.totals.authority()['generation']['baseRuntime'] if structural.totals.active() else structural.PATH).read_bytes()).hexdigest(),self.candidate['structureSHA256'])
        self.assertEqual(structural.data()['version'],('structure-count-bindings-v10' if structural.totals.active() else 'structure-count-bindings-v9'))
        self.assertEqual(len(structural.queues()['scopePending']),2073)
        for cp,a in self.a['records'].items():
            for code in a['afterCodes']:
                front=self.o.query(dict(allocation=['1'],prefix=[code]))
                back=self.o.query(dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=[code[1:]+code[0]]))
                self.assertEqual(front['total'],back['total'])
                self.assertEqual([r['cp'] for r in front['rows']],[r['cp'] for r in back['rows']])
                self.assertEqual(self.o.detail(int(cp),True)['codeCounts'][code],front['total'])
        self.assertEqual(len(self.o.allocation_members('fweg')),86)
        self.assertIn(123,self.o.key_members(2,'w',True))
        self.assertIn(123,self.o.allocation_members('f'))
        self.assertIn(123,self.o.allocation_members('a'))

if __name__=='__main__':unittest.main()
