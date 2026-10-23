"""Connected-frame ink, parent-relative attributes, and lossless candidate views."""
import copy
import unittest
from pathlib import Path

import numpy as np

import test_shape_keyboard_full as fixture
from build_shape_keyboard_full import validate_row
from shape_experiment_features import observe,render
from shape_connected_frames import connected_frames,border_spines
from shape_reviewed_routes import references
from shape_candidate_layers import CandidateLayers,route_layer


class FrameLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.FullKeyboardTests.setUpClass()
        cls.f=fixture.FullKeyboardTests()
        cls.views=references(Path('C:/Windows/Fonts/seguisym.ttf'))['familyViews']

    def observed(self,char,size=96,weight=0):
        font=self.f.baseline(char)['font']
        return observe(*render(char,font['path'],font.get('index',0),size=size,weight=weight))

    def test_connected_cells_are_actual_ink_not_drawn_boxes(self):
        f=self.observed('𒌷')
        frames=connected_frames(f,self.views)
        self.assertGreaterEqual(len(frames),2)
        for p in frames:
            mask=p['feature']['mask']
            self.assertFalse((mask&~f['body']).any())
            self.assertFalse((mask&p['remainder']).any())
            self.assertTrue(np.array_equal(mask|p['remainder'],f['body']))
            self.assertEqual(len(p['feature']['holes']),1)
            self.assertEqual(p['familyKey'],'s')

    def test_selected_frame_attributes_belong_to_same_frame(self):
        row,_=self.f.rebuilt('𒌷')
        self.assertIsNone(row['familyKey'])
        self.assertTrue({'dswe','dswk','dswm','dswn'} <= {p['code'] for p in row['paths']})
        objects={o['id']:o for o in row['objects']}
        for path in row['paths']:
            for e in path['evidence']:
                self.assertEqual(e['objectId'],e['fourthObjectId'])
                self.assertEqual(objects[e['objectId']]['positionReference'],'parent-subject')
        validate_row(row,self.f.definitions)

    def test_attached_frame_and_spine_recover_without_whole_relabel(self):
        for char in '𒌒𒀖𒋼ﻈ':
            row,_=self.f.rebuilt(char)
            self.assertIsNone(row['familyKey'])
            self.assertTrue(row['paths'],char)
            self.assertTrue(any(r.get('frameEvidence') or r.get('spineEvidence') for r in row['familyRoutes']))
            validate_row(row,self.f.definitions)

    def test_solids_and_no_hole_curves_do_not_acquire_frames(self):
        for char in '●■▲★UCJT':
            self.assertEqual(connected_frames(self.observed(char),self.views),[],char)

    def test_tiny_or_organic_holes_do_not_become_four_sided_frames(self):
        for char in '🐷🦄🌜a':
            self.assertFalse(any(p['familyKey'] in 'st' for p in connected_frames(self.observed(char),self.views)),char)

    def test_frame_proof_detects_corruption(self):
        row,_=self.f.rebuilt('𒌒')
        row['familyRoutes'][0]['frameEvidence']['framePixels']+=1
        with self.assertRaises(AssertionError):
            validate_row(row,self.f.definitions)

    def test_native_raster_variants_never_create_ink(self):
        recovered=0
        for size in (48,96,128):
            for weight in (-1,0,1):
                f=self.observed('𒌷',size,weight)
                frames=connected_frames(f,self.views)
                recovered+=bool(frames)
                for p in frames:
                    self.assertTrue(np.array_equal(p['feature']['mask']|p['remainder'],f['body']))
        self.assertGreaterEqual(recovered,6)

    def test_all_view_preserves_every_prefix_candidate(self):
        rows=[self.f.rebuilt(c)[0] for c in 'T3J7𒌷ᵏB○']
        index=CandidateLayers(rows)
        expected={}
        for row in rows:
            codes=[row['bucket']]+[r['bucket']+r['familyKey'] for r in row['familyRoutes']]+[p['code'] for p in row['paths']]
            for code in codes:
                for n in range(1,len(code)+1):
                    expected.setdefault(code[:n],set()).add(row['cp'])
        for prefix,cps in expected.items():
            result=index.query(prefix)
            self.assertEqual(set(result['candidates']),cps)
            groups=[set(v) for v in result['groups'].values()]
            self.assertEqual(sum(map(len,groups)),len(set.union(*groups)))
            self.assertLessEqual(set(index.query(prefix,'focused')['candidates']),cps)

    def test_local_only_character_is_not_lost_or_mislabeled_primary(self):
        row,_=self.f.rebuilt('ᵏ')
        index=CandidateLayers([row])
        self.assertIn(ord('ᵏ'),index.query('qhm')['groups']['supplement'])
        self.assertNotIn(ord('ᵏ'),index.query('qhm','focused')['candidates'])
        self.assertIn(ord('ᵏ'),index.query('qhm','all')['candidates'])

    def test_weak_old_hook_is_separated_not_deleted(self):
        row,_=self.f.rebuilt('7')
        index=CandidateLayers([row])
        self.assertIn(ord('7'),index.query('ajvg')['groups']['pending'])
        self.assertIn(ord('7'),index.query('ajvg')['candidates'])

    def test_frame_is_a_reliable_component_not_whole_primary(self):
        row,_=self.f.rebuilt('𒌷')
        self.assertTrue(all(route_layer(row,r)==1 for r in row['familyRoutes']))

    def test_irregular_loop_observation_does_not_invent_a_family(self):
        f=self.observed('ᕣ')
        raw=connected_frames(f,self.views,include_unclassified=True)
        self.assertTrue(raw)
        self.assertTrue(any(p['familyKey'] is None for p in raw))
        self.assertFalse(connected_frames(f,self.views))

    def test_existing_fill_preference_is_not_replaced_by_rarer_size_path(self):
        rows=[self.f.rebuilt(c)[0] for c in '○●OQ']
        index=CandidateLayers(rows)
        self.assertEqual(index.suggestions(ord('○'))[0]['code'],'iose')
        self.assertEqual(index.suggestions(ord('●'))[0]['code'],'iosf')

    def test_reviewed_frame_examples_remain_supplements(self):
        for char in '𒌒𒌷𒀖':
            row,_=self.f.rebuilt(char)
            frames=[r for r in row['familyRoutes'] if r.get('frameEvidence')]
            self.assertTrue(frames)
            self.assertTrue(all(r['familyKey']=='s' and r['supplementOnly'] and r.get('reviewedRetain') for r in frames))
            self.assertIsNone(row['familyKey'])

    def test_rejected_horizontal_spine_is_character_specific(self):
        row,_=self.f.rebuilt('ﻄ')
        self.assertFalse(any(r.get('spineEvidence',{}).get('orientation')==0 for r in row['familyRoutes']))
        other,_=self.f.rebuilt('ﻈ')
        self.assertTrue(any(r.get('spineEvidence',{}).get('orientation')==0 for r in other['familyRoutes']))
        validate_row(row,self.f.definitions)

    def test_reviewed_irregular_loop_is_real_and_not_whole_relabel(self):
        row,_=self.f.rebuilt('ᕣ')
        loops=[r for r in row['familyRoutes'] if r.get('reviewedLoopEvidence')]
        self.assertEqual(len(loops),1)
        self.assertEqual(loops[0]['familyKey'],'p')
        self.assertNotEqual(row['familyKey'],'p')
        self.assertTrue(loops[0]['supplementOnly'])
        f=self.observed('ᕣ')
        part=next(p for p in connected_frames(f,self.views,True) if p['target']==loops[0]['target'])
        self.assertEqual(part['proof'],loops[0]['reviewedLoopEvidence'])
        self.assertTrue(np.array_equal(part['feature']['mask']|part['remainder'],f['body']))
        self.assertFalse((part['feature']['mask']&part['remainder']).any())
        validate_row(row,self.f.definitions)
        self.assertEqual(route_layer(row,loops[0]),1)

    def test_reviewed_T_preference_preserves_other_paths(self):
        row,_=self.f.rebuilt('T')
        paths={p['code']:p for p in row['paths']}
        self.assertIn('chvc',paths)
        self.assertTrue(paths['chmw']['preferred'])
        self.assertEqual(CandidateLayers([row]).suggestions(ord('T'))[0]['code'],'chmw')
        validate_row(row,self.f.definitions)


if __name__=='__main__':
    unittest.main()
