"""Format detection and the single ``parse`` entry point."""

from __future__ import annotations

from testlogs.clean import clean_lines, strip_ansi
from testlogs.models import Run
from testlogs.parsers import junit, pytest, tap

FORMATS = ("pytest", "junit", "tap")


def detect_format(text: str) -> str | None:
    """Return the format name, or ``None`` when nothing matches."""
    plain = strip_ansi(text)
    if junit.looks_like(plain):
        return "junit"
    lines = clean_lines(text)
    if pytest.looks_like(lines):
        return "pytest"
    if tap.looks_like(lines):
        return "tap"
    return None


def parse(text: str, fmt: str | None = None) -> Run:
    """Parse ``text`` as ``fmt``; detect the format when ``fmt`` is ``None``."""
    if fmt is None:
        fmt = detect_format(text)
    if fmt is None:
        raise ValueError("could not detect the log format; pass one of " + ", ".join(FORMATS))
    if fmt == "junit":
        return junit.parse(strip_ansi(text))
    lines = clean_lines(text)
    if fmt == "pytest":
        return pytest.parse(lines)
    if fmt == "tap":
        return tap.parse(lines)
    raise ValueError(f"unknown format {fmt!r}; known: {', '.join(FORMATS)}")
