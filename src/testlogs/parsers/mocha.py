"""mocha ``spec`` reporter.

Describe names stand on their own lines; a test is ``✔ name`` (or ``✓``), a
failure ``N) name`` and a pending test ``- name``, each indented two spaces per
level. The run ends with ``N passing (Xms)`` and optional pending/failing
counts; the failure details that follow are not parsed.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_LEAF = re.compile(
    r"^(?P<indent>\s*)(?P<mark>✔|✓|-|\d+\))\s+(?P<name>.*?)(?:\s+\((?P<ms>\d+)ms\))?$"
)
_PASSING = re.compile(r"^\s*\d+ passing \([\d.]+ ?m?s\)$")
_COUNT = re.compile(r"^\s*(?P<n>\d+) (?:passing \(.*\)|pending|failing)$")


def looks_like(lines: list[str]) -> bool:
    return any(_PASSING.match(ln) for ln in lines) and not any(
        ln.startswith(("PASS ", "FAIL ")) for ln in lines
    )


def parse(lines: list[str]) -> Run:
    run = Run(format="mocha")
    stack: list[tuple[int, str]] = []
    complete = False
    for i, raw in enumerate(lines):
        line = raw.rstrip()
        if _PASSING.match(line):
            complete = True
            total = 0
            for tail in lines[i : i + 3]:
                m = _COUNT.match(tail.rstrip())
                if m:
                    total += int(m.group("n"))
            run.summary_total = total
            break
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        m = _LEAF.match(line)
        if m:
            while stack and stack[-1][0] >= indent:
                stack.pop()
            mark = m.group("mark")
            if mark == "-":
                status = Status.SKIPPED
            elif mark.endswith(")"):
                status = Status.FAILED
            else:
                status = Status.PASSED
            ms = m.group("ms")
            tid = " > ".join([*(n for _, n in stack), m.group("name")])
            run.results.append(TestResult(tid, status, "", None if ms is None else int(ms) / 1000))
            continue
        if indent >= 2 or (indent == 0 and not run.results and stack == []):
            # A describe title. Captured stdout at indent 0 is ignored once a
            # suite has started.
            if indent == 0 and line and run.results:
                continue
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, line.strip()))
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append("no 'N passing' line: the log is truncated or the run was interrupted")
    return run
