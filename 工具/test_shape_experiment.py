"""Object binding, ring topology, abstention and proposal-only compatibility tests."""
import json,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from build_shape_experiment import DATA,FAMILIES,font_sources,prototypes,classify,section_templates
from shape_experiment_features import observe,render,crossing_topology,component_mask,filled
from shape_lab_features import components
from shape_experiment_rules import RULES,TRIAL_KEYS,facts,paths,properties,obj
from shape_experiment_allocation import allocate
from shape_experiment_detector import detect, DOUBLE_LOOP


class ShapeExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        stage=json.loads((DATA/'shape-stage.json').read_text(encoding='utf-8'))
        project=DATA.parents[1];model=json.loads((project/stage['source']/'模型.json').read_text(encoding='utf-8'))
        cls.primary,_,_=font_sources(model);cls.fonts={};cls.anchors=prototypes(cls.primary,cls.fonts)
        cls.sections=section_templates(cls.primary,cls.fonts)
        cls.palette=json.loads((DATA/'全形第四位-当前布局.json').read_text(encoding='utf-8'))['fourth']

    def feature(self,char,size=96,weight=0):
        path,index=self.primary[ord(char)];mask,extent=render(char,path,index,size,weight,self.fonts)
        return observe(mask,extent)

    def test_ring_crossing_regression_across_sizes(self):
        for char in '○◯O0':
            for size in (48,96,128):
                with self.subTest(char=char,size=size):
                    f=self.feature(char,size);self.assertEqual(f['junctions'],0)
                    self.assertEqual(classify(f,self.anchors)[0]['key'],'o')

    def test_structural_shapes_not_ink_weight(self):
        for char in '□▫■▢':self.assertEqual(classify(self.feature(char),self.anchors)[0]['key'],'s')
        for char in '✳✴✵✷✺☆★':self.assertEqual(classify(self.feature(char),self.anchors)[0]['key'],'r')

    def test_empty_corner_does_not_fake_branch(self):
        mask=np.zeros((64,64),bool);mask[10:53,10]=True;mask[52,10:53]=True
        self.assertEqual(crossing_topology(mask)['junctions'],0)
        branch=mask.copy();branch[30,0:30]=True
        self.assertGreaterEqual(crossing_topology(branch)['junctions'],1)

    def test_low_confidence_not_compound_fallback(self):
        f=self.feature('○');f['signature']=np.ones_like(f['signature'])*100
        self.assertEqual(classify(f,self.anchors),[])

    def test_dot_is_not_hole_and_connected_cross_is_found(self):
        dot=facts(self.feature('⊙'),'o');self.assertIn('d',{a['third'] for a in dot})
        self.assertNotIn('o',{a['third'] for a in dot})
        for char in '⊕⊗':self.assertIn('x',{a['third'] for a in facts(self.feature(char),'o')})
        self.assertNotIn('x',{a['third'] for a in facts(self.feature('○'),'o')})

    def test_section_rules_and_fourth_object(self):
        for char,third,key in [('◡','p','s'),('◜','f','j')]:
            f=self.feature(char);pp=paths('a','c',facts(f,'c',self.sections),self.palette)
            self.assertIn('ac'+third+key,{p['code'] for p in pp})

    def test_exhaustive_paths_share_object_and_no_cartesian_product(self):
        f=self.feature('⊙');ff=facts(f,'o');pp=paths('i','o',ff,self.palette)
        expected={('io'+fact['third']+key,fact['object']['id']) for fact in ff for key,_ in properties(fact['object'])}
        actual={(p['code'],e['objectId']) for p in pp for e in p['evidence'] if len(p['code'])==4}
        self.assertEqual(actual,expected)
        self.assertEqual(len(pp),len({p['code'] for p in pp}))
        for p in pp:
            for e in p['evidence']:self.assertEqual(e['objectId'],e['fourthObjectId'])
        self.assertGreater(len(pp),1)
        offcentre=obj('dot','part',[42,10,48,16],[0,0,60,60],1)
        self.assertGreater(len(properties(offcentre)),1)

    def test_no_padding_and_no_centre_c(self):
        opening=obj('gap','opening',[0,0,0,0],[0,0,60,60],1)
        opening['relativePosition']=[0,0]
        pp=paths('a','c',[{'third':'u','function':RULES['u'][0],'object':opening,'reason':'test','status':'confirmed'}],self.palette)
        self.assertEqual([p['code'] for p in pp],['acu'])
        self.assertEqual(self.palette['c']['function'],'size.medium')

    def test_old_confirmed_functions_and_trial_keys_preserved(self):
        self.assertFalse(set(RULES)&set(TRIAL_KEYS))
        for suffix in ('01','02','03','05','06'):
            batch=json.loads((DATA/f'全形圆族试验-{suffix}.json').read_text(encoding='utf-8'))
            for key,function in batch['functionIds']['third'].items():self.assertEqual(RULES[key][0],function)

    def test_family_identity_is_independent_of_bucket(self):
        records=[]
        for cp in range(2100):
            records.append({'cp':cp,'oldBucket':'i','oldReviewed':False,'familyKey':'o','features':{'ratio':.6 if cp<1000 else 1.0},'familyRoutes':[], 'paths':[]})
        groups,report=allocate(records)
        self.assertEqual(len({r['bucket'] for r in records}),2)
        self.assertEqual({r['familyKey'] for r in records},{'o'})
        self.assertTrue(report['splits']);self.assertFalse(report['hardCapacity'])
        self.assertEqual(len({r['cp'] for r in records}),2100)

    def test_negative_space_route_allocation_uses_its_own_bounds(self):
        records=[{'cp':1,'oldBucket':'i','oldReviewed':False,'familyKey':'o','features':{'ratio':1.,'parts':[]},
                  'familyRoutes':[{'familyKey':'r','target':'inner-negative-1','bucket':'i'}],
                  'semantic':{'routes':[{'target':'inner-negative-1','bbox':[10,20,30,30]}]},'paths':[]},
                 {'cp':2,'oldBucket':'r','oldReviewed':False,'familyKey':'r','features':{'ratio':1.,'parts':[]},'familyRoutes':[],'paths':[]}]
        groups,_=allocate(records)
        self.assertEqual(records[0]['familyRoutes'][0]['bucket'],records[1]['bucket'])

    def test_bitboard_components_preserve_four_and_eight_connectivity(self):
        rng=np.random.default_rng(20261016)
        for connectivity in (4,8):
            for _ in range(12):
                mask=rng.random((13,17))>.6;seen=np.zeros_like(mask)
                for part in components(mask,connectivity):
                    recovered=component_mask(mask,part,connectivity)
                    self.assertEqual(int(recovered.sum()),part['area'])
                    self.assertFalse((seen&recovered).any());seen|=recovered
                np.testing.assert_array_equal(seen,mask)

    def test_fill_matches_boundary_flood_reference(self):
        rng=np.random.default_rng(47)
        for _ in range(12):
            mask=rng.random((15,16))>.4;bg=~np.pad(mask,1);todo=[(0,0)];outside={(0,0)}
            while todo:
                y,x=todo.pop()
                for dy,dx in ((0,1),(0,-1),(1,0),(-1,0)):
                    yy,xx=y+dy,x+dx
                    if 0<=yy<bg.shape[0] and 0<=xx<bg.shape[1] and bg[yy,xx] and (yy,xx) not in outside:outside.add((yy,xx));todo.append((yy,xx))
            expected=mask.copy()
            for y in range(mask.shape[0]):
                for x in range(mask.shape[1]):
                    if (y+1,x+1) not in outside:expected[y,x]=True
            np.testing.assert_array_equal(filled(mask),expected)

    def test_reviewed_rotation_and_arc_boundaries(self):
        f=self.feature('U')
        for turns in range(4):
            rotated=observe(np.rot90(f['mask'],turns).copy(),f['extent'])
            self.assertEqual(detect(rotated,self.anchors)['primaryFamilyId'],'family.u-shape')
        for c in 'U∪∩⊂⊃':self.assertEqual(classify(self.feature(c),self.anchors)[0]['key'],'u')
        for c in 'C(⌒':self.assertEqual(classify(self.feature(c),self.anchors)[0]['key'],'c')

    def test_local_arm_count_not_global_endpoints(self):
        import math
        for arms in (3,4,5,6):
            im=Image.new('1',(64,64));draw=ImageDraw.Draw(im)
            for i in range(arms):
                angle=2*math.pi*i/arms
                draw.line((32,32,round(32+26*math.cos(angle)),round(32+26*math.sin(angle))),fill=1,width=3)
            f=observe(np.array(im,dtype=bool))
            self.assertEqual([j['armCount'] for j in f['junctionObjects']],[arms])
            ff=facts(f,'r' if arms>=5 else 'h')
            self.assertIn('r' if arms>=5 else 'm',{r['third'] for r in ff})
            self.assertNotIn('m' if arms>=5 else 'r',{r['third'] for r in ff})
            families={r['familyId'] for r in detect(f,self.anchors)['routes']}
            self.assertNotIn('family.line',families)
            self.assertNotIn('family.round-outline',families)
        im=Image.new('1',(64,64));d=ImageDraw.Draw(im)
        d.line((4,32,59,32),fill=1,width=3)
        for x in (16,32,48):d.line((x,8,x,32),fill=1,width=3)
        f=observe(np.array(im,dtype=bool));self.assertGreaterEqual(f['endpoints'],5)
        self.assertTrue(all(j['armCount']<5 for j in f['junctionObjects']))
        self.assertNotIn('r',{r['third'] for r in facts(f,'h')})

    def test_crosses_fork_primary_and_cross_alternative(self):
        for char in '+×':
            result=detect(self.feature(char),self.anchors)
            self.assertEqual(result['primaryFamilyId'],'family.fork')
            self.assertIn('family.cross',{r['familyId'] for r in result['routes']})

    def test_double_loop_unassigned_letter_and_compound_priority(self):
        for char in '∞8':
            result=detect(self.feature(char),self.anchors)
            self.assertEqual(result['primaryFamilyId'],DOUBLE_LOOP)
            self.assertIsNone(result['primaryKey'])
            self.assertIn(DOUBLE_LOOP,result['pendingKeyboardFamilyIds'])
        result=detect(self.feature('B'),self.anchors)
        self.assertNotEqual(result['primaryFamilyId'],DOUBLE_LOOP)
        self.assertIn(DOUBLE_LOOP,{r['familyId'] for r in result['routes']})
        self.assertEqual(detect(self.feature('⚒'),self.anchors)['primaryFamilyId'],'family.compound')

    def test_dot_arrays_keep_both_entries_above_six(self):
        import math
        for count in (6,7,12):
            im=Image.new('1',(64,64));draw=ImageDraw.Draw(im)
            for i in range(count):
                x=32+23*math.cos(2*math.pi*i/count);y=32+23*math.sin(2*math.pi*i/count)
                draw.ellipse((x-2,y-2,x+2,y+2),fill=1)
            r=detect(observe(np.array(im,dtype=bool)),self.anchors)
            families={q['familyId'] for q in r['routes']}
            self.assertIn('family.dots',families)
            self.assertIn('family.round-outline',families)
        self.assertNotIn('family.dots',{r['familyId'] for r in detect(self.feature('○'),self.anchors)['routes']})
        im=Image.new('1',(64,64));d=ImageDraw.Draw(im)
        for x in (5,13,21,29,37,45,53):d.ellipse((x,29,x+3,32),fill=1)
        r=detect(observe(np.array(im,dtype=bool)),self.anchors)
        self.assertTrue({'family.dots','family.line'}<={q['familyId'] for q in r['routes']})

    def test_filled_square_is_not_a_line(self):
        self.assertNotIn('family.line',{r['familyId'] for r in detect(self.feature('■'),self.anchors)['routes']})
        for char in '─│╱╲∥':self.assertEqual(classify(self.feature(char),self.anchors)[0]['key'],'l')

    def test_circle_star_entries_own_objects(self):
        import math
        im=Image.new('1',(64,64));draw=ImageDraw.Draw(im)
        draw.ellipse((2,2,61,61),outline=1,width=2)
        points=[]
        for i in range(10):
            angle=-math.pi/2+i*math.pi/5;radius=16 if i%2==0 else 7
            points.append((32+radius*math.cos(angle),32+radius*math.sin(angle)))
        draw.polygon(points,fill=1)
        r=detect(observe(np.array(im,dtype=bool)),self.anchors)
        self.assertEqual(r['primaryFamilyId'],'family.round-outline')
        stars=[q for q in r['routes'] if q['familyId']=='family.radial' and q['target'].startswith('inner-')]
        self.assertTrue(stars)
        self.assertNotEqual(stars[0]['bbox'],[2,2,62,62])


if __name__=='__main__':unittest.main()
