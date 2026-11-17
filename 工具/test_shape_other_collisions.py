"""Same-cohort analysis with pooled uncertainty, immutable models and cache."""
import json
import unittest
from collections import Counter

import numpy as np
from PIL import Image,ImageDraw

from audit_shape_other_collisions import OUTPUT,PROJECT,CACHE,FIELDS,JOINT,FEATURES,THRESHOLD,overview,sha,protect,partition,feature_partition,applicability
from finalize_shape_other_collisions import scope_evidence


class OtherCollisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((OUTPUT/'其他大组分析.json').read_text(encoding='utf-8'))
        cls.o=overview.Overview();cls.rows=cls.data['records'];cls.index={r['cp']:r for r in cls.rows}

    def test_every_current_large_group_and_unique_union(self):
        expected={g['code']:g['count'] for g in self.o.collision_groups(4,True) if g['count']>=THRESHOLD and g['code']!='chvc'}
        self.assertEqual({g['code']:g['count'] for g in self.data['groups']},expected)
        union=set()
        for g in self.data['groups']:
            cps=set(self.o.allocation_members(g['code']));union|=cps
            self.assertEqual(set(g['cps']),cps)
        self.assertEqual(union,set(self.index));self.assertEqual(len(self.rows),len(union))
        self.assertFalse(union&set(overview.exclusive_intake()))

    def test_equal_memberships_are_not_independent_benefits(self):
        groups={g['code']:g for g in self.data['groups']}
        families=set()
        for g in groups.values():
            families.add(g['membershipFamily'])
            for alias in g['identicalMembershipCodes']:
                self.assertEqual(groups[alias]['cps'],g['cps'])
                self.assertEqual(groups[alias]['joint'],g['joint'])
                self.assertEqual(groups[alias]['featureMetrics'],g['featureMetrics'])
        self.assertEqual(len(families),self.data['statistics']['distinctMembershipFamilies'])

    def test_cached_observations_are_exact_and_nine_views_complete(self):
        cache={r['cp']:r for r in json.loads(CACHE.read_text(encoding='utf-8'))['records']}
        expected={(s,w) for s in (96,192,256) for w in (-1,0,1)}
        for r in self.rows:
            self.assertEqual({(v['size'],v['weight']) for v in r['observations']},expected)
            if r['fromCache']:
                prior={(v['size'],v['weight']):v for v in cache[r['cp']]['variants']}
                for v in r['observations']:
                    self.assertEqual(v['values'],[prior[(v['size'],v['weight'])]['statistics'][k] for k in FIELDS])
            if r['status']=='stable':
                self.assertEqual(r['applicability'],'line-model')
                self.assertTrue(r['numericallyStable'])
                self.assertTrue(all(v['topologyAgrees'] and not v['ambiguous'] for v in r['observations']))

    def test_group_comparisons_include_all_pending_characters(self):
        for g in self.data['groups']:
            rows=[self.index[cp] for cp in g['cps']]
            self.assertEqual(g['joint'],partition(rows,JOINT))
            self.assertEqual(g['statusCounts'],dict(Counter(r['status'] for r in rows)))
            self.assertEqual(g['joint']['pending'],g['count']-g['statusCounts'].get('stable',0))
            self.assertLessEqual(g['joint']['maximumIncludingPending'],g['count'])
            for f in FEATURES:self.assertEqual(g['featureMetrics'][f],feature_partition(rows,f))

    def test_pending_pool_cannot_be_shrunk_by_reason_labels(self):
        rows=[dict(status='stable',statistics={'corners':0}),dict(status='stable',statistics={'corners':1}),
              dict(status='filled-face',statistics={'corners':2}),dict(status='no-line',statistics={'corners':0}),
              dict(status='topology-pending',statistics={'corners':3})]
        p=partition(rows,['corners'])
        self.assertEqual(p['pending'],3);self.assertEqual(p['maximumIncludingPending'],3)
        self.assertEqual(p['stableClasses'],2)

    def test_filled_face_scope_gate_preserves_line_and_open_angle(self):
        im=Image.new('1',(192,192));ImageDraw.Draw(im).ellipse((15,15,175,175),fill=1)
        self.assertEqual(applicability(np.array(im,dtype=bool),{'statistics':{'totalSegments':3}}),'filled-face')
        im=Image.new('1',(192,192));ImageDraw.Draw(im).line([(15,95),(175,95)],fill=1,width=12)
        self.assertEqual(applicability(np.array(im,dtype=bool),{'statistics':{'totalSegments':1}}),'line-model')
        self.assertEqual(applicability(np.array(im,dtype=bool),{'statistics':{'totalSegments':0}}),'no-line')

    def test_convex_triangle_is_not_promoted_as_three_visible_strokes(self):
        im=Image.new('1',(192,192));ImageDraw.Draw(im).polygon([(96,10),(10,180),(180,180)],fill=1)
        self.assertTrue(scope_evidence(np.array(im,dtype=bool),3)['filledFace'])
        im=Image.new('1',(192,192));ImageDraw.Draw(im).line([(10,10),(180,180)],fill=1,width=12)
        self.assertFalse(scope_evidence(np.array(im,dtype=bool),1)['filledFace'])
        self.assertTrue(self.data['scopeEligibilityRevision']['numericalObservationsUnchanged'])

    def test_sources_paths_and_preferences_unchanged(self):
        self.assertEqual(protect(),self.data['protectedHashes'])
        for p,digest in {**self.data['sourceHashes'],**self.data['uiSourceHashes']}.items():
            self.assertEqual(sha(PROJECT/p),digest,p)
        for r in self.rows:
            brief=self.o.brief(r['cp'],True)
            self.assertEqual(brief['codes'],r['codes']);self.assertEqual(brief['preferredCodes'],r['preferredCodes'])
        self.assertEqual(self.data['newCodes']+self.data['removedPaths']+self.data['tBReentry'],0)

    def test_every_character_has_a_valid_sprite(self):
        active=None;images={}
        for r in self.rows:
            p=r['preview']
            if active!=p['atlas']:
                active=p['atlas'];images={view:Image.open(OUTPUT/f'atlas/{active:03}-{view}.png').convert('RGB') for view in ('plain','annotated')}
            for view,im in images.items():
                crop=im.crop((p['x'],p['y'],p['x']+80,p['y']+80))
                self.assertLess(min(v[0] for v in crop.getextrema()),230)
                self.assertGreater(max(v[1] for v in crop.getextrema()),240)


if __name__=='__main__':unittest.main()
