import unittest
from audit_shape_pictorial_exit import measure


class ExitTests(unittest.TestCase):
    def test_only_explicit_include_exits_and_codes_deduplicate(self):
        records = [{'cp': i, 'bucket': 'c', 'codes': ['chvc', 'chvc']} for i in range(4)]
        decisions = {str(i): {'decision': d} for i, d in enumerate(
            ['include', 'exclude', 'uncertain', 'pending'])}
        result = measure(records, decisions)
        self.assertEqual(result['focus'][0], {
            'code': 'chvc', 'before': 4, 'removed': 1, 'after': 3, 'removedCps': [0]})
        self.assertEqual(result['candidateAssociationsRemoved'], 1)

    def test_first_only_and_outside_ordinary(self):
        records = [{'cp': 1, 'bucket': 'a', 'codes': []},
                   {'cp': 2, 'bucket': 'c', 'codes': ['chvc']}]
        result = measure(records, {str(i): {'decision': 'include'} for i in (1, 2, 3)})
        self.assertEqual((result['approved'], result['ordinaryExits'], result['outsideOrdinary']), (3, 2, 1))
        self.assertEqual((result['firstOnlyExits'], result['detailedExits']), (1, 1))
        self.assertEqual(result['fourKeyGroupsAfter'], 0)
        self.assertEqual(result['maximumAfter'], 0)


if __name__ == '__main__':
    unittest.main()
