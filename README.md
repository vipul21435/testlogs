# testlogs

Turn any test runner's output into per-test results, and diff two runs.

## Why this is hard

Test runners write for people, not for programs. A pytest log mixes progress lines,
captured stdout, tracebacks and a short summary; with `-s` a test's own output lands
between its id and its status, and with pytest-xdist two workers interleave their lines.
Colour codes and carriage-return progress bars break naive line matching. Parametrised
ids carry spaces, brackets and non-ASCII characters, and duplicate names are legal in
jest, vitest, mocha and node:test. Default reporters (jest, vitest, cargo `--format
terse`) name only the failures. pytest 9 reports a `unittest` test whose subtest failed
as `PASSED` and counts the subtest failure separately. And a log cut off by a timeout
looks like a smaller green run unless the parser checks for the line that closes the
run. Each of these turns into a wrong "this test passed" or "this test vanished" when
two runs are compared.

## Install

```
pip install git+https://github.com/vipul21435/testlogs
```

No runtime dependencies. The package ships `py.typed` and passes
`uv run --with mypy mypy --strict src`. Development: `uv venv --python 3.12 .venv`,
then `uv pip install -e ".[dev]"` and `uv run pytest -q`.

## Quickstart

Two runs of the bundled pytest sample are in `fixtures/`. Diff them:

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

A default jest log names only failures; the gap to the log's own count is reported:

```
$ testlogs parse fixtures/jest-default.log
failed  jest/maths.test.js::maths > add > fails on purpose
failed  jest/strings.test.js::throws on purpose
-- jest: 2 failed
   note: jest totals: 2 failed, 1 skipped, 1 todo, 5 passed, 9 total
   note: default reporter: only failed tests are named individually
   note: the log's summary counts 9 tests; 2 records were parsed
```

A cut-off log is reported incomplete, not guessed:

```
$ testlogs parse fixtures/go-v-truncated.log
passed  TestParse  0.010s
-- go: 1 passed  (incomplete)
   note: 1 results after the last package line
   note: 1 tests started but never finished: TestRender
```

A failing subtest makes its test failed, in every format, and `--normalise-ids` lets
a pytest log be compared with a `unittest -v` log of the same suite:

```
$ testlogs parse fixtures/subtests-pytest-v.log
passed  fixtures/subtests_sample/test_subtests.py::Table::test_all_cases_pass
failed  fixtures/subtests_sample/test_subtests.py::Table::test_one_case_fails
passed  fixtures/subtests_sample/test_subtests.py::Table::test_plain
-- pytest: 2 passed, 1 failed
   note: pytest counts 5 subtests passed
   note: 1 failing subtests in 1 tests: those tests are recorded as failed
$ testlogs diff --normalise-ids fixtures/subtests-pytest-v.log fixtures/subtests-unittest-v.log
fixed (failed -> passed): 0
broken (passed -> failed): 0
appeared: 0
vanished: 0
```

Other options: `--json` on both commands; `--format NAME` to skip detection;
`--strip-prefix PREFIX` to drop a checkout root from ids (jest and vitest JSON reports
use absolute paths, their text reporters relative ones); on `diff`, `--fail-on-broken`
(exit 1 when a test went passed -> failed) and `--fail-on-incomplete` (exit 3 when
either log is incomplete). The Python API is `testlogs.parse(text, fmt=None)`,
`testlogs.diff_runs(before, after, key=None)` and `testlogs.normalise_id`; see
`examples/diff_two_runs.py`.

## Formats

