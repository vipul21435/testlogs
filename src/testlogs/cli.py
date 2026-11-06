"""Command line: ``testlogs parse LOG`` and ``testlogs diff BEFORE AFTER``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from testlogs.diff import diff_runs
from testlogs.ids import normalise_id
from testlogs.models import Run
from testlogs.parsers import FORMATS, parse


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _load(path: str, fmt: str | None, prefixes: list[str] | None = None) -> Run:
    run = parse(_read(path), fmt)
    for prefix in prefixes or []:
        run = run.strip_prefix(prefix)
    return run


def _print_run(run: Run, as_json: bool) -> None:
    if as_json:
        print(json.dumps(run.to_dict(), indent=2))
        return
    for r in run.results:
        dur = "" if r.duration is None else f"  {r.duration:.3f}s"
        print(f"{r.status.value:<8}{r.id}{dur}")
    counts = {k: v for k, v in run.counts().items() if v}
    tail = ", ".join(f"{v} {k}" for k, v in counts.items()) or "no tests"
    flag = "  (incomplete)" if run.incomplete else ""
    print(f"-- {run.format}: {tail}{flag}")
    for note in run.notes:
        print(f"   note: {note}")


def _print_diff(d, as_json: bool) -> None:
    if as_json:
        print(json.dumps(d.to_dict(), indent=2))
        return
    sections = [
        ("fixed (failed -> passed)", d.fixed),
        ("broken (passed -> failed)", d.broken),
        ("appeared", d.appeared),
        ("vanished", d.vanished),
    ]
    for title, ids in sections:
        print(f"{title}: {len(ids)}")
        for tid in ids:
            print(f"  {tid}")
    if d.changed:
        print(f"other changes: {len(d.changed)}")
        for tid, b, a in d.changed:
            print(f"  {tid}: {b} -> {a}")
    if d.before_incomplete:
        print("warning: BEFORE log is incomplete")
    if d.after_incomplete:
        print("warning: AFTER log is incomplete")


_STRIP_HELP = "remove PREFIX from the start of ids and files (repeatable)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="testlogs", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse", help="list per-test results from one log")
    p.add_argument("log", help="log file, or - for stdin")
    p.add_argument("--format", choices=FORMATS, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--strip-prefix", action="append", metavar="PREFIX", help=_STRIP_HELP)
    d = sub.add_parser("diff", help="compare two logs")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("--format", choices=FORMATS, default=None, help="apply to both logs")
    d.add_argument("--json", action="store_true")
    d.add_argument("--strip-prefix", action="append", metavar="PREFIX", help=_STRIP_HELP)
    d.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="exit 3 when either log is truncated or otherwise incomplete",
    )
    d.add_argument(
        "--normalise-ids",
        action="store_true",
        help="match pytest, JUnit and unittest ids of the same test (path::C::t == path.C.t)",
    )
    d.add_argument(
        "--fail-on-broken", action="store_true", help="exit 1 when any test went passed -> failed"
    )
    args = ap.parse_args(argv)
    try:
        if args.cmd == "parse":
            _print_run(_load(args.log, args.format, args.strip_prefix), args.json)
            return 0
        before = _load(args.before, args.format, args.strip_prefix)
        after = _load(args.after, args.format, args.strip_prefix)
        result = diff_runs(before, after, key=normalise_id if args.normalise_ids else None)
        _print_diff(result, args.json)
        if args.fail_on_incomplete and (result.before_incomplete or result.after_incomplete):
            return 3
        if args.fail_on_broken and result.broken:
            return 1
        return 0
    except (ValueError, OSError) as exc:
        print(f"testlogs: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
