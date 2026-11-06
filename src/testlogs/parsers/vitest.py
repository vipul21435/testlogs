"""vitest text reporters (default and ``--reporter=verbose``).

Verbose prints one line per test, ``✓ file > suite > name 3ms`` or ``×``; the
default reporter prints a ``❯ file (N tests | 1 failed) 5ms`` line per file and
names only the failures under it. The ``Tests  2 failed | 5 passed (9)`` line
closes the run. Lines joined by `` > `` keep the file as the first segment.
A test file that fails to load has no test lines; its `` FAIL  file [ file ]``
line under "Failed Suites" becomes one error record whose id is the file.
What a test prints comes under a ``stdout | file > test`` (or ``stderr |``) header
and runs to the next blank line; those lines are skipped, so a printed ``✓ x`` is
not a result. A blank line printed by the test ends the block early.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

# vitest writes "mark name duration" with one space between them, so a name with a
# leading or trailing space, or an empty name ("suite > "), is kept as written.
_LINE = re.compile(
    r"^\s*(?P<mark>✓|×|↓|✗) (?P<path>.*?\S.*?)(?: (?P<ms>[\d.]+)ms)?(?: \[skipped\])?$"
)
_FILE = re.compile(r"^\s*(?:❯|✓|×)\s+(?P<file>\S+\.[cm]?[jt]sx?)\s+\((?P<n>\d+) tests?[^)]*\)")
# Under "Failed Suites": " FAIL  file [ file ]" for a test file that failed to load.
_SUITE_FAIL = re.compile(r"^\s*FAIL\s+(?P<file>\S+) \[ .* \]$")
_FILES = re.compile(r"^\s*Test Files\s+(?P<body>.*\(\d+\))$")
_TOTAL = re.compile(r"^\s*Tests\s+(?P<body>.*\(\d+\))$")
_CAPTURED = re.compile(r"^(?:stdout|stderr) \| ")
_MARKS = {"✓": Status.PASSED, "×": Status.FAILED, "✗": Status.FAILED, "↓": Status.SKIPPED}


def looks_like(lines: list[str]) -> bool:
    return any(ln.strip().startswith("RUN  v") for ln in lines) and any(
        _TOTAL.match(ln) for ln in lines
    )


def parse(lines: list[str]) -> Run:
    run = Run(format="vitest")
    file = ""
    complete = False
    default_mode = False
    in_failures = False
    failed_files: set[str] = set()
    captured = False  # inside a "stdout | ..." block of a test's own output
    for raw in lines:
        line = raw.rstrip()
        if captured:
            captured = bool(line.strip())
            continue
        if _CAPTURED.match(line):
            captured = True
            continue
        m = _TOTAL.match(line)
        if m:
            complete = True
            run.notes.append("vitest totals: " + m.group("body"))
            run.summary_total = int(m.group("body").rsplit("(", 1)[1].rstrip(")"))
            continue
        m = _FILES.match(line)
        if m:
            run.notes.append("vitest test files: " + m.group("body").strip())
            continue
        if line.strip().startswith(("⎯", "FAIL ")):
            in_failures = True
        if in_failures:
            m = _SUITE_FAIL.match(line)
            if m and m.group("file") not in failed_files:
                # The file never ran, so it has no test lines; record it as one error,
                # as the JSON reporter does.
                failed_files.add(m.group("file"))
                run.results.append(TestResult(m.group("file"), Status.ERROR, m.group("file")))
            continue
        m = _FILE.match(line)
        if m:
            file = m.group("file")
            default_mode = True
            continue
        m = _LINE.match(line)
        if m:
            path = m.group("path")
            parts = path.split(" > ")
            if default_mode:
                tid = f"{file}::{' > '.join(parts)}"
                f = file
            else:
                f, rest = parts[0], parts[1:]
                tid = f"{f}::{' > '.join(rest)}" if rest else f
            ms = m.group("ms")
            run.results.append(
                TestResult(
                    tid, _MARKS[m.group("mark")], f, None if ms is None else float(ms) / 1000
                )
            )
    if default_mode:
        run.notes.append("default reporter: only failed tests are named individually")
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append("no 'Tests' summary line: the log is truncated or the run was interrupted")
    return run
