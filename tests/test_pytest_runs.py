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
