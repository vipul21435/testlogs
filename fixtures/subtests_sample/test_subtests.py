"""unittest subTest cases, run under both pytest and unittest for the subtest fixtures."""

import unittest


class Table(unittest.TestCase):
    def test_one_case_fails(self):
        for i in range(3):
            with self.subTest(i=i):
                self.assertNotEqual(i, 1)

    def test_all_cases_pass(self):
        for word in ("a b", "[x]", "ü"):
            with self.subTest(word=word):
                self.assertTrue(word)

    def test_plain(self):
        self.assertEqual(len("abc"), 3)
