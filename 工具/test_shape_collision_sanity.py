"""Negative certificates must not turn weak positive scores into deletion."""
import copy
import unittest

import test_shape_keyboard_full as fixture
from build_shape_keyboard_full import validate_row
from shape_collision_sanity import certify
from shape_experiment_features import observe, render


class CollisionSanityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.FullKeyboardTests.setUpClass()
        cls.f = fixture.FullKeyboardTests()

    def test_open_curve_is_not_an_intersection(self):
        row,_ = self.f.rebuilt('⧼')
        self.assertFalse(any(r['familyKey']=='x' and r['target']=='body' for r in row['familyRoutes']))
        proof = next(p for p in row['collisionSanityExclusions'] if p['familyKey']=='x')
        self.assertEqual(len(proof['variants']),9)
        validate_row(row,self.f.definitions)

    def test_angular_strokes_do_not_become_hook(self):
        row,_ = self.f.rebuilt('┘')
        self.assertFalse(any(r['familyKey']=='j' and r['target']=='body' for r in row['familyRoutes']))
        self.assertTrue(any(p['kind']=='two-long-straight-arms-not-curved-hook' for p in row['collisionSanityExclusions']))

    def test_real_hooks_and_stars_and_branches_are_not_rejected(self):
        for chars,family in [('Jjʃɟɺ','j'),('+×','x'),('TY3','h'),('☆★','r')]:
            for char in chars:
                old=self.f.baseline(char)
                f=observe(*render(char,old['font']['path'],old['font'].get('index',0)))
                self.assertIsNone(certify(old,f,family),(char,family))

    def test_unstable_seven_is_not_deleted_by_low_match(self):
        row,_=self.f.rebuilt('7')
        self.assertTrue(any(r['familyKey']=='j' for r in row['familyRoutes']))
        self.assertTrue(any(r['familyKey']=='x' for r in row['familyRoutes']))
        self.assertFalse(row['collisionSanityExclusions'])

    def test_corrupt_variant_set_is_rejected(self):
        row,_=self.f.rebuilt('⧼')
        bad=copy.deepcopy(row)
        bad['collisionSanityExclusions'][0]['variants'].pop()
        with self.assertRaises(AssertionError):
            validate_row(bad,self.f.definitions)

    def test_losing_last_trial_route_restores_original_first_bucket(self):
        for char in '𝒮✔𑿉':
            row,_=self.f.rebuilt(char)
            self.assertFalse(row['paths'])
            self.assertEqual(row['bucket'],self.f.baseline(char)['bucket'])
            self.assertEqual(row['withheldDetailedPaths']['retainedFirstKey'],row['bucket'])


if __name__=='__main__':
    unittest.main()
