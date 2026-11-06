"""pytest logs from runs that stop early, odd reasons and captured inner sessions."""

from pathlib import Path

from testlogs import parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"


def _run(name: str):
    return parse((FIX / name).read_text(), fmt="pytest")


def test_keyboard_interrupt_is_incomplete_and_names_the_running_test():
    run = _run("pytest-v-interrupt.log")
    assert run.incomplete
    assert [r.id.rsplit("::", 1)[1] for r in run.results] == ["test_first"]
    assert any("KeyboardInterrupt" in n for n in run.notes)
    assert any("test_interrupted" in n and "no status" in n for n in run.notes)


def test_collection_error_interrupt_is_incomplete():
    run = _run("pytest-v-collect-error.log")
    assert run.incomplete
    assert [(r.id, r.status.value) for r in run.results] == [
        ("fixtures/collect_error_sample/test_bad_import.py", "error")
    ]
    assert any("Interrupted: 1 error during collection" in n for n in run.notes)


def test_verbose_reasons_holding_parentheses_keep_their_tests():
    run = _run("pytest-v-tricky.log")
    by = {r.id.rsplit("::", 1)[1]: r.status.value for r in run.results}
    assert by["test_xfail_paren"] == "xfail"
    assert by["test_skip_paren"] == "skipped"
    assert [by[f"test_skip_param[{i}]"] for i in (1, 2, 3)] == ["skipped"] * 3


def test_xdist_and_bare_status_reasons_holding_parentheses():
    text = (
        "[gw0] [ 50%] SKIPPED a.py::test_s (no (reason))\n"
        "a.py::test_t output\nXFAIL (bug (see #1))\n"
        "[gw1] [100%] PASSED a.py::test_u[x (y)]\n"
        "[gw1] [100%] SKIPPED a.py::test_v[x (y)] (needs (z))\n"
        "==== 1 passed, 2 skipped, 1 xfailed in 0.01s ====\n"
    )
    run = _run_text(text)
    assert [(r.id, r.status.value) for r in run.results] == [
        ("a.py::test_s", "skipped"),
        ("a.py::test_t", "xfail"),
        ("a.py::test_u[x (y)]", "passed"),
        ("a.py::test_v[x (y)]", "skipped"),
    ]


def _run_text(text: str):
    return parse(text, fmt="pytest")
