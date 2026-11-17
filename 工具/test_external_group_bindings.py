"""Verify the approved group scope without changing g or count algorithms."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
from shape_keyboard_trial import trial_properties


class ExternalGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview()
        cls.a=so.external_groups.policy()

    def test_exact_two_external_objects_and_unchanged_g(self):
        d=self.o.detail(7897,True);objects={o['id']:o for o in d['objects']}
        p=next(p for p in d['paths']+d.get('compatibilityPaths',[]) if p['code']=='iokg');e=p['evidence'][0]
        self.assertEqual(e['objectId'],e['fourthObjectId'])
        group=objects[e['objectId']]
        self.assertEqual(group['memberCount'],2)
        self.assertEqual(set(group['members']),{'reviewed-ộ-external-caret','reviewed-ộ-external-dot'})
        self.assertNotIn('reviewed-ộ-circle-subject',group['members'])
        self.assertEqual(group['directionMode'],'group-ink-principal-axis')
        self.assertEqual(dict(trial_properties(group))['g'],'对象长轴正置')
        self.assertFalse(e['typeEncoding'])
        self.assertFalse(p['preferred'])

    def test_only_one_added_code_and_original_preferred(self):
        b=self.o.brief(7897,True);d=self.o.detail(7897,True)
        self.assertEqual(set(b['codes']),set(self.a['beforeCodes'])|({'ifgb','ifmg'} if so.joint_bc.policy() else {'iokg'}))
        self.assertEqual(b['preferredCodes'],['epki'])
        self.assertEqual(len(d['paths']),11 if so.joint_bc.policy() else 10)
        self.assertEqual(set(self.o.allocation_members('iokg')),set() if so.joint_bc.policy() else {7897})
        self.assertEqual(len(self.o.allocation_members('iokl')),0)
        self.assertNotIn('iokg',self.o.brief(7897,False)['codes'])
        self.assertEqual(set(p['code'] for p in d['paths'] if p['preferred']),{'epki'})
        a=self.o.query(dict(allocation=['1'],prefix=['iokg']))
        b=self.o.query(dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=['okgi']))
        self.assertEqual(a['total'],0 if so.joint_bc.policy() else 1)
        self.assertEqual([r['cp'] for r in a['rows']],[r['cp'] for r in b['rows']])

    def test_perception_and_latest_explicit_curve_restoration(self):
        d=self.o.detail(272,True)
        self.assertEqual({p['code'] for p in d['paths']},so.joint_bc.migrate_structure(272,so.structure.totals.resolve_codes(272,{'ikab','ikgu','ikjb','ioma','ikqu'})))
        self.assertIn('总数3' if so.structure.totals.active() else 'u表示1个成员',d['currentFeedbackNote'])
        self.assertIn('当前全局' if so.structure.totals.active() else '已按后续明确授权恢复',d['currentFeedbackNote'])
        p=next(p for p in d['paths']+d.get('compatibilityPaths',[]) if p['code']==('ikqt' if so.structure.totals.active() else 'ikqu'));self.assertEqual(p['evidence'][0]['objectId'],p['evidence'][0]['fourthObjectId'])
        self.assertIn('上小下大',self.o.detail(56,True)['currentFeedbackNote'])
        self.assertEqual(len(self.o.detail(56,True)['paths']),10 if so.joint_bc.policy() else 9)
        self.assertEqual(self.o.brief(56,True)['preferredCodes'],[])
        self.assertNotIn(56,self.o.allocation_members('ebie'))
        self.assertNotIn(56,self.o.allocation_members('ebif'))
        for code in self.a['beforeCodes']:self.assertIn(7897,self.o.allocation_members(code))

    def test_restored_union_counts_are_identical_for_every_member(self):
        if so.structure.totals.active():
            self.assertEqual(set(self.o.allocation_members('ikqt')),({7694} if so.joint_bc.policy() else {272,7694}))
            self.assertFalse(self.o.allocation_members('ikqu'))
            return
        self.assertEqual(len(self.o.allocation_members('ikqu')),10)
        for cp in self.o.allocation_members('ikqu'):
            self.assertEqual(self.o.detail(cp,True)['codeCounts']['ikqu'],10)
        for code in ('ikqt','ikqb'):
            self.assertNotIn(272,self.o.allocation_members(code))


if __name__=='__main__':unittest.main()
