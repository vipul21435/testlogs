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
    assert by["jest/maths.test.js::maths > add > adds two numbers"].duration == 0.001
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
