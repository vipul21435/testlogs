"""An outer test that runs pytest -v on an inner file and fails: its output is captured."""


def test_inner_run(pytester):
    pytester.makepyfile("def test_inner_a(): pass\ndef test_inner_b(): assert 0\n")
    result = pytester.runpytest("-v")
    assert result.ret == 0


def test_other():
    pass
