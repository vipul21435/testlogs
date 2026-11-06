"""Format detection and the single ``parse`` entry point."""

from __future__ import annotations

from testlogs.clean import clean_lines, strip_ansi
from testlogs.models import Run
from testlogs.parsers import (
    cargo,
    gotest,
    jest,
    jsjson,
    junit,
    mocha,
    nodetest,
    pytest,
    tap,
    unittest,
    vitest,
)

FORMATS = (
    "pytest",
    "unittest",
    "junit",
    "tap",
    "jest",
    "jest-json",
    "vitest",
    "mocha",
    "nodetest",
    "go",
    "go-json",
    "cargo",
)

# Line-oriented parsers, tried in this order by detect_format.
_LINE_PARSERS = (
    ("pytest", pytest),
    ("go", gotest),
    ("cargo", cargo),
    ("unittest", unittest),
    ("jest", jest),
    ("vitest", vitest),
    ("nodetest", nodetest),
    ("mocha", mocha),
    ("tap", tap),
)


def detect_format(text: str) -> str | None:
    """Return the format name, or ``None`` when nothing matches."""
    plain = strip_ansi(text)
    if junit.looks_like(plain):
        return "junit"
    if jsjson.looks_like(plain):
        return "jest-json"
    lines = clean_lines(text)
    if gotest.looks_like_json(lines):
        return "go-json"
    for name, mod in _LINE_PARSERS:
        if mod.looks_like(lines):
            return name
    return None


def _check_total(run: Run) -> Run:
    """Note when the records and the log's own summary line disagree.

    A default jest or vitest reporter names only failures, so a gap is not by
    itself an error; it is reported, never filled in.
    """
    if run.summary_total is not None and run.summary_total != len(run.results):
        run.notes.append(
            f"the log's summary counts {run.summary_total} tests; "
            f"{len(run.results)} records were parsed"
        )
    return run


def parse(text: str, fmt: str | None = None) -> Run:
    """Parse ``text`` as ``fmt``; detect the format when ``fmt`` is ``None``."""
    return _check_total(_parse(text, fmt))


def _parse(text: str, fmt: str | None) -> Run:
    if fmt is None:
        fmt = detect_format(text)
    if fmt is None:
        raise ValueError("could not detect the log format; pass one of " + ", ".join(FORMATS))
    if fmt == "junit":
        return junit.parse(strip_ansi(text))
    if fmt == "jest-json":
        return jsjson.parse(strip_ansi(text))
    lines = clean_lines(text)
    if fmt == "go-json":
        return gotest.parse_json(lines)
    for name, mod in _LINE_PARSERS:
        if fmt == name:
            return mod.parse(lines)
    raise ValueError(f"unknown format {fmt!r}; known: {', '.join(FORMATS)}")
