"""jest text reporters (default and ``--verbose``).

Every file prints a ``PASS path`` or ``FAIL path`` header. With ``--verbose``
the tests follow as an indented tree: describe names on their own lines, then
``✓ name (1 ms)``, ``✕ name``, ``○ skipped name`` and ``✎ todo name``. The
default reporter prints only the failures, as ``● suite › name`` headers, so a
default log yields failed records and the counts of the final ``Tests:`` line.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_FILE = re.compile(r"^\s*(?P<res>PASS|FAIL)\s+(?P<file>\S+)(?: \([\d.]+ ?m?s\))?$")
_LEAF = re.compile(
    r"^(?P<indent>\s*)(?P<mark>✓|✕|○ skipped|✎ todo)\s+(?P<name>.*?)(?: \((?P<ms>[\d.]+) ms\))?$"
)
_BULLET = re.compile(r"^\s*● (?P<path>.+?)$")
_TOTAL = re.compile(r"^Tests:\s+(?P<body>.*\d+ total)$")
_MARKS = {
    "✓": Status.PASSED,
    "✕": Status.FAILED,
    "○ skipped": Status.SKIPPED,
    "✎ todo": Status.SKIPPED,
}


def looks_like(lines: list[str]) -> bool:
    return any(_FILE.match(ln) for ln in lines) and any(_TOTAL.match(ln) for ln in lines)


def parse(lines: list[str]) -> Run:
    run = Run(format="jest")
    file = ""
    stack: list[tuple[int, str]] = []
    verbose_ids: set[str] = set()
    bullets: list[tuple[str, str]] = []
    complete = False
    in_tree = False
    for raw in lines:
        line = raw.rstrip()
        m = _FILE.match(line)
        if m:
            file = m.group("file")
            stack = []
            in_tree = True
            continue
        m = _TOTAL.match(line)
        if m:
            complete = True
            run.notes.append("jest totals: " + m.group("body"))
            run.summary_total = int(m.group("body").rsplit(" ", 2)[-2])
            continue
        m = _BULLET.match(line)
        if m:
            in_tree = False
            raw_path = m.group("path")
            if raw_path == "Console":
                continue
            if raw_path == "Test suite failed to run":
                # The file never ran; the JSON report records it the same way.
                bullets.append((file, ""))
                continue
            # A test name may hold "›" itself: match the bullet against the verbose
            # names first, and split it into levels only when none matches.
            for tid in verbose_ids:
                head, _, name = tid.partition("::")
                if head == file and name.replace(" > ", " › ") == raw_path:
                    bullets.append((file, name))
                    break
            else:
                bullets.append((file, " > ".join(p.strip() for p in raw_path.split("›"))))
            continue
        if not in_tree or not line.strip():
            continue
        m = _LEAF.match(line)
        if m:
            indent = len(m.group("indent"))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            name = " > ".join([*(n for _, n in stack), m.group("name")])
            ms = m.group("ms")
            tid = f"{file}::{name}"
            verbose_ids.add(tid)
            run.results.append(
                TestResult(
                    tid, _MARKS[m.group("mark")], file, None if ms is None else float(ms) / 1000
                )
            )
            continue
        indent = len(line) - len(line.lstrip())
        if indent >= 2 and not line.lstrip().startswith(("at ", "console.")):
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, line.strip()))
    # Default reporter: failures only appear as bullets.
    for file, path in bullets:
        tid = f"{file}::{path}" if path else file
        if tid not in verbose_ids:
            status = Status.FAILED if path else Status.ERROR
            run.results.append(TestResult(tid, status, file))
            verbose_ids.add(tid)
    if bullets and len(verbose_ids) == len(bullets):
        run.notes.append("default reporter: only failed tests are named individually")
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append(
            "no 'Tests:' summary line: the log is truncated or the run was interrupted"
        )
    return run