| format name | runner and mode | fixture |
|---|---|---|
| `pytest` | pytest `-v`, `-q`, `-rA` summary, `-s`, colour, pytest-xdist `-n`, pytest-rerunfailures | real run, pytest 9.2.0 |
| `junit` | JUnit XML (`testcase` elements; tested on pytest's `--junitxml`) | real run, pytest 9.2.0 |
| `unittest` | `python -m unittest -v` (3.10 and 3.11+ line shapes, doctests, subTest) | real run, Python 3.12 |
| `jest` | jest default and `--verbose` | real run, jest 29.7.0 |
| `vitest` | vitest default and `--reporter=verbose` | real run, vitest 2.1.9 |
| `jest-json` | `jest --json` and `vitest --reporter=json` | real runs |
| `mocha` | mocha `spec` reporter (TAP reporter goes to `tap`) | real run, mocha 10.8.2 |
| `nodetest` | `node --test` spec reporter (TAP reporter goes to `tap`) | real run, Node 25.9.0 |
| `tap` | TAP 13 and 14, nested subtests | real runs (mocha, node:test) and one hand-written file |
| `go`, `go-json` | `go test -v`, `go test -json` | written to the documented format: go is not installed here |
| `cargo` | `cargo test`, pretty and `--format terse` | written to the documented format: cargo is not installed here |

The Python fixtures come from `bash fixtures/regen.sh` (pytest under uv, with
`uv run --with` pytest-xdist 3.8.0 and pytest-rerunfailures 16.1 for those two logs) and the node ones from
`bash fixtures/node_sample/regen.sh` after `npm install` in `fixtures/node_sample/`.
Both scripts replace the checkout path with `/work`, the home directory with
`/home/user`, and the JUnit host name and timestamp with neutral values.

## How it works

1. **Cleaning** (`testlogs.clean`). ANSI escape sequences are removed; each line is
   replayed the way a terminal would, so the text after the last carriage return wins;
   a CI log's per-line job, step and ISO timestamp prefix is dropped. Parsers see
   plain lines.
2. **Detection** (`testlogs.parsers.detect_format`). XML with `testcase` and JSON with
   `testResults` are checked first, then go `-json` events, then each line parser's
   `looks_like` in a fixed order (pytest, go, cargo, unittest, jest, vitest, node:test,
   mocha, TAP). Each test is a cheap signature: the pytest session header, `=== RUN`,
   `running N tests`, `Ran N tests`, `PASS file` plus `Tests:`, and so on.
3. **Records** (`testlogs.models`). Every parser returns a `Run`: a list of
   `TestResult(id, status, file, duration)` with status one of `passed, failed,
   skipped, error, xfail, xpass`, plus `incomplete`, free-text `notes`, and
   `summary_total`, the count the log's own summary line gives. When `summary_total`
   and the number of records differ, a note says so. The records are never padded to
   match the count.
4. **Completeness**. Each format has a line that closes the run: pytest's
   `=== N passed in Xs ===`, unittest's `Ran N tests`, jest's `Tests:`, vitest's
   `Tests ... (N)`, mocha's `N passing`, node:test's `ℹ tests N`, the TAP plan
   (checked against the count of top-level test points, as TAP 14 asks), JUnit's
   well-formed XML, cargo's `test result:` per binary, go's package line or package
   `pass`/`fail` event. Without it the run is `incomplete`. In go and cargo, a test
   that started and has no result line also makes the run incomplete.
5. **pytest**. A verbose line is `id STATUS [ 42%]`; the id is matched lazily and the
   status word anchors the end, so spaces, brackets and unicode in a parameter id are
   fine. A line that starts with a node id but carries no status (pytest `-s`, or an
   xdist start line) holds that id until a bare status line follows; the end of a node
   id is found by counting brackets, so `[with space]` stays inside it. xdist's
   `[gw1] [ 42%] PASSED id` lines are read in whatever order the workers finish. When
   an `-rA` short summary is present its rows override the verbose status, because a
   verbose line can be split by captured output and a summary row cannot.
   `SUBFAILED(...) id` rows mark their parent failed; `--durations` tables fill
   `duration`. pytest-rerunfailures' `id RERUN` lines are counted, not recorded: the
   test's last status is its record, and a note names every test that passed only on
   a rerun, since that is the flaky case a diff would otherwise hide.
6. **Subtests**. pytest 9 runs `unittest` subtests itself
   ([pytest docs](https://docs.pytest.org/en/stable/how-to/subtests.html)). Measured
   here with pytest 9.2.0: for a `unittest.TestCase.subTest` failure the parent line
   says `PASSED`, a `SUBFAILED(i=1)` row follows, and the final line counts
   `1 failed, 3 passed` for three tests; for the `subtests` fixture the parent is also
   `FAILED` and the final line says `3 failed` for one failing test with two failing
   subtests. JUnit XML and `unittest -v` both report the parent as failed. testlogs
   records the parent as failed in every case and subtracts the subtest failures from
   `summary_total`, so the four logs of `fixtures/subtests_sample/` give the same
   records.
7. **JS reporters**. jest, vitest, mocha and node:test print describe blocks as an
   indented tree; a stack of `(indent, name)` pairs gives each test the id
   `file::outer > inner > name` (mocha's spec reporter prints no file, so its ids have
   none). node:test's closing `✔ suite` lines are recognised as summaries, not tests.
   Duplicate names are kept as separate records.
8. **JUnit XML**. Each `testcase` is a record with id `classname::name` and duration
   from `time`; the status comes from its `error`, `failure` or `skipped` child, and
   `<skipped type="pytest.xfail">` is read as xfail. Surefire's `flakyFailure` and
   `rerunFailure` children sit beside a final pass and do not make the test failed.
9. **go and cargo**. go ids are `package::TestName/subtest` and cargo ids
   `target::module::test`, because the same name can exist in two packages or test
   binaries. The go `-json` field names follow
   [cmd/test2json](https://pkg.go.dev/cmd/test2json); cargo's pretty and terse shapes
   follow the [rustc test harness docs](https://doc.rust-lang.org/rustc/tests/index.html).
   Terse output names only failures, so its passing and ignored tests are counted in a
   note instead of being given invented ids.
10. **Diff** (`testlogs.diff`). Records are grouped by id (or by `key(id)`); a
    duplicated id collapses to one status, failure winning over pass. Then
    failed/error -> passed/xpass is *fixed*, passed/xpass -> failed/error is *broken*,
    ids on one side only are *appeared* or *vanished*, and any other change (skipped ->
    passed, say) is listed under *other changes*. Both incomplete flags travel with the
    diff, so a truncated side is printed as a warning next to its "vanished" tests.
11. **Id normalisation** (`testlogs.normalise_id`). `tests/test_a.py::C::t[p]`,
    `tests.test_a.C::t[p]` (pytest's JUnit) and `tests.test_a.C.t` (unittest) all map to
    `tests.test_a.C.t[p]`: the `.py` path becomes a dotted module and `::` becomes `.`,
    leaving the parameter brackets alone.

The design follows the public problem as it appears in benchmark harnesses that grade a
code change by running its tests: the SWE-bench harness, for example, has one log
parser per repository that maps a pytest log to `{test name: status}`
([log_parsers/python.py](https://github.com/SWE-bench/SWE-bench/blob/main/swebench/harness/log_parsers/python.py)).
testlogs is the general-purpose part of that job: many runners, one record type, an
explicit `incomplete` flag and a diff. It has no notion of which run is "before" a
change beyond the argument order.

## Results on real public data

Data: the test suite of [more-itertools](https://github.com/more-itertools/more-itertools)
(MIT licence, checked on its
[LICENSE page](https://github.com/more-itertools/more-itertools/blob/master/LICENSE)),
commit `f42daddf205f`, run here with Python 3.12.13 and pytest 9.2.0 in four ways, plus
the same suite at release `v10.5.0` run with that release's code; and the mocha suite of
[bytes.js](https://github.com/visionmedia/bytes.js) (MIT licence, checked on its
[LICENSE page](https://github.com/visionmedia/bytes.js/blob/master/LICENSE)), commit
`9ddc13b6c66e`, run with mocha 10.8.2 under Node 25.9.0. The logs stay outside
the repo; the scripts regenerate them:

```
bash examples/real_data.sh DATA_DIR              # clone, run the suite, write DATA_DIR/logs
uv run python examples/real_data.py DATA_DIR     # parse, time, cross-check
```

Parse time is the median of 9 calls of `testlogs.parse` on a macOS laptop
(`real_data.py DATA_DIR --repeats 9`); the range is over three such runs.

| log | format | size | lines | records | passed | summary count | incomplete | parse time (ms) |
|---|---|---|---|---|---|---|---|---|
| pytest -v | pytest | 0.07 MB | 863 | 771 | 771 | 771 | no | 5.2-6.1 |
| pytest -v, colour | pytest | 0.08 MB | 863 | 771 | 771 | 771 | no | 6.2-7.0 |
| pytest -v -rA --durations=0 | pytest | 2.01 MB | 23,047 | 771 | 771 | 771 | no | 149-160 |
| pytest --junitxml | junit | 0.07 MB | 1 | 771 | 771 | - | no | 1.3-1.5 |
| python -m unittest -v | unittest | 0.08 MB | 1,231 | 935 | 935 | 935 | no | 4.5-4.9 |

The `-rA` log is large because the suite runs 21,203 subtests and `-rA` prints a row for
each passing one; testlogs counts them in a note and gives them no records.

Cross-checks, with `diff_runs(..., key=normalise_id)` against the plain `-v` log: the
colour, `-rA` and JUnit logs give 0 fixed, 0 broken, 0 appeared, 0 vanished, 0 other.
The unittest log gives 164 appeared and nothing else; all 164 are doctests
(`more_itertools.more.*`, `more_itertools.recipes.*`) that the suite's `load_tests` adds
under unittest and that pytest does not collect. One bug was found this way and fixed
before these numbers were taken: unittest doctest lines collapsed into two ids (774
distinct ids for 935 tests). The 21,203 subtests in this suite also led to a probe of
pytest 9's subtest output, which showed that `SUBFAILED` rows were not read; the
`fixtures/subtests_sample/` logs come from that probe.

bytes.js: the spec reporter log gives 30 records (summary count 30) and the TAP log 30;
matched with `" > "` read as a space (mocha's TAP reporter joins titles with spaces),
the diff is empty.

Release diff: `v10.5.0` gives 664 records (663 passed, 1 skipped); against the current
run, 0 fixed, 0 broken, 119 appeared, 12 vanished, 0 other.

Truncation: each of the five logs cut at 50 random byte offsets (seed 0): 50 of 50 cut
copies of every log are reported incomplete or are rejected as unrecognisable; none is
read as a complete, smaller run. The test suite also cuts 14 fixture logs at every line
before their closing line (565 cuts) and checks each is incomplete
(`tests/test_truncation.py`).

Tests: `uv run pytest -q --cov=testlogs` gives 118 passed and 96 % line coverage
(1013 statements, 38 missed) in 0.31 s; the same suite passes on Python 3.10.

## Limitations

- go and cargo fixtures are written by hand from the documented formats; no real go or
  cargo log has been parsed, because neither toolchain is installed here. go benchmark
  lines, `=== PAUSE`/`=== CONT` ordering and the `FailedBuild` field are not
  interpreted, and cargo's unstable `--format json` is not supported. With
  `cargo test -- --no-capture` a test's own output can split its `test x ... ok` line;
  that shape is not handled.
- go and cargo have no line that closes the whole run, only one per package or test
  binary, so a log cut exactly between two packages or binaries looks complete.
- Default jest and vitest reporters, cargo terse and pytest `-q` name only failures;
  passing tests are counted (`summary_total`) but have no records, so a diff against a
  verbose log shows them as vanished. vitest 2's verbose reporter does not print
  skipped or todo tests either.
- Passing subtests get no records; a failing one marks its parent failed and is not a
  record of its own.
- pytest `-s` output that a test writes without a trailing newline glues onto the
  status word (`xPASSED`); that test is then read from the `-rA` summary only, or
  missed when there is none (the summary-count note then shows the gap).
- mocha's spec reporter prints no file names, so mocha ids carry none; mocha and
  node:test TAP ids join levels differently (`a b c` and `a > b > c`).
- pytest prints non-ASCII parameter ids escaped (`\xfc`) unless configured otherwise;
  the parser keeps whatever the log says. `normalise_id` does not undo the escaping.
- pytest writes an unexpected pass (xpass) to JUnit XML as a plain pass, so a JUnit
  record says `passed` where the `-v` log says `xpass`.
- unittest `file` is the dotted module, not a path; for a doctest it is the module the
  docstring lives in.
- Detection is heuristic; pass `--format` for a log it cannot place. Logs that mix two
  runners in one file are parsed as whichever is detected first.

## Related tools

- [reporewind](https://github.com/vipul21435/reporewind): resolve Python fix commits into source and test patches.
- [graderguard](https://github.com/vipul21435/graderguard): audit graders for reward hacking and flakiness.
- [taskledger](https://github.com/vipul21435/taskledger): schema validation and lint rules for benchmark-task bundles.
- [commitminer](https://github.com/vipul21435/commitminer): mine and rank candidate tasks from repository history.

Other public tools for parts of this job:
[junitparser](https://pypi.org/project/junitparser/) reads and merges JUnit XML;
[tap-parser](https://github.com/tapjs/tapjs/tree/main/src/parser) parses TAP 14 into
events; [test2json](https://pkg.go.dev/cmd/test2json) turns go test output into JSON
events. Each covers one format; testlogs puts many formats into one record type and
diffs them.

## Licence

MIT. See `LICENSE`.

Built by Vipul Raj Jha · https://vipul21435.github.io
