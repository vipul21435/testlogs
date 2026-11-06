"""Small suite used to produce the pytest fixtures. Each outcome kind appears once or more."""

import pytest

VERSION = 2


def test_add():
    assert 1 + 1 == 2


def test_names_with_spaces():
    assert "a b".split() == ["a", "b"]


@pytest.mark.parametrize("value", ["plain", "with space", "br[ack]ets", "ünïcode"])
def test_param(value):
    assert isinstance(value, str)


def test_fixed_in_after():
    assert VERSION >= 2


def test_broken_in_after():
    assert VERSION < 2


@pytest.mark.skip(reason="not for this platform")
def test_skipped():
    raise AssertionError


@pytest.mark.xfail(reason="known gap")
def test_xfail():
    raise AssertionError


@pytest.mark.xfail(reason="documented but now passes")
def test_xpass():
    assert True


@pytest.fixture
def broken_fixture():
    raise RuntimeError("setup blew up")


def test_error(broken_fixture):
    assert True


def test_prints_then_fails():
    print("captured output line\rprogress 100%")
    assert VERSION == 0


def test_only_in_after():
    if VERSION < 2:
        pytest.skip("absent before")
    assert True
