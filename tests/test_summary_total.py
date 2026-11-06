from pathlib import Path

import pytest

from testlogs import parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.parametrize(
    "name, total, records",
    [
        ("pytest-rA-after.log", 14, 14),
        ("subtests-pytest-v.log", 3, 3),
        ("unittest-v.log", 7, 7),
        ("jest-verbose.log", 9, 9),
        ("jest-default.log", 9, 2),
        ("vitest-verbose.log", 9, 7),
        ("mocha-spec.log", 9, 9),
        ("nodetest-spec.log", 9, 9),
        ("cargo-pretty.log", 8, 8),
        ("cargo-terse.log", 7, 1),
    ],
)
def test_summary_total_against_records(name, total, records):
    run = parse((FIX / name).read_text(encoding="utf-8"))
    assert run.summary_total == total
    assert len(run.results) == records
    gap = [n for n in run.notes if "summary counts" in n]
    assert bool(gap) == (total != records)
    assert run.to_dict()["summary_total"] == total


def test_truncated_log_has_no_summary_total():
    run = parse((FIX / "pytest-v-truncated.log").read_text(encoding="utf-8"))
    assert run.summary_total is None and run.incomplete


def test_quiet_teardown_error_after_a_pass_is_not_counted_twice():
    # -q names only failures and errors, so the passing test with a teardown error
    # shows one ERROR row, while the final line counts it as passed and as an error.
    run = parse((FIX / "pytest-q-tricky.log").read_text(encoding="utf-8"), fmt="pytest")
    assert run.summary_total == 9
    assert "the log's summary counts 9 tests; 3 records were parsed" in run.notes
