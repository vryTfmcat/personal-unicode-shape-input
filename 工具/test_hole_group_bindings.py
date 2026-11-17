"""Exact approval boundary and original negative-space objects for 8."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'原型/键位编辑器'),str(ROOT/'工具')]
import shape_overview as so


class HoleGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = so.get_overview()
        cls.a = so.hole_groups.policy()

    def test_real_holes_same_group_and_member_centres(self):
        d = self.o.detail(56,True)
        obj = {o['id']:o for o in d['objects']}
        path = next(p for p in d['paths']+d.get('compatibilityPaths',[]) if p['code']=='ebii')
        e = path['evidence'][0]
        self.assertEqual(e['objectId'],e['fourthObjectId'])
        group = obj[e['objectId']]
        self.assertEqual(group['kind'],'hole-group')
        self.assertEqual(group['directionMode'],'member-centres')
        self.assertEqual(group['members'],['body:b:hole-0','body:b:hole-1'])
        for member in group['members']:
            self.assertEqual(obj[member]['kind'],'hole')
        self.assertLess(group['angleFromVerticalDegrees'],12)
        self.assertFalse(path['preferred'])

    def test_old_paths_single_holes_and_short_code_unchanged(self):
        d = self.o.detail(56,True)
        historical = self.o.detail(56,False)
        self.assertEqual(len(d['paths']),10 if so.joint_bc.policy() else 9)
        self.assertEqual(self.o.brief(56,True)['preferredCodes'],[])
        self.assertEqual(self.o.brief(56,True)['codes'],sorted((set(self.a['beforeCodes'])|{'eesw','eeci'}) if so.joint_bc.policy() else self.a['beforeCodes']+['ebii']))
        for code in ('ebic','ebix','ebis','ebiw'):
            p = next(p for p in d['paths'] if p['code']==code)
            self.assertEqual(p,next(p for p in historical['paths'] if p['code']==code))
        self.assertEqual([p['code'] for p in d['paths'] if len(p['code'])==3],['ebm'])
        self.assertNotIn('ebii',[p['code'] for p in historical['paths']])
        self.assertEqual(self.o.query(dict(allocation=['1'],order=['back'],routeLength=['3'],prefix=['bme']))['total'],67)

    def test_only_one_binding_and_shared_projection(self):
        self.assertEqual(set(self.o.allocation_members('ebii')),set() if so.joint_bc.policy() else {56})
        a=self.o.query(dict(allocation=['1'],prefix=['ebii']))
        b=self.o.query(dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=['biie']))
        self.assertEqual(a['total'],0 if so.joint_bc.policy() else 1)
        self.assertEqual([r['cp'] for r in a['rows']],[r['cp'] for r in b['rows']])
        for code in ('ebih','ebiq','ebio','iokl'):
            self.assertEqual(len(self.o.allocation_members(code)),0)
        self.assertEqual(len([g for g in self.o.collision_groups(4,True) if g['code']=='ebii']),0 if so.joint_bc.policy() else 1)
        k=next(k for k in self.o.allocation_keys() if k['position']==3 and k['key']=='i')
        expected={'position/size':'single-hole','direction':'hole-group'}
        if so.hole_groups.count_policy():expected['quantity']='hole-group'
        self.assertEqual(k['objectModes'],expected)
        self.assertIn('规范码第3位i',k['condition'])
        self.assertIn('不自动给其它字派码',k['condition'])


if __name__=='__main__':unittest.main()
