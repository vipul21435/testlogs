"""pytest parsers: ``-v`` progress lines and the ``-rA`` short test summary.

Verbose lines look like ``tests/test_a.py::test_x[a b] PASSED  [ 33%]``.
Summary lines (``-rA``) look like ``PASSED tests/test_a.py::test_x`` or
``FAILED tests/test_a.py::test_x - AssertionError``. When both are present the
summary wins, because a test's verbose line can be split by captured output.
A parameter id may contain `` - `` itself, so a summary row's id is the longest
id already seen on a verbose line, or else ends at the first `` - `` outside brackets.
The final ``==== 3 passed in 0.02s ====`` line marks a complete log; without
it the run is reported incomplete.

pytest 9 reports ``unittest`` subtests itself: the parent test is still printed
``PASSED`` and each failing subtest gets a ``SUBFAILED(i=1) node::id`` summary row.
A test with a failing subtest is recorded as failed, which is what JUnit XML and
``unittest -v`` say about the same test; passing subtests are only counted.
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
# pytest-rerunfailures prints "path::id RERUN [ 33%]" before each repeat.
_RERUN = re.compile(r"^(?P<id>\S+?::\S.*?)\s+RERUN(?:\s+\[\s*\d+%\])?\s*$")
# pytest-xdist: "[gw1] [ 42%] PASSED path::id". Workers finish in any order.
_XDIST = re.compile(
    r"^\[gw\d+\] \[\s*\d+%\] (?P<status>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS) (?P<id>\S+?::.+?)"
    r"(?:\s+\((?P<reason>[^)]*)\))?\s*$"
)
# With -s the test's own output follows the id, and the status word starts a later line.
_BARE_STATUS = re.compile(
    r"^(?P<status>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)(?:\s+\([^)]*\))?(?:\s+\[\s*\d+%\])?$"
)
_SUBTEST = re.compile(
    r"^SUB(?P<status>FAILED|PASSED|SKIPPED)(?:\[[^\]]*\])?\s*(?:\((?P<params>.*?)\))?\s+"
    r"(?P<id>[^\s:]+::.*?)(?:\s+-\s+.*)?$"
)
_SUBTEST_COUNT = re.compile(r"(?P<n>\d+) subtests? (?P<what>passed|failed|skipped)")
_FINAL_COUNT = re.compile(
    r"(?P<n>\d+) (?P<sub>subtests? )?(?P<what>passed|failed|skipped|xfailed|xpassed|errors?)\b"
)
_SUMMARY_HEADER = re.compile(r"^=+ short test summary info =+$")
_FINAL = re.compile(
    r"^=+ .*\b(?:passed|failed|error|errors|skipped|xfailed|xpassed|no tests ran)\b"
    r".* in [\d.]+s.* =+$"
)
# With -q the final line has no "=" border: "2 failed, 8 passed, 1 error in 0.03s".
_FINAL_QUIET = re.compile(
    r"^(?:\d+ [a-z]+(?: [a-z]+)?|no tests ran)(?:, \d+ [a-z]+(?: [a-z]+)?)* in [\d.]+s"
    r"(?: \([\d:]+\))?$"
)
_DURATION = re.compile(r"^(?P<secs>\d+\.\d+)s\s+(?:call|setup|teardown)\s+(?P<id>\S.*)$")


def looks_like(lines: list[str]) -> bool:
    if any(ln.startswith("============================= test session starts") for ln in lines):
        return True
    hits = sum(1 for ln in lines if _VERBOSE.match(ln) or _SUMMARY.match(ln))
    return hits >= 2 and any("::" in ln for ln in lines)


def _leading_node_id(line: str) -> str | None:
    """The node id at the start of ``line``: up to the first space outside brackets."""
    if "::" not in line or line[0].isspace():
        return None
    space = line.find(" ")
    bracket = line.find("[")
    if space == -1:
        head = line
    elif bracket == -1 or bracket > space:
        head = line[:space]  # no parameter brackets before the first space
    else:
        depth = 0
        head = line
        for i in range(bracket, len(line)):
            ch = line[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth = max(depth - 1, 0)
            elif ch.isspace() and depth == 0:
                head = line[:i]
                break
    first, sep, _ = head.partition("::")
    if sep and first and ":" not in first.replace(":\\", ""):
        return head
    return None


def _summary_id(rest: str, known: set[str]) -> str:
    """The node id at the start of a summary row's text, before any " - reason".

    A parameter id may itself contain " - " or unbalanced brackets, so a known id
    from a verbose line wins; otherwise " - " only ends the id outside brackets.
    """
    if rest in known:
        return rest
    cut = rest.rfind(" - ")
    while cut > 0:
        if rest[:cut] in known:
            return rest[:cut]
        cut = rest.rfind(" - ", 0, cut)
    depth = 0
    for i, ch in enumerate(rest):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(depth - 1, 0)
        elif depth == 0 and rest.startswith(" - ", i):
            return rest[:i]
    return rest.rstrip()


def _file_of(node_id: str) -> str:
    if "::" in node_id:
        return node_id.split("::", 1)[0]
    return node_id.split(":", 1)[0]


def parse(lines: list[str]) -> Run:
    run = Run(format="pytest")
    verbose: list[TestResult] = []
    summary: list[TestResult] = []
    known: set[str] = set()  # ids seen on verbose lines
    durations: dict[str, float] = {}
    subfailed: dict[str, int] = {}
    final_total: int | None = None
    in_summary = False
    complete = False
    pending: str | None = None  # an id whose status has not been printed yet
    reruns: dict[str, int] = {}
    for raw in lines:
        line = raw.rstrip()
        if not line:
            continue
        if _SUMMARY_HEADER.match(line):
            in_summary = True
            continue
        if _FINAL.match(line) or _FINAL_QUIET.match(line):
            complete = True
            in_summary = False
            for sc in _SUBTEST_COUNT.finditer(line):
                run.notes.append(f"pytest counts {sc.group('n')} subtests {sc.group('what')}")
            final_total = sum(
                int(fc.group("n")) for fc in _FINAL_COUNT.finditer(line) if not fc.group("sub")
            )
            continue
        m = _DURATION.match(line)
        if m:
            tid = m.group("id")
            durations[tid] = max(durations.get(tid, 0.0), float(m.group("secs")))
            continue
        if in_summary:
            m = _SUBTEST.match(line)
            if m:
                if m.group("status") == "FAILED":
                    tid = _summary_id(line[m.start("id") :], known)
                    subfailed[tid] = subfailed.get(tid, 0) + 1
                continue
            m = _SUMMARY.match(line)
            if m:
                tid = m.group("id")
                if "::" in tid:
                    rest = line[m.start("id") :]
                    tid = _summary_id(rest, known)
                summary.append(TestResult(tid, _STATUS_WORDS[m.group("status")], _file_of(tid)))
            continue
        m = _RERUN.match(line)
        if m:
            reruns[m.group("id")] = reruns.get(m.group("id"), 0) + 1
            pending = None
            continue
        m = _XDIST.match(line) or _VERBOSE.match(line)
        if m:
            tid = m.group("id")
            verbose.append(TestResult(tid, _STATUS_WORDS[m.group("status")], _file_of(tid)))
            known.add(tid)
            pending = None
            continue
        m = _BARE_STATUS.match(line)
        if m and pending is not None:
            verbose.append(TestResult(pending, _STATUS_WORDS[m.group("status")], _file_of(pending)))
            known.add(pending)
            pending = None
            continue
        if line.startswith("=") or line.startswith("_"):
            pending = None
            continue
        tid = _leading_node_id(line)
        if tid is not None:
            pending = tid
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
    for tid in subfailed:
        if tid not in status:
            order.append(tid)
        if status.get(tid) not in (Status.FAILED, Status.ERROR):
            status[tid] = Status.FAILED
    if subfailed:
        n = sum(subfailed.values())
        run.notes.append(
            f"{n} failing subtests in {len(subfailed)} tests: those tests are recorded as failed"
        )
    run.results = [TestResult(i, status[i], _file_of(i), durations.get(i)) for i in order]
    if reruns:
        passed_late = [i for i in reruns if status.get(i) is Status.PASSED]
        note = f"{len(reruns)} tests were rerun ({sum(reruns.values())} reruns)"
        if passed_late:
            note += f"; {len(passed_late)} passed only on a rerun: {', '.join(passed_late)}"
        run.notes.append(note)
    if final_total is not None:
        # pytest counts each failing subtest as one "failed" on top of its test.
        run.summary_total = final_total - sum(subfailed.values())
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append("no final summary line: the log is truncated or the run was interrupted")
    return run
