from testlogs.clean import clean_lines, resolve_carriage_returns, strip_ansi


def test_strip_ansi_removes_colour_and_cursor_codes():
    assert strip_ansi("\x1b[32mPASSED\x1b[0m \x1b[1A") == "PASSED "


def test_carriage_return_keeps_last_segment():
    assert resolve_carriage_returns("10%\r50%\r100%\n") == "100%\n"


def test_trailing_cr_keeps_previous_segment():
    assert resolve_carriage_returns("done\r") == "done"


def test_crlf_is_newline():
    assert clean_lines("a\r\nb") == ["a", "b"]
