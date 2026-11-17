"""Guard Đ's partial code acceptance independently of machine count suggestions."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
import shape_structure_bindings as binding

class DStrokeKTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview()
        cls.a=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')['dStrokeKScopeAcceptance20261026']
        cls.base=so.read(ROOT/cls.a['generation']['baseReport'])

    def test_only_selected_three_codes_and_two_withdrawals(self):
        row=self.o.brief(272,True);detail=self.o.detail(272,True)
        self.assertEqual((row['bucket'],row['familyKey']),('i','k'))
        self.assertEqual(row['preferredCodes'],[])
        self.assertEqual(set(row['codes']),so.joint_bc.migrate_structure(272,binding.totals.resolve_codes(272,{'ikab','ikgu','ikjb','ioma'}|({'ikqu'} if so.external_groups.curve_restore_policy() else set()))))
        self.assertEqual({p['code'] for p in detail['paths']},set(row['codes']))
        self.assertEqual({p['code'] for p in detail['paths'] if p.get('compatibilityOnly')},{'ioma'})
        self.assertEqual(set(self.o.brief(272,False)['codes']),{'iocv','iosc','ioma'})
        self.assertNotIn(272,self.o.key_members(2,'o',True))
        for code in (('ikqb','ikqu','ikjb','iocv','iosc') if binding.totals.active() else ('ikqb','ikqt','iocv','iosc')):
            self.assertNotIn(272,self.o.allocation_members(code))
        for code in row['codes']:
            front=self.o.query(dict(allocation=['1'],prefix=[code]))
            back=self.o.query(dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=[code[1:]+code[0]]))
            self.assertEqual([r['cp'] for r in front['rows']],[r['cp'] for r in back['rows']])
            self.assertEqual(detail['codeCounts'][code],front['total'])
        self.assertIn('两笔写成',self.a['originalAnswer'])

    def test_only_D_changes_and_machine_curve_and_prior_authorities_remain(self):
        report=(so.read(ROOT/binding.totals.authority()['generation']['baseReport']) if binding.totals.active() else binding.review_report());before={r['cp']:r for r in self.base['records']}
        self.assertEqual([r['cp'] for r in report['records'] if r!=before[r['cp']]],[272])
        row=next(r for r in report['records'] if r['cp']==272)
        self.assertEqual(row['statistics'],before[272]['statistics'])
        self.assertEqual(row['statistics']['curveStrokes'],1)
        self.assertEqual(row['acceptedBoundary']['rejectedCodes'],['ikqu'])
        self.assertEqual(report['definitions'],self.base['definitions'])
        self.assertEqual(report['codeMembers']['ikqu'],self.base['codeMembers']['ikqu'])
        self.assertEqual(report['sevenAngleScopeAcceptance'],self.base['sevenAngleScopeAcceptance'])
        self.assertEqual(len(self.o.allocation_members('ikab')),3)
        self.assertEqual(len(self.o.allocation_members('ikgu')),1)
        self.assertEqual(len(self.o.allocation_members(binding.totals.resolve_codes(272,['ikjb'])[0])),1 if so.joint_bc.policy() else 2)
        self.assertEqual(len(self.o.allocation_members('ikqu')),(0 if binding.totals.active() else 9+len(so.external_groups.count_members('ikqu'))))
        self.assertNotIn(272,binding.queues()['scopePending'])

if __name__=='__main__':unittest.main()
