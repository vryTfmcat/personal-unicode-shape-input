"""Guard the accepted two-character hint against accidental membership migration."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'原型/键位编辑器'),str(ROOT/'工具')]
import shape_overview as so


class FirstBucketPrimaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview()
        cls.baseline=json.loads((ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/第一位分桶专项-20261025/代表字与对象证据.json').read_text(encoding='utf-8'))

    def test_only_two_primary_fields_change_and_original_view_is_untouched(self):
        for ch in 'ρộ':
            cp=ord(ch);b=self.o.brief(cp,True);d=self.o.detail(cp,True)
            self.assertEqual((b['bucket'],b['familyKey']),('i','o'))
            self.assertEqual((d['bucket'],d['familyKey']),('i','o'))
            self.assertEqual(b['legacyPrimaryBucket'],'e')
            self.assertEqual(self.o.brief(cp,False)['bucket'],'e')
            self.assertNotIn('firstBucketPrimaryAcceptance',self.o.detail(cp,False))
        self.assertEqual(self.o.brief(ord('ộ'),True)['preferredCodes'],['epki'])
        self.assertEqual((self.o.brief(ord('D'),True)['bucket'],self.o.brief(ord('D'),True)['familyKey']),('i','k'))

    def test_all_representative_paths_counts_preferences_and_queries_survive(self):
        for old in self.baseline:
            cp=old['cp'];b=self.o.brief(cp,True);d=self.o.detail(cp,True)
            refinement=so.round_refinement.policy()
            withdrawn=set(refinement['withdrawnCurrentCodes'].get(str(cp),[]))
            expected={p['code'] for p in old['paths']}-withdrawn
            addition=(refinement.get('kFamilyDecisions',{}).get(str(cp),{}).get('newCodes',[])
                      +refinement.get('shapeDecisions',{}).get(str(cp),{}).get('newCodes',[]))
            if cp == 56 and so.hole_groups.policy():addition = addition + ['ebii']
            if cp == 7897 and so.external_groups.policy():addition = addition + ['iokg']
            if cp == 272 and so.external_groups.curve_restore_policy():addition = addition + ['ikqu']
            expected.update(addition)
            if cp==79:expected.add('ioqc')
            expected=set(so.structure.totals.resolve_codes(cp,expected))
            joint=so.accepted_bc_records().get(str(cp))
            if joint:expected=(expected-set(joint['retiredCanonicalCodes']))|set(joint['newCodes'])
            self.assertEqual(set(b['codes']),expected)
            self.assertEqual({p['code'] for p in d['paths'] if p.get('preferred')},{p['code'] for p in old['paths'] if p.get('preferred')})
            for p in old['paths']:
                code=p['code']
                if code in withdrawn or code in so.accepted_bc_records().get(str(cp),{}).get('retiredCanonicalCodes',[]):
                    self.assertNotIn(cp,self.o.allocation_members(code))
                    continue
                delta=sum(code in cs for cs in refinement['withdrawnCurrentCodes'].values())+sum(code in r['retiredCanonicalCodes'] for r in so.accepted_bc_records().values())
                added=sum(code in a['newCodes'] for name in ('kFamilyDecisions','shapeDecisions') for a in refinement.get(name,{}).values())
                if so.structure.totals.active() and len(code)==4 and code[2] in 'jq' and code[3] in 'ubtyp':
                    effective=next(iter(so.joint_bc.migrate_structure(cp,so.structure.totals.resolve_codes(cp,[code]))))
                    self.assertIn(cp,self.o.allocation_members(effective))
                    self.assertEqual(set(self.o.allocation_members(effective)),{int(p) for p,r in so.accepted_bc_records().items() if effective in r['newCodes']} if effective in so.count_bc.codes() else set(so.structure.data()['codeMembers'][effective])-{int(p) for p,r in so.accepted_bc_records().items() if effective in r['retiredCanonicalCodes']})
                    continue
                self.assertIn(cp,self.o.allocation_members(code))
                self.assertEqual(len(self.o.allocation_members(code)),p['count']-delta+added+len(so.external_groups.count_members(code)))
            if cp not in (961,7897) and str(cp) not in refinement.get('shapeDecisions',{}):
                self.assertEqual(b['bucket'],old['bucket'])
                self.assertEqual(b['familyKey'],old['family'])

    def test_every_character_ownership_changes_only_with_explicit_confirmation(self):
        old=json.loads((ROOT/'数据/三模式/规则库/四键实验/键位试验/20261025-structure-count-bindings-v5/第一位分桶专项-20261025/统计.json').read_text(encoding='utf-8'))
        changes=[]
        for cp,entry in old['ownership'].items():
            row=self.o.brief(int(cp),True)
            withdrawn=so.round_refinement.policy()['withdrawnCurrentCodes'].get(cp,[])
            added=(so.round_refinement.policy().get('kFamilyDecisions',{}).get(cp,{}).get('newCodes',[])
                   +so.round_refinement.policy().get('shapeDecisions',{}).get(cp,{}).get('newCodes',[]))
            if cp == '56' and so.hole_groups.policy():added = added + ['ebii']
            if cp == '7897' and so.external_groups.policy():added = added + ['iokg']
            if cp == '272' and so.external_groups.curve_restore_policy():added = added + ['ikqu']
            self.assertEqual(len(row['codes']),entry['codeRoutes']-len(withdrawn)+len(added)+(1 if int(cp) in (79,55) else 0)+(len(so.accepted_bc_records().get(cp,{}).get('newCodes',[]))-len(so.accepted_bc_records().get(cp,{}).get('retiredCanonicalCodes',[]))))
            if row.get('bucket')!=entry['bucket']:changes.append(int(cp))
        self.assertEqual(set(changes),{961,7897,123}|({127251} if 'dSubjectHoleShapeAcceptance20261027Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({127376} if 'dSubjectHoleShapeAcceptance20261027Batch3' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set()))
        for entry in old['buckets']:
            bucket=entry['bucket']
            approved=so.round_refinement.policy().get('boxedDDecisions',{})
            removed=sum(any(c.startswith(bucket) for c in a['withdrawnCurrentCodes'])
                        and not any(c.startswith(bucket) for c in a['retainedCurrentCodes'])
                        for a in approved.values())
            new_aliases=sum(any(c.startswith(bucket) for c in a['newCodes']) and not any(c.startswith(bucket) for c in a['beforeCodes'])
                            for a in so.round_refinement.policy().get('shapeDecisions',{}).values())
            self.assertEqual(len(self.o.allocation_members(bucket)),entry['query']-removed+new_aliases)


if __name__=='__main__':unittest.main()
