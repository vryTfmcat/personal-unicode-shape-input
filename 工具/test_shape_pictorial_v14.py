import copy
import unittest
import tempfile
from collections import Counter
from pathlib import Path
from build_shape_pictorial_review import read,EDITOR
from build_shape_pictorial_review_v13 import OUT as V13
from build_shape_pictorial_review_v14 import OUT,SNAPSHOT,EXACT,MOVED_CATEGORIES
from save_shape_pictorial_review import save_snapshot


class V14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=read(OUT/'拟物收入全量初稿.json');cls.rows={r['cp']:r for r in cls.r['records']}

    def test_explicit_scope_and_latest_review(self):
        expected={str(d['cp']):copy.deepcopy(d) for d in read(SNAPSHOT)['decisions']}
        old=read(V13/'拟物收入全量初稿.json')
        for cp in old['discoveryQueues']['bBadges']['cps']:
            expected.setdefault(str(cp),{'cp':cp,'char':chr(cp)}).update(decision='include',category='字符标识',firstKey='b')
        self.assertEqual(self.r['reviewDecisions'],expected)
        self.assertEqual(Counter(x.get('decision') for x in expected.values()),{'include':3878,'exclude':59,None:1})
        self.assertEqual(self.r['bucketSplit']['admittedCounts'],{'t':3279,'b':599})
        for row in self.r['draftFirstKeyAllocations']:
            if row['category'] in MOVED_CATEGORIES+('字符标识',):self.assertEqual(row['firstKey'],'b')
        self.assertEqual(self.r['bucketSplit']['admittedCategoryCounts']['b']['字符标识'],43)

    def test_egyptian_explanations_do_not_admit(self):
        pending=[cp for cp in self.r['discoveryQueues']['egyptAnimalParts']['cps'] if
                 self.r['reviewDecisions'].get(str(cp),{}).get('decision','pending') in ('pending','uncertain')]
        self.assertEqual(len(pending),148)
        self.assertEqual(sum(not self.rows[cp]['egyptianExplanation']['hasOfficialDescription'] for cp in pending),16)
        for cp in pending:self.assertFalse(self.rows[cp]['egyptianExplanation']['admissionEvidence'])
        for cp,zh in EXACT.items():self.assertEqual(self.rows[cp]['egyptianExplanation']['zh'],zh)
        self.assertNotIn(str(0x1312E),self.r['reviewDecisions'])

    def test_original_codes_sources_and_notes_preserved(self):
        old=read(V13/'拟物收入全量初稿.json')
        self.assertEqual(old['protectedHashes'],self.r['protectedHashes'])
        self.assertEqual(old['secondReview']['boundaryCps'],self.r['secondReview']['boundaryCps'])
        self.assertEqual([(r['cp'],r['oldCodes'],r['oldBucket']) for r in old['records']],
                         [(r['cp'],r['oldCodes'],r['oldBucket']) for r in self.r['records']])
        self.assertEqual(read(EDITOR/'data/pictorial-category-labels.json')['aliases']['字母标识'],'字符标识')

    def test_new_version_can_save(self):
        r=self.r
        data={'format':'pictorial-intake-human-review-v1','version':r['version'],'sourceIndexSHA256':r['sourceIndexSHA256'],
              'scope':r['scope'],'allocationChanged':False,'decisions':list(r['reviewDecisions'].values())}
        with tempfile.TemporaryDirectory() as folder:
            receipt=save_snapshot(data,Path(folder))
            self.assertEqual(receipt['summary']['explicitDecisions'],{'include':3878,'exclude':59,'note-only':1})


if __name__=='__main__':unittest.main()
