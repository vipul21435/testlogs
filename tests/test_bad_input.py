"""JSON input of the wrong shape, and parse failures at the command line."""

import pytest

from testlogs import parse
from testlogs.cli import main


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        '{"testResults": [1]}',
        '{"testResults": 5}',
        '{"testResults": [{"name": "a.js", "assertionResults": [7, {"title": 3}]}]}',
        '{"testResults": [{"name": "a.js", "assertionResults": [{"duration": "x"}]}]}',
    ],
)
def test_jest_json_of_the_wrong_shape_does_not_raise(text):
    run = parse(text, fmt="jest-json")
    assert run.format == "jest-json"


def test_jest_json_skips_entries_that_are_not_objects():
    run = parse(
        '{"testResults": [1, {"name": "a.js", "assertionResults": '
        '[2, {"title": "t", "status": "passed"}]}]}',
        fmt="jest-json",
    )
    assert [r.id for r in run.results] == ["a.js::t"]
    assert any("2 entries" in n for n in run.notes)
    assert parse("[]", fmt="jest-json").incomplete


def test_go_json_bare_values_are_not_events():
    lines = [
        '{"Action":"run","Package":"p","Test":"TestA"}',
        "5",
        '{"Action":"pass","Package":"p","Test":"TestA","Elapsed":"soon"}',
        '{"Action":"pass","Package":"p","Elapsed":0.1}',
    ]
    run = parse("\n".join(lines), fmt="go-json")
    assert [(r.id, r.duration) for r in run.results] == [("p::TestA", None)]
    assert run.incomplete and any("not a JSON event" in n for n in run.notes)


def test_cli_reports_a_parse_failure_in_one_line(tmp_path, capsys, monkeypatch):
    import testlogs.parsers as parsers

    def boom(text, fmt=None):
        raise KeyError("x")

    log = tmp_path / "a.log"
    log.write_text("anything")
    monkeypatch.setattr("testlogs.cli.parse", boom)
    assert main(["parse", str(log)]) == 2
    err = capsys.readouterr().err
    assert err.startswith(f"testlogs: {log}: cannot parse") and "Traceback" not in err
    assert parsers.parse is not boom
