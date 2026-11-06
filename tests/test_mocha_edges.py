"""mocha spec logs with output mixed into the tree, an npm banner and a run over a minute."""

from pathlib import Path

from testlogs import detect_format, diff_runs, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"
EXPECTED = [
    ("outer > first", "passed"),
    ("outer > logs", "passed"),
    ("outer > fails", "failed"),
    ("outer > pending one", "skipped"),
    ("outer > after the nested block", "passed"),
    ("outer > - dash describe > inside dash", "passed"),
    ("second > adds", "passed"),
]


def _ids(name: str):
    run = parse((FIX / name).read_text(), fmt="mocha")
    return run, [(r.id, r.status.value) for r in run.results]


def test_output_mixed_into_the_tree_does_not_change_ids():
    run, got = _ids("mocha-spec-edge.log")
    assert got == EXPECTED
    assert not run.incomplete and run.summary_total == 7


def test_npm_banner_is_not_a_describe_title():
    text = (FIX / "mocha-spec-npm.log").read_text()
    assert text.startswith("\n> testlogs-node-sample@")
    assert detect_format(text) == "mocha"
    run, got = _ids("mocha-spec-npm.log")
    assert got == EXPECTED
    plain = parse((FIX / "mocha-spec-edge.log").read_text(), fmt="mocha")
    d = diff_runs(plain, run)
    assert d.appeared == [] and d.vanished == []


def test_run_over_a_minute_is_detected_and_details_are_not_tests():
    text = (FIX / "mocha-spec-slow.log").read_text()
    assert "6 passing (1m)" in text
    assert detect_format(text) == "mocha"
    run = parse(text)
    assert not run.incomplete and run.summary_total == 8
    assert [r.id for r in run.results] == ["slow > waits 61 seconds"] + [i for i, _ in EXPECTED]
    assert sum(r.status.value == "failed" for r in run.results) == 1


def test_failure_details_after_a_cut_summary_are_not_tests():
    text = (FIX / "mocha-spec-slow.log").read_text().replace("6 passing (1m)\n", "")
    run = parse(text, fmt="mocha")
    assert run.incomplete and len(run.results) == 8
