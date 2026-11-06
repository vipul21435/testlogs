"""The runner-side counting helpers of examples/js_real_data.py, on the fixtures."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"
_spec = importlib.util.spec_from_file_location("js_real_data", ROOT / "examples/js_real_data.py")
assert _spec and _spec.loader
js = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(js)


def test_jest_summary_line():
    text = (FIX / "jest-default.log").read_text(encoding="utf-8")
    # "Tests:       2 failed, 1 skipped, 1 todo, 5 passed, 9 total"
    assert js.summary_counts(text) == {"passed": 5, "failed": 2, "skipped": 2, "total": 9}


def test_vitest_summary_line():
    text = (FIX / "vitest-verbose-spaces.log").read_text(encoding="utf-8")
    assert js.summary_counts(text) == {"passed": 4, "failed": 1, "skipped": 0, "total": 5}


def test_no_summary_line():
    assert js.summary_counts("TAP version 13\n1..1\nok 1 - a\n") is None


def test_json_report_counts():
    report = json.loads((FIX / "jest-report.json").read_text(encoding="utf-8"))
    # numPendingTests 1 and numTodoTests 1 are both counted as skipped.
    assert js.json_counts(report) == {"passed": 5, "failed": 2, "skipped": 2, "total": 9}


def test_junit_counts():
    xml = (
        '<testsuites><testsuite><testcase name="a"/><testcase name="b"><failure/></testcase>'
        '<testcase name="c"><skipped/></testcase></testsuite></testsuites>'
    )
    assert js.junit_counts(xml) == {"passed": 1, "failed": 1, "skipped": 1, "total": 3}


def test_id_keys():
    assert js.id_key("/work/ufo/repo/test/a.test.ts::d > t") == "test/a.test.ts > d > t"
    assert js.loose_key("test/a.ts > d >  with {}") == js.loose_key("test/a.ts > d > with {}")
    assert js.loose_key("test/a.ts > d > \x00x") == "test/a.ts > d > x"
    assert js.loose_key("test/a.ts > d > /\t//x") == "test/a.ts > d > / //x"
    assert js.loose_key("test/a.ts::d > ") == js.loose_key("test/a.ts > d >") == "test/a.ts > d"
