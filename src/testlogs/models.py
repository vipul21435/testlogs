"""Data model shared by every parser."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


def plural(n: int, word: str, many: str | None = None) -> str:
    """``"1 test"``, ``"2 tests"``: a count with its noun, for notes."""
    return f"{n} {word if n == 1 else (many or word + 's')}"


class Status(str, enum.Enum):
    """A test's outcome. ``error`` is a failure outside the test body (setup,
    teardown, a file that fails to load); ``xfail`` and ``xpass`` are an expected
    failure that failed and one that passed."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    XFAIL = "xfail"
    XPASS = "xpass"


@dataclass(frozen=True)
class TestResult:
    """One test outcome.

    ``id`` is the runner's own identifier for the test (for pytest the node id,
    for JUnit ``classname::name``, for TAP the description). ``file`` is the
    source file when the runner reports one, else ``""``. ``duration`` is in
    seconds, or ``None`` when the log carries no timing.
    """

    __test__ = False  # keep pytest from collecting this class

    id: str
    status: Status
    file: str = ""
    duration: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "file": self.file,
            "status": self.status.value,
            "duration": self.duration,
        }


@dataclass
class Run:
    """All records parsed from one log, plus what the parser could tell about it."""

    format: str
    results: list[TestResult] = field(default_factory=list)
    incomplete: bool = False
    notes: list[str] = field(default_factory=list)
    # The number of tests the log's own summary line reports, when it has one.
    summary_total: int | None = None

    def counts(self) -> dict[str, int]:
        out = {s.value: 0 for s in Status}
        for r in self.results:
            out[r.status.value] += 1
        return out

    def by_id(self) -> dict[str, list[TestResult]]:
        """Group records by id. Duplicate ids stay distinct: the list keeps order."""
        groups: dict[str, list[TestResult]] = {}
        for r in self.results:
            groups.setdefault(r.id, []).append(r)
        return groups

    def strip_prefix(self, prefix: str) -> Run:
        """A copy with ``prefix`` removed from the start of every id and file.

        JSON reports from jest and vitest name files by absolute path while
        their text reporters use relative ones; stripping the checkout root
        makes the two diffable.
        """

        def cut(s: str) -> str:
            return s[len(prefix) :] if prefix and s.startswith(prefix) else s

        return Run(
            format=self.format,
            results=[
                TestResult(cut(r.id), r.status, cut(r.file), r.duration) for r in self.results
            ],
            incomplete=self.incomplete,
            notes=list(self.notes),
            summary_total=self.summary_total,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "incomplete": self.incomplete,
            "summary_total": self.summary_total,
            "notes": list(self.notes),
            "counts": self.counts(),
            "results": [r.to_dict() for r in self.results],
        }
