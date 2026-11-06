"""Data model shared by every parser."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Status(str, enum.Enum):
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

    def to_dict(self) -> dict:
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

    def to_dict(self) -> dict:
        return {
            "format": self.format,
            "incomplete": self.incomplete,
            "notes": list(self.notes),
            "counts": self.counts(),
            "results": [r.to_dict() for r in self.results],
        }
