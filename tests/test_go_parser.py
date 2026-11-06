from pathlib import Path

from testlogs import Status, detect_format, diff_runs, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"
PARSER = "example.com/sample/parser"


def test_go_verbose_subtests_and_packages():
    text = (FIX / "go-v.log").read_text()
    assert detect_format(text) == "go"
    run = parse(text)
    assert not run.incomplete
    by = {r.id: r for r in run.results}
    assert by[f"{PARSER}::TestParse/unicode_name_ü"].status is Status.PASSED
    assert by[f"{PARSER}::TestParse/brackets_[a_b]"].file == PARSER
    assert by[f"{PARSER}::TestRender"].status is Status.FAILED
    assert by[f"{PARSER}::TestSkipped"].status is Status.SKIPPED
    assert by["example.com/sample/render::TestSlow"].duration == 1.2


def test_go_same_name_in_two_packages_stays_distinct():
    run = parse((FIX / "go-v.log").read_text())
    dup = [r for r in run.results if r.id.endswith("::TestDuplicate")]
    assert {r.file for r in dup} == {PARSER, "example.com/sample/render"}


def test_go_truncated_reports_unfinished_test():
    run = parse((FIX / "go-v-truncated.log").read_text())
    assert run.incomplete
    assert any("TestRender" in n for n in run.notes)
    assert [r.id for r in run.results] == ["TestParse"]


def test_go_json_events():
    text = (FIX / "go-json.log").read_text()
    assert detect_format(text) == "go-json"
    run = parse(text)
    assert not run.incomplete
    c = run.counts()
    assert (c["passed"], c["failed"], c["skipped"]) == (3, 1, 1)


def test_go_json_cut_mid_line_is_incomplete():
    text = (FIX / "go-json.log").read_text()
    cut = text[: text.index('"Action":"fail","Package":"example.com/sample/parser","Test"') + 9]
    run = parse(cut)
    assert run.format == "go-json"
    assert run.incomplete
    assert any("never finished" in n for n in run.notes)


def test_go_diff_verbose_against_json():
    d = diff_runs(parse((FIX / "go-v.log").read_text()), parse((FIX / "go-json.log").read_text()))
    assert d.fixed == [] and d.broken == []
    assert f"{PARSER}::TestDuplicate" in d.vanished
