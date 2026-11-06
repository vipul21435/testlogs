# testlogs

Turn any test runner's output into per-test results, and diff two runs.

Status: first version. Parsers for pytest (`-v` and `-rA`), JUnit XML and TAP 13/14
are in and tested. jest, vitest, mocha, node:test, go test and cargo test are planned
and not implemented yet.

## Why this is hard

Test runners write for people, not for programs. A pytest log mixes progress lines,
captured stdout, tracebacks and a short summary, and a long test name can be split
across lines by captured output. Colour codes and carriage-return progress bars
corrupt naive line matching. Parametrised ids carry spaces, brackets and non-ASCII
characters. Duplicate names exist. A log cut off by a timeout looks like a smaller
green run unless the parser checks for the closing summary line. Diffing two runs
on top of that has to decide what a test that was skipped before and passes now
means, and what to report when one side is truncated.

## Install

```
pip install git+https://github.com/vipul21435/testlogs
```

Development: `uv venv --python 3.12 .venv`, then `uv pip install -e ".[dev]"`.

## Quickstart

Two runs of the bundled sample suite are in `fixtures/`. Diff them:

```
$ testlogs diff fixtures/pytest-v-before.log fixtures/pytest-v-after.log
fixed (failed -> passed): 1
  fixtures/pytest_sample/test_sample.py::test_fixed_in_after
broken (passed -> failed): 1
  fixtures/pytest_sample/test_sample.py::test_broken_in_after
appeared: 0
vanished: 0
other changes: 1
  fixtures/pytest_sample/test_sample.py::test_only_in_after: skipped -> passed
```

List the records of one log (`--json` gives the same as JSON):

```
$ testlogs parse fixtures/tap-nested.tap
passed  maths > adds  0.002s
failed  maths > divides by zero  0.000s
skipped strings
xpass   later
-- tap: 1 passed, 1 failed, 1 skipped, 1 xpass
```

A truncated log is reported, not guessed:

```
$ testlogs parse fixtures/pytest-v-truncated.log | tail -2
-- pytest: 5 passed  (incomplete)
   note: no final summary line: the log is truncated or the run was interrupted
```

`testlogs diff --fail-on-broken` exits 1 when any test went from passed to failed,
for use in a shell pipeline. The format is auto-detected; `--format pytest|junit|tap`
overrides it. The Python API is `testlogs.parse(text)` and
`testlogs.diff_runs(before, after)`; see `examples/diff_two_runs.py`.

## How it works

1. Cleaning (`testlogs.clean`): ANSI escape sequences are removed, then each line
   is replayed the way a terminal would, so the text after the last carriage
   return wins. Parsers only see plain lines.
2. Records (`testlogs.models`): every parser emits `TestResult(id, status, file,
   duration)` with status in `passed, failed, skipped, error, xfail, xpass`, and a
   `Run` that carries an `incomplete` flag and free-text notes.
3. pytest: verbose lines (`path::name[param] STATUS [ 42%]`) give the order and ids;
   the id is matched lazily and the status word anchors the end, so spaces, brackets
   and unicode in a parameter id are fine. When an `-rA` short summary is present,
   its rows override the status per id, because a verbose line can be split by
   captured output while the summary cannot. The run is complete only if the final
   `=== N passed ... in Xs ===` line is present. `--durations` tables fill
   `duration`.
4. JUnit XML: `testcase` elements, status from the `failure`/`error`/`skipped`
   child, id `classname::name`, duration from `time`.
5. TAP: `ok`/`not ok` lines with `# SKIP` and `# TODO` directives, nested subtests
   (TAP 14 and the node:test reporter) joined with ` > `, `duration_ms` from the
   YAML block, and the plan line checked against the count of top-level tests. A
   missing plan or a short count marks the run incomplete.
6. Diff (`testlogs.diff`): records are grouped by id; a duplicated id collapses to
   one status, failure winning over pass. Then: failed/error -> passed/xpass is
   *fixed*, passed/xpass -> failed/error is *broken*, ids on one side only are
   *appeared* or *vanished*, and any other status change (skipped -> passed, say)
   is listed under *other changes*. The diff carries both incomplete flags so a
   truncated side is never read as "tests vanished" without a warning.

## Fixtures

`fixtures/pytest_sample/` is a 14-test suite covering every outcome kind, parameter
ids with a space, brackets and unicode, a fixture error, and captured output with a
carriage return. `fixtures/regen.sh` runs it twice (before and after a one-line
change) with pytest under uv and writes the `-v`, `-rA --durations=0`, colour,
truncated and JUnit XML logs. The checkout path is replaced by `/work` so the files
are portable. `fixtures/tap-nested.tap` is written by hand.

## Results

Tests: `uv run pytest -q --cov=testlogs` gives 25 passed, 93 % line coverage
(389 statements, 29 missed), 0.1 s. No real public data has been run through this
version yet; that is the next stage.

## Limitations

- Only pytest, JUnit XML and TAP so far. jest, vitest, mocha spec, node:test spec,
  go test and cargo test are not implemented.
- pytest `-rA` rows for skipped tests carry `file:line` instead of a node id; the
  parser keeps the verbose line's id when one exists and falls back to `file:line`.
- pytest prints non-ASCII parameter ids escaped (`\xfc`) unless configured
  otherwise; the parser keeps whatever the log says.
- Durations are only present when the log carries them (`--durations` for pytest,
  `time` in JUnit, `duration_ms` in TAP YAML).
- Format detection is heuristic; pass `--format` for a log it cannot place.

## Related tools

- https://github.com/vipul21435/taskgate
- https://github.com/vipul21435/verifybench
- https://github.com/vipul21435/graderguard
- https://github.com/vipul21435/evalstats
- https://github.com/vipul21435/patchmin

## Licence

MIT. See `LICENSE`.

Built by Vipul Raj Jha · https://vipul21435.github.io
