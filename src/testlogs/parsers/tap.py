"""TAP version 13 and 14 (also what mocha and node:test emit with their TAP reporters)."""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_PLAN = re.compile(r"^(?P<indent>\s*)(?P<lo>\d+)\.\.(?P<hi>\d+)(?:\s*#.*)?$")
_TEST = re.compile(
    r"^(?P<indent>\s*)(?P<ok>not ok|ok)\b\s*(?P<num>\d+)?\s*(?:-\s*)?(?P<desc>[^#]*?)\s*"
    r"(?:#\s*(?P<directive>SKIP|TODO)\b\s*(?P<reason>.*))?$",
    re.IGNORECASE,
)
_VERSION = re.compile(r"^TAP version \d+")
_SUBTEST_HEADER = re.compile(r"^\s*# Subtest: (?P<name>.*)$")
_DURATION_YAML = re.compile(r"^\s*duration_ms:\s*(?P<ms>[\d.]+)")


def looks_like(lines: list[str]) -> bool:
    if any(_VERSION.match(ln) for ln in lines[:5]):
        return True
    tests = sum(1 for ln in lines if ln.strip() and _TEST.match(ln))
    return tests >= 2 and any(_PLAN.match(ln) for ln in lines)


def parse(lines: list[str]) -> Run:
    run = Run(format="tap")
    plan: tuple[int, int] | None = None
    plan_before_tests = False
    seen_test = False
    # Nested subtests (TAP 14 / node:test): a stack of (indent, name).
    stack: list[tuple[int, str]] = []
    last: int | None = None
    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("Bail out!"):
            if line.lstrip().startswith("Bail out!"):
                run.incomplete = True
                run.notes.append(line.strip())
            continue
        m = _SUBTEST_HEADER.match(line)
        if m:
            indent = len(line) - len(line.lstrip())
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, m.group("name").strip()))
            continue
        m = _PLAN.match(line)
        if m:
            if m.group("indent") == "":
                plan = (int(m.group("lo")), int(m.group("hi")))
                plan_before_tests = not seen_test
            continue
        m = _DURATION_YAML.match(line)
        if m and last is not None:
            r = run.results[last]
            run.results[last] = TestResult(r.id, r.status, r.file, float(m.group("ms")) / 1000.0)
            continue
        m = _TEST.match(line)
        if m:
            indent = len(m.group("indent"))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            desc = m.group("desc").strip()
            if desc.startswith("- "):
                desc = desc[2:].strip()
            # A parent "ok" line that closes a subtest block is a summary of its
            # children, not a test: skip it when its description names a subtest
            # we already recorded at a deeper indent.
            parents = [n for _, n in stack]
            full = " > ".join([*parents, desc]) if parents else desc
            if (
                m.group("num")
                and indent == 0
                and any(r.id.startswith(desc + " > ") for r in run.results)
            ):
                continue
            if m.group("num") and indent > 0 and any(
                r.id.startswith(full + " > ") for r in run.results
            ):
                continue
            ok = m.group("ok").lower() == "ok"
            directive = (m.group("directive") or "").upper()
            if directive == "SKIP":
                status = Status.SKIPPED
            elif directive == "TODO":
                status = Status.XPASS if ok else Status.XFAIL
            else:
                status = Status.PASSED if ok else Status.FAILED
            run.results.append(TestResult(full, status))
            last = len(run.results) - 1
            seen_test = True
            continue
    if plan is None:
        run.incomplete = True
        run.notes.append("no plan line")
    else:
        expected = plan[1] - plan[0] + 1 if plan[1] >= plan[0] else 0
        top = sum(1 for r in run.results if " > " not in r.id) + len(
            {r.id.split(" > ", 1)[0] for r in run.results if " > " in r.id}
        )
        if top != expected:
            run.incomplete = True
            run.notes.append(f"plan says {expected} tests, found {top}")
        if plan_before_tests and not seen_test and expected > 0:
            run.incomplete = True
    return run
