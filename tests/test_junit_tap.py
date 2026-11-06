from pathlib import Path

from testlogs import Status, detect_format, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"


def test_junit_counts_and_duration():
    run = parse((FIX / "junit-after.xml").read_text())
    assert run.format == "junit"
    c = run.counts()
    assert c["failed"] == 2 and c["error"] == 1
    # pytest writes xfail and xpass as skipped in JUnit XML; the skip row is there too.
    assert c["skipped"] == 2
    assert all(r.duration is not None for r in run.results)


def test_junit_broken_xml_is_incomplete():
    run = parse("<testsuites><testsuite><testcase name='a'/>", fmt="junit")
    assert run.incomplete and run.results == []


def test_tap_nested_subtests_skip_and_todo():
    text = (FIX / "tap-nested.tap").read_text()
    assert detect_format(text) == "tap"
    run = parse(text)
    by = {r.id: r for r in run.results}
    assert by["maths > adds"].status is Status.PASSED
    assert by["maths > adds"].duration == 0.0015
    assert by["maths > divides by zero"].status is Status.FAILED
    assert by["strings"].status is Status.SKIPPED
    assert by["later"].status is Status.XPASS
    assert not run.incomplete


def test_tap_missing_plan_is_incomplete():
    run = parse("TAP version 13\nok 1 - a\nok 2 - b\n")
    assert run.incomplete
    assert "no plan line" in run.notes[0]


def test_tap_short_of_plan_is_incomplete():
    run = parse("TAP version 13\n1..3\nok 1 - a\nok 2 - b\n")
    assert run.incomplete


def test_unknown_format_raises():
    import pytest

    with pytest.raises(ValueError):
        parse("hello world\n")
