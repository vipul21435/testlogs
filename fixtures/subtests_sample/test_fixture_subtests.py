"""pytest's own ``subtests`` fixture (pytest 9+), run under pytest only."""


def test_fixture_cases(subtests):
    for i in range(4):
        with subtests.test(msg="case", i=i):
            assert i % 2 == 0


def test_fixture_all_pass(subtests):
    for i in range(2):
        with subtests.test(i=i):
            assert i < 2
