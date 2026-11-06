import json
from pathlib import Path

from testlogs import Run, Status, TestResult, diff_runs, parse
from testlogs.cli import main

FIX = Path(__file__).resolve().parent.parent / "fixtures"


def _run(*pairs):
    return Run("x", [TestResult(i, s) for i, s in pairs])


def test_diff_categories():
    before = _run(
        ("a", Status.FAILED), ("b", Status.PASSED), ("c", Status.PASSED), ("d", Status.SKIPPED)
    )
    after = _run(
        ("a", Status.PASSED), ("b", Status.ERROR), ("d", Status.PASSED), ("e", Status.PASSED)
    )
    d = diff_runs(before, after)
    assert d.fixed == ["a"]
    assert d.broken == ["b"]
    assert d.vanished == ["c"]
    assert d.appeared == ["e"]
    assert d.changed == [("d", "skipped", "passed")]


def test_duplicate_ids_collapse_failure_first():
    before = _run(("a", Status.PASSED), ("a", Status.FAILED))
    after = _run(("a", Status.PASSED), ("a", Status.PASSED))
    assert diff_runs(before, after).fixed == ["a"]


def test_diff_on_real_fixtures():
    d = diff_runs(
        parse((FIX / "pytest-v-before.log").read_text()),
        parse((FIX / "pytest-v-after.log").read_text()),
    )
    assert [i.rsplit("::", 1)[-1] for i in d.fixed] == ["test_fixed_in_after"]
    assert [i.rsplit("::", 1)[-1] for i in d.broken] == ["test_broken_in_after"]
    assert d.appeared == [] and d.vanished == []


def test_cli_parse_json(capsys):
    assert main(["parse", str(FIX / "junit-after.xml"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["format"] == "junit" and len(data["results"]) == 14


def test_cli_diff_fail_on_broken(capsys):
    rc = main(
        [
            "diff",
            str(FIX / "pytest-v-before.log"),
            str(FIX / "pytest-v-after.log"),
            "--fail-on-broken",
        ]
    )
    assert rc == 1
    assert "broken (passed -> failed): 1" in capsys.readouterr().out


def test_cli_diff_warns_on_incomplete(capsys):
    main(["diff", str(FIX / "pytest-v-before.log"), str(FIX / "pytest-v-truncated.log")])
    assert "AFTER log is incomplete" in capsys.readouterr().out


def test_cli_bad_format(capsys):
    assert main(["parse", str(FIX / "regen.sh")]) == 2
    assert "could not detect" in capsys.readouterr().err


def test_strip_prefix_makes_json_report_diffable(capsys):
    args = ["diff", str(FIX / "vitest-report.json"), str(FIX / "vitest-verbose.log"), "--json"]
    assert main([*args, "--strip-prefix", "/work/node_sample/"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["appeared"] == []
    # The verbose reporter of vitest 2 does not name skipped and todo tests.
    assert out["vanished"] == [
        "vitest/maths.test.js::maths > not written yet",
        "vitest/maths.test.js::maths > skipped for now",
    ]


def test_parse_strip_prefix(capsys):
    assert main(["parse", str(FIX / "jest-report.json"), "--strip-prefix", "/work/"]) == 0
    assert "\npassed  node_sample/jest/" in "\n" + capsys.readouterr().out


def test_fail_on_incomplete_exit_code():
    before, after = str(FIX / "pytest-v-truncated.log"), str(FIX / "pytest-v-after.log")
    assert main(["diff", before, after, "--fail-on-incomplete"]) == 3
    assert main(["diff", after, after, "--fail-on-incomplete"]) == 0


def test_notes_use_singular_for_one():
    from testlogs.models import plural

    assert plural(1, "test") == "1 test"
    assert plural(0, "test") == "0 tests"
    assert plural(2, "failing subtest") == "2 failing subtests"
    run = parse("TAP version 13\n1..1\n", fmt="tap")
    assert "plan says 1 test, found 0" in run.notes
