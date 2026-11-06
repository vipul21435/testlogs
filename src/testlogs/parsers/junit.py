"""JUnit XML, as written by pytest, surefire, and most JS and Go reporters."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from testlogs.models import Run, Status, TestResult


def looks_like(text: str) -> bool:
    head = text.lstrip()[:200]
    return head.startswith("<") and ("<testsuite" in text or "<testsuites" in text)


def _status(case: ET.Element) -> Status:
    tags = {child.tag for child in case}
    if "error" in tags:
        return Status.ERROR
    if "failure" in tags:
        return Status.FAILED
    if "skipped" in tags:
        return Status.SKIPPED
    return Status.PASSED


def parse(text: str) -> Run:
    run = Run(format="junit")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        run.incomplete = True
        run.notes.append(f"XML does not parse: {exc}")
        return run
    for case in root.iter("testcase"):
        name = case.get("name", "")
        classname = case.get("classname", "")
        tid = f"{classname}::{name}" if classname else name
        file = case.get("file", "")
        raw = case.get("time")
        duration = float(raw) if raw not in (None, "") else None
        run.results.append(TestResult(tid, _status(case), file, duration))
    return run
