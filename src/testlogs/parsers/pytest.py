"""pytest parsers: ``-v`` progress lines and the ``-rA`` short test summary.

Verbose lines look like ``tests/test_a.py::test_x[a b] PASSED  [ 33%]``.
Summary lines (``-rA``) look like ``PASSED tests/test_a.py::test_x`` or
``FAILED tests/test_a.py::test_x - AssertionError``. When both are present the
summary wins, because a test's verbose line can be split by captured output.
A parameter id may contain `` - `` itself, so a summary row's id is the longest
id already seen on a verbose line, or else ends at the first `` - `` outside brackets.
The final ``==== 3 passed in 0.02s ====`` line marks a complete log; without
it the run is reported incomplete. pytest prints the final line even after a run
stops early, so a ``!!! KeyboardInterrupt !!!`` or ``!!! Interrupted: ... !!!``
banner also makes the run incomplete, and the test that was running is named.
Lines inside the FAILURES, ERRORS and PASSES sections are captured output, and a
whole pytest session printed by a test (pytester) is skipped from its
``test session starts`` line to its own final line.

Measured with pytest 9.2, pytest reports ``unittest`` subtests: the parent test is
still printed ``PASSED`` and each failing subtest gets a ``SUBFAILED(i=1) node::id`` summary row.
A test with a failing subtest is recorded as failed, which is what JUnit XML and
``unittest -v`` say about the same test; passing subtests are only counted.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult, plural

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
    r"(?:\s+\((?P<reason>.*)\))?"  # a reason may hold ")" itself: "(bug (see #1))"
    r"(?:\s+\[\s*\d+%\])?\s*$"
)
_SUMMARY = re.compile(
    r"^(?P<status>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)\s+"
    r"(?:\[\d+\]\s+)?(?P<id>\S+?(?:::\S.*?|:\d+)?)(?:\s+-\s+.*)?$"
)
# pytest groups skips by location: "SKIPPED [3] tests/a.py:18: reason" names no test.
_SKIP_ROW = re.compile(r"^SKIPPED \[(?P<n>\d+)\] (?P<loc>\S+?:\d+)(?::\s.*)?$")
# -q progress: one character per test, then the percentage.
_PROGRESS = re.compile(r"^[.FEsxXR]+\s*(?:\[\s*\d+%\])?$")
# pytest-rerunfailures prints "path::id RERUN [ 33%]" before each repeat.
_RERUN = re.compile(r"^(?P<id>\S+?::\S.*?)\s+RERUN(?:\s+\[\s*\d+%\])?\s*$")
# pytest-xdist: "[gw1] [ 42%] PASSED path::id". Workers finish in any order.
_XDIST = re.compile(
    r"^\[gw\d+\] \[\s*\d+%\] (?P<status>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS) (?P<id>\S+?::.+?)"
    r"(?:\s+\((?P<reason>.*)\))?\s*$"
)
# With -s the test's own output follows the id, and the status word starts a later line.
_BARE_STATUS = re.compile(
    r"^(?P<status>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)(?:\s+\(.*\))?(?:\s+\[\s*\d+%\])?$"
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
_SESSION_START = re.compile(r"^=+ test session starts =+$")
# Sections that hold tracebacks and captured output, which can contain lines shaped
# like pytest's own (a test that runs pytest itself, or prints such lines).
# The warnings summary is pytest's own text, so it ends a section, like the
# durations and short summary headers. Inside a section a final line counts only as
# the log's last line (with -rN no summary header follows the tracebacks).
_SECTION = re.compile(r"^=+ (?:FAILURES|ERRORS|PASSES|XFAILURES|XPASSES) =+$")
# Inside a section: "---- Captured stdout call ----" starts a test's own output, and
# "____ test_name ____" starts the next test's block.
_CAPTURED = re.compile(r"^-+ Captured (?:stdout|stderr|log) .*-+$")
_BLOCK = re.compile(r"^_{3,} .* _{3,}$")
_SECTION_END = re.compile(
    r"^=+ (?:short test summary info|warnings summary|slowest .*durations.*) =+$"
)
_FINAL = re.compile(
    r"^=+ .*\b(?:passed|failed|error|errors|skipped|xfailed|xpassed|no tests ran)\b"
    r".* in [\d.]+s.* =+$"
)
# With -q the final line has no "=" border: "2 failed, 8 passed, 1 error in 0.03s".
_FINAL_QUIET = re.compile(
    r"^(?:\d+ [a-z]+(?: [a-z]+)?|no tests ran)(?:, \d+ [a-z]+(?: [a-z]+)?)* in [\d.]+s"
    r"(?: \([\d:]+\))?$"
)
# pytest prints a "!" banner when a run stops early: Ctrl-C or a timeout's KeyboardInterrupt,
# errors during collection, -x/--maxfail, or pytest.exit(). The final line still follows.
_INTERRUPT = re.compile(
    r"^!+ (?P<what>KeyboardInterrupt|Interrupted: .*?|stopping after .*?"
    r"|_pytest\.outcomes\.Exit.*?) !+$"
)
_COLLECTED = re.compile(r"^collect(?:ing \.\.\. collect)?ed (?P<n>\d+) items?\b")
_DURATION = re.compile(r"^(?P<secs>\d+\.\d+)s\s+(?:call|setup|teardown)\s+(?P<id>\S.*)$")


def looks_like(lines: list[str]) -> bool:
    if any(ln.startswith("============================= test session starts") for ln in lines):
        return True
    hits = sum(1 for ln in lines if _VERBOSE.match(ln) or _SUMMARY.match(ln))
    if hits >= 2 and any("::" in ln for ln in lines):
        return True
    # A short -q log: a borderless final line after progress characters or a summary row.
    stripped = [ln.rstrip() for ln in lines]
    if any(_FINAL.match(ln) or _FINAL_QUIET.match(ln) for ln in stripped):
        return any(_PROGRESS.match(ln) or (_SUMMARY.match(ln) and "::" in ln) for ln in stripped)
    return False


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


def _merge(
    results: list[TestResult], order: list[str], seen: dict[str, set[Status]]
) -> dict[str, Status]:
    status: dict[str, Status] = {}
    for r in results:
        if r.id not in seen:
            order.append(r.id)
            seen[r.id] = set()
        seen[r.id].add(r.status)
        old = status.get(r.id)
        if old is Status.FAILED and r.status is Status.ERROR:
            continue
        if old is Status.ERROR and r.status is not Status.FAILED:
            continue
        status[r.id] = r.status
    return status


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
    interrupted: list[str] = []
    grouped_skips = 0  # skips counted by "SKIPPED [n] file:line" rows
    unfinished: str | None = None  # the test running when the run was interrupted
    collected: int | None = None
    last = max((i for i, ln in enumerate(lines) if ln.strip()), default=-1)
    seen_session = False
    depth = 0  # pytest sessions nested in captured output
    in_section = False
    captured = False  # inside a section, within a test's captured output
    for idx, raw in enumerate(lines):
        line = raw.rstrip()
        if not line:
            continue
        if _SESSION_START.match(line):
            if seen_session:
                depth += 1
            seen_session = True
            continue
        if depth:
            if _FINAL.match(line) or _FINAL_QUIET.match(line):
                depth -= 1
            continue
        if _SECTION.match(line):
            in_section = True
            captured = False
            pending = None
            continue
        if in_section:
            if _CAPTURED.match(line):
                captured = True
            elif _BLOCK.match(line):
                captured = False
            if _SECTION_END.match(line):
                in_section = False
            elif (
                (_FINAL.match(line) or _FINAL_QUIET.match(line)) and idx == last and not captured
            ):
                in_section = False
            elif not _INTERRUPT.match(line):
                continue
        m = _INTERRUPT.match(line)
        if m:
            interrupted.append(m.group("what"))
            if pending is not None and unfinished is None:
                unfinished = pending
            continue
        m = _COLLECTED.match(line)
        if m and collected is None:
            collected = int(m.group("n"))
            continue
        if _SUMMARY_HEADER.match(line):
            in_summary = True
            continue
        if _FINAL.match(line) or _FINAL_QUIET.match(line):
            complete = True
            in_summary = False
            for sc in _SUBTEST_COUNT.finditer(line):
                n = int(sc.group("n"))
                run.notes.append(f"pytest counts {plural(n, 'subtest')} {sc.group('what')}")
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
            m = _SKIP_ROW.match(line)
            if m:
                grouped_skips += int(m.group("n"))
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
            if m.re is _XDIST and tid.count("[") != tid.count("]"):
                # "[gw0] ... SKIPPED a.py::t[x (y)] (reason)": the lazy id stopped
                # inside the brackets; take the id up to the first space outside them.
                whole = _leading_node_id(line[m.start("id") :])
                if whole is not None and whole.count("[") == whole.count("]"):
                    tid = whole
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
    # A test whose setup or teardown errors gets a second line or row; the two are
    # merged the same way from either source (failed over error over the rest).
    order: list[str] = []
    seen: dict[str, set[Status]] = {}
    v_status = _merge(verbose, order, seen)
    s_status = _merge(summary, order, seen)
    status = {**v_status, **s_status}
    for tid in subfailed:
        if tid not in status:
            order.append(tid)
        if status.get(tid) not in (Status.FAILED, Status.ERROR):
            status[tid] = Status.FAILED
    if subfailed:
        n = sum(subfailed.values())
        run.notes.append(
            f"{plural(n, 'failing subtest')} in {plural(len(subfailed), 'test')}: "
            f"{'that test is' if len(subfailed) == 1 else 'those tests are'} recorded as failed"
        )
    run.results = [TestResult(i, status[i], _file_of(i), durations.get(i)) for i in order]
    named_skips = sum(1 for i in order if status[i] is Status.SKIPPED)
    if grouped_skips > named_skips:
        n = grouped_skips - named_skips
        run.notes.append(
            f"{plural(n, 'skipped test')} counted by file and line in the summary "
            "with no test id; run pytest with -v to name them"
        )
    if reruns:
        passed_late = [i for i in reruns if status.get(i) is Status.PASSED]
        n_runs = sum(reruns.values())
        note = (
            f"{plural(len(reruns), 'test')} {'was' if len(reruns) == 1 else 'were'} rerun "
            f"({plural(n_runs, 'rerun')})"
        )
        if passed_late:
            note += f"; {len(passed_late)} passed only on a rerun: {', '.join(passed_late)}"
        run.notes.append(note)
    if final_total is not None:
        # pytest counts each failing subtest as one "failed" on top of its test.
        # and a test with a setup or teardown error once more as an error.
        doubled = sum(1 for st in seen.values() if Status.ERROR in st and len(st) > 1)
        run.summary_total = final_total - sum(subfailed.values()) - doubled
    if pending is not None and unfinished is None and not complete:
        unfinished = pending
    run.incomplete = not complete or bool(interrupted)
    if not complete:
        run.notes.append("no final summary line: the log is truncated or the run was interrupted")
    for what in interrupted:
        if what == "KeyboardInterrupt":
            run.notes.append(f"pytest printed '{what}': stopped by the user or a timeout")
        else:
            run.notes.append(f"pytest printed '{what}': the run stopped early")
    if unfinished is not None:
        run.notes.append(f"{unfinished} started and has no status")
    if interrupted and collected is not None and collected > len(run.results):
        run.notes.append(
            f"pytest collected {plural(collected, 'test')}; "
            f"{len(run.results)} {'has' if len(run.results) == 1 else 'have'} a status"
        )
    return run
