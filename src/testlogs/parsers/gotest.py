"""``go test -v`` and ``go test -json``.

Verbose output prints ``=== RUN   TestX`` when a test starts and
``--- PASS: TestX (0.01s)`` (or FAIL, SKIP) when it ends; subtests are indented
and named ``TestX/case``. The package line ``ok  pkg  0.1s`` (or ``FAIL pkg``)
closes a package, so every result before it gets that package as its file. The id
is ``package::TestName`` because the same test name can exist in two packages;
results with no package line after them (a cut-off log) keep the bare name.
JSON output is one event per line with ``Action``, ``Package``, ``Test`` and
``Elapsed``; the terminal actions are pass, fail and skip.
"""

from __future__ import annotations

import json
import re

from testlogs.models import Run, Status, TestResult

_RUN = re.compile(r"^\s*=== RUN\s+(?P<name>\S+)\s*$")
_END = re.compile(r"^\s*--- (?P<res>PASS|FAIL|SKIP): (?P<name>\S+) \((?P<secs>[\d.]+)s\)\s*$")
_PKG = re.compile(r"^(?:ok|FAIL|\?)\s+(?P<pkg>\S+)\s+(?:(?P<secs>[\d.]+)s|\[.*\])")
_ACTIONS = {"pass": Status.PASSED, "fail": Status.FAILED, "skip": Status.SKIPPED}
_STATUS = {"PASS": Status.PASSED, "FAIL": Status.FAILED, "SKIP": Status.SKIPPED}


def looks_like(lines: list[str]) -> bool:
    return sum(1 for ln in lines if _RUN.match(ln) or _END.match(ln)) >= 2


def looks_like_json(lines: list[str]) -> bool:
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if not ln.startswith("{"):
            return False
        try:
            ev = json.loads(ln)
        except ValueError:
            return False
        return isinstance(ev, dict) and "Action" in ev
    return False


def parse(lines: list[str]) -> Run:
    run = Run(format="go")
    started: list[str] = []
    ended: list[TestResult] = []
    for raw in lines:
        line = raw.rstrip()
        m = _RUN.match(line)
        if m:
            started.append(m.group("name"))
            continue
        m = _END.match(line)
        if m:
            ended.append(
                TestResult(m.group("name"), _STATUS[m.group("res")], "", float(m.group("secs")))
            )
            if m.group("name") in started:
                started.remove(m.group("name"))
            continue
        m = _PKG.match(line)
        if m:
            pkg = m.group("pkg")
            run.results.extend(
                TestResult(f"{pkg}::{r.id}", r.status, pkg, r.duration) for r in ended
            )
            ended = []
    if ended:
        run.results.extend(ended)
        run.incomplete = True
        run.notes.append(f"{len(ended)} results after the last package line")
    if started:
        run.incomplete = True
        run.notes.append(f"{len(started)} tests started but never finished: {started[0]}")
    if not run.results and not started:
        run.incomplete = True
        run.notes.append("no test results found")
    return run


def parse_json(lines: list[str]) -> Run:
    run = Run(format="go-json")
    started: set[tuple[str, str]] = set()
    bad = 0
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            bad += 1
            continue
        test = ev.get("Test")
        if not test:
            continue
        pkg = ev.get("Package", "")
        action = ev.get("Action")
        if action == "run":
            started.add((pkg, test))
        elif action in _ACTIONS:
            started.discard((pkg, test))
            raw_secs = ev.get("Elapsed")
            dur = float(raw_secs) if raw_secs is not None else None
            tid = f"{pkg}::{test}" if pkg else test
            run.results.append(TestResult(tid, _ACTIONS[action], pkg, dur))
    if bad:
        run.incomplete = True
        run.notes.append(f"{bad} lines are not JSON events")
    if started:
        run.incomplete = True
        run.notes.append(f"{len(started)} tests started but never finished")
    return run
