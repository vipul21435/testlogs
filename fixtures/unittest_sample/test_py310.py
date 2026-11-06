"""Cases that print differently across Python versions or after the run summary.

Run with ``python -m unittest -v`` under Python 3.10 and 3.12, stdout redirected to a
file (so it is block-buffered and the printed lines land after the summary).
"""

import unittest


class Sub(unittest.TestCase):
    def test_sub(self):
        for i in range(3):
            with self.subTest(i=i):
                self.assertNotEqual(i, 1)

    @unittest.expectedFailure
    def test_xf(self):
        self.assertTrue(False)

    def test_zz_prints(self):
        print("test_fake (pkg.test_u.A.test_fake) ... ok")


class Broken(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raise RuntimeError("no fixture")

    def test_never_runs(self):
        pass
