"""Diff two runs by test id."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from testlogs.models import Run, Status, TestResult

_FAIL_LIKE = {Status.FAILED, Status.ERROR}
_PASS_LIKE = {Status.PASSED, Status.XPASS}


def _collapse(records: list[TestResult]) -> Status:
    """One status for a duplicated id: a failure anywhere wins, then pass."""
    statuses = {r.status for r in records}
    if statuses & _FAIL_LIKE:
        return Status.FAILED if Status.FAILED in statuses else Status.ERROR
    if statuses & _PASS_LIKE:
        return Status.PASSED if Status.PASSED in statuses else Status.XPASS
    return records[0].status


@dataclass
class RunDiff:
    """The difference between two runs, by test id.

    ``fixed`` went failed or error -> passed or xpass, ``broken`` the reverse;
    ``appeared`` and ``vanished`` are ids on one side only, with their status in
    ``after_status`` and ``before_status``; ``changed`` holds every other status
    change as ``(id, before, after)``.
    """

    fixed: list[str] = field(default_factory=list)  # failed -> passed
    broken: list[str] = field(default_factory=list)  # passed -> failed
    appeared: list[str] = field(default_factory=list)
    vanished: list[str] = field(default_factory=list)
    changed: list[tuple[str, str, str]] = field(default_factory=list)  # other changes
    before_incomplete: bool = False
    after_incomplete: bool = False
    before_status: dict[str, str] = field(default_factory=dict)  # of vanished ids
    after_status: dict[str, str] = field(default_factory=dict)  # of appeared ids
    before_format: str = ""
    after_format: str = ""

    def is_empty(self) -> bool:
        return not (self.fixed or self.broken or self.appeared or self.vanished or self.changed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixed": self.fixed,
            "broken": self.broken,
            "appeared": self.appeared,
            "vanished": self.vanished,
            "changed": [list(c) for c in self.changed],
            "before_incomplete": self.before_incomplete,
            "after_incomplete": self.after_incomplete,
            "before_status": self.before_status,
            "after_status": self.after_status,
            "before_format": self.before_format,
            "after_format": self.after_format,
        }


def _grouped(run: Run, key: Callable[[str], str] | None) -> dict[str, Status]:
    groups: dict[str, list[TestResult]] = {}
    for r in run.results:
        groups.setdefault(key(r.id) if key else r.id, []).append(r)
    return {k: _collapse(v) for k, v in groups.items()}


def diff_runs(before: Run, after: Run, key: Callable[[str], str] | None = None) -> RunDiff:
    """Compare two runs by test id.

    ``key`` maps each id before matching, for example
    :func:`testlogs.ids.normalise_id` to compare a pytest log with a unittest log.
    """
    b = _grouped(before, key)
    a = _grouped(after, key)
    d = RunDiff(
        before_incomplete=before.incomplete,
        after_incomplete=after.incomplete,
        before_format=before.format,
        after_format=after.format,
    )
    for tid in sorted(set(a) - set(b)):
        d.appeared.append(tid)
        d.after_status[tid] = a[tid].value
    for tid in sorted(set(b) - set(a)):
        d.vanished.append(tid)
        d.before_status[tid] = b[tid].value
    for tid in sorted(set(a) & set(b)):
        sb, sa = b[tid], a[tid]
        if sb == sa:
            continue
        if sb in _FAIL_LIKE and sa in _PASS_LIKE:
            d.fixed.append(tid)
        elif sb in _PASS_LIKE and sa in _FAIL_LIKE:
            d.broken.append(tid)
        else:
            d.changed.append((tid, sb.value, sa.value))
    return d
