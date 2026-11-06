# Changelog

## Unreleased

- unittest: on Python 3.10 a test whose `subTest` fails no longer takes the next
  test's result (the two heads on one line are split, and the `FAIL: ... (i=1)` header
  gives the status); lines printed after `Ran N tests` are not results; a failing
  `setUpClass` is one `error` record on 3.10 as on 3.12.
- pytest: under `-s` a pytester session glued to the outer id is skipped and the outer
  test gets its status; a final-shaped line printed by a running test, or followed by
  results, no longer marks the run complete; with `-q`, a passing test's teardown error
  is not counted twice in `summary_total`.
- JUnit: pytest's second `<testcase>` for a teardown error is merged into its test.
- vitest: `stdout |` and `stderr |` blocks are not read as results.
- mocha: printed lines with the check mark the run does not use are dropped.
- `examples/real_data.sh` passes `--rootdir .` to pytest.

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
- pytest: `!!! KeyboardInterrupt !!!` and `!!! Interrupted: ... !!!` make a run
  incomplete and name the test that was running; reasons holding `)` no longer drop a
  verbose line; captured output and nested pytest sessions are not read as results;
  grouped `SKIPPED [n] file:line` rows are counted in a note; short `-q` logs are
  detected; a teardown error merges the same way in `-v` and `-rA`.
- mocha: npm banners, output printed at load time and indented printed lines no longer
  become describe titles; a describe titled `- x` is not a pending test; run times in
  minutes (`(1m)`) close a run, and failure details are not read as tests.
- go: `ok pkg (cached)` closes its package. cargo: terse progress counters
  (` 87/200`) are read.
- unittest: tests whose printed output comes before the result are recorded.
- vitest and jest text reporters: a test file that fails to load is an `error` record
  named by the file; jest bullets are matched to verbose names that hold `›`.
- node:test: result-shaped lines outside the spec tree are not tests.
- Input: JSON reports and go events of the wrong shape, a UTF-8 byte-order mark, and
  JUnit times that are not finite numbers no longer raise; the CLI prints one line
  when a parser fails. Long whitespace runs are capped so parsing stays linear.
- `diff` prints the status of appeared and vanished tests and warns when the two logs
  have different formats; `--version`; `examples/real_data.sh` pins its clones.

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
