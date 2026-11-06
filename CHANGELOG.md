# Changelog

## Unreleased

- pytest: a summary row's id is no longer cut at a ` - ` inside the parameter brackets
  (`test_p[a - b]` gave a second, phantom record `test_p[a`).
- TAP: names with an escaped `\#` are read instead of dropped, a `#` comment that is not
  `SKIP` or `TODO` no longer drops the line, each indented subtest plan is checked, and
  a suite's `duration_ms` no longer overwrites its last child's duration.
- TAP: lines inside a YAML block are not read as test points, and subtests without a
  `# Subtest:` header take their parent's name.
- Notes use the singular for a count of one; the CLI help has a plain description.
- `examples/real_data.sh` stops when a clone or install fails; the node sample's
  `package-lock.json` is committed.

## 0.1.0

First version.

- Record model: one record per test with id, file, status (passed, failed, skipped,
  error, xfail, xpass) and duration; each run carries `incomplete`, notes and the
  count from the log's own summary line.
- Parsers: pytest (`-v`, `-q`, `-rA`, `-s`, pytest-xdist, pytest 9 subtests), JUnit
  XML, `unittest -v` (3.10 and 3.11+ lines, doctests, subTest), jest and vitest
  (default, verbose, JSON report), mocha spec, node:test spec, TAP 13/14 (also the
  mocha and node:test TAP reporters), `go test -v` and `-json`, `cargo test` pretty
  and terse.
- Format auto-detection.
- `testlogs parse` and `testlogs diff`, with `--json`, `--format`, `--strip-prefix`,
  `--normalise-ids`, `--fail-on-broken` and `--fail-on-incomplete`.
- ANSI colour, carriage-return progress lines and CI log line prefixes are stripped
  before parsing.
- A log without the line that closes its run is reported incomplete.
- Fixtures from real runs of small pytest, unittest, jest, vitest, mocha and node:test
  suites, with the scripts that regenerate them; go and cargo fixtures written to the
  documented formats.
- `examples/real_data.sh` and `examples/real_data.py`: run the more-itertools suite
  four ways and cross-check the parsers.
