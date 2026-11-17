"""Lossless membership, honest stability, and sprite integrity for full review."""
import json
import unittest
from collections import Counter

from PIL import Image, ImageStat

from audit_shape_historical_buckets import protect
from build_shape_turn_classification import OUTPUT, PROJECT, FIELDS, classify_records, overview
from build_shape_turn_samples import sha


class ClassificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((OUTPUT/'分类数据.json').read_text(encoding='utf-8'))
        cls.o=overview.Overview()

    def test_same_current_cohort_and_no_tb_reentry(self):
        rows=self.report['records'];cps=[r['cp'] for r in rows]
        self.assertEqual(len(cps),len(set(cps)))
        self.assertEqual(set(cps),set(self.o.allocation_members('chvc')))
        self.assertFalse(set(cps)&set(overview.exclusive_intake()))
        self.assertEqual(len(cps),1554)

    def test_group_partition_and_feature_signatures(self):
        rows=self.report['records'];groups={g['id']:g for g in self.report['groups']}
        self.assertEqual(sum(g['count'] for g in groups.values()),len(rows))
        counts=Counter(r['groupId'] for r in rows)
        for gid,g in groups.items():self.assertEqual(g['count'],counts[gid])
        for r in rows:
            if r['status']=='stable':
                self.assertTrue(r['stableAcrossNineVariants'])
                self.assertEqual([r['statistics'][k] for k in FIELDS],groups[r['groupId']]['signature'])
                self.assertFalse(r['statistics']['otherJunctions'] or r['statistics']['uncertainSegments'])

    def test_nine_variants_and_uncertainty_not_hidden(self):
        combinations={(s,w) for s in (96,192,256) for w in (-1,0,1)}
        for r in self.report['records']:
            self.assertEqual({(v['size'],v['weight']) for v in r['variants']},combinations)
            self.assertEqual(len(r['variants']),9)
            actual=sum(v['statistics']==r['statistics'] for v in r['variants'])
            self.assertEqual(actual,r['variantsAgreeWithBaseline'])
            self.assertEqual(not r['errors'] and actual==9,r['stableAcrossNineVariants'])
            if not r['stableAcrossNineVariants']:self.assertEqual(r['groupId'],'pending-unstable')

    def test_original_codes_and_preferences_preserved(self):
        for r in self.report['records']:
            current=self.o.brief(r['cp'],True)
            self.assertEqual(r['originalCodes'],current['codes'])
            self.assertEqual(r['originalPreferredCodes'],current['preferredCodes'])
        self.assertEqual(self.report['newCodes']+self.report['removedPaths']+self.report['tBReentry'],0)

    def test_confirmed_sample_baselines_and_previously_guaranteed_fields(self):
        rows={r['cp']:r for r in self.report['records']}
        accepted=self.report['sampleAcceptance']['samples']
        prior=json.loads((OUTPUT.parent/'20261024-turn-junction-samples-v2/七例转折与分段结果.json').read_text(encoding='utf-8'))
        expected={r['cp']:r['userExpected'] for r in prior['records']}
        self.assertEqual(len(accepted),7)
        for sample in accepted:
            r=rows[sample['cp']]
            self.assertEqual(r['statistics'],sample['statistics'])
            # Prior calibration guaranteed the fields explicitly specified by
            # the user, not every newly inferred straight/curved segment count.
            for v in r['variants']:
                for key,value in expected[r['cp']].items():
                    self.assertEqual(v['statistics'][key],value)
            if r['variantsAgreeWithBaseline']<9:
                self.assertEqual(r['status'],'pending-unstable')

    def test_existing_inputs_unchanged(self):
        self.assertEqual(protect(),self.report['protectedHashes'])
        for name,digest in self.report['sourceHashes'].items():
            self.assertEqual(sha(PROJECT/name),digest,name)

    def test_every_plain_and_marked_tile_exists_and_has_ink(self):
        images={}
        for r in self.report['records']:
            p=r['preview']
            crops=[]
            for view in ('plain','annotated'):
                key=(p['atlas'],view)
                if key not in images:images[key]=Image.open(OUTPUT/f'atlas/{key[0]:03}-{key[1]}.png').convert('RGB')
                crop=images[key].crop((p['x'],p['y'],p['x']+96,p['y']+96))
                self.assertLess(min(v[0] for v in crop.getextrema()),220)
                self.assertGreater(max(v[1] for v in crop.getextrema()),240)
                crops.append(crop.tobytes())
            self.assertNotEqual(crops[0],crops[1])

    def test_multiexit_is_not_forced_into_a_standard_class(self):
        s=dict(corners=0,forks=1,crosses=0,straightSegments=3,curveSegments=0,otherJunctions=0,uncertainSegments=0,totalSegments=3)
        rows=[dict(cp=1,statistics=s,errors=[],stableAcrossNineVariants=True),
              dict(cp=2,statistics=dict(s,otherJunctions=1),errors=[],stableAcrossNineVariants=True),
              dict(cp=3,statistics=s,errors=[],stableAcrossNineVariants=False)]
        classify_records(rows)
        self.assertEqual([r['status'] for r in rows],['stable','pending-interpretation','pending-unstable'])


if __name__=='__main__':unittest.main()
