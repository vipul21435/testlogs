from pathlib import Path

from testlogs import Status, detect_format, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"


def _statuses(run):
    return {r.id.rsplit("::", 1)[-1]: r.status for r in run.results}


def test_verbose_log_has_every_outcome_kind():
    run = parse((FIX / "pytest-v-after.log").read_text())
    assert run.format == "pytest"
    assert not run.incomplete
    s = _statuses(run)
    assert s["test_add"] is Status.PASSED
    assert s["test_broken_in_after"] is Status.FAILED
    assert s["test_skipped"] is Status.SKIPPED
    assert s["test_xfail"] is Status.XFAIL
    assert s["test_xpass"] is Status.XPASS
    assert s["test_error"] is Status.ERROR
    assert len(run.results) == 14


def test_parametrised_ids_with_space_brackets_unicode():
    run = parse((FIX / "pytest-v-after.log").read_text())
    ids = {r.id.rsplit("::", 1)[-1] for r in run.results}
    assert "test_param[with space]" in ids
    assert "test_param[br[ack]ets]" in ids
    assert any(i.startswith("test_param[\\xfc") for i in ids)


def test_summary_log_matches_verbose_log():
    v = parse((FIX / "pytest-v-after.log").read_text())
    s = parse((FIX / "pytest-rA-after.log").read_text())
    assert _statuses(v) == _statuses(s)


def test_colour_log_matches_plain_log():
    plain = parse((FIX / "pytest-v-after.log").read_text())
    colour = parse((FIX / "pytest-v-color.log").read_text())
    assert _statuses(plain) == _statuses(colour)
    assert not colour.incomplete


def test_truncated_log_is_incomplete_not_guessed():
    run = parse((FIX / "pytest-v-truncated.log").read_text())
    assert run.incomplete
    assert len(run.results) == 5
    assert all(r.status is Status.PASSED for r in run.results)


def test_file_is_taken_from_node_id():
    run = parse((FIX / "pytest-v-after.log").read_text())
    assert {r.file for r in run.results} == {"fixtures/pytest_sample/test_sample.py"}


def test_detect_format_pytest():
    assert detect_format((FIX / "pytest-v-after.log").read_text()) == "pytest"


def test_interleaved_output_between_lines():
    text = (
        "============================= test session starts ==============================\n"
        "collected 2 items\n\n"
        "t/test_a.py::test_one some stray print\n"
        "PASSED\n"
        "t/test_a.py::test_two PASSED\n"
        "=========================== short test summary info ============================\n"
        "PASSED t/test_a.py::test_one\n"
        "PASSED t/test_a.py::test_two\n"
        "============================== 2 passed in 0.01s ===============================\n"
    )
    run = parse(text)
    assert [r.id for r in run.results] == ["t/test_a.py::test_two", "t/test_a.py::test_one"]
    assert not run.incomplete
