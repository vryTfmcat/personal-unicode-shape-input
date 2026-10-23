"""Full-generator integration checks using immutable baseline evidence shards."""
import copy
import unittest
from pathlib import Path

from build_shape_keyboard_full import rebuild_row, validate_row
from shape_keyboard_trial import (DATA, PROJECT, load, trial_definitions, outline_anchors, trial_properties, obj)
from shape_experiment_features import observe, render
from shape_reviewed_routes import amend, references, straight_body, dominant_double_loop
from shape_family_boundaries import fits
from shape_reviewed_components import closed_spine_arc


class FullKeyboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = load(DATA / '全形核对版.json')
        cls.index = load(PROJECT / manifest['indexPath'])
        cls.definitions = trial_definitions(cls.index)
        cls.anchors = outline_anchors(Path('C:/Windows/Fonts/seguisym.ttf'))
        cls.shards = {}

    def baseline(self, char):
        slim = next(r for r in self.index['records'] if r['char'] == char)
        url = slim['detailUrl']
        if url not in self.shards:
            self.shards[url] = load(PROJECT / '原型/键位编辑器' / url)
        return next(r for r in self.shards[url]['records'] if r['cp'] == ord(char))

    def rebuilt(self, char):
        return rebuild_row(self.baseline(char), self.definitions, self.index['bucketGroups'], self.anchors, {})

    def test_all_ten_approved_sample_paths_are_preferred(self):
        for char, code in [('○', 'iose'), ('●', 'iosf'), ('□', 'dswe'), ('■', 'dswf'),
                           ('☆', 'qrwe'), ('★', 'qrwf'), ('∥', 'alkh'), ('=', 'wlki'),
                           ('∴', 'mdkw'), ('∵', 'mdks')]:
            with self.subTest(char=char):
                row, delta = self.rebuilt(char)
                self.assertFalse(delta['lostAll'])
                self.assertGreater(validate_row(row, self.definitions), 0)
                self.assertIn(code, [p['code'] for p in row['paths'] if p['preferred']])

    def test_double_loop_binding_and_B_alternate_keep_distinct_roles(self):
        for char in ('∞', '8'):
            row, delta = self.rebuilt(char)
            self.assertEqual(row['familyKey'], 'b')
            self.assertTrue(row['paths'])
            self.assertTrue(any(r['familyKey'] == 'b' for r in row['familyRoutes']))
            self.assertFalse(delta['lineRepair'])
        b, _ = self.rebuilt('B')
        self.assertNotEqual(b['familyKey'], 'b')
        self.assertTrue(any(r['familyKey'] == 'b' for r in b['familyRoutes']))

    def test_dots_keep_their_original_entry_and_gain_shape_entry(self):
        for char, family in [('•', 'o'), ('∙', 'o'), ('▪', 's'), ('◾', 's')]:
            row, _ = self.rebuilt(char)
            keys = {r['familyKey'] for r in row['familyRoutes']}
            self.assertTrue({'d', family} <= keys, (char, keys))
            validate_row(row, self.definitions)

    def test_visible_round_line_and_angular_shapes_reject_square_routes(self):
        for char, family in [('⬤', 'o'), ('I', 'l')]:
            row, _ = self.rebuilt(char)
            self.assertEqual(row['familyKey'], family)
            self.assertFalse(any(r['familyKey'] == 's' and r['target'] == 'body' for r in row['familyRoutes']))
        four, _ = self.rebuilt('4')
        self.assertIn(four['familyKey'], ('a', 'h'))
        self.assertFalse(any(r['familyKey'] == 's' and r['target'] == 'body' for r in four['familyRoutes']))

    def test_reviewed_compound_and_previous_entries_are_preserved(self):
        wedge, _ = self.rebuilt('𐎊')
        self.assertEqual(wedge['familyKey'], 'm')
        self.assertTrue({'m', 'l'} <= {r['familyKey'] for r in wedge['familyRoutes']})
        for char in ('𝍫', '﹦', '𝌆'):
            row, _ = self.rebuilt(char)
            old = {r['familyKey'] for r in self.baseline(char)['familyRoutes']}
            new = {r['familyKey'] for r in row['familyRoutes']}
            self.assertIn('l', new)
            self.assertTrue(old <= new)

    def test_all_sixteen_reviewed_size_references_get_their_own_tier(self):
        series = [('o', '◯○o◦'), ('o', '⬤●•∙'), ('s', '□◻◽▫'), ('s', '■◼◾▪')]
        for family, chars in series:
            for char, suffix in zip(chars, 'vcxz'):
                with self.subTest(char=char):
                    row, _ = self.rebuilt(char)
                    objects = {o['id']: o for o in row['objects']}
                    sizes = {p['code'][-1] for p in row['paths'] if len(p['code']) == 4 and p['code'][1] == family
                             and p['code'][-1] in 'zxcv'
                             and any(objects[e['objectId']]['kind'] == 'body' for e in p['evidence'])}
                    self.assertEqual(sizes, {suffix})

    def test_reviewed_route_geometry_across_sizes_and_weights(self):
        font = Path('C:/Windows/Fonts/seguisym.ttf')
        templates = references(font)
        for char, required, forbidden in [('⬤', 'o', 's'), ('I', 'l', 's'), ('4', 'h', 's'),
                                           ('•', 'o', None), ('▪', 's', None), ('◾', 's', None)]:
            for size in (48, 96, 128):
                for weight in (-1, 0, 1):
                    with self.subTest(char=char, size=size, weight=weight):
                        mask, extent = render(char, font, size=size, weight=weight)
                        routes, _, _, _ = amend(self.baseline(char), observe(mask, extent),
                                                self.index['bucketGroups'], self.anchors, templates)
                        keys = {r['familyKey'] for r in routes if r['target'] == 'body'}
                        self.assertIn(required, keys)
                        if forbidden:
                            self.assertNotIn(forbidden, keys)

    def test_relative_size_tiers_are_stable_at_reference_font_sizes(self):
        font = Path('C:/Windows/Fonts/seguisym.ttf')
        for family, style, chars in [('o', 'hollow', '◯○o◦'), ('o', 'solid', '⬤●•∙'),
                                      ('s', 'hollow', '□◻◽▫'), ('s', 'solid', '■◼◾▪')]:
            for char, tier in zip(chars, 'vcxz'):
                for size in (48, 96, 128):
                    mask, extent = render(char, font, size=size)
                    o = obj('body', 'body', [0, 0, 60, 60], [0, 0, 60, 60], extent)
                    o['sizeReferenceFill'] = style
                    attrs = dict(trial_properties(o, family, self.definitions['sizePolicy']))
                    self.assertEqual(set(attrs) & set('zxcv'), {tier}, (char, size))

    def test_angular_reference_does_not_reclassify_unrelated_closed_shapes(self):
        font = Path('C:/Windows/Fonts/seguisym.ttf')
        templates = references(font)
        for char in ('B', '□', '■', '○', '8'):
            f = observe(*render(char, font))
            _, _, _, changes = amend(self.baseline(char), f, self.index['bucketGroups'], self.anchors, templates)
            self.assertNotIn('已核对角折／相交字形原型，排除四边形入口', changes)

    def test_contrast_policy_retains_round_square_sizes_but_not_star_sizes(self):
        for char in ('○', '●', '□', '■', '▫'):
            row, _ = self.rebuilt(char)
            objects = {o['id']: o for o in row['objects']}
            self.assertTrue(any(len(p['code']) == 4 and p['code'][-1] in 'zxcv'
                                and any(objects[e['objectId']]['kind'] == 'body' for e in p['evidence'])
                                for p in row['paths']), char)
        for char in ('☆', '★'):
            row, _ = self.rebuilt(char)
            objects = {o['id']: o for o in row['objects']}
            self.assertFalse(any(len(p['code']) == 4 and p['code'][-1] in 'zxcv'
                                 and any(objects[e['objectId']]['kind'] in ('body', 'hole') for e in p['evidence'])
                                 for p in row['paths']), char)

    def test_validator_rejects_fill_attached_to_hole(self):
        row, _ = self.rebuilt('○')
        row = copy.deepcopy(row)
        target = next(p for p in row['paths'] if p['code'] == 'iose')['evidence'][0]['objectId']
        next(o for o in row['objects'] if o['id'] == target)['kind'] = 'hole'
        with self.assertRaises(AssertionError):
            validate_row(row, self.definitions)

    def test_original_records_are_not_modified(self):
        baseline = self.baseline('=')
        saved = copy.deepcopy(baseline)
        row, delta = self.rebuilt('=')
        self.assertEqual(baseline, saved)
        self.assertEqual(row['familyKey'], 'l')
        self.assertTrue(delta['lineRepair'])

    def test_curved_hooked_and_tapered_strokes_do_not_gain_straight_body_route(self):
        for char in '（[⌠⎧⏠⁀𐎃':
            with self.subTest(char=char):
                row, _ = self.rebuilt(char)
                self.assertNotIn('单长直线排除四边形入口', row['routeAmendments'])
                self.assertFalse(any(r.get('newGeometryBasis') == '单长直线排除四边形入口' for r in row['familyRoutes']))
                if row['familyKey'] is None:
                    self.assertTrue(row['familyBoundaryReview']['excluded'])

    def test_true_straight_strokes_still_qualify(self):
        for char in 'I┃ㄧ':
            row, _ = self.rebuilt(char)
            self.assertEqual(row['familyKey'], 'l')
            source = self.baseline(char)['font']
            self.assertTrue(straight_body(observe(*render(char, source['path'], source.get('index', 0)))))

    def test_accidental_or_subordinate_holes_do_not_gain_double_loop(self):
        for char in '🕶🛩⥈༔៖ⴻ':
            with self.subTest(char=char):
                row, _ = self.rebuilt(char)
                self.assertFalse(any(r['familyKey'] == 'b' and r['target'] == 'body' for r in row['familyRoutes']))

    def test_two_dominant_rings_with_a_connector_keep_supplement(self):
        row, _ = self.rebuilt('⧟')
        self.assertTrue(any(r['familyKey'] == 'b' for r in row['familyRoutes']))
        self.assertEqual(row['familyKey'], self.baseline('⧟')['familyKey'])

    def test_B_like_body_with_short_tail_keeps_double_loop_supplement(self):
        row, _ = self.rebuilt(chr(0x11D55))
        self.assertTrue(any(r['familyKey'] == 'b' for r in row['familyRoutes']))
        self.assertNotEqual(row['familyKey'], 'b')
        if row['familyKey'] != self.baseline(chr(0x11D55))['familyKey']:
            self.assertTrue(row['familyBoundaryReview']['excluded'])

    def test_strict_geometry_across_font_size_and_weight(self):
        for char, helper, expected in [('I', straight_body, True), ('（', straight_body, False),
                                       ('[', straight_body, False), ('⌠', straight_body, False),
                                       ('B', dominant_double_loop, True), ('8', dominant_double_loop, True),
                                       ('∞', dominant_double_loop, True), ('⧟', dominant_double_loop, True),
                                       (chr(0x11D55), dominant_double_loop, True),
                                       ('🛩', dominant_double_loop, False), ('⥈', dominant_double_loop, False)]:
            source = self.baseline(char)['font']
            for size in (48, 96, 128):
                for weight in (-1, 0, 1):
                    with self.subTest(char=char, size=size, weight=weight):
                        f = observe(*render(char, source['path'], source.get('index', 0), size=size, weight=weight))
                        self.assertEqual(bool(helper(f)), expected)

    def test_incompatible_U_arc_and_closed_body_routes_are_withdrawn(self):
        for char, forbidden in [('H', 'u'), ('2', 'u'), ('5', 'u'), ('S', 'u'),
                                 ('K', 'c'), ('?', 'c'), ('B', 's'), ('B', 'o'),
                                 ('a', 'o'), ('a', 's'), ('@', 'o')]:
            with self.subTest(char=char, family=forbidden):
                row, _ = self.rebuilt(char)
                self.assertFalse(any(r['familyKey'] == forbidden and r['target'] == 'body' for r in row['familyRoutes']))
                self.assertTrue(row['familyBoundaryReview']['excluded'])

    def test_no_reliable_family_retains_first_key_and_explicit_pending_identity(self):
        for char in ('5', 'a'):
            row, delta = self.rebuilt(char)
            self.assertEqual(row['cp'], ord(char))
            self.assertEqual(row['bucket'], self.baseline(char)['bucket'])
            self.assertIsNone(row['familyKey'])
            self.assertEqual(row['paths'], [])
            self.assertTrue(row['withheldDetailedPaths']['baselineHadPaths'])
            self.assertTrue(delta['lostAll'])
        h, _ = self.rebuilt('H')
        self.assertIsNone(h['familyKey'])
        self.assertEqual(h['bucket'], self.baseline('H')['bucket'])
        self.assertTrue(all(r.get('localBranchProof') for r in h['familyRoutes']))
        self.assertTrue(h['paths'])

    def test_B_keeps_supplement_without_becoming_a_double_loop_primary(self):
        row, _ = self.rebuilt('B')
        self.assertIsNone(row['familyKey'])
        self.assertTrue(row['paths'])
        self.assertTrue(all(r['familyKey'] == 'b' and r['supplementOnly'] for r in row['familyRoutes']))

    def test_solid_triangle_is_not_a_skeletal_fork(self):
        for char in ('▲', '△'):
            row, _ = self.rebuilt(char)
            self.assertEqual(row['familyKey'], 't')
            self.assertFalse(any(r['familyKey'] in ('h', 'r') and r['target'] == 'body' for r in row['familyRoutes']))

    def test_boundary_reference_families_are_stable_across_sizes_and_weights(self):
        templates = references(Path('C:/Windows/Fonts/seguisym.ttf'))
        for family, chars in [('u', 'U∪∩⊂⊃⊔'), ('c', 'C(⌒◡◜◝◟◞'),
                              ('o', '○●0O'), ('s', '□■◇◆'), ('t', '△▲▷')]:
            for char in chars:
                for size in (48, 96, 128):
                    for weight in (-1, 0, 1):
                        with self.subTest(char=char, size=size, weight=weight):
                            f = observe(*render(char, Path('C:/Windows/Fonts/seguisym.ttf'), size=size, weight=weight))
                            self.assertTrue(fits(f, family, templates['familyViews'])[0])

    def test_boundary_counterexamples_do_not_return_with_weight_or_size_changes(self):
        templates = references(Path('C:/Windows/Fonts/seguisym.ttf'))
        for char, family in [('H', 'u'), ('2', 'u'), ('5', 'u'), ('S', 'u'), ('L', 'u'),
                              ('K', 'c'), ('?', 'c'), ('B', 's'), ('B', 'o'),
                              ('a', 'o'), ('a', 's'), ('@', 'o')]:
            source = self.baseline(char)['font']
            for size in (48, 96, 128):
                for weight in (-1, 0, 1):
                    with self.subTest(char=char, family=family, size=size, weight=weight):
                        f = observe(*render(char, source['path'], source.get('index', 0), size=size, weight=weight))
                        self.assertFalse(fits(f, family, templates['familyViews'])[0])

    def test_square_and_rotated_U_shapes_keep_U_entry(self):
        for char in ('U', '⊔', '[', ']'):
            row, _ = self.rebuilt(char)
            self.assertTrue(any(r['familyKey'] == 'u' and r['target'] == 'body' for r in row['familyRoutes']))
            validate_row(row, self.definitions)

    def test_cross_is_primary_and_fork_remains_supplementary(self):
        for char in ('+', '×'):
            row, _ = self.rebuilt(char)
            self.assertEqual(row['familyKey'], 'x')
            self.assertTrue({'x', 'h'} <= {r['familyKey'] for r in row['familyRoutes']})
            validate_row(row, self.definitions)

    def test_D_has_round_and_real_spine_arc_lookups(self):
        row, _ = self.rebuilt('D')
        self.assertIn(('o', 'body'), {(r['familyKey'], r['target']) for r in row['familyRoutes']})
        self.assertTrue({'alli', 'fcpd'} <= {p['code'] for p in row['paths']})
        objects = {o['id']: o for o in row['objects']}
        for code, kind in [('alli', 'part'), ('fcpd', 'contour-section')]:
            path = next(p for p in row['paths'] if p['code'] == code)
            for e in path['evidence']:
                self.assertEqual(objects[e['objectId']]['kind'], kind)
                self.assertNotEqual(e['familyTarget'], 'body')
        validate_row(row, self.definitions)

    def test_D_partition_survives_font_size_and_weight_changes(self):
        source = self.baseline('D')['font']
        for size in (48, 96, 128):
            for weight in (-1, 0, 1):
                with self.subTest(size=size, weight=weight):
                    f = observe(*render('D', source['path'], source.get('index', 0), size=size, weight=weight))
                    parts = closed_spine_arc(f)
                    self.assertEqual(len(parts), 2)
                    proof = parts[0]['proof']
                    self.assertEqual(proof['parentPixels'], proof['spinePixels'] + proof['arcPixels'])
                    self.assertEqual(proof['overlapPixels'], 0)
                    self.assertEqual(proof['parentPixels'], int(f['body'].sum()))

    def test_reviewed_component_partition_is_not_applied_to_other_identities(self):
        for char in ('B', 'O', '□', 'H'):
            row, _ = self.rebuilt(char)
            self.assertFalse(any(r.get('objectPartitionProof') for r in row['familyRoutes']))

    def test_validator_rejects_overlap_in_reviewed_component_proof(self):
        row, _ = self.rebuilt('D')
        route = next(r for r in row['familyRoutes'] if r.get('objectPartitionProof'))
        route['objectPartitionProof']['overlapPixels'] = 1
        with self.assertRaises(AssertionError):
            validate_row(row, self.definitions)

    def test_bracket_U_entry_survives_rotation_and_font_sizes(self):
        import numpy as np
        templates = references(Path('C:/Windows/Fonts/seguisym.ttf'))
        for char in ('[', ']'):
            source = self.baseline(char)['font']
            for size in (48, 96, 128):
                mask, extent = render(char, source['path'], source.get('index', 0), size=size)
                for turns in range(4):
                    with self.subTest(char=char, size=size, turns=turns):
                        f = observe(np.rot90(mask, turns).copy(), extent)
                        self.assertTrue(fits(f, 'u', templates['familyViews'])[0])

    def test_T_and_Y_are_not_split_into_new_subfamilies_or_bindings(self):
        from shape_family_boundaries import lookup_boundary_decisions
        self.assertFalse(lookup_boundary_decisions()['splitTY'])
        for char in ('T', 'Y'):
            row, _ = self.rebuilt(char)
            self.assertEqual(row['familyKey'], 'h')
            self.assertFalse(any('armPattern' in o for o in row['objects']))

    def test_Q_ring_and_tail_use_distinct_actual_objects(self):
        row, _ = self.rebuilt('Q')
        self.assertEqual(row['familyKey'], 'o')
        route = next(r for r in row['familyRoutes'] if r['target'] == 'cycle-subject')
        proof = route['componentPartitionProof']
        self.assertEqual(proof['ringPixels'] + proof['tailPixels'], proof['parentPixels'])
        self.assertEqual(proof['overlapPixels'], 0)
        ring = next(o for o in row['objects'] if o['kind'] == 'body')
        tail = next(o for o in row['objects'] if o['id'].endswith('attached-tail'))
        self.assertNotEqual(ring['id'], tail['id'])
        self.assertEqual(ring['bbox'], proof['ringBBox'])
        self.assertLess(ring['bbox'][3], proof['tailBBox'][3])
        self.assertTrue(any(p['code'] == 'iose' for p in row['paths']))
        validate_row(row, self.definitions)

    def test_cycle_partition_and_T_hook_gate_across_raster_variants(self):
        import numpy as np
        from shape_reviewed_components import cycle_subject
        templates = references(Path('C:/Windows/Fonts/seguisym.ttf'))
        for size in (48, 96, 128):
            for weight in (-1, 0, 1):
                with self.subTest(size=size, weight=weight):
                    q = observe(*render('Q', self.baseline('Q')['font']['path'], size=size, weight=weight))
                    split = cycle_subject(q)
                    self.assertIsNotNone(split)
                    rf, tail, proof = split
                    self.assertTrue(fits(rf, 'o', templates['familyViews'])[0])
                    self.assertTrue(np.array_equal(rf['mask'] | tail, q['body']))
                    self.assertFalse((rf['mask'] & tail).any())
                    t = observe(*render('T', self.baseline('T')['font']['path'], size=size, weight=weight))
                    self.assertFalse(fits(t, 'j', templates['familyViews'])[0])

    def test_hook_fix_preserves_J_and_recovers_L_as_angle(self):
        t, _ = self.rebuilt('T')
        self.assertFalse(any(r['familyKey'] == 'j' for r in t['familyRoutes']))
        self.assertEqual(t['familyKey'], 'h')
        j, _ = self.rebuilt('J')
        self.assertIn('j', {r['familyKey'] for r in j['familyRoutes']})
        l, _ = self.rebuilt('L')
        self.assertEqual(l['familyKey'], 'a')
        self.assertTrue(l['paths'])

    def test_Q_partition_proof_detects_corruption(self):
        row, _ = self.rebuilt('Q')
        row['familyRoutes'][0]['componentPartitionProof']['tailPixels'] += 1
        with self.assertRaises(AssertionError):
            validate_row(row, self.definitions)

    def test_accented_line_recovers_line_not_false_square(self):
        for char in 'ĨÎ':
            baseline = copy.deepcopy(self.baseline(char))
            # Exercise component recovery independently of an unrelated legacy
            # hook candidate, which this narrowly scoped T repair does not judge.
            baseline['familyKey'] = 'c'
            baseline['familyRoutes'] = [dict(r, familyKey='c') for r in baseline['familyRoutes']]
            row, _ = rebuild_row(baseline, self.definitions, self.index['bucketGroups'], self.anchors, {})
            self.assertTrue(any(r['familyKey'] == 'l' and r.get('componentEvidence') for r in row['familyRoutes']))
            self.assertFalse(any(r['familyKey'] == 's' for r in row['familyRoutes']))
            validate_row(row, self.definitions)
        row, _ = self.rebuilt('ĵ')
        self.assertTrue(any(r['familyKey'] == 'j' for r in row['familyRoutes']))
        validate_row(row, self.definitions)

    def test_genuine_hook_with_crossbar_is_not_deleted_as_T(self):
        for char in 'ɟʃjJ':
            old = self.baseline(char)
            if any(r['familyKey'] == 'j' for r in old['familyRoutes']):
                row, _ = self.rebuilt(char)
                self.assertTrue(any(r['familyKey'] == 'j' for r in row['familyRoutes']), char)


if __name__ == '__main__':
    unittest.main()
