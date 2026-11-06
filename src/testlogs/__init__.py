"""testlogs: turn test runner output into per-test records and diff two runs."""

from testlogs.diff import RunDiff, diff_runs
from testlogs.ids import normalise_id
from testlogs.models import Run, Status, TestResult
from testlogs.parsers import detect_format, parse

__all__ = [
    "Run",
    "RunDiff",
    "Status",
    "TestResult",
    "detect_format",
    "diff_runs",
    "normalise_id",
    "parse",
]

__version__ = "0.1.0"
