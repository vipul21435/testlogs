"""Tests that print. With unbuffered stdout the output lands after the " ... "."""

import sys
import unittest


class Printing(unittest.TestCase):
    def test_line_then_pass(self):
        print("hello")

    def test_no_newline_then_pass(self):
        sys.stdout.write("x")

    def test_line_ending_ok_then_fail(self):
        print("look")
        self.fail("on purpose")

    def test_no_newline_then_fail(self):
        sys.stdout.write("partial")
        self.fail("on purpose")

    def test_two_lines_then_skip(self):
        print("one")
        print("two")
        self.skipTest("not here")

    def test_quiet(self):
        pass
