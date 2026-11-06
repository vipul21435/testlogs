from pathlib import Path

import pytest

from testlogs import Status, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.parametrize(
    "name",
    [
        "subtests-pytest-v.log",
        "subtests-pytest-rA.log",
        "subtests-junit.xml",
        "subtests-unittest-v.log",
    ],
)
def test_failing_subtest_marks_parent_failed_in_every_format(name):
    run = parse((FIX / name).read_text(encoding="utf-8"))
    assert not run.incomplete
    by = {r.id.replace("::", ".").rsplit(".", 1)[-1]: r.status for r in run.results}
    assert by == {
        "test_all_cases_pass": Status.PASSED,
        "test_one_case_fails": Status.FAILED,
        "test_plain": Status.PASSED,
    }


def test_pytest_subtest_counts_are_noted():
    run = parse((FIX / "subtests-pytest-rA.log").read_text(encoding="utf-8"))
    assert "pytest counts 5 subtests passed" in run.notes


def test_unittest_parent_line_without_result_is_not_lost():
    text = (
        "test_a (m.T.test_a) ... \n"
        "  test_a (m.T.test_a) (i=1) ... FAIL\n"
        "  test_a (m.T.test_a) (i=2) ... ERROR\n"
        "test_b (m.T.test_b) ... ok\n\n"
        "Ran 2 tests in 0.001s\n\nFAILED (failures=1, errors=1)\n"
    )
    run = parse(text, fmt="unittest")
    assert [(r.id, r.status) for r in run.results] == [
        ("m.T.test_a", Status.FAILED),
        ("m.T.test_b", Status.PASSED),
    ]


def test_pytest_subtests_fixture_parent_failed_and_counts_agree():
    run = parse((FIX / "subtests-fixture-pytest-v.log").read_text(encoding="utf-8"))
    by = {r.id.rsplit("::", 1)[1]: r.status for r in run.results}
    assert by == {"test_fixture_cases": Status.FAILED, "test_fixture_all_pass": Status.PASSED}
    # "3 failed, 1 passed" counts two failing subtests on top of their parent.
    assert run.summary_total == 2
    assert not [n for n in run.notes if "summary counts" in n]


def test_subtest_summary_row_shapes():
    text = (
        "t/test_a.py::test_x PASSED [100%]\n"
        "=========================== short test summary info ============================\n"
        "SUBFAILED[msg] (i=1) t/test_a.py::test_x - assert False\n"
        "============== 1 failed, 1 passed in 0.01s ==============\n"
    )
    run = parse(text, fmt="pytest")
    assert [(r.id, r.status) for r in run.results] == [("t/test_a.py::test_x", Status.FAILED)]
