"""Locked three-hole quantity is independent of the rejected stroke graph model."""
from collections import deque
import hashlib
import sys
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
import shape_structure_bindings as structural

class RoundClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview()
        cls.a=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')['roundSubjectClosureAcceptance20261028Batch1']
        cls.proof=so.read(ROOT/cls.a['proofReport'])

    def test_three_actual_enclosed_pixel_components_without_skeleton(self):
        p=self.proof;sheet=ROOT/p['sourceSheet']
        self.assertEqual(hashlib.sha256(sheet.read_bytes()).hexdigest(),p['sourceSheetSHA256'])
        x,y,w,h=p['crop'];im=Image.open(sheet).convert('RGB').crop((x,y,x+w,y+h))
        ink={(i%64,i//64) for i,pixel in enumerate(im.getdata()) if pixel[0]<128}
        white={(x,y) for y in range(64) for x in range(64)}-ink
        enclosed=[]
        # Independent breadth-first flood, with no feature extractor or area threshold.
        while white:
            start=next(iter(white));white.remove(start);q=deque([start]);component={start}
            while q:
                x,y=q.popleft()
                for xy in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
                    if xy in white:white.remove(xy);component.add(xy);q.append(xy)
            if not any(x in (0,63) or y in (0,63) for x,y in component):enclosed.append(component)
        self.assertEqual(len(enclosed),3)
        actual=sorted(([min(x for x,y in c),min(y for x,y in c),max(x for x,y in c)+1,max(y for x,y in c)+1],len(c)) for c in enclosed)
        self.assertEqual(actual,[([13,6,20,57],307),([25,7,44,56],777),([40,7,57,56],309)])
        self.assertEqual(sorted((m['bbox'],m['area']) for m in p['members']),actual)
        failed=ROOT/p['historicalTopologyFailure']
        self.assertEqual(hashlib.sha256(failed.read_bytes()).hexdigest(),p['historicalTopologyFailureSHA256'])
        self.assertEqual(len(so.read(failed)['failedVariants']),3)
        r=next(r for r in structural.review_report()['records'] if r['cp']==120123)
        self.assertFalse(r['eligible']);self.assertEqual(r['codes'],[])

    def test_D_distinguishes_central_hole_size_and_whole_hole_group_quantity(self):
        b=self.o.brief(120123,True);d=self.o.detail(120123,True)
        self.assertEqual(b['codes'],(['iegt','iezv','iold'] if so.joint_bc.policy() else ['ikit','ikiv','iold']));self.assertEqual(b['preferredCodes'],[])
        self.assertEqual((b['bucket'],b['familyKey']),('i','k'))
        objects={o['id']:o for o in d['objects']};paths={p['code']:p for p in d['paths']}
        size=paths['iezv' if so.joint_bc.policy() else 'ikiv']['evidence'][0];count=paths['iegt' if so.joint_bc.policy() else 'ikit']['evidence'][0]
        self.assertEqual(size['objectId'],size['fourthObjectId']);self.assertEqual(count['objectId'],count['fourthObjectId'])
        self.assertNotEqual(size['objectId'],count['objectId'])
        self.assertEqual(objects[size['objectId']]['kind'],'hole')
        self.assertAlmostEqual(objects[size['objectId']]['relativeSize'],49/60)
        group=objects[count['objectId']]
        self.assertEqual(group['kind'],'hole-group');self.assertEqual(group['count'],3)
        self.assertEqual(group['members'],[m['objectId'] for m in self.proof['members']])
        self.assertEqual(count['quantityFeature'],'closedHoles');self.assertEqual(count['count'],3)
        self.assertFalse(group['originalNinePerturbationModelPassed'])
        self.assertEqual(group['countAcceptanceScope'],'locked-original-64px-only')
        self.assertEqual(objects[group['parentObjectId']]['bbox'],[2.,2.,62.,61.])
        for member in group['members']:self.assertEqual(objects[member]['kind'],'hole')
        self.assertTrue(paths['iold']['compatibilityOnly'])
        self.assertEqual(len(self.o.brief(120123,False)['codes']),13)

    def test_deseret_b_paths_are_retained_without_new_codes_or_counts(self):
        cp=66580;b=self.o.brief(cp,True);d=self.o.detail(cp,True);old=self.o.detail(cp,False)
        keep={'ibis','ibiv','ibiw','ibma','ibmd','ibmk','ibmm'}
        self.assertEqual((b['bucket'],b['familyKey']),('i','b'));self.assertEqual(set(b['codes']),keep)
        self.assertEqual(b['preferredCodes'],[])
        self.assertEqual({p['code']:p for p in d['paths']},{p['code']:p for p in old['paths'] if p['code'] in keep})
        self.assertTrue(next(r for r in d['familyRoutes'] if r['familyKey']=='b')['primary'])
        self.assertFalse(any(r['familyKey']=='o' for r in d['familyRoutes']))
        self.assertNotIn(cp,self.o.key_members(2,'o',True));self.assertEqual(len(old['paths']),18)
        self.assertEqual(min(d['codeCounts'].values()),27)

    def test_scope_of_i_t_and_both_query_orders(self):
        groups=[g for g in self.o.collision_groups(4,True) if g['code'][2:]=='it']
        self.assertEqual(groups,[] if so.joint_bc.policy() else [{'code':'ikit','count':1}])
        for c in (['iezv','iegt'] if so.joint_bc.policy() else ['ikiv','ikit']):
            self.assertEqual(set(self.o.allocation_members(c)),{120123})
            f=self.o.query(dict(allocation=['1'],prefix=[c]))
            b=self.o.query(dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=[c[1:]+c[0]]))
            self.assertEqual(f['total'],b['total']);self.assertEqual([r['cp'] for r in f['rows']],[r['cp'] for r in b['rows']])
        k=next(k for k in self.o.allocation_keys() if k['position']==3 and k['key']=='i')
        self.assertEqual(k['objectModes'],{'position/size':'single-hole','direction':'hole-group','quantity':'hole-group'})
        self.assertIn('不是直曲总数3',k['condition'])
        t=next(k for k in self.o.allocation_keys() if k['position']==4 and k['key']=='t')
        self.assertEqual(t['meaning'],'三个');self.assertIn('3孔',t['condition'])
        self.assertEqual(structural.data()['version'],'structure-count-bindings-v10')
        self.assertEqual(len(structural.queues()['scopePending']),2073)

if __name__=='__main__':unittest.main()
