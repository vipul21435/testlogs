"""A test that fails on its first call only, for the pytest-rerunfailures fixture."""

_calls: list[int] = []


def test_flaky_then_passes():
    _calls.append(1)
    assert len(_calls) > 1


def test_always_fails():
    assert 1 + 1 == 3


def test_steady():
    assert True
