"""Reasons holding ')', a teardown error after a failure, and output that looks like pytest's."""

import pytest


@pytest.mark.xfail(reason="bug (see #1)")
def test_xfail_paren():
    assert 0


@pytest.mark.skip(reason="no (reason)")
def test_skip_paren():
    pass


@pytest.mark.parametrize("n", [1, 2, 3])
def test_skip_param(n):
    pytest.skip("needs (x)")


@pytest.fixture
def broken_teardown():
    yield
    raise RuntimeError("teardown")


def test_fail_and_teardown_error(broken_teardown):
    assert 0


def test_pass_and_teardown_error(broken_teardown):
    pass


def test_prints_pytest_lines():
    print("test_fake.py::test_phantom PASSED")
    print("========== 1 passed in 0.01s ==========")
    assert 0


def test_plain():
    pass
