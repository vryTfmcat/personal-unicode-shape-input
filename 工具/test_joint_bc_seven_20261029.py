"""Four-character approval boundary, all memberships and explicit compatibility."""
import sys,copy,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
BATCH=ROOT/'数据/三模式/规则库/四键实验/键位试验/20261027-structure-count-bindings-v10/七组合接入-20261029'

@unittest.skipUnless(so.joint_bc.policy(),'七组合未接入')
class JointBCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview();cls.a=so.joint_bc.policy();cls.before=so.read(BATCH/'接入前全字.json')

    def test_exact_four_changes_and_all_original_preferred(self):
        changes=[];before=after=0
        for cp,b in self.before.items():
            c=self.o.brief(int(cp),True);before+=len(b['codes']);after+=len(c['codes'])
            self.assertEqual(c['preferredCodes'],b['preferredCodes'],cp)
            self.assertEqual((c.get('bucket'),c.get('familyKey')),(b.get('bucket'),b.get('familyKey')),cp)
            if c!=b:
                changes.append(cp);r=so.accepted_bc_records()[cp];self.assertEqual(c['codes'],r['afterCodes'])
        self.assertEqual(set(changes),set(so.accepted_bc_records()));self.assertEqual((before,after),(208926,208925 if so.count_bc.policy() else 208927))

    def test_all_prefix_members_and_no_other_character_changes(self):
        prior=so.read(BATCH/'接入前完整前缀成员.json');prefixes=set(prior)
        prefixes|={c[:n] for c in self.a['approvedCodes']+so.count_bc.codes() for n in range(1,5)}
        for prefix in prefixes:
            old={int(cp):tier for cp,tier in prior.get(prefix,{}).items()};expected=set(old)
            for cp,r in so.accepted_bc_records().items():
                cp=int(cp)
                had=any(c.startswith(prefix) for c in r['beforeCodes']);has=any(c.startswith(prefix) for c in r['afterCodes'])
                if had and not has:expected.discard(cp)
                elif has and not had:expected.add(cp)
            current=self.o.allocation_members(prefix)
            self.assertEqual(set(current),expected,prefix)
            for cp,tier in old.items():
                if str(cp) not in so.accepted_bc_records():self.assertEqual(current.get(cp),tier,(prefix,cp))

    def test_all104_keys_and_real_short_routes(self):
        old=so.read(BATCH/'接入前104键.json')
        for name,cps in old.items():
            n=int(name[0]);key=name[1];expected=set(cps)
            for cp,r in so.accepted_bc_records().items():
                had=any(len(c)>=n and c[n-1]==key for c in r['beforeCodes']);has=any(len(c)>=n and c[n-1]==key for c in r['afterCodes'])
                if had and not has and not(n==2 and self.before[cp].get('familyKey')==key):expected.discard(int(cp))
                elif has and not had:expected.add(int(cp))
            self.assertEqual(set(self.o.key_members(n,key,True)),expected,name)
        for cp,b in self.before.items():
            self.assertEqual([c for c in b['codes'] if len(c)==3],[c for c in self.o.brief(int(cp),True)['codes'] if len(c)==3],cp)

    def test_both_orders_default_and_explicit_compatibility(self):
        for cp,r in so.accepted_bc_records().items():
            for code in r['newCodes']+r['retiredCanonicalCodes']:
                for compat in [False,True]:
                    p=dict(allocation=['1'],prefix=[code]);q=dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=[code[1:]+code[0]])
                    if compat:p['compatibility']=q['compatibility']=['1']
                    f=self.o.query(p);b=self.o.query(q)
                    self.assertEqual(f['total'],b['total']);self.assertEqual([x['cp'] for x in f['rows']],[x['cp'] for x in b['rows']])
                    if code in r['retiredCanonicalCodes']:self.assertEqual(int(cp) in [x['cp'] for x in f['rows']],compat)
            d=self.o.detail(int(cp),True)
            self.assertEqual({p['code'] for p in d['paths']},set(r['afterCodes']))
            self.assertEqual({p['code'] for p in d['compatibilityPaths']},set(r['retiredCanonicalCodes']))
        self.assertEqual(set(self.o.allocation_members('ikjt')),{7694});self.assertEqual(set(self.o.allocation_members('ikqt')),{7694})

    def test_fixed_objects_illegal_values_and_negative_binding_fixtures(self):
        for cp,r in self.a['records'].items():
            d=self.o.detail(int(cp),True);objects={o['id']:o for o in d['objects']}
            for path in r['paths']:
                self.assertTrue(so.joint_bc.validate_binding(int(cp),path,objects))
                code=path['code']
                for digit in so.LETTERS:
                    if digit==code[3]:continue
                    wrong=copy.deepcopy(path);wrong['code']=code[:3]+digit
                    with self.assertRaises(ValueError):so.joint_bc.validate_binding(int(cp),wrong,objects)
                    self.assertNotIn(int(cp),self.o.allocation_members(wrong['code']))
                bad=copy.deepcopy(objects);oid=path['evidence'][0]['objectId']
                if code=='eesw':bad[oid]['area']=max(o.get('area') or 0 for o in bad.values())
                elif code[1:3] in ['ec','fg','fm','eg']:bad[oid]['members']=bad[oid]['members']+['unapproved-third-member']
                elif code=='inmt':bad[oid]['memberTypeCounts']={'straight':3,'curve':0}
                else:bad[path['evidence'][0]['sizeReferenceObjectId']]['bbox']=[0,0,49,49]
                with self.assertRaises(ValueError):so.joint_bc.validate_binding(int(cp),path,bad)
        for code in ['eecb','eehi','izec']:self.assertFalse(self.o.allocation_members(code))
        with self.assertRaises(ValueError):self.o.query(dict(allocation=['1'],compatibility=['1'],prefix=['iki']))

    def test_unchanged_authority_sources_history_and_scope(self):
        manual=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json');before=so.read(BATCH/'接入前人工审议.json')
        self.assertEqual(set(manual)-set(before),{so.joint_bc.FIELD}|({so.count_bc.FIELD,so.count_bc.BOUNDARY} if so.count_bc.policy() else set()))
        for k,v in before.items():self.assertEqual(manual[k],v,k)
        self.assertFalse(self.a['globalClassifierCompleted'])
        for cp in self.a['records']:
            old=self.o.brief(int(cp),False);self.assertFalse(set(old['codes'])&set(self.a['approvedCodes']))
        self.assertEqual(so.structure.data()['version'],'structure-count-bindings-v10')
        self.assertEqual(len(so.structure.queues()['scopePending']),2073)
        self.assertEqual(len(so.exclusive_intake()),4362)

if __name__=='__main__':unittest.main()
