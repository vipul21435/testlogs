from pathlib import Path

from testlogs import Status, detect_format, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"


def test_cargo_pretty_blocks_and_doctests():
    text = (FIX / "cargo-pretty.log").read_text()
    assert detect_format(text) == "cargo"
    run = parse(text)
    assert not run.incomplete
    by = {r.id: r for r in run.results}
    assert by["src/lib.rs::render::tests::wide_table"].status is Status.FAILED
    assert by["src/lib.rs::parser::tests::needs_network"].status is Status.SKIPPED
    assert by["tests/integration.rs::needs_network"].file == "tests/integration.rs"
    assert by["src/lib.rs::parser::tests::unicode_name_ü"].status is Status.PASSED
    assert by["doctests sample::src/lib.rs - parse (line 12)"].status is Status.PASSED
    assert len(run.results) == 8


def test_cargo_terse_names_only_failures():
    run = parse((FIX / "cargo-terse.log").read_text())
    assert not run.incomplete
    assert [(r.id, r.status) for r in run.results] == [
        ("src/lib.rs::render::tests::wide_table", Status.FAILED)
    ]
    assert any("3 passed and 1 ignored" in n for n in run.notes)


def test_cargo_truncated_is_detected_and_incomplete():
    text = (FIX / "cargo-pretty-truncated.log").read_text()
    assert detect_format(text) == "cargo"
    run = parse(text)
    assert run.incomplete and len(run.results) == 2


def test_cargo_count_mismatch_is_incomplete():
    text = (
        "running 2 tests\ntest a ... ok\n\n"
        "test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; "
        "finished in 0.00s\n"
    )
    run = parse(text)
    assert run.incomplete
    assert "counts 2, found 1" in run.notes[0]


def test_cargo_bench_lines_are_not_tests():
    text = (
        "running 1 test\ntest bench_x ... bench:  12 ns/iter (+/- 1)\n\n"
        "test result: ok. 0 passed; 0 failed; 0 ignored; 1 measured; 0 filtered out; "
        "finished in 0.10s\n"
    )
    run = parse(text, fmt="cargo")
    assert run.results == [] and not run.incomplete


def test_cargo_text_without_blocks_is_incomplete():
    run = parse("   Compiling sample v0.1.0\nerror: could not compile\n", fmt="cargo")
    assert run.incomplete and run.notes == ["no test results found"]
