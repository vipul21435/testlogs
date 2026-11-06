from pathlib import Path

import pytest

from testlogs import diff_runs, normalise_id, parse
from testlogs.cli import main

FIX = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.parametrize(
    "raw, key",
    [
        ("tests/test_a.py::C::test_x", "tests.test_a.C.test_x"),
        ("./tests/test_a.py::test_x[a b]", "tests.test_a.test_x[a b]"),
        ("tests.test_a.C::test_x[p::q]", "tests.test_a.C.test_x[p::q]"),
        ("tests.test_a.C.test_x", "tests.test_a.C.test_x"),
        ("tests\\test_a.py::t", "tests.test_a.t"),
        ("jest/a.test.js::suite > name", "jest/a.test.js.suite > name"),
        ("plain", "plain"),
    ],
)
def test_normalise_id(raw, key):
    assert normalise_id(raw) == key


def test_normalised_diff_matches_three_formats_of_one_suite():
    runs = [
        parse((FIX / n).read_text(encoding="utf-8"))
        for n in ("subtests-pytest-v.log", "subtests-junit.xml", "subtests-unittest-v.log")
    ]
    for other in runs[1:]:
        assert diff_runs(runs[0], other, key=normalise_id).is_empty()
        assert not diff_runs(runs[0], other).is_empty()


def test_cli_normalise_ids(capsys):
    args = ["diff", str(FIX / "subtests-pytest-v.log"), str(FIX / "subtests-unittest-v.log")]
    assert main([*args, "--normalise-ids", "--json"]) == 0
    assert '"appeared": []' in capsys.readouterr().out
