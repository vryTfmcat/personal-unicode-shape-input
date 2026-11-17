"""Approved full migration: exact members, selector domains and preserved authority."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'工具'),str(ROOT/'原型/键位编辑器')]
import shape_overview as so
import shape_structure_bindings as binding


@unittest.skipUnless(binding.totals.active(),'仅适用于已激活的直曲总数量规则')
class ContinuousTotalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o=so.get_overview();cls.a=binding.totals.policy()
        cls.folder=(ROOT/cls.a['generation']['baseRuntime']).parent
        cls.rows=so.read(cls.folder/'全量逐路迁移清单.json')

    def test_exact_reviewed_paths_same_total_objects_and_no_new_selectors(self):
        cache={};actual=set()
        for r in self.rows:
            cp=r['cp']
            if cp not in cache:cache[cp]=self.o.detail(cp,True)
            d=cache[cp];p=next(p for p in d['paths']+d.get('compatibilityPaths',[]) if p['code']==r['newCode'])
            e=p['evidence'][0];objects={o['id']:o for o in d['objects']};obj=objects[e['objectId']]
            self.assertEqual(e['objectId'],e['fourthObjectId'])
            self.assertEqual(obj['feature'],'totalContinuousGroups')
            self.assertEqual(obj['count'],r['straight']+r['curve'])
            self.assertEqual(obj['memberTypeCounts'],{'straight':r['straight'],'curve':r['curve']})
            self.assertIn('总数'+str(r['total']),e['attribute'])
            actual.add((cp,p['code']))
        expected={(r['cp'],r['newCode']) for r in self.rows}
        self.assertEqual(actual,expected);self.assertEqual(len(actual),1930)
        registered={(r['cp'],c) for r in binding.data()['records'] for c in r['codes'] if c[2] in 'jq'}
        self.assertEqual(registered,expected)

    def test_every_merged_split_or_retired_group_has_exact_members(self):
        groups=so.read(self.folder/'完整候选组差异.json')
        for g in groups:
            expected=set(g['retained'])|set(g['added'])
            if so.joint_bc.policy():expected-={int(cp) for cp,r in so.accepted_bc_records().items() if g['code'] in r['retiredCanonicalCodes']}
            self.assertEqual(set(self.o.allocation_members(g['code'])),expected,g['code'])
        self.assertEqual(set(self.o.allocation_members('ikjt')),({7694} if so.joint_bc.policy() else {272,7694}))
        self.assertEqual(set(self.o.allocation_members('ikqt')),({7694} if so.joint_bc.policy() else {272,7694}))
        self.assertFalse(self.o.allocation_members('ikqu'))
        self.assertFalse(so.external_groups.curve_restore_active())

    def test_all_preferred_candidate_sets_and_key_members(self):
        # v10 froze these sets before the later, explicit two-subject withdrawals.
        manual=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')
        batches=[manual[k] for k in ['dSubjectHoleShapeAcceptance20261027Batch1','dSubjectHoleShapeAcceptance20261027Batch2','dSubjectHoleShapeAcceptance20261027Batch3','roundSubjectClosureAcceptance20261028Batch1'] if k in manual]
        records={cp:a for batch in batches for cp,a in batch['records'].items()}
        for c,cps in so.read(self.folder/'既有首选候选集合.json').items():
            expected=set(cps)-{int(cp) for cp,a in records.items() if c in a['withdrawnCurrentCodes']}
            self.assertEqual(set(self.o.allocation_members(c)),expected,c)
        changes=[]
        for later in batches:
            changes+=so.read((ROOT/later['candidateReport']).parent/'精确全字与成员差异验收.json')['keys']
        for k in so.read(self.folder/'规范位每键去重人数差异.json'):
            current=set(self.o.key_members(k['position'],k['key'],True))
            delta=sum(x['after']-x['before'] for x in changes if (x['position'],x['key'])==(k['position'],k['key']))
            if so.joint_bc.policy():
                for r in so.accepted_bc_records().values():
                    present=lambda codes:any(len(c)>=k['position'] and c[k['position']-1]==k['key'] for c in codes)
                    delta+=int(present(r['afterCodes']) or (k['position']==2 and (r.get('familyKey') if 'familyKey' in r else so.joint_bc.baseline_families().get(r['cp']))==k['key']))-int(present(r['beforeCodes']))
            self.assertEqual(len(current),k['after']+delta,(k['position'],k['key']))
            retired={int(cp) for cp,r in so.accepted_bc_records().items() if any(len(c)>=k['position'] and c[k['position']-1]==k['key'] for c in r['beforeCodes']) and not any(len(c)>=k['position'] and c[k['position']-1]==k['key'] for c in r['afterCodes'])}
            self.assertTrue(set(k['added'])-retired<=current)
            self.assertFalse(set(k['removed'])&current)

    def test_frozen_stats_abg_and_all_prior_authority_are_unchanged(self):
        frozen=so.read(ROOT/self.a['generation']['baseReport'])
        current=binding.review_report();old={r['cp']:r for r in frozen['records']}
        for r in current['records']:
            self.assertEqual(r['statistics'],old[r['cp']]['statistics'])
            self.assertEqual([a for a in r['assignments'] if a['code'][2] in 'abg'],
                             [a for a in old[r['cp']]['assignments'] if a['code'][2] in 'abg'])
        manual=so.read(ROOT/'数据/三模式/规则库/四键实验/人工审议.json')
        for k,v in so.read(self.folder/'全局确认前人工审议.json').items():self.assertEqual(manual[k],v,k)
        self.assertEqual(binding.data()['version'],'structure-count-bindings-v10')
        self.assertEqual(binding.data()['countSemanticsVersion'],'whole-continuous-total-v1')

    def test_all_quantity_groups_both_orders_and_detail_counts(self):
        cache={}
        for r in self.rows:
            c=r['newCode']
            if c in cache:continue
            front=self.o.query(dict(allocation=['1'],prefix=[c]))
            back=self.o.query(dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=[c[1:]+c[0]]))
            retired=sum(c in x['retiredCanonicalCodes'] for x in so.accepted_bc_records().values())
            self.assertEqual(front['total'],r['newCandidateCount']-retired)
            self.assertEqual(front['total'],back['total'])
            self.assertEqual([x['cp'] for x in front['rows']],[x['cp'] for x in back['rows']])
            for cp in self.o.allocation_members(c):self.assertEqual(self.o.detail(cp,True)['codeCounts'][c],front['total'])
            cache[c]=True
        self.assertEqual(len(cache),67)

    def test_noncount_exceptions_and_no_missing_type_entries(self):
        self.assertIn('ioqc',self.o.brief(79,True)['codes'])
        self.assertEqual(len(self.o.detail(56,True)['paths']),10 if so.joint_bc.policy() else 9)
        self.assertIn('上小下大',self.o.detail(56,True)['currentFeedbackNote'])
        self.assertIn('ifmg' if so.joint_bc.policy() else 'iokg',self.o.brief(7897,True)['codes'])
        self.assertEqual(self.o.brief(7897,True)['preferredCodes'],['epki'])
        self.assertNotIn('ckqt',self.o.brief(ord('4'),True)['codes'])
        self.assertEqual(set(self.o.brief(272,True)['codes']),({'ikab','ikgu','inmt','ioma'} if so.joint_bc.policy() else {'ikab','ikgu','ikjt','ikqt','ioma'}))
        self.assertEqual(self.o.brief(272,True)['preferredCodes'],[])
        self.assertEqual(self.o.query(dict(allocation=['1'],order=['back'],routeLength=['3'],prefix=['bme']))['total'],67)


if __name__=='__main__':unittest.main()
