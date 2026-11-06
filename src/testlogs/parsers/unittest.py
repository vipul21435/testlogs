"""``python -m unittest -v`` output.

Lines look like ``test_x (pkg.mod.Class.test_x) ... ok``. A test with a docstring
prints the description on the next line before the result. The run is complete
when the ``Ran N tests in Xs`` line is present.

A test whose ``subTest`` cases fail prints ``test_x (qual) ... `` with no result,
then one indented ``test_x (qual) (i=1) ... FAIL`` line per failing case and no
line for the parent. The parent is recorded once, as failed (or error), so that
it lines up with the pytest and JUnit records of the same run.

With unbuffered stdout a test's own output follows the `` ... `` and the result
comes after it, on the same line (``... xok``) or a later one. A result word that
only ends a line of output (``... look``) is kept as a guess until the next line
shows whether the real result follows.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult, plural

_RESULTS = {
    "ok": Status.PASSED,
    "FAIL": Status.FAILED,
    "ERROR": Status.ERROR,
    "skipped": Status.SKIPPED,
    "expected failure": Status.XFAIL,
    "unexpected success": Status.XPASS,
}
_RESULT_RE = r"(?P<result>ok|FAIL|ERROR|skipped(?:\s+.*)?|expected failure|unexpected success)"
_HEAD = re.compile(r"^(?P<name>\S+) \((?P<qual>[\w.]+)\)(?: \.\.\.(?: (?P<rest>.*))?)?$")
_EXACT = re.compile(r"^" + _RESULT_RE + r"\s*$")
_ENDS = re.compile(
    r"(?P<result>ok|FAIL|ERROR|skipped '.*'|expected failure|unexpected success)\s*$"
)
_SUB = re.compile(
    r"^\s+(?P<name>\S+) \((?P<qual>[\w.]+)\) \(.*\) \.\.\. (?P<result>FAIL|ERROR|skipped.*)$"
)
_TAIL = re.compile(r"^.*\.\.\. " + _RESULT_RE + r"\s*$")
_RAN = re.compile(r"^Ran (?P<n>\d+) tests? in [\d.]+s$")


def looks_like(lines: list[str]) -> bool:
    heads = sum(1 for ln in lines if _HEAD.match(ln))
    return heads >= 1 and any(_RAN.match(ln) or ln.rstrip() in ("OK", "FAILED") for ln in lines)


def _status(result: str) -> Status:
    key = result.split()[0] if result.startswith("skipped") else result
    return _RESULTS[key]


def _ident(name: str, qual: str) -> tuple[str, str]:
    """Return (id, file) for a ``name (qual)`` pair.

    Python 3.11+ prints ``test_x (pkg.mod.Class.test_x)``; 3.10 prints
    ``test_x (pkg.mod.Class)``; a doctest prints ``func (pkg.mod)``. The id is
    always ``qual`` ending in ``name``. The file is the dotted module: the class
    is dropped for ``test*`` methods, while a doctest's ``qual`` is the module.
    """
    tid = qual if qual == name or qual.endswith("." + name) else f"{qual}.{name}"
    owner = tid[: -len(name) - 1] if tid.endswith("." + name) else ""
    if name.startswith("test") and "." in owner:
        owner = owner.rsplit(".", 1)[0]
    return tid, owner


def parse(lines: list[str]) -> Run:
    run = Run(format="unittest")
    pending: tuple[str, str] | None = None
    guess: Status | None = None  # a result word that ended the pending test's output
    sub_failed: dict[str, Status] = {}
    complete = False

    def settle(status: Status | None) -> None:
        nonlocal pending, guess
        if pending is not None and status is not None:
            run.results.append(TestResult(pending[0], status, pending[1]))
        pending, guess = None, None

    for raw in lines:
        line = raw.rstrip()
        m = _RAN.match(line)
        if m:
            settle(guess)
            complete = True
            run.summary_total = int(m.group("n"))
            continue
        m = _SUB.match(line)
        if m:
            tid, file = _ident(m.group("name"), m.group("qual"))
            status = _status(m.group("result"))
            if status is not Status.SKIPPED and tid not in sub_failed:
                sub_failed[tid] = status
                run.results.append(TestResult(tid, status, file))
            pending, guess = None, None
            continue
        m = _HEAD.match(line)
        if m:
            settle(guess)
            tid, file = _ident(m.group("name"), m.group("qual"))
            rest = (m.group("rest") or "").strip()
            exact = _EXACT.match(rest)
            if exact:
                run.results.append(TestResult(tid, _status(exact.group("result")), file))
                continue
            pending = (tid, file)
            ends = _ENDS.search(rest)
            guess = _status(ends.group("result")) if ends else None
            continue
        if pending is None:
            continue
        if line.startswith(("=" * 10, "-" * 10)):
            settle(guess)  # the failure details begin
            continue
        exact = _EXACT.match(line.strip()) or _TAIL.match(line)
        if exact:
            settle(_status(exact.group("result")))
            continue
        if line.strip():
            ends = _ENDS.search(line)
            guess = _status(ends.group("result")) if ends else None
    # A guess left open at the end of a cut log is dropped, not recorded.
    if sub_failed:
        n = len(sub_failed)
        run.notes.append(f"{plural(n, 'test')} with failing subtests, recorded as failed")
    run.incomplete = not complete
    if run.incomplete:
        run.notes.append("no 'Ran N tests' line: the log is truncated or the run was interrupted")
    return run
