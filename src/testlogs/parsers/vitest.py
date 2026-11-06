"""vitest text reporters (default and ``--reporter=verbose``).

Verbose prints one line per test, ``✓ file > suite > name 3ms`` or ``×``; the
default reporter prints a ``❯ file (N tests | 1 failed) 5ms`` line per file and
names only the failures under it. The ``Tests  2 failed | 5 passed (9)`` line
closes the run. Lines joined by `` > `` keep the file as the first segment.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_LINE = re.compile(
    r"^\s*(?P<mark>✓|×|↓|✗)\s+(?P<path>.+?)(?:\s+(?P<ms>[\d.]+)ms)?(?:\s+\[skipped\])?$"
)
_FILE = re.compile(r"^\s*(?:❯|✓|×)\s+(?P<file>\S+\.[cm]?[jt]sx?)\s+\((?P<n>\d+) tests?[^)]*\)")
_TOTAL = re.compile(r"^\s*Tests\s+(?P<body>.*\(\d+\))$")
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
    for raw in lines:
        line = raw.rstrip()
        m = _TOTAL.match(line)
        if m:
            complete = True
            run.notes.append("vitest totals: " + m.group("body"))
            continue
        if line.strip().startswith(("⎯", "FAIL ")):
            in_failures = True
        if in_failures:
            continue
        m = _FILE.match(line)
        if m:
            file = m.group("file")
            default_mode = True
            continue
        m = _LINE.match(line)
        if m:
            path = m.group("path")
            parts = [p.strip() for p in path.split(" > ")]
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
