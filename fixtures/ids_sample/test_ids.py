"""Parameter ids that need care in summary rows and -s output, and a slow setup."""

import time

import pytest


@pytest.mark.parametrize("v", ["x] - y", "ok"])
def test_r(v):
    assert v == "ok"


@pytest.mark.parametrize("n", [1, 2])
def test_param_fail(n):
    assert n != 2


@pytest.mark.parametrize("s", ["a b"])
def test_out(s):
    print("hello world")


@pytest.fixture
def slow_setup():
    time.sleep(0.05)


def test_slow_setup(slow_setup):
    time.sleep(0.02)
