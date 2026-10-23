import unittest
import hashlib
import copy
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'原型/键位编辑器'))
import build_shape_centre_trial as trial
from shape_experiment_features import observe,render
from shape_experiment_rules import obj,position
from audit_shape_historical_buckets import assert_protected_snapshot


class CentreTests(unittest.TestCase):
    def test_exclusive_position_boundary(self):
        for x,y in [(0,0),(.119,-.119),(.12,0),(0,-.12),(.2,.2),(-.4,0)]:
            self.assertEqual(trial.is_centre([x,y]),position(x,y,0,0) is None)
        self.assertFalse(trial.is_centre([.12,0]))

    def test_y_actual_central_fork(self):
        f=observe(*render('Y','C:/Windows/Fonts/seguisym.ttf',0))
        for j in f['junctionObjects']:
            o=obj('junction','junction',[j[k] for k in ('x0','y0','x1','y1')],f['bbox'],f['extent'])
            if trial.is_centre(o['relativePosition']):
                self.assertTrue(trial.matching_junction(f,o)['passed']);return
        self.fail('control Y has no central junction')

    def test_t_upper_junction_is_not_centre(self):
        f=observe(*render('T','C:/Windows/Fonts/seguisym.ttf',0))
        for j in f['junctionObjects']:
            o=obj('junction','junction',[j[k] for k in ('x0','y0','x1','y1')],f['bbox'],f['extent'])
            self.assertFalse(trial.matching_junction(f,o)['passed'])

    def test_unrestorable_parent_is_not_guessed(self):
        self.assertFalse(trial.matching_junction(None,{'bbox':[1,1,2,2]})['passed'])

    def test_saved_observations_use_the_same_geometry_recipe(self):
        snapshot=trial.OUTPUT/'中心观测生成器快照.py'
        if not snapshot.is_file():self.skipTest('no observation snapshot')
        self.assertEqual(trial.observation_source(snapshot.read_text(encoding='utf-8')),
                         trial.observation_source(Path(trial.__file__).read_text(encoding='utf-8')))

    def test_parent_component_survives_small_raster_bbox_shift(self):
        index=trial.load(trial.SOURCE/'发布核对索引.json')
        brief=next(r for r in index['records'] if r['cp']==0x1F127)
        row=next(r for r in trial.load(trial.SOURCE/brief['detailUrl'])['records'] if r['cp']==0x1F127)
        item=next(i for i in trial.facts_for(row) if i['route']['target']=='inner-0')
        f=observe(*render(row['char'],row['font']['path'],row['font'].get('index',0),size=48,weight=-1))
        parent=trial.parent_feature(row,item['route'],f)
        self.assertIsNotNone(parent)
        self.assertEqual(len(parent['parts']),1)
        self.assertFalse((parent['mask'] & ~f['mask']).any())
        self.assertTrue(trial.matching_junction(parent,item['object'])['passed'])

    @unittest.skipUnless((trial.OUTPUT/'中心属性交点试验.json').is_file(),'full trial not yet built')
    def test_full_overlay(self):
        r=trial.load(trial.OUTPUT/'中心属性交点试验.json')
        self.assertEqual(r['ordinaryScanned'],28223)
        self.assertEqual(r['forkRelatedCharacters'],5041)
        self.assertEqual(r['sourceCodeSHA256'],hashlib.sha256(Path(trial.__file__).read_bytes()).hexdigest())
        self.assertEqual(r['previous101Stable'],100)
        self.assertEqual([x['cp'] for x in r['previous101Unresolved']],[0x1F127])
        self.assertTrue(assert_protected_snapshot(r['protectedHashes']))
        self.assertTrue(all(not x['preferredCodes'] for x in r['records'] if x['frozenPreference']))
        for x in r['records']:
            for p in x['paths']:
                self.assertTrue(p['code'].endswith('hmo'))
                self.assertTrue(all(e['objectId']==e['fourthObjectId'] for e in p['evidence']))
                for e in p['evidence']:
                    checks=next(o['checks'] for o in x['objectsChecked'] if o['objectId']==e['objectId'])
                    self.assertTrue(all(c['passed'] and c['positionKey'] is None for c in checks))
                    self.assertEqual(len(checks),9)
        import shape_overview as v
        overview=v.get_overview()
        for code,n in r['codeCounts'].items():
            self.assertEqual(overview.query({'prefix':[code],'allocation':['1']})['total'],n)
            self.assertEqual(overview.query({'prefix':[code]})['total'],0)
        for x in v.chvc_trial()['records']:
            if x['preferredCodes']:
                self.assertEqual(overview.brief(x['cp'],True)['preferredCodes'],x['preferredCodes'])
        self.assertEqual(overview.query({'prefix':['chvc'],'allocation':['1']})['total'],1562)
        self.assertEqual(overview.brief(ord('T'),True)['preferredCodes'],['chmw'])
        self.assertIn('iose',overview.brief(ord('Q'),True)['preferredCodes'])
        keys=overview.allocation_keys()
        o=next(k for k in keys if k['position']==4 and k['key']=='o')
        self.assertEqual(o['meaning'],'中心')
        self.assertTrue(o['assigned'])
        self.assertEqual(o['count'],r['stableCharacters'])
        self.assertEqual(v.centre_summary()['newChvcPreferred'],80)
        self.assertEqual(v.centre_summary()['currentChvcSpecificPreferred'],498)
        self.assertEqual(len(v.chvc_members('currentResidual')),781)


if __name__=='__main__':unittest.main()
