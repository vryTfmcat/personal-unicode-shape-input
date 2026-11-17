import sys,copy,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
BATCH=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261027-structure-count-bindings-v10/六字计数接入-20261029'
@unittest.skipUnless(so.count_bc.policy(),'六字尚未接入')
class SixCountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.o=so.get_overview();cls.a=so.count_bc.policy();cls.before=so.read(BATCH/'接入前全字.json')
    def test_all_characters_only_six_change_and_preferences(self):
        changed=[];total=0
        for cp,b in self.before.items():
            c=self.o.brief(int(cp),True);total+=len(c['codes']);self.assertEqual(b['preferredCodes'],c['preferredCodes']);self.assertEqual((b.get('bucket'),b.get('familyKey')),(c.get('bucket'),c.get('familyKey')))
            if b!=c:changed.append(cp);self.assertEqual(c['codes'],self.a['records'][cp]['afterCodes'])
        self.assertEqual(set(changed),set(self.a['records']));self.assertEqual(total,208925)
    def test_all_prefixes_and104_keys(self):
        before=so.read(BATCH/'接入前完整前缀成员.json');prefix=set(before)|{c[:n] for c in so.count_bc.codes() for n in range(1,5)}
        for p in prefix:
            expected={int(cp) for cp in before.get(p,{})}
            for cp,r in self.a['records'].items():
                had=any(c.startswith(p) for c in r['beforeCodes']);has=any(c.startswith(p) for c in r['afterCodes'])
                if had and not has:expected.discard(int(cp))
                elif has and not had:expected.add(int(cp))
            self.assertEqual(set(self.o.allocation_members(p)),expected,p)
        for k,cps in so.read(BATCH/'接入前104键.json').items():
            n=int(k[0]);key=k[1];expected=set(cps)
            for cp,r in self.a['records'].items():
                f=lambda cs:any(len(c)>=n and c[n-1]==key for c in cs)
                if f(r['beforeCodes']) and not f(r['afterCodes']) and not(n==2 and r['familyKey']==key):expected.discard(int(cp))
                elif f(r['afterCodes']) and not f(r['beforeCodes']):expected.add(int(cp))
            self.assertEqual(set(self.o.key_members(n,key,True)),expected,k)
    def test_objects_fixed_D_and_all_orders_and_compatibility(self):
        for cp,r in self.a['records'].items():
            d=self.o.detail(int(cp),True);obj={o['id']:o for o in d['objects']};self.assertEqual({p['code'] for p in d['paths']},set(r['afterCodes']))
            for path in r['paths']:
                self.assertTrue(so.count_bc.validate_binding(int(cp),path,obj))
                for digit in so.LETTERS:
                    if digit==path['code'][3]:continue
                    wrong=copy.deepcopy(path);wrong['code']=path['code'][:3]+digit
                    with self.assertRaises(ValueError):so.count_bc.validate_binding(int(cp),wrong,obj)
            for c in r['newCodes']+r['retiredCanonicalCodes']:
                for compat in [False,True]:
                    a=dict(allocation=['1'],prefix=[c]);b=dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=[c[1:]+c[0]])
                    if compat:a['compatibility']=b['compatibility']=['1']
                    f=self.o.query(a);g=self.o.query(b);self.assertEqual(f['total'],g['total']);self.assertEqual([x['cp'] for x in f['rows']],[x['cp'] for x in g['rows']])
                    if c in r['retiredCanonicalCodes']:self.assertEqual(int(cp) in [x['cp'] for x in f['rows']],compat)
    def test_boundaries_and_prior_authority_and_existing_seven(self):
        m=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json');old=so.read(BATCH/'接入前人工审议.json')
        self.assertEqual(set(m)-set(old),{so.count_bc.FIELD,so.count_bc.BOUNDARY})
        for k,v in old.items():self.assertEqual(m[k],v)
        for cp in [66,561]:self.assertEqual(self.o.brief(cp,True)['codes'],self.before[str(cp)]['codes'])
        self.assertFalse(any(c[1:3]=='fg' for c in self.o.brief(561,True)['codes']))
        for code in so.joint_bc.codes():self.assertEqual(len(self.o.allocation_members(code)),1)
        self.assertEqual(len(so.exclusive_intake()),4362);self.assertEqual(len(so.structure.queues()['scopePending']),2073)
if __name__=='__main__':unittest.main()
