"""JUnit XML, as written by pytest, surefire, and most JS and Go reporters."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from testlogs.models import Run, Status, TestResult, plural


def looks_like(text: str) -> bool:
    head = text.lstrip()[:200]
    return head.startswith("<") and ("<testsuite" in text or "<testsuites" in text)


def _status(case: ET.Element) -> Status:
    """Status from the child elements. Surefire's ``flakyFailure`` and
    ``rerunFailure`` children sit beside a final pass, so they do not count.
    pytest marks an expected failure ``<skipped type="pytest.xfail">``; an
    unexpected pass has no child at all and stays ``passed``."""
    tags = {child.tag for child in case}
    if "error" in tags:
        return Status.ERROR
    if "failure" in tags:
        return Status.FAILED
    skipped = case.find("skipped")
    if skipped is not None:
        return Status.XFAIL if skipped.get("type") == "pytest.xfail" else Status.SKIPPED
    return Status.PASSED


def parse(text: str) -> Run:
    run = Run(format="junit")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        run.incomplete = True
        run.notes.append(f"XML does not parse: {exc}")
        return run
    odd_times = 0
    for case in root.iter("testcase"):
        name = case.get("name", "")
        classname = case.get("classname", "")
        tid = f"{classname}::{name}" if classname else name
        file = case.get("file", "")
        raw = case.get("time")
        duration = None
        if raw not in (None, ""):
            try:
                duration = float(raw)
            except ValueError:
                duration = None
            if duration is None or not math.isfinite(duration) or duration < 0:
                odd_times += 1
                duration = None
        run.results.append(TestResult(tid, _status(case), file, duration))
    if odd_times:
        run.notes.append(
            f"{plural(odd_times, 'testcase')} with a time that is not a finite number of "
            "seconds; their durations are left empty"
        )
    return run
