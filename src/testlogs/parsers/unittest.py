"""``python -m unittest -v`` output.

Lines look like ``test_x (pkg.mod.Class.test_x) ... ok``. A test with a docstring
prints the description on the next line before the result. The run is complete
when the ``Ran N tests in Xs`` line is present.

A test whose ``subTest`` cases fail prints ``test_x (qual) ... `` with no result,
then one indented ``test_x (qual) (i=1) ... FAIL`` line per failing case and no
line for the parent. The parent is recorded once, as failed (or error), so that
it lines up with the pytest and JUnit records of the same run.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_RESULTS = {
    "ok": Status.PASSED,
    "FAIL": Status.FAILED,
    "ERROR": Status.ERROR,
    "skipped": Status.SKIPPED,
    "expected failure": Status.XFAIL,
    "unexpected success": Status.XPASS,
}
_RESULT_RE = r"(?P<result>ok|FAIL|ERROR|skipped(?:\s+.*)?|expected failure|unexpected success)"
_HEAD = re.compile(r"^(?P<name>\S+) \((?P<qual>[\w.]+)\)(?: \.\.\.(?: " + _RESULT_RE + r")?)?\s*$")
_SUB = re.compile(
    r"^\s+(?P<name>\S+) \((?P<qual>[\w.]+)\) \(.*\) \.\.\. (?P<result>FAIL|ERROR|skipped.*)$"
)
_TAIL = re.compile(r"^.*\.\.\. " + _RESULT_RE + r"\s*$")
_RAN = re.compile(r"^Ran \d+ tests? in [\d.]+s$")


def looks_like(lines: list[str]) -> bool:
    heads = sum(1 for ln in lines if _HEAD.match(ln))
    return heads >= 1 and any(_RAN.match(ln) or ln.rstrip() in ("OK", "FAILED") for ln in lines)


def _status(result: str) -> Status:
    key = result.split()[0] if result.startswith("skipped") else result
    return _RESULTS[key]


def _file_of(qual: str) -> str:
    # pkg.mod.Class.test_x -> pkg/mod.py is a guess; keep the dotted module instead.
    parts = qual.split(".")
    return ".".join(parts[:-2]) if len(parts) > 2 else ""


def parse(lines: list[str]) -> Run:
    run = Run(format="unittest")
    pending: tuple[str, str] | None = None
    sub_failed: dict[str, Status] = {}
    complete = False
    for raw in lines:
        line = raw.rstrip()
        if _RAN.match(line):
            complete = True
            continue
        m = _SUB.match(line)
        if m:
            tid = m.group("qual")
            status = _status(m.group("result"))
            if status is not Status.SKIPPED and tid not in sub_failed:
                sub_failed[tid] = status
                run.results.append(TestResult(tid, status, _file_of(tid)))
            pending = None
            continue
        m = _HEAD.match(line)
        if m:
            tid = m.group("qual")
            if m.group("result"):
                run.results.append(TestResult(tid, _status(m.group("result")), _file_of(tid)))
                pending = None
            else:
                pending = (tid, _file_of(tid))
            continue
        if pending is not None:
            m = _TAIL.match(line)
            if m:
                run.results.append(TestResult(pending[0], _status(m.group("result")), pending[1]))
                pending = None
    if sub_failed:
        run.notes.append(f"{len(sub_failed)} tests with failing subtests are recorded as failed")
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append("no 'Ran N tests' line: the log is truncated or the run was interrupted")
    return run
