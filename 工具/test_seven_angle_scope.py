"""Guard exact single-character scope, union counts, and the original answers."""
import hashlib
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
import shape_structure_bindings as binding

class SevenAngleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview();cls.report=binding.review_report()
        cls.acceptance=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')['sevenAngleScopeAcceptance20261025']
        cls.previous=so.read(ROOT/cls.acceptance['generation']['baseReport'])

    def test_only_seven_gets_exactly_one_selected_feature(self):
        old={r['cp']:r for r in self.previous['records']}
        frozen=so.read(ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v8/大组结构键位分配.json')
        self.assertEqual([r['cp'] for r in frozen['records'] if r!=old[r['cp']]],[55])
        self.assertEqual(next(r for r in self.report['records'] if r['cp']==55),next(r for r in frozen['records'] if r['cp']==55))
        row=next(r for r in self.report['records'] if r['cp']==55)
        self.assertEqual(row['codes'],['aaau'])
        self.assertEqual(row['acceptedBoundary']['selectedFeatures'],['corners'])
        self.assertEqual(row['acceptedBoundary']['selectedCodes'],['aaau'])
        b=self.o.brief(55,True)
        self.assertEqual((b['bucket'],b['familyKey']),('a','a'))
        self.assertEqual(set(b['codes']),set(old[55]['oldCodes'])|({'aqau'} if so.count_bc.policy() else {'aaau'}))
        self.assertEqual(b['preferredCodes'],[])
        self.assertEqual(self.o.brief(55,False)['familyKey'],'j')
        self.assertNotIn('aaau',self.o.brief(55,False)['codes'])
        self.assertNotIn(55,self.o.allocation_members('aajb'))
        self.assertFalse(binding.record(49))

    def test_exact_union_all_members_details_and_front_back_order(self):
        expected=set(self.previous['codeMembers']['aaau'])|{55}
        self.assertEqual(len(expected),80)
        if so.count_bc.policy():expected=expected-{55}
        self.assertEqual(set(self.o.allocation_members('aaau')),expected)
        for cp in expected:
            d=self.o.detail(cp,True);self.assertEqual(d['codeCounts']['aaau'],79 if so.count_bc.policy() else 80)
            p=next(p for p in d['paths'] if p['code']=='aaau');e=p['evidence'][0]
            self.assertEqual(e['objectId'],e['fourthObjectId'])
            self.assertIn(e['objectId'],{o['id'] for o in d['objects']})
        front=self.o.query(dict(allocation=['1'],prefix=['aaau']))
        back=self.o.query(dict(allocation=['1'],order=['back'],prefix=['aaua']))
        self.assertEqual(front['total'],79 if so.count_bc.policy() else 80);self.assertEqual(back['total'],79 if so.count_bc.policy() else 80)
        self.assertEqual([r['cp'] for r in front['rows']],[r['cp'] for r in back['rows']])
        self.assertFalse(expected & so.exclusive_intake().keys())

    def test_authority_proof_and_raw24_answers_are_locked(self):
        a=self.acceptance
        for rel,h in [(a['proofReport'],a['proofSHA256']),(a['candidateReport'],a['candidateSHA256']),
                      (a['generation']['baseReport'],a['generation']['baseSHA256'])]:
            self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),h)
        self.assertEqual(a['originalAnswer'],'接受角折主体及aaau入口')
        raw=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/代表字实际查找测试/多路径规则草案/本人24字审核答复-20261025.json'
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),'38acc193520dfd6f2298e8872fbb9f0ad87b64a65f03d36a983bb3eded032367')

if __name__=='__main__':unittest.main()
