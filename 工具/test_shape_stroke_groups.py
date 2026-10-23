"""Connected stroke counts must not be connected-component counts or serifs."""
import unittest

import numpy as np

import test_shape_keyboard_full as fixture
from shape_experiment_features import render,observe
from shape_keyboard_trial import trial_properties
from shape_stroke_groups import stable_stroke_group,horizontal_stroke_group
from shape_reviewed_components import cycle_subject


class StrokeGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.FullKeyboardTests.setUpClass()
        cls.f=fixture.FullKeyboardTests()

    def observed(self,ch,size=96,weight=0):
        font=self.f.baseline(ch)['font']
        return observe(*render(ch,font['path'],font.get('index',0),size=size,weight=weight))

    def test_connected_E_F_have_three_and_two_bars(self):
        for ch,count in [('E',3),('F',2)]:
            f=self.observed(ch)
            self.assertEqual(len(f['parts']),1)
            group=stable_stroke_group(self.f.baseline(ch),f)
            self.assertEqual(group['object']['memberCount'],count)
            self.assertEqual(len(group['stabilityProof']['variants']),9)

    def test_all_nine_variants_keep_count(self):
        for ch,count in [('E',3),('F',2)]:
            for size in (48,96,128):
                for weight in (-1,0,1):
                    g=horizontal_stroke_group(self.observed(ch,size,weight))
                    self.assertEqual(g['object']['memberCount'],count)

    def test_members_are_existing_disjoint_ink(self):
        for ch in 'EF':
            f=self.observed(ch); g=horizontal_stroke_group(f)
            self.assertTrue(np.array_equal(g['mask']|g['remainder'],f['body']))
            self.assertFalse((g['mask']&g['remainder']).any())
            seen=np.zeros_like(f['body'])
            for member in g['members']:
                self.assertFalse((member&~f['body']).any())
                self.assertFalse((member&seen).any())
                seen|=member

    def test_horizontal_members_are_vertically_arranged(self):
        g=horizontal_stroke_group(self.observed('E'))
        self.assertEqual(g['object']['memberOrientation'],'h')
        self.assertEqual(g['object']['arrangement'],'i')

    def test_quantity_and_arrangement_belong_to_group(self):
        for ch,key in [('E','t'),('F','b')]:
            o=horizontal_stroke_group(self.observed(ch))['object']
            attrs=dict(trial_properties(o,'h',self.f.definitions['sizePolicy']))
            self.assertIn(key,attrs)
            self.assertIn('i',attrs)

    def test_T_L_I_and_non_comb_controls_do_not_acquire_group(self):
        for ch in 'TLIHKBROUΞ=∥':
            self.assertIsNone(stable_stroke_group(self.f.baseline(ch)),ch)

    def test_all_masked_members_absent_is_not_a_group(self):
        f=self.observed('E')
        mask=f['mask'].copy()
        mask[:,f['bbox'][0]+7:]=False
        self.assertIsNone(horizontal_stroke_group(observe(mask,f['extent'])))

    def test_Q_has_real_tail_but_O_has_none(self):
        q=cycle_subject(self.observed('Q'))
        self.assertIsNotNone(q)
        self.assertTrue(q[1].any())
        self.assertIsNone(cycle_subject(self.observed('O')))

    def test_z_paths_are_preferred_and_k_semantics_unchanged(self):
        self.assertEqual(self.f.definitions['third']['k']['function'],'topology.separated')
        for ch,code in [('E','chzt'),('F','chzb')]:
            row,_=self.f.rebuilt(ch)
            self.assertIn(code,[p['code'] for p in row['paths'] if p['preferred']])
            self.assertIn('chvc',[p['code'] for p in row['paths']])
            for path in row['paths']:
                if path['code'][2]=='z':
                    for e in path['evidence']:
                        self.assertEqual(e['objectId'],e['fourthObjectId'])

    def test_new_z_paths_not_given_to_T_L_I(self):
        for ch in 'TLI':
            row,_=self.f.rebuilt(ch)
            self.assertFalse(any(p['code'][2]=='z' for p in row['paths']))


if __name__=='__main__':
    unittest.main()
