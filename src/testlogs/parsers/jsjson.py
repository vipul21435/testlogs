"""The JSON report written by ``jest --json`` and ``vitest --reporter=json``.

Both write one object with ``testResults``: a list of files, each with
``assertionResults`` carrying ``ancestorTitles``, ``title``, ``status``
(passed, failed, pending, skipped, todo) and ``duration`` in milliseconds.
"""

from __future__ import annotations

import json

from testlogs.models import Run, Status, TestResult, plural

_STATUS = {
    "passed": Status.PASSED,
    "failed": Status.FAILED,
    "pending": Status.SKIPPED,
    "skipped": Status.SKIPPED,
    "todo": Status.SKIPPED,
    "disabled": Status.SKIPPED,
}


def looks_like(text: str) -> bool:
    head = text.lstrip()
    return head.startswith("{") and '"testResults"' in text


def _ms(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value / 1000


def parse(text: str) -> Run:
    run = Run(format="jest-json")
    try:
        doc = json.loads(text)
    except ValueError as exc:
        run.incomplete = True
        run.notes.append(f"JSON does not parse: {exc}")
        return run
    if not isinstance(doc, dict) or not isinstance(doc.get("testResults", []), list):
        run.incomplete = True
        run.notes.append("JSON is not a report object with a testResults list")
        return run
    bad = 0  # entries that are not objects
    for suite in doc.get("testResults", []):
        if not isinstance(suite, dict):
            bad += 1
            continue
        file = str(suite.get("name", ""))
        assertions = suite.get("assertionResults", [])
        if not isinstance(assertions, list):
            bad += 1
            assertions = []
        for a in assertions:
            if not isinstance(a, dict):
                bad += 1
                continue
            ancestors = a.get("ancestorTitles", [])
            if not isinstance(ancestors, list):
                ancestors = [ancestors]
            parts = [str(p) for p in ancestors] + [str(a.get("title", ""))]
            tid = f"{file}::{' > '.join(parts)}"
            status = _STATUS.get(str(a.get("status", "")), Status.ERROR)
            run.results.append(TestResult(tid, status, file, _ms(a.get("duration"))))
        if suite.get("status") == "failed" and not assertions:
            run.results.append(TestResult(file, Status.ERROR, file))
            run.notes.append(f"{file}: suite failed with no test results")
    if bad:
        run.incomplete = True
        what = "is not an object" if bad == 1 else "are not objects"
        run.notes.append(f"{plural(bad, 'entry', 'entries')} in the report {what}")
    if doc.get("wasInterrupted"):
        run.incomplete = True
        run.notes.append("report says the run was interrupted")
    total = doc.get("numTotalTests")
    if isinstance(total, int) and not isinstance(total, bool):
        run.summary_total = total
    return run
