"""Focused recovery regressions; no historical identity bypasses geometry."""
import copy
import unittest
from pathlib import Path

import test_shape_keyboard_full as full_fixture
from shape_experiment_features import render, observe
from shape_recovery_geometry import two_stroke_angle, converging_stroke_bands, visible_fork
from build_shape_keyboard_full import validate_row, rebuild_row


class ReviewedRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        full_fixture.FullKeyboardTests.setUpClass()
        cls.fixture = full_fixture.FullKeyboardTests()

    def observed(self, char, size=96, weight=0):
        font = self.fixture.baseline(char)['font']
        return observe(*render(char, font['path'], font.get('index', 0), size=size, weight=weight))

    def test_reviewed_angles_recover_actual_angle_not_U(self):
        for char in '¬ᶺ𝙫':
            row, _ = self.fixture.rebuilt(char)
            self.assertEqual(row['familyKey'], 'a', char)
            self.assertTrue(row['paths'])
            self.assertFalse(any(r['familyKey']=='u' for r in row['familyRoutes']))
            validate_row(row, self.fixture.definitions)

    def test_angle_geometry_rejects_curves_solids_and_multi_strokes(self):
        for char in 'UCJSWNMKXYR▲■●★◣◤◥◢◀▶':
            f = self.observed(char)
            self.assertIsNone(two_stroke_angle(f), char)
            self.assertIsNone(converging_stroke_bands(f), char)

    def test_solid_convex_triangles_do_not_gain_angle_routes(self):
        for char in '▲◣◤◥◢◀▶':
            row,_ = self.fixture.rebuilt(char)
            self.assertFalse(any(r.get('recoveryGeometry') for r in row['familyRoutes']),char)

    def test_real_forks_reconnect_saved_local_semantics(self):
        for char in 'ᵏₖ𝘒𒋡':
            row, _ = self.fixture.rebuilt(char)
            self.assertIsNone(row['familyKey'], 'local fork must not become whole primary')
            routes = [r for r in row['familyRoutes'] if r.get('localBranchProof')]
            self.assertTrue(routes, char)
            self.assertTrue(all(r['familyKey']=='h' for r in routes))
            self.assertTrue(row['paths'])
            self.assertFalse(any(len(p['code'])==4 and p['code'][-1] in 'zxcv' for p in row['paths']))
            validate_row(row, self.fixture.definitions)

    def test_solid_faces_cannot_recover_as_local_forks(self):
        for char in '▲■●★⬤':
            f = self.observed(char)
            self.assertFalse(any(visible_fork(f,j) for j in f['junctionObjects']), char)

    def test_accented_U_component_keeps_own_object_and_size(self):
        row, _ = self.fixture.rebuilt('Ṷ')
        route = next(r for r in row['familyRoutes'] if r['familyKey']=='u')
        self.assertTrue(route['target'].startswith('visible-component-'))
        self.assertTrue(route['componentEvidence']['openCurveMarginVerified'])
        self.assertIsNone(row['familyKey'])
        validate_row(row,self.fixture.definitions)

    def test_recovery_does_not_depend_on_historical_review_flag(self):
        old = copy.deepcopy(self.fixture.baseline('ᵏ'))
        old['oldReviewed'] = False
        row, _ = rebuild_row(old,self.fixture.definitions,self.fixture.index['bucketGroups'],self.fixture.anchors,{})
        self.assertTrue(any(r.get('localBranchProof') for r in row['familyRoutes']))

    def test_validator_rejects_forged_local_branch_proof(self):
        row, _ = self.fixture.rebuilt('ᵏ')
        row['familyRoutes'][0]['localBranchProof']['visiblePortCounts'][0] = 1
        with self.assertRaises(AssertionError):
            validate_row(row,self.fixture.definitions)

    def test_recover_or_conservatively_withhold_raster_variants(self):
        recovered = 0
        for char in '¬ᶺ𝙫':
            for size in (48,96,128):
                for weight in (-1,0,1):
                    with self.subTest(char=char,size=size,weight=weight):
                        f = self.observed(char,size,weight)
                        from shape_reviewed_routes import amend, references
                        row = self.fixture.baseline(char)
                        routes, main, _, _ = amend(row,f,self.fixture.index['bucketGroups'],self.fixture.anchors,
                                                  references(Path('C:/Windows/Fonts/seguisym.ttf')))
                        self.assertIn(main,(None,'a'))
                        if main == 'a':
                            recovered += 1
                        else:
                            self.assertFalse(routes)
        self.assertGreaterEqual(recovered,26)


if __name__ == '__main__':
    unittest.main()
