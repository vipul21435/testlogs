# Changelog

## Unreleased

### Added

- `examples/js_real_data.sh` and `examples/js_real_data.py`: run the jest suite of
  ms and the vitest suite of ufo at pinned commits with several reporters, once as is
  and once with one test made to fail by a reverted one-line edit, then check the
  parsed counts against each runner's summary line and JSON report, compare ids
  across reporters and diff the two runs. Results are in the README.

### Fixed

- vitest's TAP reporter (`--reporter=tap`), which writes each file and describe block
  as a point ending in `{` closed by `}`: those points were read as tests and the run
  was reported incomplete. They are now headers for the tests inside, and `# time=`
  gives the duration.
- vitest verbose lines: a test name with a space at either end, or an empty name, was
  trimmed, so its id did not match the JSON report of the same run.

## 0.1.0 - 2026-11-06

### Added

- Record model: one record per test with id, file, status (passed, failed, skipped,
  error, xfail, xpass) and duration; each run carries `incomplete`, notes and the
  count from the log's own summary line.
- Parsers for pytest (`-v`, `-q`, `-rA`, `-s`, pytest-xdist, pytest 9 subtests), JUnit
  XML, `unittest -v` (3.10 and 3.11+ lines, doctests, subTest), jest and vitest
  (text reporters and JSON report), mocha spec, node:test spec, TAP 13/14 (also the
  mocha and node:test TAP reporters), `go test -v` and `-json`, and `cargo test`
  pretty and terse.
- Format auto-detection, or `--format` to choose one.
- `testlogs parse` and `testlogs diff` (fixed, broken, appeared and vanished tests,
  with a warning when the two logs have different formats), with `--json`,
  `--strip-prefix`, `--normalise-ids`, `--fail-on-broken` and `--fail-on-incomplete`;
  `--version`.
- ANSI colour, carriage-return progress lines, CI log line prefixes and a UTF-8
  byte-order mark are stripped before parsing.
- A log without the line that closes its run, or interrupted by a keyboard interrupt,
  is reported incomplete instead of as a smaller passing run.
- Run notes for cases the records cannot show, such as skipped tests counted by file
  and line in a pytest summary, failing subtests and reruns.
- Malformed input (JSON reports and go events of the wrong shape, non-finite JUnit
  times) gives one line on the CLI instead of a traceback; parsing time stays linear
  on long whitespace runs.
- Fixtures from real runs of small pytest, unittest, jest, vitest, mocha and node:test
  suites, with the scripts that regenerate them; go and cargo fixtures written to the
  documented formats.
- `examples/real_data.sh` and `examples/real_data.py`: run the more-itertools and
  bytes.js suites at pinned commits, then parse, time and cross-check the logs.
- `examples/diff_two_runs.py`, a small library example of diffing two runs.
- README with the method, results on real public data and related tools.

### Known limitations

See the Limitations section of the README (go and cargo are tested on hand-written
fixtures only).
