from pathlib import Path

from testlogs import Status, detect_format, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"


def test_junit_counts_and_duration():
    run = parse((FIX / "junit-after.xml").read_text())
    assert run.format == "junit"
    c = run.counts()
    assert c["failed"] == 2 and c["error"] == 1
    # pytest writes xfail as <skipped type="pytest.xfail"> and xpass as a plain pass.
    assert c["skipped"] == 1 and c["xfail"] == 1 and c["xpass"] == 0
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


def test_junit_other_producers_shapes():
    xml = (
        '<testsuites><testsuite name="pkg">'
        '<testcase classname="pkg" name="TestA" time="0.5"/>'
        '<testcase classname="pkg" name="TestB" time=""><flakyFailure message="x"/></testcase>'
        '<testcase name="bare"><skipped message="later"/></testcase>'
        '<testcase classname="pkg" name="TestC"><error message="boom"/></testcase>'
        "</testsuite></testsuites>"
    )
    run = parse(xml)
    assert [(r.id, r.status.value, r.duration) for r in run.results] == [
        ("pkg::TestA", "passed", 0.5),
        ("pkg::TestB", "passed", None),
        ("bare", "skipped", None),
        ("pkg::TestC", "error", None),
    ]
