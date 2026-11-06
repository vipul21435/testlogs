"""The README's ``$ testlogs ...`` examples print exactly what the README shows."""

import re
import shlex
from pathlib import Path

import pytest

from testlogs.cli import main

ROOT = Path(__file__).resolve().parent.parent


def _examples():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for block in re.findall(r"```\n(.*?)```", text, re.S):
        if not block.startswith("$ testlogs"):
            continue
        for part in re.split(r"^\$ ", block, flags=re.M)[1:]:
            cmd, _, expected = part.partition("\n")
            yield cmd, expected


EXAMPLES = list(_examples())


def test_readme_has_examples():
    assert len(EXAMPLES) >= 4


@pytest.mark.parametrize("cmd, expected", EXAMPLES, ids=[c for c, _ in EXAMPLES])
def test_readme_example_output(cmd, expected, capsys, monkeypatch):
    monkeypatch.chdir(ROOT)
    argv = shlex.split(cmd)
    assert argv[0] == "testlogs"
    main(argv[1:])
    assert capsys.readouterr().out == expected
