"""The JSON report written by ``jest --json`` and ``vitest --reporter=json``.

Both write one object with ``testResults``: a list of files, each with
``assertionResults`` carrying ``ancestorTitles``, ``title``, ``status``
(passed, failed, pending, skipped, todo) and ``duration`` in milliseconds.
"""

from __future__ import annotations

import json

from testlogs.models import Run, Status, TestResult

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


def parse(text: str) -> Run:
    run = Run(format="jest-json")
    try:
        doc = json.loads(text)
    except ValueError as exc:
        run.incomplete = True
        run.notes.append(f"JSON does not parse: {exc}")
        return run
    for suite in doc.get("testResults", []):
        file = suite.get("name", "")
        for a in suite.get("assertionResults", []):
            parts = [*a.get("ancestorTitles", []), a.get("title", "")]
            tid = f"{file}::{' > '.join(parts)}"
            status = _STATUS.get(a.get("status", ""), Status.ERROR)
            ms = a.get("duration")
            run.results.append(TestResult(tid, status, file, None if ms is None else ms / 1000))
        if suite.get("status") == "failed" and not suite.get("assertionResults"):
            run.results.append(TestResult(file, Status.ERROR, file))
            run.notes.append(f"{file}: suite failed with no test results")
    if doc.get("wasInterrupted"):
        run.incomplete = True
        run.notes.append("report says the run was interrupted")
    if doc.get("numTotalTests") is not None and doc["numTotalTests"] != len(run.results):
        run.notes.append(f"report counts {doc['numTotalTests']} tests, found {len(run.results)}")
    return run
