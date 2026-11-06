"""A small unittest suite; its -v log is fixtures/unittest-v.log."""

import unittest


class Maths(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)

    def test_with_docstring(self):
        """Adds two floats."""
        self.assertAlmostEqual(0.1 + 0.2, 0.3)

    def test_fails(self):
        self.assertEqual(2 + 2, 5)

    def test_error(self):
        raise RuntimeError("boom")

    @unittest.skip("not now")
    def test_skipped(self):
        pass

    @unittest.expectedFailure
    def test_expected_failure(self):
        self.assertTrue(False)

    @unittest.expectedFailure
    def test_unexpected_success(self):
        self.assertTrue(True)
