"""``cargo test`` output from the Rust test harness, pretty (default) and terse.

Pretty prints ``test name ... ok`` (or FAILED, ignored) one per line; terse
prints one character per test (``.``, ``F``, ``i``) and names only the failures
in the ``failures:`` section. Each test binary opens with ``running N tests``
and closes with ``test result: ok. N passed; ...``. The ``Running`` line before a
block names the binary, which becomes the file.
"""

from __future__ import annotations

import re

from testlogs.models import Run, Status, TestResult

_RUNNING = re.compile(r"^\s*Running (?:unittests )?(?P<file>\S+)(?: \(.*\))?$")
_DOCTEST = re.compile(r"^\s*Doc-tests (?P<crate>\S+)$")
_BLOCK = re.compile(r"^running (?P<n>\d+) tests?$")
_TEST = re.compile(r"^test (?P<name>.+?) \.\.\. (?P<res>ok|FAILED|ignored|bench:.*)(?:, .*)?$")
_RESULT = re.compile(
    r"^test result: (?P<res>ok|FAILED)\. (?P<passed>\d+) passed; (?P<failed>\d+) failed; "
    r"(?P<ignored>\d+) ignored; (?P<measured>\d+) measured; .*finished in (?P<secs>[\d.]+)s"
)
_FAILURE_HEAD = re.compile(r"^---- (?P<name>.+?) stdout ----$")
_TERSE = re.compile(r"^[.Fi]+$")
_STATUS = {"ok": Status.PASSED, "FAILED": Status.FAILED, "ignored": Status.SKIPPED}


def looks_like(lines: list[str]) -> bool:
    return any(_BLOCK.match(ln) for ln in lines) and any(_RESULT.match(ln) for ln in lines)


def parse(lines: list[str]) -> Run:
    run = Run(format="cargo")
    file = ""
    in_block = False
    block_results: list[TestResult] = []
    terse_chars = ""
    failure_names: list[str] = []
    after_failures = False
    for raw in lines:
        line = raw.rstrip()
        m = _RUNNING.match(line)
        if m:
            file = m.group("file")
            continue
        m = _DOCTEST.match(line)
        if m:
            file = f"doctests {m.group('crate')}"
            continue
        if _BLOCK.match(line):
            in_block = True
            block_results, terse_chars, failure_names, after_failures = [], "", [], False
            continue
        if not in_block:
            continue
        if line == "failures:":
            after_failures = True
            continue
        m = _FAILURE_HEAD.match(line)
        if m and after_failures:
            failure_names.append(m.group("name"))
            continue
        m = _RESULT.match(line)
        if m:
            in_block = False
            if block_results:
                run.results.extend(block_results)
            else:
                # Terse: named failures first, then unnamed passed and ignored tests.
                remaining = list(terse_chars)
                for name in failure_names:
                    run.results.append(TestResult(name, Status.FAILED, file))
                    if "F" in remaining:
                        remaining.remove("F")
                for i, ch in enumerate(remaining, 1):
                    status = Status.SKIPPED if ch == "i" else Status.PASSED
                    run.results.append(TestResult(f"{file}::unnamed test {i}", status, file))
                if terse_chars:
                    run.notes.append(
                        f"terse output in {file or 'a test binary'}: passing tests are unnamed"
                    )
            expected = int(m.group("passed")) + int(m.group("failed")) + int(m.group("ignored"))
            got = len(block_results) if block_results else len(terse_chars)
            if got != expected:
                run.incomplete = True
                run.notes.append(f"{file or 'block'}: result line counts {expected}, found {got}")
            continue
        if after_failures:
            continue
        m = _TEST.match(line)
        if m:
            res = m.group("res")
            if res.startswith("bench:"):
                continue
            block_results.append(TestResult(m.group("name"), _STATUS[res], file))
            continue
        if _TERSE.match(line) and not block_results:
            terse_chars += line
    if in_block:
        run.incomplete = True
        run.results.extend(block_results)
        run.notes.append("last test block has no 'test result:' line")
    if not run.results and not run.incomplete:
        run.incomplete = True
        run.notes.append("no test results found")
    return run
