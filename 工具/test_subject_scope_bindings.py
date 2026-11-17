"""Meaningful checks for subject/attachment identity and compatibility separation."""
import sys
import unittest
from pathlib import Path

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'原型/键位编辑器')]
import shape_overview as so
import shape_structure_bindings as structural
import subject_scope_bindings as subject


class SubjectScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.o=so.get_overview()

    def test_two_attachment_attributes_use_same_object_in_third_and_fourth(self):
        row=self.o.detail(ord('ộ'),True)
        self.assertEqual(row['familyKey'],'o')
        self.assertEqual(self.o.brief(ord('ộ'),True)['preferredCodes'],['epki'])
        ids={o['id'] for o in row['objects']}
        for code in ('iots','ioyw'):
            p=next(p for p in row['paths'] if p['code']==code)
            self.assertFalse(p['preferred'])
            e=p['evidence'][0]
            self.assertEqual(e['objectId'],e['fourthObjectId'])
            self.assertIn(e['objectId'],ids)
            self.assertIn(ord('ộ'),self.o.allocation_members(code))
            self.assertEqual(row['codeCounts'][code],len(self.o.allocation_members(code)))

    def test_current_family_is_distinct_from_old_code_compatibility(self):
        self.assertNotIn(ord('D'),self.o.key_members(2,'o',True))
        self.assertIn(ord('D'),self.o.key_members(2,'k',True))
        self.assertIn(ord('D'),self.o.key_members(2,'o',False))
        row=self.o.detail(ord('D'),True)
        old=[p for p in row['paths'] if len(p['code'])>=2 and p['code'][1]=='o']
        self.assertTrue(old)
        self.assertTrue(all(p['compatibilityOnly'] for p in old))
        for path in old:self.assertIn(ord('D'),self.o.allocation_members(path['code']))
        self.assertNotIn(ord('ộ'),self.o.key_members(2,'p',True))
        self.assertIn(ord('ộ'),self.o.key_members(2,'o',True))

    def test_legacy_view_and_structure_counts_remain_separate(self):
        legacy=self.o.detail(ord('ộ'),False)
        self.assertNotIn('subjectAttachmentBinding',legacy)
        self.assertFalse(any(p.get('subjectAttachment') for p in legacy['paths']))
        self.assertEqual(structural.data()['version'],('structure-count-bindings-v10' if structural.totals.active() else 'structure-count-bindings-v9'))
        self.assertEqual(structural.data()['statistics']['newCharacterCodePairs'],3259 if structural.totals.active() else 3258)
        self.assertFalse(structural.record(ord('ộ')))
        self.assertEqual(len(subject.additions()['ioyw']),1)
        self.assertEqual(len(structural.queues()['scopePending']),2073)

    def test_two_nonround_subjects_keep_preferred_only_in_current_view(self):
        expected={7692:{'ioki','iocv','iokb','iokv','iosc','iots','iotz'},
                  7696:{'ioki','iocv','iokb','ioks','iokv','iosc','iots','iotx'}}
        self.assertEqual(len(self.o.key_members(2,'o',True)),(1707 if 'dSubjectHoleShapeAcceptance20261027Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else 1709)-(1 if 'dSubjectHoleShapeAcceptance20261027Batch2' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else 0)-(1 if 'dSubjectHoleShapeAcceptance20261027Batch3' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else 0)-(2 if 'roundSubjectClosureAcceptance20261028Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else 0))
        self.assertEqual(len(self.o.allocation_members('iots')),5)
        for cp,codes in expected.items():
            self.assertNotIn(cp,self.o.key_members(2,'o',True))
            self.assertIn(cp,self.o.key_members(2,'o',False))
            d=self.o.detail(cp,True)
            self.assertEqual({p['code'] for p in d['paths']},{'ioki'})
            self.assertEqual({p['code'] for p in self.o.detail(cp,False)['paths']},codes)
            self.assertEqual(self.o.brief(cp,True)['preferredCodes'],['ioki'])
            self.assertEqual([p['code'] for p in d['paths'] if p.get('preferred')],['ioki'])
            self.assertTrue(all(p.get('compatibilityOnly') for p in d['paths']))
            self.assertTrue(all(r.get('compatibilityOnly') for r in d['familyRoutes']))
            for code in codes:
                self.assertEqual(cp in self.o.allocation_members(code),code=='ioki')
            self.assertEqual(self.o.brief(cp,True)['codes'],['ioki'])
        self.assertEqual(set(subject.summary()['currentRoundExclusions']),{52,68,80,7692,7696,270,7690,7694,7698,7472,8558,65316,120279,127283,127347,272,42951}|({119811,127251} if 'dSubjectHoleShapeAcceptance20261027Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({120227} if 'dSubjectHoleShapeAcceptance20261027Batch2' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({127376} if 'dSubjectHoleShapeAcceptance20261027Batch3' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set())|({120123,66580} if 'roundSubjectClosureAcceptance20261028Batch1' in so.read(so.PROJECT/'数据/三模式/规则库/四键实验/人工审议.json') else set()))

    def test_boxed_D_withdrawals_preserve_other_routes_and_remove_dead_bucket_aliases(self):
        decisions=so.round_refinement.policy()['boxedDDecisions']
        for key,a in decisions.items():
            cp=int(key);row=self.o.brief(cp,True);detail=self.o.detail(cp,True)
            self.assertEqual((row['bucket'],row['familyKey']),('d','s'))
            self.assertEqual(row['preferredCodes'],[])
            self.assertEqual(set(row['codes']),set(a['retainedCurrentCodes']))
            self.assertEqual({p['code'] for p in detail['paths']},set(row['codes']))
            self.assertNotIn(cp,self.o.key_members(2,'o',True))
            for code in a['withdrawnCurrentCodes']:
                self.assertNotIn(cp,self.o.allocation_members(code))
                self.assertIn(code,self.o.brief(cp,False)['codes'])
                back=code[1:]+code[0]
                q=self.o.query(dict(allocation=['1'],order=['back'],routeLength=['4'],prefix=[back]))
                self.assertNotIn(cp,{r['cp'] for r in q['rows']})
            for code in a['retainedCurrentCodes']:
                self.assertIn(cp,self.o.allocation_members(code))
        self.assertNotIn(127283,self.o.allocation_members('i'))
        self.assertNotIn(127347,self.o.allocation_members('e'))
        self.assertIn(127283,self.o.allocation_members('d'))
        self.assertIn(127347,self.o.allocation_members('r'))

    def test_O_hollow_size_does_not_redefine_whole_count(self):
        d=self.o.detail(79,True)
        p=next(p for p in d['paths'] if p['code']=='ioqc')
        e=p['evidence'][0]
        self.assertEqual(e['objectId'],e['fourthObjectId'])
        self.assertEqual(self.o.allocation_members('ioqc'),{79:0})
        self.assertEqual(d['codeCounts']['ioqc'],1)
        self.assertIn('incu' if so.count_bc.policy() else 'ioqu',self.o.brief(79,True)['codes'])
        self.assertEqual(self.o.brief(79,True)['preferredCodes'],['iose'])
        self.assertNotIn('ioqc',self.o.brief(79,False)['codes'])
        self.assertNotIn('ioqc',self.o.brief(ord('ộ'),True)['codes'])
        self.assertNotIn('ioqc',self.o.brief(ord('Q'),True)['codes'])
        self.assertEqual(len(self.o.allocation_members('ioqu')),171 if so.count_bc.policy() else 172)
        self.assertEqual(self.o.query({'allocation':['1'],'order':['back'],'routeLength':['4'],'prefix':['oqci']})['total'],1)
        self.assertEqual(self.o.query({'allocation':['1'],'order':['back'],'routeLength':['4'],'prefix':['otsi']})['total'],5)

    def test_four_k_whole_objects_and_authorized_withdrawals(self):
        expected={'Ď':{'ikab','ikjt','ikqu'},'Ḋ':{'ikau','ikju','ikqu'},
                  'Ḏ':{'ikau','ikjb','ikqu'},'Ḓ':{'ikab','ikjt','ikqu'}}
        for ch,codes in expected.items():
            cp=ord(ch);b=self.o.brief(cp,True);d=self.o.detail(cp,True)
            codes=set(structural.totals.resolve_codes(cp,codes))
            self.assertEqual((b['bucket'],b['familyKey']),('i','k'))
            self.assertEqual(set(b['codes']),codes|{'ioki'})
            self.assertEqual(b['preferredCodes'],['ioki'])
            self.assertNotIn(cp,self.o.key_members(2,'o',True))
            self.assertEqual({x['code'] for x in d['paths']},set(b['codes']))
            self.assertTrue(next(x for x in d['paths'] if x['code']=='ioki')['compatibilityOnly'])
            for p in d['paths']:
                self.assertEqual(d['codeCounts'][p['code']],len(self.o.allocation_members(p['code'])))
                if p['code'] in codes:
                    self.assertEqual(p['evidence'][0]['familyTarget'],'whole-glyph')
                    self.assertEqual(p['evidence'][0]['objectId'],p['evidence'][0]['fourthObjectId'])
            self.assertNotIn(cp,structural.queues()['scopePending'])
            self.assertNotIn('k',{p['code'][1] for p in self.o.detail(cp,False)['paths']})
        self.assertEqual(len(self.o.allocation_members('ikqu')),(0 if structural.totals.active() else 9+len(so.external_groups.count_members('ikqu'))))
        self.assertEqual(len(self.o.allocation_members('ikjt' if structural.totals.active() else 'ikjb')),1 if so.joint_bc.policy() else 2)

    def test_second_k_batch_does_not_invent_a_preferred_code(self):
        for ch,kept in [('ᴰ','iosx'),('Ⅾ','iosc'),('Ｄ','iosc'),('𝗗','iolk')]:
            cp=ord(ch);b=self.o.brief(cp,True);d=self.o.detail(cp,True)
            self.assertEqual((b['bucket'],b['familyKey']),('i','k'))
            self.assertEqual(set(b['codes']),set(structural.totals.resolve_codes(cp,{'ikau','ikju','ikqu',kept})))
            self.assertEqual(b['preferredCodes'],[])
            self.assertFalse(any(p['preferred'] for p in d['paths']))
            self.assertEqual({p['code'] for p in d['paths']},set(b['codes']))
            self.assertTrue(next(p for p in d['paths'] if p['code']==kept)['compatibilityOnly'])
            self.assertNotIn(cp,self.o.key_members(2,'o',True))
            self.assertNotIn(cp,structural.queues()['scopePending'])
        self.assertEqual(len(self.o.allocation_members('ikau')),6 if so.count_bc.policy() else 7)
        self.assertEqual(len(self.o.allocation_members(structural.totals.resolve_codes(ord('ᴰ'),['ikju'])[0])),5 if so.count_bc.policy() else 6)


if __name__=='__main__':unittest.main()
