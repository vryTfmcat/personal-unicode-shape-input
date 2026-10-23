"""Intake completeness, source protection and explicit boundary regressions."""
import unittest
from collections import Counter

from fontTools.ttLib import TTFont
from build_shape_pictorial_review import (OUT, EDITOR, SOURCE, UCD, EXPLICIT_YES,
    EXPLICIT_NO, EXAMPLES, classify, load_ucd, read, sha)
from audit_shape_historical_buckets import protect


class PictorialReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(OUT/'拟物收入全量初稿.json')
        cls.rows = {r['cp']: r for r in cls.report['records']}

    def test_source_and_partition(self):
        d = self.report
        self.assertEqual(d['protectedHashes'], protect())
        self.assertEqual(d['sourceIndexSHA256'], sha(SOURCE/'发布核对索引.json'))
        self.assertEqual(d['scope']['sourceIdentities'], 159345)
        self.assertEqual(len(self.rows), len(d['records']))
        self.assertEqual(d['scope']['listedSymbols']+d['scope']['outsidePictorialRetrieval'], 159345)
        self.assertEqual(d['statistics'], dict(Counter(r['proposal'] for r in d['records'])))
        for path, digest in d['sourceFiles'].items():
            self.assertEqual(sha(EDITOR.parents[1]/path), digest)

    def test_explicit_decisions(self):
        for cp in EXPLICIT_YES:
            self.assertEqual(self.rows[cp]['proposal'], 'confirmed')
        for cp in EXPLICIT_NO:
            self.assertEqual(self.rows[cp]['proposal'], 'exclude')
        for cp in EXAMPLES:
            self.assertEqual(self.rows[cp]['proposal'], 'propose')
            self.assertFalse(self.rows[cp]['humanReviewed'])
        self.assertTrue(self.report['policy']['multiObjectScenes'])
        self.assertEqual(self.report['policy']['firstKey'], 't')
        self.assertTrue(self.report['policy']['exclusiveAfterIndividualApproval'])

    def test_no_whole_hieroglyph_block_accepted(self):
        for r in self.rows.values():
            if 'HIEROGLYPH' in r['name'] and r['cp'] not in EXPLICIT_YES:
                self.assertIn(r['proposal'], ('boundary', 'exclude'))
        self.assertEqual(self.rows[0x13441]['proposal'], 'exclude')
        self.assertEqual(self.rows[0x13460]['proposal'], 'boundary')
        self.assertEqual(self.rows[0x14400]['proposal'], 'boundary')
        self.assertEqual(self.rows[0x10080]['proposal'], 'boundary')

    def test_name_matching_not_substrings(self):
        for char in '℩↊↋↼⌢⌣⌬':
            self.assertNotEqual(self.rows[ord(char)]['proposal'], 'propose')
        for char in '♞✈⚓☂':
            self.assertEqual(self.rows[ord(char)]['proposal'], 'propose')
        self.assertEqual(self.rows[0x1F60D]['proposal'], 'propose')  # A face with hearts is a face.
        self.assertEqual(self.rows[0x1FAC0]['proposal'], 'propose')  # Anatomical, not geometric heart.

    def test_all_symbol_and_hieroglyph_retrieval_accounted(self):
        index=read(SOURCE/'发布核对索引.json')
        corpus={r['cp'] for r in index['records']} | set(index['unclassified'])
        for values in index['collections'].values(): corpus.update(values)
        names, blocks=load_ucd()
        for cp in corpus:
            name,gc=names.get(cp,('', 'Lo'))
            if gc=='So' or 'HIEROGLYPH' in name:
                self.assertIn(cp, self.rows, f'U+{cp:04X}')

    def test_actual_shipped_cmap_for_every_listed_glyph(self):
        by_font={}
        for r in self.rows.values():
            by_font.setdefault(r['font']['file'], []).append(r['cp'])
        for filename,cps in by_font.items():
            with TTFont(EDITOR/'fonts'/filename) as font:
                cmap=font.getBestCmap()
                for cp in cps:
                    self.assertIn(cp,cmap,f'U+{cp:04X}')
                    self.assertNotEqual(cmap[cp],'.notdef')

    def test_no_migration_or_deployment(self):
        self.assertFalse(self.report['allocationChanged'])
        self.assertFalse(self.report['runtimeDeployed'])
        self.assertFalse(self.report['policy']['secondKeysAssigned'])
        current=read(EDITOR/'data/pictorial-intake-review.json')
        if current['version']==self.report['version']:
            self.assertEqual(current['records'],self.report['records'])
        else:
            self.assertTrue(current['predecessorVersion']==self.report['version'] or self.report['version'] in current.get('lineageVersions',[]))
            self.assertEqual([(r['cp'],r['oldBucket'],r['oldCodes']) for r in current['records']],
                             [(r['cp'],r['oldBucket'],r['oldCodes']) for r in self.report['records']])


if __name__ == '__main__':
    unittest.main()
