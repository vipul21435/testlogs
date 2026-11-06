from pathlib import Path

import pytest

from testlogs import Status, detect_format, diff_runs, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"
UNI = "handles [brackets] and spaces (ünïcode)"


def _load(name):
    return parse((FIX / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name, fmt",
    [
        ("jest-default.log", "jest"),
        ("jest-verbose.log", "jest"),
        ("jest-verbose-color.log", "jest"),
        ("jest-report.json", "jest-json"),
        ("vitest-default.log", "vitest"),
        ("vitest-verbose.log", "vitest"),
        ("vitest-report.json", "jest-json"),
        ("mocha-spec.log", "mocha"),
        ("mocha-tap.log", "tap"),
        ("nodetest-spec.log", "nodetest"),
        ("nodetest-tap.log", "tap"),
    ],
)
def test_detects_each_node_fixture(name, fmt):
    text = (FIX / name).read_text(encoding="utf-8")
    assert detect_format(text) == fmt
    run = parse(text)
    assert not run.incomplete
    assert run.counts()["failed"] == 2


def test_jest_verbose_nested_describe_and_duplicates():
    run = _load("jest-verbose.log")
    ids = [r.id for r in run.results]
    assert f"jest/maths.test.js::maths > add > {UNI}" in ids
    assert ids.count("jest/maths.test.js::maths > duplicate name") == 2
    by = {r.id: r for r in run.results}
    assert by["jest/maths.test.js::maths > add > fails on purpose"].status is Status.FAILED
    # Durations change on every run, so only their shape is checked; jest prints
    # none for skipped and todo tests.
    assert all(r.duration is None or r.duration >= 0 for r in run.results)
    assert any(r.duration and r.duration > 0 for r in run.results)
    assert by["jest/strings.test.js::trims whitespace"].file == "jest/strings.test.js"


def test_jest_colour_log_matches_plain():
    plain = [(r.id, r.status) for r in _load("jest-verbose.log").results]
    colour = [(r.id, r.status) for r in _load("jest-verbose-color.log").results]
    assert plain == colour


def test_jest_default_names_failures_only():
    run = _load("jest-default.log")
    assert {r.status for r in run.results} == {Status.FAILED}
    assert any("only failed tests" in n for n in run.notes)


def test_jest_truncated_is_incomplete():
    text = (FIX / "jest-verbose.log").read_text(encoding="utf-8")
    run = parse(text[: text.index("Test Suites:")], fmt="jest")
    assert run.incomplete


def test_json_report_statuses_and_ancestors():
    run = _load("jest-report.json")
    by = {r.id.split("::", 1)[1]: r for r in run.results}
    assert by["maths > skipped for now"].status is Status.SKIPPED
    assert by["maths > not written yet"].status is Status.SKIPPED
    assert by[f"maths > add > {UNI}"].status is Status.PASSED


def test_json_report_cut_short_is_incomplete():
    text = (FIX / "vitest-report.json").read_text(encoding="utf-8")
    run = parse(text[: len(text) // 2])
    assert run.format == "jest-json" and run.incomplete


def test_vitest_verbose_ids_split_file_from_path():
    run = _load("vitest-verbose.log")
    ids = [r.id for r in run.results]
    assert f"vitest/maths.test.js::maths > add > {UNI}" in ids
    assert ids.count("vitest/maths.test.js::maths > duplicate name") == 2


def test_vitest_default_failures_under_file_header():
    run = _load("vitest-default.log")
    ids = {r.id for r in run.results}
    assert ids == {
        "vitest/strings.test.js::throws on purpose",
        "vitest/maths.test.js::maths > add > fails on purpose",
    }


def test_mocha_spec_nesting_pending_and_captured_output():
    run = _load("mocha-spec.log")
    by = {r.id: r.status for r in run.results}
    assert by[f"maths > add > {UNI}"] is Status.PASSED
    assert by["maths > add > fails on purpose"] is Status.FAILED
    assert by["maths > skipped for now"] is Status.SKIPPED
    assert not any("captured" in r.id for r in run.results)


def test_mocha_truncated_is_incomplete():
    lines = (FIX / "mocha-spec.log").read_text(encoding="utf-8").splitlines()[:6]
    run = parse("\n".join(lines), fmt="mocha")
    assert run.incomplete and len(run.results) == 3


def test_nodetest_spec_matches_tap():
    spec = _load("nodetest-spec.log")
    tap = _load("nodetest-tap.log")
    assert [(r.id, r.status) for r in spec.results] == [(r.id, r.status) for r in tap.results]
    assert diff_runs(spec, tap).is_empty()


def test_nodetest_suite_summary_lines_are_not_tests():
    ids = [r.id for r in _load("nodetest-spec.log").results]
    assert "maths" not in ids and "maths > add" not in ids
    assert len(ids) == 9


def test_json_report_suite_failure_interruption_and_total():
    doc = (
        '{"numTotalTests": 3, "wasInterrupted": true, "testResults": ['
        '{"name": "/w/a.test.js", "status": "failed", "assertionResults": []},'
        '{"name": "/w/b.test.js", "status": "passed", "assertionResults": ['
        '{"ancestorTitles": ["s"], "title": "t", "status": "passed", "duration": 4}]}]}'
    )
    run = parse(doc)
    assert run.format == "jest-json" and run.incomplete
    assert [(r.id, r.status.value) for r in run.results] == [
        ("/w/a.test.js", "error"),
        ("/w/b.test.js::s > t", "passed"),
    ]
    assert run.results[1].duration == 0.004
    assert run.summary_total == 3
    assert any("suite failed with no test results" in n for n in run.notes)
    assert any("summary counts 3 tests; 2 records" in n for n in run.notes)


def test_vitest_text_reporters_record_a_suite_that_fails_to_load():
    broken = "vitest-broken/broken.test.js"
    for name in ("vitest-verbose-broken.log", "vitest-default-broken.log"):
        run = parse((FIX / name).read_text(encoding="utf-8"))
        assert run.format == "vitest" and not run.incomplete
        by = {r.id: r.status for r in run.results}
        assert by[broken] is Status.ERROR
        assert by["vitest-broken/fine.test.js::fails"] is Status.FAILED
        assert "vitest test files: 2 failed (2)" in run.notes
    report = parse((FIX / "vitest-report-broken.json").read_text(encoding="utf-8"))
    assert [r.status for r in report.results if r.id.endswith(broken)] == [Status.ERROR]


def test_jest_bullets_match_verbose_names_holding_the_level_separator():
    run = parse((FIX / "jest-verbose-edge.log").read_text(encoding="utf-8"))
    assert [(r.id, r.status) for r in run.results] == [
        ("jest-edge/arrow.test.js::second > a › b", Status.FAILED),
        ("jest-edge/arrow.test.js::second > plain", Status.PASSED),
        ("jest-edge/broken.test.js", Status.ERROR),
    ]


def test_jest_suite_that_fails_to_run_is_an_error_named_by_its_file():
    run = parse((FIX / "jest-default-edge.log").read_text(encoding="utf-8"))
    assert ("jest-edge/broken.test.js", Status.ERROR) in [(r.id, r.status) for r in run.results]
    report = parse((FIX / "jest-report-edge.json").read_text(encoding="utf-8"))
    assert [r.status for r in report.results if r.id.endswith("broken.test.js")] == [Status.ERROR]


def test_nodetest_printed_result_lines_outside_the_tree_are_not_tests():
    run = parse((FIX / "nodetest-spec-edge.log").read_text(encoding="utf-8"))
    assert [r.id for r in run.results] == [
        "outer > prints",
        "outer > fails",
        "parent with subtests > sub a",
        "parent with subtests > sub b",
    ]
    # node counts the parent of subtests as a test; its spec line looks like a suite's.
    assert run.summary_total == 5
    assert any("counts 5 tests; 4 records" in n for n in run.notes)


def test_vitest_printed_output_blocks_are_not_results():
    # vitest prints console output under "stdout | file > test" up to a blank line.
    pf = "vitest-print/print.test.js::printing > "
    verbose = parse((FIX / "vitest-verbose-print.log").read_text())
    assert [(r.id, r.status.value) for r in verbose.results] == [
        (pf + "prints a pass mark", "passed"),
        (pf + "prints a fail mark", "passed"),
        (pf + "really fails", "failed"),
    ]
    default = parse((FIX / "vitest-default-print.log").read_text())
    assert [(r.id, r.status.value) for r in default.results] == [(pf + "really fails", "failed")]
    assert not [n for n in verbose.notes if "summary counts" in n]


def test_vitest_verbose_keeps_spaces_at_the_ends_of_names():
    # Trimmed from a real vitest 4.1.5 verbose run of unjs/ufo. vitest writes
    # "mark name duration" with single spaces, so "encodeHash >  0ms" is a test with
    # an empty name and "withQuery >  with {}" one whose name starts with a space;
    # the JSON report of the same run has the same titles.
    run = parse((FIX / "vitest-verbose-spaces.log").read_text(encoding="utf-8"))
    assert run.format == "vitest" and not run.incomplete
    assert [r.id for r in run.results] == [
        "test/query.test.ts::withQuery >  with {}",
        "test/encoding.test.ts::encodeHash > ",
        "test/utilities.test.ts::isEqual > foo == /foo/ ",
        "test/is-same.test.ts::isSamePath > / == ",
        "test/is-same.test.ts::isSamePath > /foo != /bar",
    ]
    assert run.results[-1].status is Status.FAILED
    assert run.results[0].duration == 0.003
    assert run.summary_total == 5
