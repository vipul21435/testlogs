"""node:test ``spec`` reporter.

``▶ suite`` opens a describe block; tests are ``✔ name (0.6ms)``,
``✖ name (0.9ms)``, ``﹣ name (0.1ms) # SKIP`` and ``✔ name (0.1ms) # TODO``.
A suite closes with a ``✔ suite`` or ``✖ suite`` line at its own indent, which
is a summary rather than a test. ``ℹ tests N`` closes the run.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_SUITE = re.compile(r"^(?P<indent>\s*)▶ (?P<name>.*)$")
_LEAF = re.compile(
    r"^(?P<indent>\s*)(?P<mark>✔|✖|﹣)\s+(?P<name>.*?)\s+\((?P<ms>[\d.]+)ms\)"
    r"(?:\s+#\s*(?P<directive>SKIP|TODO).*)?$"
)
_TOTAL = re.compile(r"^ℹ tests (?P<n>\d+)$")


def looks_like(lines: list[str]) -> bool:
    return any(_TOTAL.match(ln) for ln in lines) and any(_LEAF.match(ln) for ln in lines)


def parse(lines: list[str]) -> Run:
    run = Run(format="nodetest")
    stack: list[tuple[int, str]] = []
    complete = False
    for raw in lines:
        line = raw.rstrip()
        m = _TOTAL.match(line)
        if m:
            complete = True
            break
        m = _SUITE.match(line)
        if m:
            indent = len(m.group("indent"))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, m.group("name").strip()))
            continue
        m = _LEAF.match(line)
        if not m:
            continue
        indent = len(m.group("indent"))
        name = m.group("name")
        if stack and stack[-1][0] == indent and stack[-1][1] == name:
            stack.pop()  # closing summary line of the suite
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        directive = m.group("directive")
        mark = m.group("mark")
        if directive == "SKIP" or mark == "﹣":
            status = Status.SKIPPED
        elif directive == "TODO":
            status = Status.XPASS if mark == "✔" else Status.XFAIL
        else:
            status = Status.PASSED if mark == "✔" else Status.FAILED
        tid = " > ".join([*(n for _, n in stack), name])
        run.results.append(TestResult(tid, status, "", float(m.group("ms")) / 1000))
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append("no 'ℹ tests N' line: the log is truncated or the run was interrupted")
    return run
