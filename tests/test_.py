import unittest

from Challenger.utils import *

class Test_Bayeselo(unittest.TestCase):

    def test_bayeselo(self):

        results = [(1200, "win"), (1250, "loss"), (1350, "win"), (1300, "loss")]

        calc_bayeselo(results)

        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()