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
        "[gw0] [100%] SKIPPED a.py::test_w[  (x) (x)] \\]\n"
        "==== 1 passed, 3 skipped, 1 xfailed in 0.01s ====\n"
    )
    run = _run_text(text)
    assert [(r.id, r.status.value) for r in run.results] == [
        ("a.py::test_s", "skipped"),
        ("a.py::test_t", "xfail"),
        ("a.py::test_u[x (y)]", "passed"),
        ("a.py::test_v[x (y)]", "skipped"),
        ("a.py::test_w[  (x) (x)] \\]", "skipped"),
    ]


def _run_text(text: str):
    return parse(text, fmt="pytest")


def test_captured_inner_session_adds_no_records():
    run = _run("pytest-v-pytester.log")
    assert not run.incomplete
    assert [(r.id.rsplit("::", 1)[1], r.status.value) for r in run.results] == [
        ("test_inner_run", "failed"),
        ("test_other", "passed"),
    ]
    assert run.summary_total == 2


def test_log_cut_after_a_captured_final_line_is_incomplete():
    run = _run("pytest-v-pytester-cut.log")
    assert run.incomplete
    assert len(run.results) == 2


def test_printed_pytest_lines_in_captured_output_are_not_tests():
    run = _run("pytest-v-tricky.log")
    assert not any("test_phantom" in r.id for r in run.results)
    cut = "\n".join((FIX / "pytest-v-tricky.log").read_text().splitlines()[:-3])
    assert _run_text(cut).incomplete


def test_warnings_summary_ends_a_captured_section():
    text = (
        "============================= test session starts ==============================\n"
        "a.py::test_x FAILED [100%]\n"
        "=================================== FAILURES ===================================\n"
        "a.py::test_fake PASSED\n"
        "=============================== warnings summary ===============================\n"
        "a.py::test_x\n  a.py:3: UserWarning: w\n"
        "========================= 1 failed, 1 warning in 0.01s =========================\n"
        "make: *** [test] Error 1\n"
    )
    run = _run_text(text)
    assert not run.incomplete
    assert [r.id for r in run.results] == ["a.py::test_x"]


def test_grouped_skip_rows_are_counted_in_a_note():
    run = _run("pytest-q-rA-tricky.log")
    assert not run.incomplete
    assert not any(r.status.value == "skipped" for r in run.results)
    assert any("4 skipped tests" in n and "no test id" in n for n in run.notes)
    # With -v the same skips have ids, and the rows add nothing.
    verbose = _run("pytest-rA-tricky.log")
    assert sum(r.status.value == "skipped" for r in verbose.results) == 4
    assert not any("no test id" in n for n in verbose.notes)


def test_small_quiet_logs_are_detected():
    from testlogs import detect_format

    assert detect_format((FIX / "pytest-q-one.log").read_text()) == "pytest"
    text = "F..                                                                      [100%]\n"
    text += "=========================== short test summary info ============================\n"
    text += "FAILED a.py::test_x - assert 0\n1 failed, 2 passed in 0.12s\n"
    assert detect_format(text) == "pytest"
    run = _run("pytest-q-one.log")
    assert not run.incomplete and run.summary_total == 1


def test_teardown_errors_merge_the_same_way_in_v_and_rA():
    from testlogs import diff_runs

    v, ra = _run("pytest-v-tricky.log"), _run("pytest-rA-tricky.log")
    for run in (v, ra):
        by = {r.id.rsplit("::", 1)[1]: r.status.value for r in run.results}
        assert by["test_fail_and_teardown_error"] == "failed"
        assert by["test_pass_and_teardown_error"] == "error"
        # pytest counts a test with a teardown error twice: 11 in the line, 9 tests.
        assert run.summary_total == 9 == len(run.results)
    assert diff_runs(v, ra).is_empty()


def test_random_verbose_lines_with_parenthesised_reasons():
    # A compact form of the fuzz run that found the ")" bug: random parameter ids and
    # reasons, written the way pytest -v writes them, must come back whole.
    import random

    rng = random.Random(0)
    alphabet = "ab (x) [y] - ü:"
    statuses = ["PASSED", "FAILED", "SKIPPED", "XFAIL", "XPASS", "ERROR"]
    expected, lines = [], ["============================= test session starts ===="]
    for i in range(300):
        param = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8))).strip()
        param = param.replace("[", "").replace("]", "")
        tid = f"t.py::test_{i}[{param}]" if param else f"t.py::test_{i}"
        status = rng.choice(statuses)
        reason = ""
        if status in ("SKIPPED", "XFAIL"):
            reason = " (" + "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 9))) + ")"
        pad = " " * rng.randint(1, 40)
        lines.append(f"{tid} {status}{reason}{pad}[{i % 100:3d}%]")
        expected.append(tid)
    lines.append("==== 300 passed in 0.10s ====")
    run = _run_text("\n".join(lines))
    assert [r.id for r in run.results] == expected
