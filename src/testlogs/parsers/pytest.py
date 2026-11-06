"""pytest parsers: ``-v`` progress lines and the ``-rA`` short test summary.

Verbose lines look like ``tests/test_a.py::test_x[a b] PASSED  [ 33%]``.
Summary lines (``-rA``) look like ``PASSED tests/test_a.py::test_x`` or
``FAILED tests/test_a.py::test_x - AssertionError``. When both are present the
summary wins, because a test's verbose line can be split by captured output.
The final ``==== 3 passed in 0.02s ====`` line marks a complete log; without
it the run is reported incomplete.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_STATUS_WORDS = {
    "PASSED": Status.PASSED,
    "FAILED": Status.FAILED,
    "SKIPPED": Status.SKIPPED,
    "ERROR": Status.ERROR,
    "XFAIL": Status.XFAIL,
    "XPASS": Status.XPASS,
}

# nodeid: path, "::", then anything up to the status word. Parametrised ids may
# hold spaces, brackets or unicode, so the id is matched lazily and the status
# word anchors the end.
_VERBOSE = re.compile(
    r"^(?P<id>\S+?::\S.*?)\s+(?P<status>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)"
    r"(?:\s+\((?P<reason>[^)]*)\))?"
    r"(?:\s+\[\s*\d+%\])?\s*$"
)
_SUMMARY = re.compile(
    r"^(?P<status>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)\s+"
    r"(?:\[\d+\]\s+)?(?P<id>\S+?(?:::\S.*?|:\d+)?)(?:\s+-\s+.*)?$"
)
_SUMMARY_HEADER = re.compile(r"^=+ short test summary info =+$")
_FINAL = re.compile(
    r"^=+ .*\b(?:passed|failed|error|errors|skipped|xfailed|xpassed|no tests ran)\b"
    r".* in [\d.]+s.* =+$"
)
_DURATION = re.compile(r"^(?P<secs>\d+\.\d+)s\s+(?:call|setup|teardown)\s+(?P<id>\S.*)$")


def looks_like(lines: list[str]) -> bool:
    if any(ln.startswith("============================= test session starts") for ln in lines):
        return True
    hits = sum(1 for ln in lines if _VERBOSE.match(ln) or _SUMMARY.match(ln))
    return hits >= 2 and any("::" in ln for ln in lines)


def _file_of(node_id: str) -> str:
    if "::" in node_id:
        return node_id.split("::", 1)[0]
    return node_id.split(":", 1)[0]


def parse(lines: list[str]) -> Run:
    run = Run(format="pytest")
    verbose: list[TestResult] = []
    summary: list[TestResult] = []
    durations: dict[str, float] = {}
    in_summary = False
    complete = False
    for raw in lines:
        line = raw.rstrip()
        if not line:
            continue
        if _SUMMARY_HEADER.match(line):
            in_summary = True
            continue
        if _FINAL.match(line):
            complete = True
            in_summary = False
            continue
        m = _DURATION.match(line)
        if m:
            tid = m.group("id")
            durations[tid] = max(durations.get(tid, 0.0), float(m.group("secs")))
            continue
        if in_summary:
            m = _SUMMARY.match(line)
            if m:
                tid = m.group("id")
                summary.append(TestResult(tid, _STATUS_WORDS[m.group("status")], _file_of(tid)))
            continue
        m = _VERBOSE.match(line)
        if m:
            tid = m.group("id")
            verbose.append(TestResult(tid, _STATUS_WORDS[m.group("status")], _file_of(tid)))
    # Merge: verbose lines give the order and every id; summary rows override the
    # status (a verbose line can be split by captured output, the summary cannot).
    order: list[str] = []
    status: dict[str, Status] = {}
    for r in verbose:
        if r.id not in status:
            order.append(r.id)
        status[r.id] = r.status
    for r in summary:
        if "::" not in r.id:
            # "SKIPPED [1] file:line: reason" carries no node id; keep it only
            # when no verbose line already recorded a skip in that file.
            if any(status.get(i) == Status.SKIPPED and i.startswith(r.file) for i in order):
                continue
        if r.id not in status:
            order.append(r.id)
        status[r.id] = r.status
    run.results = [TestResult(i, status[i], _file_of(i), durations.get(i)) for i in order]
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append("no final summary line: the log is truncated or the run was interrupted")
    return run
