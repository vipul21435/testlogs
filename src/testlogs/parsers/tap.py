"""TAP version 13 and 14 (also what mocha and node:test emit with their TAP reporters)."""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_PLAN = re.compile(r"^(?P<indent>\s*)(?P<lo>\d+)\.\.(?P<hi>\d+)(?:\s*#.*)?$")
# "ok 3 - name # SKIP reason". The description runs to the first unescaped "#":
# TAP 14 writes a literal "#" in a name as "\#" (and "\" as "\\").
_TEST = re.compile(
    r"^(?P<indent>\s*)(?P<ok>not ok|ok)\b\s*(?P<num>\d+)?\s*(?:-\s*)?"
    r"(?P<desc>(?:[^#\\]|\\.|\\$)*?)\s*(?:#\s*(?P<comment>.*))?$",
    re.IGNORECASE,
)
_DIRECTIVE = re.compile(r"^(?P<directive>SKIP|TODO)\S*\s*(?P<reason>.*)$", re.IGNORECASE)
_VERSION = re.compile(r"^TAP version \d+")
_SUBTEST_HEADER = re.compile(r"^\s*# Subtest: (?P<name>.*)$")
_DURATION_YAML = re.compile(r"^\s*duration_ms:\s*(?P<ms>[\d.]+)")
_ESCAPE = re.compile(r"\\([\\#])")


def _unescape(text: str) -> str:
    return _ESCAPE.sub(r"\1", text)


def looks_like(lines: list[str]) -> bool:
    if any(_VERSION.match(ln) for ln in lines[:5]):
        return True
    tests = sum(1 for ln in lines if ln.strip() and _TEST.match(ln))
    return tests >= 2 and any(_PLAN.match(ln) for ln in lines)


class _Level:
    """Test points and the plan seen at one indent of a (possibly nested) stream."""

    def __init__(self, indent: int, first: int) -> None:
        self.indent = indent
        self.points = 0
        self.plan: int | None = None
        self.first = first  # index of the first result recorded inside this level


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def parse(lines: list[str]) -> Run:
    run = Run(format="tap")
    plan: tuple[int, int] | None = None
    plan_before_tests = False
    seen_test = False
    # "# Subtest: name" headers in force, as (indent, name).
    headers: list[tuple[int, str]] = []
    levels: list[_Level] = [_Level(0, 0)]
    last: int | None = None  # the result a following YAML block describes
    last_indent = 0
    yaml_indent: int | None = None  # inside a "---" ... "..." block at this indent
    yaml_owner: int | None = None

    def close_deeper(indent: int) -> list[_Level]:
        closed = []
        while len(levels) > 1 and levels[-1].indent > indent:
            closed.append(levels.pop())
        for lv in closed:
            if lv.plan is not None and lv.plan != lv.points:
                run.incomplete = True
                run.notes.append(
                    f"a subtest plan at indent {lv.indent} says {lv.plan} tests, found {lv.points}"
                )
        return closed

    def level_at(indent: int) -> _Level:
        close_deeper(indent)
        if levels[-1].indent < indent:
            levels.append(_Level(indent, len(run.results)))
        return levels[-1]

    for raw in lines:
        line = raw.rstrip()
        if yaml_indent is not None:
            if line.strip() == "..." and _indent(line) == yaml_indent:
                yaml_indent = None
                continue
            if not line.strip() or _indent(line) >= yaml_indent:
                m = _DURATION_YAML.match(line)
                if m and yaml_owner is not None and _indent(line) == yaml_indent:
                    r = run.results[yaml_owner]
                    run.results[yaml_owner] = TestResult(
                        r.id, r.status, r.file, float(m.group("ms")) / 1000.0
                    )
                continue
            yaml_indent = None  # an unterminated block: read this line normally
        if not line.strip():
            continue
        if line.lstrip().startswith("Bail out!"):
            run.incomplete = True
            run.notes.append(line.strip())
            continue
        if line.strip() == "---":
            yaml_indent = _indent(line)
            yaml_owner = last if last is not None and yaml_indent > last_indent else None
            last = None
            continue
        m = _SUBTEST_HEADER.match(line)
        if m:
            indent = _indent(line)
            while headers and headers[-1][0] >= indent:
                headers.pop()
            headers.append((indent, _unescape(m.group("name").strip())))
            continue
        m = _PLAN.match(line)
        if m:
            indent = len(m.group("indent"))
            if indent == 0:
                plan = (int(m.group("lo")), int(m.group("hi")))
                plan_before_tests = not seen_test
            else:
                lo, hi = int(m.group("lo")), int(m.group("hi"))
                level_at(indent).plan = hi - lo + 1 if hi >= lo else 0
            continue
        m = _TEST.match(line)
        if not m:
            last = None
            continue
        indent = len(m.group("indent"))
        while headers and headers[-1][0] > indent:
            headers.pop()
        desc = _unescape(m.group("desc").strip())
        if desc.startswith("- "):
            desc = desc[2:].strip()
        closed = close_deeper(indent)
        level = level_at(indent)
        level.points += 1
        children = [lv for lv in closed if lv.points]
        if children:
            # This point closes a subtest block: it summarises its children and
            # is not a test itself. Without a "# Subtest:" header the children
            # were recorded without the parent's name, so add it now.
            if not any(i == indent and n == desc for i, n in headers):
                first = min(lv.first for lv in children)
                for i in range(first, len(run.results)):
                    r = run.results[i]
                    run.results[i] = TestResult(f"{desc} > {r.id}", r.status, r.file, r.duration)
            last = None
            continue
        parents = [n for i, n in headers if i < indent]
        full = " > ".join([*parents, desc])
        directive = _DIRECTIVE.match(m.group("comment") or "")
        ok = m.group("ok").lower() == "ok"
        if directive and directive.group("directive").upper() == "SKIP":
            status = Status.SKIPPED
        elif directive:
            status = Status.XPASS if ok else Status.XFAIL
        else:
            status = Status.PASSED if ok else Status.FAILED
        run.results.append(TestResult(full, status))
        last = len(run.results) - 1
        last_indent = indent
        seen_test = True
    open_children = [lv for lv in levels[1:] if lv.points or lv.plan]
    if open_children:
        run.incomplete = True
        run.notes.append("a subtest block was never closed by its parent's result line")
    if plan is None:
        run.incomplete = True
        run.notes.append("no plan line")
    else:
        expected = plan[1] - plan[0] + 1 if plan[1] >= plan[0] else 0
        top = levels[0].points
        if top != expected:
            run.incomplete = True
            run.notes.append(f"plan says {expected} tests, found {top}")
        if plan_before_tests and not seen_test and expected > 0:
            run.incomplete = True
    return run
