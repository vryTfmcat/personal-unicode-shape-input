"""Regressions for visible objects, fill polarity and group/member separation."""
import unittest
from pathlib import Path

from shape_experiment_features import observe, render
from shape_experiment_rules import obj, properties
from shape_keyboard_trial import (fill_state, group_object, line_group, outline_anchors,
                                  trial_facts, trial_properties, make_paths)


class KeyboardTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = Path('C:/Windows/Fonts/seguisym.ttf')
        cls.anchors = outline_anchors(cls.font)

    def feature(self, char, size=96, weight=0):
        mask, extent = render(char, self.font, size=size, weight=weight)
        return observe(mask, extent)

    def test_no_measurement_window_size_but_visible_sizes_remain(self):
        for size in (5, 12, 25, 45):
            box = [0, 0, size, size]
            junction = obj('j', 'junction', box, [0, 0, 60, 60], .8)
            self.assertFalse(set(k for k, _ in trial_properties(junction)) & set('zxcv'))
            for kind in ('body', 'part', 'hole', 'inner-ink'):
                visible = obj('v', kind, box, [0, 0, 60, 60], .8)
                self.assertTrue(set(k for k, _ in trial_properties(visible)) & set('zxcv'))
            self.assertTrue(set(k for k, _ in properties(junction)) & set('zxcv'))

    def test_fill_pairs_across_sizes_and_weights(self):
        for char, family, fill in [('○', 'o', 'hollow'), ('●', 'o', 'solid'),
                                    ('□', 's', 'hollow'), ('■', 's', 'solid'),
                                    ('☆', 'r', 'hollow'), ('★', 'r', 'solid')]:
            for size in (48, 96, 128):
                for weight in (-1, 0, 1):
                    with self.subTest(char=char, size=size, weight=weight):
                        self.assertEqual(fill_state(self.feature(char, size, weight), family, self.anchors), fill)

    def test_open_arc_and_decorated_ring_not_pure_fill(self):
        for char in ('C', '⊙', '⊕', '◐', '◑', '◒', '◓'):
            for size in (48, 96, 128):
                for weight in (-1, 0, 1):
                    with self.subTest(char=char, size=size, weight=weight):
                        self.assertIsNone(fill_state(self.feature(char, size, weight), 'o', self.anchors))

    def test_two_lines_keep_member_direction_and_group_arrangement(self):
        for char, member, arrangement in [('∥', 'i', 'h'), ('=', 'h', 'i')]:
            for size in (48, 96, 128):
                f = self.feature(char, size)
                self.assertTrue(line_group(f))
                self.assertEqual(group_object(f)['memberCount'], 2)
                self.assertEqual(group_object(f)['arrangement'], arrangement)
                ff = trial_facts(f, 'l', self.anchors)
                members = [a for a in ff if a['third'] == 'n']
                self.assertTrue(members)
                self.assertTrue(all(member in dict(trial_properties(a['object'])) for a in members))

    def test_triangle_orientation_is_a_group_property(self):
        for char, direction in [('∴', 'w'), ('∵', 's')]:
            for size in (48, 96, 128):
                o = group_object(self.feature(char, size))
                self.assertEqual(o['memberCount'], 3)
                self.assertEqual(o['triangleDirection'], direction)
                self.assertIn((direction, '选定三点组的整体尖端朝向'), trial_properties(o))

    def test_fill_path_uses_body_and_old_alignment_is_rebound(self):
        definitions = {'fourth': dict.fromkeys('abcdefghijklmnopqrstuvwxyz')}
        f = self.feature('○')
        paths = make_paths('i', 'o', trial_facts(f, 'o', self.anchors), definitions)
        preferred = next(p for p in paths if p['code'] == 'iose')
        self.assertTrue(preferred['preferred'])
        self.assertTrue(all(e['object']['kind'] == 'body' for e in preferred['evidence']))
        aligned = obj('line', 'part', [0, 0, 5, 50], [0, 0, 60, 60], .8, orientation=90)
        attrs = dict(trial_properties(aligned))
        self.assertIn('g', attrs)
        self.assertIn('i', attrs)
        self.assertNotIn('e', attrs)

    def test_size_paths_follow_family_contrast_not_just_measurability(self):
        policy = {'r': {'excludedKinds': ['body', 'hole', 'contour-section']}}
        for kind in ('body', 'hole', 'contour-section'):
            measured = obj('measured', kind, [0, 0, 20, 20], [0, 0, 60, 60], .8)
            self.assertFalse(set(k for k, _ in trial_properties(measured, 'r', policy)) & set('zxcv'))
            for family in ('o', 's'):
                self.assertTrue(set(k for k, _ in trial_properties(measured, family, policy)) & set('zxcv'))
        dot = obj('visible-dot', 'part', [0, 0, 5, 5], [0, 0, 60, 60], .8)
        self.assertIn('z', dict(trial_properties(dot, 'r', policy)))

    def test_small_square_body_size_does_not_require_a_fill_decision(self):
        ff = trial_facts(self.feature('▫'), 's', self.anchors)
        bodies = [f for f in ff if f['third'] == 'w' and f['object']['kind'] == 'body']
        self.assertTrue(bodies)
        self.assertTrue(set(k for k, _ in trial_properties(bodies[0]['object'], 's')) & set('zxcv'))


if __name__ == '__main__':
    unittest.main()
