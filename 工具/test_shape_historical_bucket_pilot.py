"""Geometry controls and immutable audit contracts for the retained-bucket pilot."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np

PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'工具'),str(PROJECT/'原型/键位编辑器')]
from shape_historical_bucket_pilot import ink_info,parallel_layers,stepped_face,stable_probe
from shape_overview import historical_pilot,historical_summary,get_overview


class GeometryTests(unittest.TestCase):
    def test_broken_rows_count_layers_not_ink_components(self):
        mask=np.zeros((64,64),bool)
        for y in (4,14,24,34,44,54):
            mask[y:y+5,4:25]=True;mask[y:y+5,36:57]=True
        obj=parallel_layers(ink_info(mask))
        self.assertEqual(obj['layerCount'],6)
        self.assertEqual(obj['pieceCount'],12)
        self.assertEqual(obj['piecesPerLayer'],[2]*6)
        self.assertEqual(obj['memberDirection'],'h')
        self.assertEqual(obj['arrangement'],'i')
        self.assertEqual(obj['explainedInkFraction'],1)

    def test_rotated_group_and_nonparallel_negative(self):
        mask=np.zeros((64,64),bool);mask[8:13,4:60]=True;mask[43:48,4:60]=True
        obj=parallel_layers(ink_info(np.rot90(mask)))
        self.assertEqual(obj['memberDirection'],'i')
        mask[20:38,27:32]=True
        self.assertIsNone(parallel_layers(ink_info(mask)))

    def test_step_face_not_plain_square_or_triangle_or_hole(self):
        mask=np.zeros((64,64),bool);mask[2:62,2:32]=True;mask[42:62,32:62]=True
        self.assertIsNotNone(stepped_face(ink_info(mask)))
        mask[2:62,2:62]=True
        self.assertIsNone(stepped_face(ink_info(mask)))
        mask[24:40,24:40]=False
        self.assertIsNone(stepped_face(ink_info(mask)))


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=historical_pilot();cls.overview=get_overview()

    def test_all_443_identities_and_old_codes_preserved(self):
        d=self.report;records=d['records']
        self.assertEqual(len(records),443)
        self.assertEqual(len({r['cp'] for r in records}),443)
        self.assertEqual(sum(r['oldBucket']!='g' for r in records),282)
        self.assertEqual(sum(r['historicallyReviewed'] for r in records),10)
        self.assertEqual(sum(d['categories'].values()),443)
        for r in records:
            source=self.overview.rows[r['cp']]
            self.assertEqual(set(r['codesBefore']),set(source['codes']))
            self.assertEqual(r['oldBucket'],source['bucket'])
            self.assertFalse(r['migrationApplied'])
            self.assertFalse(r['codesApplied'])
        self.assertEqual(d['spriteMismatchCharacters'],0)
        self.assertEqual(d['migrations'],0)
        self.assertEqual(d['newCodePaths'],0)

    def test_stability_failures_not_promoted(self):
        d=self.report
        self.assertEqual(d['trials']['u']['stableCount'],42)
        self.assertEqual(d['trials']['v']['baseCount'],8)
        self.assertEqual(d['trials']['v']['stableCount'],1)
        self.assertEqual(d['trials']['v']['unstableCount'],7)
        for r in d['records']:
            for key in 'uv':
                p=r['probes'][key]
                if p['base']:
                    self.assertEqual(len(p['stability']['variants']),9)
                    if r['cp'] in d['trials'][key]['cps']:
                        self.assertTrue(p['stability']['passed'])
        self.assertFalse(d['trials']['u']['bindingAccepted'])
        self.assertFalse(d['trials']['v']['bindingAccepted'])

    def test_existing_triangle_proposals_and_b_supplement(self):
        d=self.report
        proposals=[r for r in d['records'] if r['category']=='现有形族补回候选']
        self.assertEqual({r['char'] for r in proposals},set('🢐⏴🭮𐰶'))
        self.assertTrue(all(r['existingFamilyProbe']['family']=='t' for r in proposals))
        self.assertEqual(d['existingCoded'],1)
        self.assertFalse(d['rootCause']['implementedInGenerator'])
        self.assertEqual(sum(r['oldGeneratorSkippedAmendment'] for r in d['records']),442)

    def test_existing_semantics_and_controls_retained(self):
        controls={r['char']:r for r in self.report['controls']}
        for char in '=≡∥䷀䷁':
            self.assertTrue(controls[char]['probes']['u']['stability']['passed'],char)
        for char in 'EFTLIH○●□■△▲☆★∴∵U∩C':
            self.assertIsNone(controls[char]['probes']['u']['base'],char)
        for char in '○●□■△▲☆★EFTHU∩C':
            self.assertIsNone(controls[char]['probes']['v']['base'],char)
        key=next(k for k in self.overview.keys if k['position']==2 and k['key']=='u')
        self.assertEqual(key['meaning'],'U形')

    def test_read_only_queries(self):
        v=self.overview
        self.assertEqual(v.query({'trial':['history']})['total'],443)
        self.assertEqual(v.query({'trial':['history'],'oldKey':['t']})['total'],27)
        self.assertEqual(v.query({'trial':['u']})['total'],42)
        self.assertEqual(v.query({'trial':['v']})['total'],1)
        self.assertEqual(v.query({'trial':['existing']})['total'],4)
        self.assertEqual(v.query({'trial':['reviewed']})['total'],10)
        self.assertEqual(v.query({'prefix':['u']})['total'],73)
        self.assertEqual(v.query({'prefix':['v']})['total'],16)
        self.assertNotIn('records',historical_summary())
        self.assertIsNotNone(v.detail(ord('🢐'))['historicalPilot'])


if __name__=='__main__':
    unittest.main()
