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


def _yaml_duration(text: str, point: str) -> float:
    """The duration_ms of the YAML block right after the test point line ``point``."""
    lines = text.splitlines()
    i = next(n for n, ln in enumerate(lines) if ln.strip() == point)
    assert lines[i + 1].strip() == "---"
    ms = lines[i + 2].split("duration_ms:")[1]
    return float(ms) / 1000.0


def test_tap_suite_duration_does_not_overwrite_last_child():
    text = (FIX / "nodetest-tap.log").read_text()
    run = parse(text)
    by: dict[str, list[float | None]] = {}
    for r in run.results:
        by.setdefault(r.id, []).append(r.duration)
    assert by["maths > add > fails on purpose"] == [
        _yaml_duration(text, "not ok 3 - fails on purpose")
    ]
    assert by["maths > duplicate name"][1] == _yaml_duration(text, "ok 5 - duplicate name")


def test_tap_escaped_hash_in_names_from_node_test():
    text = (FIX / "nodetest-tap-escapes.log").read_text()
    run = parse(text)
    assert not run.incomplete, run.notes
    assert [r.id for r in run.results] == [
        "outer > plain",
        "outer > issue #42 works",
        "outer > back\\slash # and hash",
        "outer > slow",
        "top level #7",
    ]
    assert all(r.status is Status.PASSED for r in run.results)
    slow = run.results[3].duration
    assert slow == _yaml_duration(text, "ok 4 - slow")
    spec = parse((FIX / "nodetest-spec-escapes.log").read_text())
    assert [r.id for r in spec.results] == [r.id for r in run.results]


def test_tap_comment_after_hash_is_not_a_directive():
    run = parse("TAP version 14\n1..2\nok 1 - a # just a note\nnot ok 2 - b # todo later\n")
    assert [(r.id, r.status) for r in run.results] == [("a", Status.PASSED), ("b", Status.XFAIL)]
    assert not run.incomplete


def test_tap_nested_plan_short_of_children_is_incomplete():
    text = "\n".join(
        [
            "TAP version 14",
            "# Subtest: outer",
            "    1..3",
            "    ok 1 - a",
            "    ok 2 - b",
            "ok 1 - outer",
            "1..1",
        ]
    )
    run = parse(text)
    assert [r.id for r in run.results] == ["outer > a", "outer > b"]
    assert run.incomplete
    assert "says 3 tests, found 2" in run.notes[0]


def test_tap_subtests_without_header_take_the_parent_name():
    text = (
        "TAP version 14\n    ok 1 - a\n    not ok 2 - b\n    1..2\n"
        "not ok 1 - outer\nok 2 - c\n1..2\n"
    )
    run = parse(text)
    assert [(r.id, r.status) for r in run.results] == [
        ("outer > a", Status.PASSED),
        ("outer > b", Status.FAILED),
        ("c", Status.PASSED),
    ]
    assert not run.incomplete


def test_tap_cut_inside_a_subtest_is_incomplete():
    text = "TAP version 14\n# Subtest: outer\n    1..2\n    ok 1 - a\n"
    run = parse(text)
    assert run.incomplete


def test_tap_yaml_block_lines_are_not_tests():
    text = "TAP version 13\n1..1\nnot ok 1 - a\n  ---\n  message: |-\n    ok 2 - fake\n  ...\n"
    run = parse(text)
    assert [r.id for r in run.results] == ["a"]
    assert not run.incomplete


def test_pytest_teardown_error_testcase_merges_into_its_test():
    # pytest writes a second <testcase> for a test that fails and then errors in
    # teardown; the -v parser records that test once, as failed.
    run = parse((FIX / "junit-tricky.xml").read_text(encoding="utf-8"), fmt="junit")
    s = {r.id.rsplit("::", 1)[1]: r.status for r in run.results}
    assert len(run.results) == 9
    assert s["test_fail_and_teardown_error"] is Status.FAILED
    assert s["test_pass_and_teardown_error"] is Status.ERROR
    assert "1 teardown error testcase merged into the testcase before it" in run.notes


def test_vitest_tap_brace_blocks_are_headers_not_tests():
    # Trimmed from a real vitest 4.1.5 --reporter=tap run of unjs/ufo with one test
    # made to fail. A point ending in "{" names a file or describe block; its tests
    # follow, indented, up to a "}" at the same indent.
    text = (FIX / "vitest-tap.log").read_text(encoding="utf-8")
    assert detect_format(text) == "tap"
    run = parse(text)
    assert not run.incomplete, run.notes
    assert len(run.results) == 7
    by = {r.id: r for r in run.results}
    assert by["test/is-same.test.ts > isSamePath > /foo != /bar"].status is Status.FAILED
    assert by['test/base.test.ts > withBase > "/" + "/"'].duration == 0.00181
    assert by["test/is-same.test.ts > isSamePath > /%D1%82%D0%B5%D1%81%D1%82 == /тест"]
    assert run.counts()["passed"] == 6


def test_vitest_tap_block_cut_before_its_brace_is_incomplete():
    text = "TAP version 13\n1..1\nok 1 - f.test.ts {\n    1..1\n    ok 1 - a\n"
    run = parse(text)
    assert run.incomplete
    assert any("never closed" in n for n in run.notes)


def test_vitest_tap_empty_block_keeps_its_point():
    # A file block with no test points (a file that failed to load, say) is kept as a
    # record, so its failure is not lost.
    text = (
        "TAP version 13\n1..2\nnot ok 1 - broken.test.ts {\n}\n"
        "ok 2 - b.test.ts {\n    1..1\n    ok 1 - t\n}\n"
    )
    run = parse(text)
    assert [(r.id, r.status) for r in run.results] == [
        ("broken.test.ts", Status.FAILED),
        ("b.test.ts > t", Status.PASSED),
    ]
    assert not run.incomplete
