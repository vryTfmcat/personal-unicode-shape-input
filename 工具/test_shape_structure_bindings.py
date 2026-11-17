"""Whole-scope additive binding checks: no missing candidates or altered preferences."""
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / '原型/键位编辑器')]
import shape_overview as so
import shape_structure_bindings as binding
from build_shape_structure_bindings import OUT, whole_curve_scope
from shape_structure_scope import check_scope, load_facts


class StructureBindingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = so.get_overview()
        cls.report = binding.review_report()

    def test_complete_curve_examples_and_counterexamples(self):
        cps = set(self.o.allocation_members('ajqu'))
        for char in ')J':
            self.assertIn(ord(char), cps)
        for char in 'fjĳĲt':
            self.assertNotIn(ord(char), cps)
            self.assertTrue(self.o.brief(ord(char), True)['codes'])
        source = so.read(so.RUNS / '20261024-other-large-collisions-v1/其他大组分析.json')
        by_cp = {r['cp']: r for r in source['records']}
        for cp in cps:
            self.assertTrue(whole_curve_scope(by_cp[cp])[0], cp)
        previous = so.read(so.RUNS / '20261024-structure-count-bindings-v2/大组结构键位分配.json')
        self.assertEqual(cps, set(previous['codeMembers']['ajqu']))

    def test_all_remaining_prefixes_meet_whole_scope_conditions(self):
        source = so.read(so.RUNS / '20261024-other-large-collisions-v1/其他大组分析.json')
        by_cp = {r['cp']: r for r in source['records']}
        for r in self.report['records']:
            for a in r['assignments']:
                if r.get('acceptedBoundary'):
                    self.assertIn(r['char'], '4ftDPᶔĎḊḎḒᴰⅮＤ𝗗7Đ')
                    self.assertTrue(a['humanScopeConfirmed'])
                    self.assertTrue(a['code'].startswith(r['acceptedBoundary']['prefix']))
                    continue
                if a['code'][1] == 'j':
                    self.assertTrue(whole_curve_scope(by_cp[r['cp']])[0])
                else:
                    self.assertTrue(check_scope(a['code'][:2], by_cp[r['cp']], r['wholeRouteFacts'])[0])
        self.assertFalse(any(c[1] == 'd' for c in self.report['codeMembers']))

    def test_real_line_circle_and_branch_examples(self):
        source = so.read(so.RUNS / '20261024-other-large-collisions-v1/其他大组分析.json')
        rows = {r['cp']: r for r in source['records']}
        facts = load_facts(self.o, {ord(c) for c in 'TꓬꚔO∥f'})
        for char, prefix in [('T', 'ch'), ('ꓬ', 'ch'), ('Ꚕ', 'ch'), ('O', 'io'), ('∥', 'al')]:
            self.assertTrue(check_scope(prefix, rows[ord(char)], facts[ord(char)])[0], char)
        hypothetical_line = dict(routes=[dict(prefix='al', target='body', supplementOnly=False, verified=None)])
        self.assertFalse(check_scope('al', rows[ord('f')], hypothetical_line)[0])
        local = dict(routes=[dict(prefix='ch', target='inner-0', supplementOnly=False, verified=True)])
        self.assertFalse(check_scope('ch', rows[ord('T')], local)[0])

    def test_visible_counterexamples_do_not_gain_whole_subject_routes(self):
        index = {r['cp']: r for r in self.report['records']}
        for cp, prefix in [(0x44, 'io'), (0x1F119, 'hw'), (0x1F122, 'hw'), (0x1F7C6, 'qx')]:
            self.assertFalse(any(c.startswith(prefix) for c in index[cp]['codes']))
            self.assertTrue(self.o.brief(cp, True)['codes'], '原入口应保留')
            self.assertTrue(any(x['prefix'] == prefix for x in index[cp].get('previousScopeRejections', index[cp]['scopeRejections'])))

    def test_every_new_code_has_exact_full_union_and_prefix_members(self):
        for code, cps in self.report['codeMembers'].items():
            expected=(set(cps)|so.external_groups.count_members(code))-{int(cp) for cp,r in so.accepted_bc_records().items() if code in r['retiredCanonicalCodes']}
            self.assertEqual(set(self.o.allocation_members(code)), expected, code)
            self.assertLessEqual(expected, set(self.o.allocation_members(code[:3])))
            self.assertLessEqual(expected, set(self.o.allocation_members(code[:2])))
            self.assertFalse(set(self.o.allocation_members(code,)) & so.exclusive_intake().keys())

    def test_all_characters_preserve_previous_codes_and_preferences(self):
        for r in self.report['records']:
            brief = self.o.brief(r['cp'], True)
            withdrawn=set(so.round_refinement.policy()['withdrawnCurrentCodes'].get(str(r['cp']),[]))
            self.assertLessEqual(set(r['oldCodes'])-withdrawn-set(so.accepted_bc_records().get(str(r['cp']),{}).get('retiredCanonicalCodes',[])), set(brief['codes']))
            self.assertFalse(withdrawn & set(brief['codes']))
            self.assertEqual(r['oldPreferredCodes'], brief['preferredCodes'])
            self.assertEqual(so.joint_bc.migrate_structure(r['cp'],r['codes']), set(brief.get('structuralCodes', [])))
            if not r['eligible']:
                self.assertFalse(r['codes'])

    def test_nine_view_gate_and_count_buckets(self):
        suffixes = {1: 'u', 2: 'b', 3: 't', 4: 'y', 5: 'p'}
        for r in self.report['records']:
            for a in r['assignments']:
                self.assertTrue(r['eligible'])
                self.assertEqual(a['variants'], 9)
                self.assertGreater(a['count'], 0)
                self.assertEqual(a['count'], (r['statistics']['straightStrokes']+r['statistics']['curveStrokes'] if a['feature']=='totalContinuousGroups' else r['statistics'][a['feature']]))
                self.assertEqual(a['code'][3], suffixes[min(a['count'], 5)])

    def test_details_and_historical_isolation(self):
        for char, new in [('T', 'chjb'), ('ꓬ', 'chjt'), ('Ꚕ', 'chqb')]:
            cp = ord(char)
            new=next(iter(so.joint_bc.migrate_structure(cp,{new})))
            row = self.o.detail(cp, True)
            self.assertIn(new, [p['code'] for p in row['paths']])
            self.assertEqual(set(self.o.brief(cp, True)['codes']), {p['code'] for p in row['paths']})
            for p in row['paths']:
                self.assertEqual(row['codeCounts'][p['code']], len(self.o.allocation_members(p['code'])))
                if p.get('structuralCollection'):
                    e = p['evidence'][0]
                    self.assertEqual(e['objectId'], e['fourthObjectId'])
                    self.assertTrue(any(o['id'] == e['objectId'] for o in row['objects']))
            self.assertFalse(any(p.get('structuralCollection') for p in self.o.detail(cp, False)['paths']))

    def test_all_old_large_groups_are_unchanged_and_not_aliased_in_statistics(self):
        for g in self.report['groups']:
            actual = self.o.allocation_members(g['code'])
            withdrawals=so.round_refinement.policy()['withdrawnCurrentCodes']
            withdrawals={cp:list(cs) for cp,cs in withdrawals.items()}
            for cp,accepted in so.accepted_bc_records().items():
                withdrawals.setdefault(cp,[]).extend(accepted['retiredCanonicalCodes'])
            removed={int(cp) for cp,cs in withdrawals.items() if g['code'] in cs}
            self.assertEqual(len(actual), g['before']-len(removed))
            self.assertEqual(set(actual), {r['cp'] for r in g['recommendations']}-removed)
            for r in g['recommendations']:
                if r['code'] in withdrawals.get(str(r['cp']),[]):
                    self.assertNotIn(r['cp'],self.o.allocation_members(r['code']))
                    continue
                self.assertIn(r['cp'], self.o.allocation_members(r['code']))
                delta=sum(r['code'] in cs for cs in withdrawals.values())
                self.assertEqual(r['burden']-delta, len(self.o.allocation_members(r['code'])))

    def test_current_keys_and_legacy_keys_are_separate(self):
        keys = {(k['position'], k['key']): k for k in self.o.allocation_keys()}
        for key in 'abgjq':
            self.assertTrue(keys[3, key]['assigned'])
            self.assertGreater(keys[3, key]['count'], 0)
            self.assertFalse(self.o.key_members(3, key, False))
        for key in 'uyp':
            self.assertTrue(keys[4, key]['assigned'])
        for key in 'abgjq':
            expected=binding.key_index()[3,key]|(so.external_groups.count_members('ikqu') if key=='q' else set())
            for cp,r in so.accepted_bc_records().items():
                had=any(len(c)>2 and c[2]==key for c in r['beforeCodes']);has=any(len(c)>2 and c[2]==key for c in r['afterCodes'])
                if had and not has:expected=expected-{int(cp)}
                elif has and not had:expected=expected|{int(cp)}
            self.assertEqual(set(self.o.key_members(3,key,True)),expected)


    def test_four_round_summary_and_actual_queues(self):
        summary = binding.summary()
        self.assertEqual(summary['codeCounts'], {c: len(v) for c,v in self.report['codeMembers'].items()})
        self.assertEqual(len(summary['groups']), 55)
        assigned = set(binding.queues()['assigned'])
        observation = set(binding.queues()['observationPending'])
        scope = set(binding.queues()['scopePending'])
        self.assertFalse(assigned & (observation | scope))
        self.assertFalse(observation & scope)
        self.assertEqual(len(assigned | observation | scope | set(binding.queues()['reviewedRetained'])), summary['statistics']['observed'])
        for key, cps in binding.queues().items():
            result = self.o.query({'structure':[key], 'allocation':['1']})
            self.assertEqual(result['total'], len(cps))
            self.assertEqual({r['cp'] for r in result['rows']}, set(cps[:60]))
        with self.assertRaises(ValueError):
            self.o.query({'structure':['assigned']})
        with self.assertRaises(ValueError):
            self.o.query({'structure':['unknown'], 'allocation':['1']})

    def test_key_examples_belong_to_new_collection(self):
        for k in self.o.allocation_keys():
            if 'collectionExamples' not in k:
                continue
            self.assertTrue(k['collectionExamples'])
            for r in k['collectionExamples']:
                self.assertIn(r['cp'], binding.key_index()[k['position'], k['key']])
                self.assertTrue(any(c[k['position']-1] == k['key'] for c in r['structuralCodes']))
            if k['position'] == 3:
                self.assertEqual(k['anchors'], [r['char'] for r in k['collectionExamples']])


    def test_seven_accepted_boundaries_and_preserved_v3(self):
        history_report=(so.read(so.PROJECT/binding.totals.authority()['generation']['baseReport']) if binding.totals.active() else self.report)
        previous=so.read(so.RUNS/'20261024-structure-count-bindings-v3/大组结构键位分配.json')
        before={r['cp']:r for r in previous['records']}
        mapping={'4':'ck','D':'ik','P':'rk','f':'cx','t':'cx','ᶔ':'cw','Q':'io'}
        for r in history_report['records']:
            if r['char'] not in mapping:
                if r['cp']==55 and history_report['version'] in ('structure-count-bindings-v8','structure-count-bindings-v9'):
                    self.assertEqual(r['acceptedBoundary'],so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json')['sevenAngleScopeAcceptance20261025']['decisions']['55'])
                    continue
                if r['char'] in 'ĎḊḎḒᴰⅮＤ𝗗Đ':
                    self.assertEqual(r['acceptedBoundary'],so.round_refinement.policy()['kFamilyDecisions'][str(r['cp'])])
                    continue
                if binding.p_family_decision(r['cp']) and binding.p_family_decision(r['cp'])['action']=='withdraw-p-whole-counts':
                    continue
                self.assertEqual(r,before[r['cp']])
                continue
            cp=r['cp'];a=r['acceptedBoundary']
            self.assertEqual(a['prefix'],mapping[r['char']])
            brief=self.o.brief(cp,True);detail=self.o.detail(cp,True)
            self.assertEqual(brief['familyKey'],a['familyKey'])
            self.assertEqual(detail['familyKey'],a['familyKey'])
            if any(c.startswith(a['prefix']) for c in brief['codes']):
                self.assertIn(cp,self.o.allocation_members(a['prefix']))
            else:
                self.assertIn(str(cp),so.accepted_bc_records())
            self.assertIn(cp,self.o.key_members(2,a['familyKey'],True))
            if r['char']=='Q':
                self.assertFalse(r['codes'])
                self.assertIn(cp,binding.queues()['reviewedRetained'])
            else:
                self.assertTrue(r['codes'])
                self.assertTrue(all(c.startswith(a['prefix']) for c in r['codes']))
            self.assertEqual(set(brief['codes']),{x['code'] for x in detail['paths']})
            self.assertEqual(before[cp]['oldPreferredCodes'],brief['preferredCodes'])
        self.assertEqual(set(self.o.key_members(2,'k',True)),{ord(c) for c in '4DPĎḊḎḒᴰⅮＤ𝗗Đ'}|({119811,127251} if 'dSubjectHoleShapeAcceptance20261027Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({120227} if 'dSubjectHoleShapeAcceptance20261027Batch2' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({127376} if 'dSubjectHoleShapeAcceptance20261027Batch3' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({120123} if 'roundSubjectClosureAcceptance20261028Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set()))
        self.assertFalse(self.o.key_members(2,'k',False))
        self.assertEqual(history_report['statistics']['scopeAddedPaths'],46)
        self.assertEqual(history_report['statistics']['wholeScopePending'],2073)


    def test_closed_family_policy_changes_definitions_not_members(self):
        policy=binding.closed_family_policy()
        self.assertEqual(policy['decisions'],{'K1':0,'K2':0})
        self.assertEqual(set(policy['definitions']),set('kostbp'))
        effective=binding.effective_definitions()
        for key in 'kostbp':
            self.assertEqual(effective['second'][key]['status'],'accepted-closed-family-policy')
            self.assertTrue(effective['second'][key]['condition'])
        self.assertNotIn('s',binding.data()['definitions']['second'])
        self.assertNotIn('s',self.report['definitions']['second'])
        keys={(r['position'],r['key']):r for r in self.o.allocation_keys()}
        for key in 'kostbp':
            self.assertEqual(keys[2,key]['count'],len(self.o.key_members(2,key,True)))
            self.assertEqual(keys[2,key]['status'],'accepted-closed-family-policy')
        self.assertEqual(set(self.o.key_members(2,'k',True)),{ord(c) for c in '4DPĎḊḎḒᴰⅮＤ𝗗Đ'}|({119811,127251} if 'dSubjectHoleShapeAcceptance20261027Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({120227} if 'dSubjectHoleShapeAcceptance20261027Batch2' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({127376} if 'dSubjectHoleShapeAcceptance20261027Batch3' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({120123} if 'roundSubjectClosureAcceptance20261028Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set()))
        self.assertEqual(binding.data()['statistics'],self.report['statistics'])

    def test_p_batch_scope_and_exact_five_path_withdrawal(self):
        history_report=(so.read(so.PROJECT/binding.totals.authority()['generation']['baseReport']) if binding.totals.active() else self.report)
        review=binding.data().get('pFamilyBoundaryReview')
        if not review:
            self.skipTest('p首批尚未接入此历史版')
        base=so.read(so.PROJECT/review['generation']['baseReport'])
        old={r['cp']:r for r in base['records']}
        removed=[]
        for r in history_report['records']:
            before=old[r['cp']]
            if r['char'] in 'ρộ':
                self.assertEqual(r['oldCodes'],before['oldCodes'])
                self.assertEqual(r['oldPreferredCodes'],before['oldPreferredCodes'])
                self.assertFalse(any(c[1]=='p' for c in r['codes']))
                removed.extend(set(before['codes'])-set(r['codes']))
                self.assertIn(r['cp'],binding.queues()['reviewedRetained'])
            elif r['char'] in 'ĎḊḎḒᴰⅮＤ𝗗Đ':
                self.assertEqual(r['acceptedBoundary'],so.round_refinement.policy()['kFamilyDecisions'][str(r['cp'])])
            elif r['cp']==55 and history_report['version'] in ('structure-count-bindings-v8','structure-count-bindings-v9'):
                self.assertEqual(r['codes'],['aaau'])
                self.assertEqual(r['oldCodes'],before['oldCodes'])
                self.assertEqual(r['oldPreferredCodes'],before['oldPreferredCodes'])
            else:self.assertEqual(r,before)
        self.assertEqual(len(removed),5)
        self.assertEqual(len(review['decisions']),8)
        self.assertEqual({r['char'] for r in review['decisions'].values() if r['action']=='deferred'},set('𐘰𖧚𔕛'))
        self.assertFalse(any(r['countHumanConfirmed'] for r in review['decisions'].values()))
        for ch in 'ȣᛒ𞥕':
            self.assertEqual(self.o.brief(ord(ch),True)['structuralCodes'],sorted(binding.totals.resolve_codes(ord(ch),old[ord(ch)]['codes'])))
            self.assertIn('pFamilyBoundaryReview',self.o.detail(ord(ch),True))
            self.assertNotIn('pFamilyBoundaryReview',self.o.detail(ord(ch),False))


if __name__ == '__main__':
    unittest.main()
