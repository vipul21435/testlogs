"""mocha ``spec`` reporter.

Describe names stand on their own lines; a test is ``✔ name`` (or ``✓``), a
failure ``N) name`` and a pending test ``- name``, each indented two spaces per
level. The run ends with ``N passing (Xms)`` and optional pending/failing
counts; the failure details that follow are not parsed. A run uses one of the
two check marks; when a log holds both, the one whose count matches ``N passing``
(else the more frequent one) is the reporter's and lines with the other are output.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult, plural

_LEAF = re.compile(
    r"^(?P<indent>\s*)(?P<mark>✔|✓|-|\d+\))\s+(?P<name>.*?)(?:\s+\((?P<ms>\d+)ms\))?$"
)
# mocha formats the run time with ms(): "12ms", "1s", "1m", "2h", "1d".
_PASSING = re.compile(r"^\s*\d+ passing \(\d+(?:\.\d+)?\s?(?:ms|s|m|h|d)\)$")
_COUNT = re.compile(r"^\s*(?P<n>\d+) (?:passing \(.*\)|pending|failing)$")
_TAIL_COUNT = re.compile(r"^\s*\d+ (?:pending|failing)$")


def looks_like(lines: list[str]) -> bool:
    return any(_PASSING.match(ln) for ln in lines) and not any(
        ln.startswith(("PASS ", "FAIL ")) for ln in lines
    )


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _next_indent(lines: list[str], i: int) -> int:
    """Indent of the first non-empty line after ``lines[i]``, or -1 at the end."""
    for nxt in lines[i + 1 :]:
        if nxt.strip():
            return _indent(nxt.rstrip())
    return -1


def _foreign_mark(lines: list[str]) -> str | None:
    """The check mark that is not this run's, when the log holds both."""
    counts = {"✔": 0, "✓": 0}
    passing = None
    for raw in lines:
        line = raw.rstrip()
        m = _LEAF.match(line)
        if m and m.group("mark") in counts:
            counts[m.group("mark")] += 1
        if passing is None and _PASSING.match(line):
            passing = int(line.split()[0])
    if not counts["✔"] or not counts["✓"]:
        return None
    for mark, other in (("✔", "✓"), ("✓", "✔")):
        if counts[mark] == passing and counts[other] != passing:
            return other
    return "✓" if counts["✔"] >= counts["✓"] else "✔"


def parse(lines: list[str]) -> Run:
    run = Run(format="mocha")
    foreign = _foreign_mark(lines)
    ignored = 0
    stack: list[tuple[int, str]] = []
    complete = False
    prev_blank = True
    prev_leaf = -1  # indent of the line before, when it was a test result
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
        if _TAIL_COUNT.match(line):
            break  # "N failing" without a passing line: the summary was cut
        if not line.strip():
            prev_blank = True
            continue
        was_blank, prev_blank = prev_blank, False
        after_leaf, prev_leaf = prev_leaf, -1
        indent = _indent(line)
        m = _LEAF.match(line)
        if m and m.group("mark") == foreign:
            ignored += 1
            continue
        # "- title" is a pending test unless deeper lines follow it: then it is a
        # describe whose title starts with "- ".
        if m and not (m.group("mark") == "-" and _next_indent(lines, i) > indent):
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
            prev_leaf = indent
            continue
        # A describe title. mocha indents two spaces per level, starting at two (the
        # root suite has no title), and prints a blank line before each top-level
        # suite unless it follows a root-level test; a title is always followed by
        # deeper lines. Anything else (npm's
        # "> script" banner, console output) is not part of the tree.
        top = stack[-1][0] if stack else 0
        if (
            indent >= 2
            and indent % 2 == 0
            and indent <= top + 2
            and (indent > 2 or was_blank or after_leaf == 2)
            and _next_indent(lines, i) > indent
        ):
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, line.strip()))
    if ignored:
        run.notes.append(
            f"{plural(ignored, 'printed line')} with the other check mark ({foreign}) ignored"
        )
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append("no 'N passing' line: the log is truncated or the run was interrupted")
    return run
