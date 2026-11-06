from pathlib import Path

from testlogs import Status, detect_format, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"
Q = "fixtures.unittest_sample.test_unit.Maths."


def test_unittest_every_outcome_kind():
    text = (FIX / "unittest-v.log").read_text()
    assert detect_format(text) == "unittest"
    run = parse(text)
    assert not run.incomplete
    s = {r.id: r.status for r in run.results}
    assert s[Q + "test_add"] is Status.PASSED
    assert s[Q + "test_fails"] is Status.FAILED
    assert s[Q + "test_error"] is Status.ERROR
    assert s[Q + "test_skipped"] is Status.SKIPPED
    assert s[Q + "test_expected_failure"] is Status.XFAIL
    assert s[Q + "test_unexpected_success"] is Status.XPASS
    assert len(run.results) == 7


def test_unittest_docstring_puts_result_on_next_line():
    run = parse((FIX / "unittest-v.log").read_text())
    by = {r.id: r for r in run.results}
    assert by[Q + "test_with_docstring"].status is Status.PASSED
    assert by[Q + "test_add"].file == "fixtures.unittest_sample.test_unit"


def test_unittest_truncated_is_incomplete():
    lines = (FIX / "unittest-v.log").read_text().splitlines()[:4]
    run = parse("\n".join(lines), fmt="unittest")
    assert run.incomplete
    assert len(run.results) == 4
    assert "Ran N tests" in run.notes[0]
