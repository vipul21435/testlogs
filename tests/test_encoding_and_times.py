"""A byte-order mark before the log, and JUnit times that are not finite numbers."""

import pytest

from testlogs import detect_format, parse
from testlogs.cli import main


def test_byte_order_mark_does_not_defeat_detection(tmp_path, capsys):
    xml = '<?xml version="1.0"?><testsuite><testcase classname="a" name="t"/></testsuite>'
    assert detect_format("\ufeff" + xml) == "junit"
    assert [r.id for r in parse("\ufeff" + xml).results] == ["a::t"]
    log = tmp_path / "r.xml"
    log.write_bytes(b"\xef\xbb\xbf" + xml.encode())
    assert main(["parse", str(log)]) == 0
    assert "a::t" in capsys.readouterr().out


@pytest.mark.parametrize("raw", ["1,5", "nan", "inf", "soon"])
def test_junit_time_that_is_not_a_finite_number_is_dropped(raw):
    xml = f'<testsuite><testcase classname="a" name="t" time="{raw}"/></testsuite>'
    run = parse(xml)
    assert [(r.id, r.duration) for r in run.results] == [("a::t", None)]
    assert any("time" in n for n in run.notes)
