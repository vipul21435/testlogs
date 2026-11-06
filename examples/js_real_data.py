"""Parse the logs written by examples/js_real_data.sh and check them three ways.

Usage: uv run python examples/js_real_data.py DATA_DIR [--repeats 9] [--cuts 50]

1. Per log: the format testlogs detects, its per-status counts and the median time of
   ``testlogs.parse``.
2. Each count is checked against the runner's own numbers, read here without testlogs:
   the summary line of a text log (jest ``Tests:``, vitest ``Tests ... (N)``), the
   ``num*Tests`` fields of the JSON report of the same run, and for JUnit XML the
   ``testcase`` elements and their ``failure`` and ``skipped`` children.
3. The ids from every reporter of one run are compared with the verbose reporter's,
   and the clean run is diffed against the run with one test made to fail.
Last, each log is cut at random character offsets, as in examples/real_data.py.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from testlogs import Run, diff_runs, parse

# "Tests:       1 failed, 166 passed, 167 total"
_JEST_TESTS = re.compile(r"^Tests:\s+(?P<body>.*?),?\s*(?P<total>\d+) total\s*$", re.M)
# "      Tests  1 failed | 488 passed (489)"
_VITEST_TESTS = re.compile(r"^\s+Tests\s+(?P<body>.*?)\s*\((?P<total>\d+)\)\s*$", re.M)
_PART = re.compile(r"(\d+) (passed|failed|skipped|todo|pending)")

# The four numbers compared everywhere; jest's "todo" and "pending" count as skipped.
KEYS = ("passed", "failed", "skipped", "total")


def summary_counts(text: str) -> dict[str, int] | None:
    """The counts a jest or vitest text log states in its own closing line."""
    m = _JEST_TESTS.search(text) or _VITEST_TESTS.search(text)
    if not m:
        return None
    out = dict.fromkeys(KEYS, 0)
    for n, word in _PART.findall(m.group("body")):
        key = "skipped" if word in ("todo", "pending", "skipped") else word
        out[key] += int(n)
    out["total"] = int(m.group("total"))
    return out


def json_counts(report: dict) -> dict[str, int]:
    """The counts in a jest ``--json`` or vitest ``--reporter=json`` report."""
    return {
        "passed": report["numPassedTests"],
        "failed": report["numFailedTests"],
        "skipped": report["numPendingTests"] + report.get("numTodoTests", 0),
        "total": report["numTotalTests"],
    }


def junit_counts(xml_text: str) -> dict[str, int]:
    """The counts in a JUnit XML file, from its ``testcase`` elements."""
    cases = list(ET.fromstring(xml_text).iter("testcase"))
    failed = sum(1 for c in cases if c.find("failure") is not None or c.find("error") is not None)
    skipped = sum(1 for c in cases if c.find("skipped") is not None)
    return {
        "passed": len(cases) - failed - skipped,
        "failed": failed,
        "skipped": skipped,
        "total": len(cases),
    }


def record_counts(run: Run) -> dict[str, int]:
    c = run.counts()
    return {
        "passed": c["passed"] + c["xpass"],
        "failed": c["failed"] + c["error"],
        "skipped": c["skipped"] + c["xfail"],
        "total": len(run.results),
    }


def id_key(test_id: str) -> str:
    """One id shape for every reporter: no checkout path, levels joined with " > "."""
    test_id = re.sub(r"^/work/[^/]+/repo/", "", test_id)
    return test_id.replace("::", " > ")


def loose_key(test_id: str) -> str:
    """``id_key`` without what some formats cannot carry: C0 control characters
    (JUnit XML cannot hold a NUL), tabs read as spaces (XML attribute values) and
    space at the ends of each level (TAP descriptions are trimmed), so an empty
    last level is dropped."""
    test_id = re.sub(r"[\x00-\x08\x0b-\x1f]", "", id_key(test_id)).replace("\t", " ")
    joined = " > ".join(part.strip() for part in test_id.split(" > ")).rstrip()
    # An empty last level: "suite > " (verbose) and "suite >" (trimmed flat TAP).
    return joined[:-2] if joined.endswith(" >") else joined


def _run_of(name: str) -> tuple[str, str, str]:
    """``ufo-vitest-tap-broken.log`` -> ("ufo", "vitest", "-broken")."""
    lib, runner = Path(name).stem.split("-")[:2]
    return lib, runner, "-broken" if "broken" in name else ""


def _median_ms(text: str, repeats: int) -> float:
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        parse(text)
        times.append(time.perf_counter() - t0)
    return statistics.median(times) * 1000


def _line_count(text: str) -> int:
    """Lines as an editor counts them: a last line without a newline still counts."""
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def _fmt(c: dict[str, int] | None) -> str:
    return "-" if c is None else "/".join(str(c[k]) for k in KEYS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--repeats", type=int, default=9)
    ap.add_argument("--cuts", type=int, default=50, help="truncated copies per log")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    logs = args.data_dir / "logs"
    paths = sorted(p for p in logs.iterdir() if p.suffix in (".log", ".json", ".xml"))
    texts = {p.name: p.read_text(encoding="utf-8") for p in paths}
    runs = {name: parse(text) for name, text in texts.items()}

    def report_for(name: str) -> dict[str, int] | None:
        """The JSON report written by the same run as this log."""
        lib, runner, broken = _run_of(name)
        report = f"{lib}-{runner}{broken}.json"
        if report not in texts:
            return None
        return json_counts(json.loads(texts[report]))

    print("counts are passed/failed/skipped/total")
    print(
        "| log | format | lines | records | testlogs counts | summary_total "
        "| runner summary line | JSON report | agree | incomplete | parse time (ms) |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for name, text in texts.items():
        run = runs[name]
        mine = record_counts(run)
        own = junit_counts(text) if name.endswith(".xml") else summary_counts(text)
        rep = report_for(name)
        checks = [c for c in (own, rep) if c is not None]
        if mine["total"] == 0:
            # A default reporter names no passing test: only the total can be checked.
            agree = all(run.summary_total == c["total"] for c in checks)
            note = " (total only)"
        else:
            agree = all(mine == c for c in checks)
            note = ""
        print(
            f"| {name} | {run.format} | {_line_count(text)} | {len(run.results)} "
            f"| {_fmt(mine)} | {run.summary_total if run.summary_total is not None else '-'} "
            f"| {_fmt(own)} | {_fmt(rep)} | {'yes' if agree else 'NO'}{note} "
            f"| {'yes' if run.incomplete else 'no'} | {_median_ms(text, args.repeats):.2f} |"
        )

    print(
        "\nIds against the verbose reporter of the same run: ids that differ under id_key "
        "(exact) and under loose_key, then any status that differs:"
    )
    for name, run in runs.items():
        lib, runner, broken = _run_of(name)
        base_name = f"{lib}-{runner}-verbose{broken}.log"
        if name == base_name or not run.results or base_name not in runs:
            continue
        exact = diff_runs(runs[base_name], run, key=id_key)
        loose = diff_runs(runs[base_name], run, key=loose_key)
        print(
            f"  {name} vs {base_name}: exact {len(exact.vanished)} vanished, "
            f"{len(exact.appeared)} appeared; loose {len(loose.vanished)} vanished, "
            f"{len(loose.appeared)} appeared; status changes "
            f"{len(loose.fixed) + len(loose.broken) + len(loose.changed)}; distinct ids "
            f"{len({id_key(r.id) for r in run.results})} exact, "
            f"{len({loose_key(r.id) for r in run.results})} loose"
        )

    print("\nClean run against the run with one test made to fail:")
    for before, after in [
        ("ms-jest-verbose.log", "ms-jest-verbose-broken.log"),
        ("ms-jest.json", "ms-jest-broken.json"),
        ("ufo-vitest-verbose.log", "ufo-vitest-verbose-broken.log"),
        ("ufo-vitest-tap.log", "ufo-vitest-tap-broken.log"),
        ("ufo-vitest.json", "ufo-vitest-broken.json"),
    ]:
        if before not in runs or after not in runs:
            continue
        d = diff_runs(runs[before], runs[after])
        print(
            f"  {before} -> {after}: fixed {len(d.fixed)}, broken {len(d.broken)}, "
            f"appeared {len(d.appeared)}, vanished {len(d.vanished)}, other {len(d.changed)}"
        )
        for test_id in d.broken:
            print(f"    broken: {id_key(test_id)}")

    rng = random.Random(args.seed)
    print(f"\nTruncation: {args.cuts} cuts per log at random character offsets:")
    for name, text in texts.items():
        if len(text) < 1000:
            print(f"  {name}: skipped, under 1000 characters")
            continue
        flagged = 0
        for _ in range(args.cuts):
            cut = text[: rng.randrange(1, len(text) - 200)]
            try:
                run = parse(cut)
            except ValueError:
                flagged += 1  # too short to recognise: nothing is reported as a result
                continue
            flagged += run.incomplete
        print(f"  {name}: {flagged}/{args.cuts} reported incomplete or unrecognised")


if __name__ == "__main__":
    main()
