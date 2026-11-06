from testlogs.clean import clean_lines, resolve_carriage_returns, strip_ansi


def test_strip_ansi_removes_colour_and_cursor_codes():
    assert strip_ansi("\x1b[32mPASSED\x1b[0m \x1b[1A") == "PASSED "


def test_carriage_return_keeps_last_segment():
    assert resolve_carriage_returns("10%\r50%\r100%\n") == "100%\n"


def test_trailing_cr_keeps_previous_segment():
    assert resolve_carriage_returns("done\r") == "done"


def test_crlf_is_newline():
    assert clean_lines("a\r\nb") == ["a", "b"]


def test_long_whitespace_runs_parse_in_linear_time():
    import time

    from testlogs import parse

    pad = " " * 40000
    cases = {
        "pytest": "=== test session starts\na.py::t" + pad + "x\n",
        "tap": "TAP version 14\nok 1 - a" + pad + "x\n1..1\n",
        "mocha": "  suite\n    ✔ a" + pad + "x\n\n  1 passing (2ms)\n",
        "nodetest": "✔ a" + pad + "x (1ms)\nℹ tests 1\n",
        "jest": "PASS a.test.js\n  ✓ a" + pad + "x\nTests:       1 passed, 1 total\n",
        "vitest": " RUN  v2\n ✓ a.test.js > a" + pad + "x\n      Tests  1 passed (1)\n",
        "unittest": "test_a (m.C.test_a) ... " + pad + "x\nRan 1 test in 0.0s\n",
    }
    for fmt, text in cases.items():
        t0 = time.perf_counter()
        parse(text, fmt)
        assert time.perf_counter() - t0 < 0.5, fmt


def test_whitespace_runs_are_capped_but_short_padding_is_kept():
    padded = "a.py::t" + " " * 100 + "PASSED [ 50%]"
    assert clean_lines(padded) == [padded]
    assert clean_lines("a" + " " * 1000 + "b") == ["a" + " " * 256 + "b"]
