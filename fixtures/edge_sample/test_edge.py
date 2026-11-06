"""Parameter ids that look like parts of a pytest summary row: " - ", "]" and "[ 5%]"."""

import pytest


@pytest.mark.parametrize("x", ["a - b", "c]d", "q [ 5%]", "plain"])
def test_p(x):
    assert x


@pytest.mark.parametrize("x", ["fails - here", "ok"])
def test_q(x):
    assert x == "ok"
