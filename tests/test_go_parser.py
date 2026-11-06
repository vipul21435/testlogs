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


def test_go_parallel_pause_cont_lines_are_ignored():
    text = (
        "=== RUN   TestA\n=== PAUSE TestA\n=== RUN   TestB\n=== PAUSE TestB\n"
        "=== CONT  TestA\n=== CONT  TestB\n=== NAME  TestB\n    b_test.go:9: slow\n"
        "--- PASS: TestB (0.20s)\n--- FAIL: TestA (0.30s)\nFAIL\n"
        "FAIL\texample.com/p\t0.501s\n"
    )
    run = parse(text)
    assert run.format == "go" and not run.incomplete
    assert [(r.id, r.status) for r in run.results] == [
        ("example.com/p::TestB", Status.PASSED),
        ("example.com/p::TestA", Status.FAILED),
    ]


def test_go_json_interleaved_packages_and_same_test_name():
    events = [
        '{"Action":"start","Package":"a"}',
        '{"Action":"start","Package":"b"}',
        '{"Action":"run","Package":"a","Test":"TestX"}',
        '{"Action":"run","Package":"b","Test":"TestX"}',
        '{"Action":"output","Package":"b","Test":"TestX","Output":"--- FAIL\\n"}',
        '{"Action":"fail","Package":"b","Test":"TestX","Elapsed":0.2}',
        '{"Action":"pass","Package":"a","Test":"TestX","Elapsed":0.1}',
        '{"Action":"pass","Package":"a","Elapsed":0.3}',
        '{"Action":"fail","Package":"b","Elapsed":0.4}',
    ]
    run = parse("\n".join(events))
    assert not run.incomplete
    assert [(r.id, r.status, r.duration) for r in run.results] == [
        ("b::TestX", Status.FAILED, 0.2),
        ("a::TestX", Status.PASSED, 0.1),
    ]
    cut = parse("\n".join(events[:-1]))
    assert cut.incomplete and any("without a final pass or fail event: b" in n for n in cut.notes)


def test_go_cached_package_line_closes_its_package():
    # cmd/go prints "(cached)" in place of the elapsed time for a cached result.
    text = (
        "=== RUN   TestA\n--- PASS: TestA (0.00s)\nPASS\nok  \texample.com/a\t(cached)\n"
        "=== RUN   TestB\n--- PASS: TestB (0.00s)\nPASS\nok  \texample.com/b\t0.012s\n"
    )
    run = parse(text)
    assert not run.incomplete
    assert [r.id for r in run.results] == ["example.com/a::TestA", "example.com/b::TestB"]
    last = parse(text.split("=== RUN   TestB")[0])
    assert not last.incomplete and [r.file for r in last.results] == ["example.com/a"]
