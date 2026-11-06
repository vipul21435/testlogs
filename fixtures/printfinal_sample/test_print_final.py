"""A test that prints a line shaped like pytest's final line; run with -v -s."""

import warnings


def test_prints_a_final_line():
    print()
    print("========================= 1 failed, 1 passed in 0.03s ==========================")


def test_after():
    assert 1 + 1 == 2


def test_warns():
    warnings.warn("careful", UserWarning, stacklevel=1)


def test_fails():
    assert 1 + 1 == 3
