"""Every cut of a complete fixture log before its closing line is reported incomplete.

This is the "never guess" rule checked exhaustively at line boundaries: a parser
that reported a cut log as a complete, smaller run would fail here.
"""

import re
from pathlib import Path

import pytest

from testlogs import detect_format, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"

# fixture -> regex of the line that closes the run (the last match is used)
CLOSERS = {
    "pytest-v-after.log": r"^=+ .* in [\d.]+s",
    "pytest-rA-before.log": r"^=+ .* in [\d.]+s",
    "pytest-xdist.log": r"^=+ .* in [\d.]+s",
    "unittest-v.log": r"^Ran \d+ tests",
    "subtests-unittest-v.log": r"^Ran \d+ tests",
    "jest-verbose.log": r"^Tests:",
    "vitest-verbose.log": r"^\s+Tests\s",
    "mocha-spec.log": r"^\s+\d+ passing",
    "nodetest-spec.log": r"^ℹ tests",
    "nodetest-tap.log": r"^1\.\.\d+",
    "mocha-tap.log": r"^1\.\.\d+",
    "go-v.log": r"^(?:ok|FAIL)\s+\S+\s+[\d.]+s",
    "go-json.log": r'"Action":"(?:pass|fail)","Package":"[^"]*","Elapsed"',
    # cargo and go have no closing line for the whole run, only one per test
    # binary or package; a cut between two of them is a documented gap, so only
    # cuts before the first closing line are checked.
    "cargo-pretty.log": r"^test result:",
}
FIRST_ONLY = {"cargo-pretty.log", "go-v.log", "go-json.log"}


@pytest.mark.parametrize("name", sorted(CLOSERS))
def test_every_cut_before_the_closing_line_is_incomplete(name):
    text = (FIX / name).read_text(encoding="utf-8")
    fmt = detect_format(text)
    assert not parse(text, fmt).incomplete
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if re.search(CLOSERS[name], ln)]
    assert hits, name
    closer = hits[0] if name in FIRST_ONLY else hits[-1]
    for k in range(closer):
        run = parse("\n".join(lines[:k]), fmt)
        assert run.incomplete, f"{name} cut after {k} lines looks complete"


def test_junit_cut_at_any_tag_is_incomplete():
    text = (FIX / "junit-after.xml").read_text(encoding="utf-8")
    for k in range(1, len(text) - 1, 97):
        assert parse(text[:k], "junit").incomplete
