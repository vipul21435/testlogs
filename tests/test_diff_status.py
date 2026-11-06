"""Appeared and vanished tests carry their status, and differing formats are flagged."""

import json

from testlogs import Run, Status, TestResult, diff_runs
from testlogs.cli import main


def _run(fmt, *pairs):
    return Run(format=fmt, results=[TestResult(i, s, "") for i, s in pairs])


def test_appeared_and_vanished_keep_their_status():
    before = _run("pytest", ("a", Status.PASSED), ("gone", Status.FAILED))
    after = _run("pytest", ("a", Status.PASSED), ("new", Status.FAILED))
    d = diff_runs(before, after)
    assert d.appeared == ["new"] and d.vanished == ["gone"]
    assert d.after_status == {"new": "failed"} and d.before_status == {"gone": "failed"}
    out = d.to_dict()
    assert out["after_status"] == {"new": "failed"} and out["before_status"] == {"gone": "failed"}


def test_cli_prints_status_and_a_format_warning(tmp_path, capsys):
    b = tmp_path / "b.log"
    a = tmp_path / "a.log"
    b.write_text(
        "a.py::test_x PASSED [100%]\na.py::test_y PASSED [100%]\n==== 2 passed in 0.01s ====\n"
    )
    a.write_text("PASS a.test.js\n  ✕ x (1 ms)\n\nTests:       1 failed, 1 total\n")
    assert main(["diff", str(b), str(a)]) == 0
    out = capsys.readouterr().out
    assert "  a.test.js::x (failed)" in out
    assert "  a.py::test_x (passed)" in out
    assert "warning: formats differ (pytest vs jest)" in out
    main(["diff", str(b), str(a), "--json"])
    doc = json.loads(capsys.readouterr().out)
    assert doc["before_format"] == "pytest" and doc["after_format"] == "jest"
