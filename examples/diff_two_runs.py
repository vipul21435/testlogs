"""Parse the two bundled pytest logs and print what changed between them.

Run from the repo root:  uv run python examples/diff_two_runs.py
"""

from pathlib import Path

from testlogs import diff_runs, parse

FIX = Path(__file__).resolve().parent.parent / "fixtures"

before = parse((FIX / "pytest-v-before.log").read_text())
after = parse((FIX / "pytest-v-after.log").read_text())
print(f"before: {before.counts()}")
print(f"after:  {after.counts()}")

d = diff_runs(before, after)
for label, ids in (("fixed", d.fixed), ("broken", d.broken), ("appeared", d.appeared)):
    print(f"{label}: {ids}")
for tid, was, now in d.changed:
    print(f"changed: {tid} {was} -> {now}")
