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


def test_python310_and_doctest_lines_get_distinct_ids():
    text = (
        "test_a (pkg.mod.Case) ... ok\n"
        "test_b (pkg.mod.Case) ... FAIL\n"
        "adjacent (pkg.more) ... ok\n"
        "chunked (pkg.more) ... ok\n\n"
        "Ran 4 tests in 0.001s\n\nFAILED (failures=1)\n"
    )
    run = parse(text, fmt="unittest")
    assert [(r.id, r.file) for r in run.results] == [
        ("pkg.mod.Case.test_a", "pkg.mod"),
        ("pkg.mod.Case.test_b", "pkg.mod"),
        ("pkg.more.adjacent", "pkg.more"),
        ("pkg.more.chunked", "pkg.more"),
    ]
    assert not [n for n in run.notes if "summary counts" in n]


def test_output_printed_after_the_dots_keeps_every_test():
    run = parse((FIX / "unittest-v-print.log").read_text())
    assert run.format == "unittest" and not run.incomplete
    got = {r.id.rsplit(".", 1)[1]: r.status.value for r in run.results}
    assert got == {
        "test_line_ending_ok_then_fail": "failed",
        "test_line_then_pass": "passed",
        "test_no_newline_then_fail": "failed",
        "test_no_newline_then_pass": "passed",
        "test_quiet": "passed",
        "test_two_lines_then_skip": "skipped",
    }
    assert run.summary_total == len(run.results)
