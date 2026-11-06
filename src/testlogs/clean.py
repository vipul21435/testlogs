"""Normalise raw runner output before parsing.

Runners write ANSI colour, carriage-return progress lines and mixed line
endings. Parsers see plain lines only.

A run of more than ``MAX_SPACE_RUN`` whitespace characters inside a line is cut to
that length. Several line patterns end an id lazily and then match whitespace, so
their cost grows with the square of such a run (one line with 40,000 spaces took
seconds); no runner pads a line that far, so the cut changes no record.
"""

from __future__ import annotations

import re

MAX_SPACE_RUN = 256
_SPACE_RUN = re.compile(rf"[^\S\n]{{{MAX_SPACE_RUN + 1},}}")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\x1b[()][A-Z0-9]")
# A CI job log line: optional "job<TAB>step<TAB>" then an ISO timestamp, then the
# runner's own text. Both the raw download and the per-job view use this shape.
_CI_PREFIX = re.compile(r"^(?:[^\t\n]*\t[^\t\n]*\t)?\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z ?")


def strip_ansi(text: str) -> str:
    """Remove ANSI colour, cursor and title escape sequences."""
    return _ANSI.sub("", text)


def strip_ci_prefix(line: str) -> str:
    """Drop a CI log's per-line job, step and timestamp prefix."""
    return _CI_PREFIX.sub("", line, count=1)


def resolve_carriage_returns(text: str) -> str:
    """Apply ``\\r`` the way a terminal would: the text after the last ``\\r``
    on a line overwrites what came before it. ``\\r\\n`` is a plain newline."""
    text = text.replace("\r\n", "\n")
    out = []
    for line in text.split("\n"):
        if "\r" in line:
            segments = line.split("\r")
            final = segments[-1]
            # A trailing "\r" with nothing after it keeps the previous segment.
            if final == "" and len(segments) > 1:
                final = segments[-2]
            line = final
        out.append(line)
    return "\n".join(out)


def clean_lines(text: str) -> list[str]:
    """Plain lines: ANSI codes removed, carriage returns applied, CI prefixes dropped
    and whitespace runs longer than ``MAX_SPACE_RUN`` shortened to it."""
    text = strip_ansi(text)
    text = resolve_carriage_returns(text)
    text = _SPACE_RUN.sub(lambda m: m.group()[:MAX_SPACE_RUN], text)
    return [strip_ci_prefix(ln) for ln in text.split("\n")]
