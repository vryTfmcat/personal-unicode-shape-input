"""Two explicitly approved D subjects: scope, relative size, history and queries."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
import shape_structure_bindings as structural

class DSubjectHoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview()
        cls.a=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')['dSubjectHoleShapeAcceptance20261027Batch1']

    def test_only_approved_hole_routes_and_compatibility(self):
        later=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json').get('dSubjectHoleShapeAcceptance20261027Batch3')
        self.assertEqual(set(self.o.allocation_members('ikcv')),{119811,127251}|({127376} if later else set()))
        for cp,keep,old_count in [(119811,'iold',9),(127251,'dscv',3)]:
            b=self.o.brief(cp,True);d=self.o.detail(cp,True)
            self.assertEqual(set(b['codes']),{keep,'ikcv'})
            self.assertEqual(b['preferredCodes'],[])
            self.assertEqual((b['bucket'],b['familyKey']),('i','k'))
            self.assertEqual(len(self.o.brief(cp,False)['codes']),old_count)
            self.assertEqual({p['code'] for p in d['paths']},{keep,'ikcv'})
            self.assertTrue(next(p for p in d['paths'] if p['code']==keep)['compatibilityOnly'])
            self.assertNotIn(cp,self.o.key_members(2,'o',True))
            self.assertIn(cp,self.o.key_members(2,'k',True))
            for c in self.a['records'][str(cp)]['withdrawnCurrentCodes']:
                self.assertNotIn(cp,self.o.allocation_members(c))

    def test_hole_size_uses_selected_D_and_same_C_D_object(self):
        for cp,expected in [(119811,50/60),(127251,35/45)]:
            d=self.o.detail(cp,True);p=next(p for p in d['paths'] if p['code']=='ikcv');e=p['evidence'][0]
            objects={o['id']:o for o in d['objects']}
            self.assertEqual(e['objectId'],e['fourthObjectId'])
            hole=objects[e['objectId']];body=objects[e['sizeReferenceObjectId']]
            longest=lambda b:max(b[2]-b[0],b[3]-b[1])
            self.assertEqual(hole['parentObjectId'],body['id'])
            self.assertAlmostEqual(longest(hole['bbox'])/longest(body['bbox']),expected)
            self.assertAlmostEqual(hole['relativeSize'],expected)
            self.assertEqual(e['firstBucketReferenceObjectId'],body['id'])
            self.assertFalse(p['preferred']);self.assertNotIn('count',hole)
        self.assertEqual(self.o.brief(127251,True)['primaryShapeScope'],'selected-inner-D-subject')
        self.assertNotIn(127251,self.o.key_members(2,'s',True))

    def test_both_orders_and_protected_noncount_and_count_rules(self):
        for code in ['ikcv','iold','dscv']:
            f=self.o.query(dict(allocation=['1'],prefix=[code]))
            b=self.o.query(dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=[code[1:]+code[0]]))
            self.assertEqual(f['total'],b['total'])
            self.assertEqual([r['cp'] for r in f['rows']],[r['cp'] for r in b['rows']])
        self.assertEqual(structural.data()['version'],'structure-count-bindings-v10')
        self.assertEqual(structural.data()['countSemanticsVersion'],'whole-continuous-total-v1')
        self.assertEqual(set(self.o.allocation_members('ikqt')),({7694} if so.joint_bc.policy() else {272,7694}))
        self.assertEqual(set(self.o.allocation_members('ikjt')),({7694} if so.joint_bc.policy() else {272,7694}))
        self.assertFalse(self.o.allocation_members('ikqu'))
        self.assertIn('ioqc',self.o.brief(79,True)['codes'])
        self.assertIn('eeci' if so.joint_bc.policy() else 'ebii',self.o.brief(56,True)['codes'])
        self.assertIn('ifmg' if so.joint_bc.policy() else 'iokg',self.o.brief(7897,True)['codes'])
        self.assertEqual(len(structural.queues()['scopePending']),2073)

    def test_later_sans_D_single_hole_only_after_explicit_approval(self):
        manual=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')
        if 'dSubjectHoleShapeAcceptance20261027Batch2' not in manual:self.skipTest('后续𝖣尚未接入')
        cp=120227;b=self.o.brief(cp,True);d=self.o.detail(cp,True)
        self.assertEqual(set(self.o.allocation_members('ekcv')),{cp})
        self.assertEqual((b['bucket'],b['familyKey']),('e','k'))
        self.assertEqual(b['codes'],['ekcv','eovc']);self.assertEqual(b['preferredCodes'],[])
        self.assertEqual(len(self.o.brief(cp,False)['codes']),4)
        self.assertNotIn(cp,self.o.key_members(2,'o',True))
        self.assertIn(cp,self.o.key_members(2,'k',True))
        p=next(p for p in d['paths'] if p['code']=='ekcv');e=p['evidence'][0]
        self.assertEqual(e['objectId'],e['fourthObjectId'])
        hole=next(o for o in d['objects'] if o['id']==e['objectId'])
        self.assertAlmostEqual(hole['relativeSize'],48/60)
        for c in ['eocv','eovg','eovi']:self.assertNotIn(cp,self.o.allocation_members(c))
        self.assertEqual(self.o.brief(127376,True)['preferredCodes'],['eokh'])
        self.assertEqual(len(self.o.brief(127376,True)['codes']),2 if 'dSubjectHoleShapeAcceptance20261027Batch3' in manual else 12)

    def test_DJ_whole_subject_uses_whole_group_reference_and_protects_preferred(self):
        manual=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')
        if 'dSubjectHoleShapeAcceptance20261027Batch3' not in manual:self.skipTest('DJ整组尚未接入')
        cp=127376;b=self.o.brief(cp,True);d=self.o.detail(cp,True)
        self.assertEqual((b['bucket'],b['familyKey']),('i','k'))
        self.assertEqual(set(b['codes']),{'ikcv','eokh'})
        self.assertEqual(b['preferredCodes'],['eokh'])
        self.assertEqual(b['primaryShapeScope'],'whole-glyph-DJ-group')
        self.assertEqual(len(self.o.brief(cp,False)['codes']),12)
        self.assertNotIn(cp,self.o.allocation_members('ekcv'))
        self.assertNotIn(cp,self.o.allocation_members('ikca'))
        keep=next(p for p in d['paths'] if p['code']=='eokh')
        self.assertTrue(keep['preferred']);self.assertTrue(keep['compatibilityOnly'])
        e=next(p for p in d['paths'] if p['code']=='ikcv')['evidence'][0]
        objects={o['id']:o for o in d['objects']}
        self.assertEqual(e['objectId'],e['fourthObjectId'])
        hole=objects[e['objectId']];body=objects[e['sizeReferenceObjectId']]
        self.assertEqual(body['bbox'],[6.,3.,59.,61.])
        self.assertEqual(body['sourceComponentBBoxes'],[[6,3,39,60],[39,3,59,61]])
        self.assertAlmostEqual(hole['relativeSize'],45/58)
        self.assertNotAlmostEqual(hole['relativeSize'],45/57)
        self.assertEqual(d['codeCounts']['ikcv'],3)
        self.assertEqual(set(self.o.allocation_members('ikcv')),{119811,127251,127376})

if __name__=='__main__':unittest.main()
