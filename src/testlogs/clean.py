"""Normalise raw runner output before parsing.

Runners write ANSI colour, carriage-return progress lines and mixed line
endings. Parsers see plain lines only.
"""

from __future__ import annotations

import re

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\x1b[()][A-Z0-9]")


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


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
    text = strip_ansi(text)
    text = resolve_carriage_returns(text)
    return text.split("\n")
