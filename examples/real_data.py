"""Parse the logs written by examples/real_data.sh and check them against each other.

Usage: uv run python examples/real_data.py DATA_DIR [--repeats 5] [--cuts 50]

For every log it prints the detected format, the record counts, the log's own
summary count and the median parse time. Then it diffs every pytest-family log
against the plain ``-v`` log with ids normalised, and cuts each log at random
byte offsets to count how many of the cut copies are reported incomplete.
"""

from __future__ import annotations

import argparse
import random
import statistics
import time
from pathlib import Path

from testlogs import diff_runs, normalise_id, parse


def _median_seconds(text: str, repeats: int) -> float:
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        parse(text)
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--cuts", type=int, default=50, help="truncated copies per log")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    logs = sorted(p for p in (args.data_dir / "logs").iterdir() if p.suffix in (".log", ".xml"))
    texts = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in logs}
    runs = {name: parse(text) for name, text in texts.items()}

    print(
        "| log | format | size | lines | records | passed | failed | summary count "
        "| incomplete | parse time (median) |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name, text in texts.items():
        run = runs[name]
        c = run.counts()
        secs = _median_seconds(text, args.repeats)
        print(
            f"| {name} | {run.format} | {len(text.encode()) / 1e6:.2f} MB "
            f"| {text.count(chr(10))} | {len(run.results)} | {c['passed']} | {c['failed']} "
            f"| {run.summary_total} | {run.incomplete} | {secs * 1000:.1f} ms |"
        )

    base = runs["pytest-v.log"]
    print("\nDiff against pytest-v.log with --normalise-ids:")
    for name, run in runs.items():
        if name == "pytest-v.log":
            continue
        d = diff_runs(base, run, key=normalise_id)
        print(
            f"  {name}: fixed {len(d.fixed)}, broken {len(d.broken)}, appeared "
            f"{len(d.appeared)}, vanished {len(d.vanished)}, other {len(d.changed)}"
        )

    old_log = args.data_dir / "logs" / "old" / "pytest-v.log"
    if old_log.exists():
        old = parse(old_log.read_text(encoding="utf-8"))
        d = diff_runs(old, base)
        print(f"\nOlder release ({len(old.results)} records, {old.counts()['skipped']} skipped)")
        print(
            f"  -> current ({len(base.results)} records): fixed {len(d.fixed)}, broken "
            f"{len(d.broken)}, appeared {len(d.appeared)}, vanished {len(d.vanished)}, "
            f"other {len(d.changed)}"
        )

    rng = random.Random(args.seed)
    print(f"\nTruncation: {args.cuts} cuts per log at random byte offsets:")
    for name, text in texts.items():
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
