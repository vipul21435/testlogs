#!/usr/bin/env bash
# Regenerate the Python fixtures by really running the sample suites with uv.
# Run from the repo root: bash fixtures/regen.sh
set -u
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
S=fixtures/pytest_sample
P="uv run --no-sync python -m pytest -p no:cacheprovider --color=no"
U="uv run --no-sync python -m unittest -v"

sed -i.bak 's/^VERSION = .*/VERSION = 1/' $S/test_sample.py && rm $S/test_sample.py.bak
$P -v $S > fixtures/pytest-v-before.log 2>&1
$P -v -rA --durations=0 $S > fixtures/pytest-rA-before.log 2>&1
$P -q --junitxml=fixtures/junit-before.xml $S > /dev/null 2>&1

sed -i.bak 's/^VERSION = .*/VERSION = 2/' $S/test_sample.py && rm $S/test_sample.py.bak
$P -v $S > fixtures/pytest-v-after.log 2>&1
$P -v -rA --durations=0 $S > fixtures/pytest-rA-after.log 2>&1
$P -q --junitxml=fixtures/junit-after.xml $S > /dev/null 2>&1
# A colour run with progress output, to exercise ANSI stripping.
uv run --no-sync python -m pytest -p no:cacheprovider --color=yes -v $S \
  > fixtures/pytest-v-color.log 2>&1
# -q prints dots and only names failures; its final line has no "=" border.
$P -q $S > fixtures/pytest-q-after.log 2>&1
# -s lets test output split a verbose line; -n 2 (pytest-xdist) interleaves two workers.
$P -v -s $S > fixtures/pytest-v-s.log 2>&1
uv run --no-sync --with pytest-xdist==3.8.0 python -m pytest -p no:cacheprovider --color=no \
  -v -n 2 $S > fixtures/pytest-xdist.log 2>&1
# pytest-rerunfailures: a test that passes on its second call, one that never does.
uv run --no-sync --with pytest-rerunfailures==16.1 python -m pytest -p no:cacheprovider \
  --color=no -v -rA --reruns 2 fixtures/rerun_sample > fixtures/pytest-rerun.log 2>&1
# A truncated tail: the first 12 lines of the verbose log.
head -n 12 fixtures/pytest-v-after.log > fixtures/pytest-v-truncated.log

# Parameter ids holding " - ", an unbalanced "]" and "[ 5%]", which look like parts of a row.
$P -v fixtures/edge_sample > fixtures/pytest-v-edge.log 2>&1
$P -v -rA fixtures/edge_sample > fixtures/pytest-rA-edge.log 2>&1

# unittest -v on its own sample (kept out of pytest_sample so the pytest logs stay the same).
$U fixtures.unittest_sample.test_unit > fixtures/unittest-v.log 2>&1
# Tests that print: with unbuffered stdout (a terminal, or PYTHONUNBUFFERED=1 in CI) the
# output lands after " ... " and the result follows it on the same or a later line.
PYTHONUNBUFFERED=1 $U fixtures.unittest_sample.test_print > fixtures/unittest-v-print.log 2>&1

# Python 3.10 prints no result for a test whose subTest fails, so the next test's head
# follows on the same line; stdout redirected to a file is block-buffered, so what the
# tests print lands after the run summary. The same suite on 3.12 for comparison.
uv run --no-project --python 3.10 python -m unittest -v fixtures.unittest_sample.test_py310 \
  > fixtures/unittest-v-py310.log 2>&1
uv run --no-project --python 3.12 python -m unittest -v fixtures.unittest_sample.test_py310 \
  > fixtures/unittest-v-py312.log 2>&1

# subTest cases, under pytest (which reports subtests itself from version 9) and unittest.
T=fixtures/subtests_sample/test_subtests.py
$P -v $T > fixtures/subtests-pytest-v.log 2>&1
$P -v -rA $T > fixtures/subtests-pytest-rA.log 2>&1
$P -q --junitxml=fixtures/subtests-junit.xml $T > /dev/null 2>&1
$U fixtures.subtests_sample.test_subtests > fixtures/subtests-unittest-v.log 2>&1
# pytest's own subtests fixture: the parent is reported FAILED as well.
$P -v fixtures/subtests_sample/test_fixture_subtests.py > fixtures/subtests-fixture-pytest-v.log 2>&1

# Runs that stop early: KeyboardInterrupt in a test (as a timeout would raise) and a
# module that fails to import, which interrupts collection.
$P -v fixtures/interrupt_sample > fixtures/pytest-v-interrupt.log 2>&1
$P -v fixtures/collect_error_sample > fixtures/pytest-v-collect-error.log 2>&1
# A -q run with a single passing test: one dot and a borderless final line.
$P -q fixtures/collect_error_sample/test_ok.py > fixtures/pytest-q-one.log 2>&1
# Skip and xfail reasons holding ")", a teardown error after a failure and after a pass,
# and a test that prints lines shaped like pytest's. A wide terminal keeps reasons whole.
COLUMNS=160 $P -v fixtures/tricky_sample > fixtures/pytest-v-tricky.log 2>&1
COLUMNS=160 $P -v -rA fixtures/tricky_sample > fixtures/pytest-rA-tricky.log 2>&1
COLUMNS=160 $P -q -rA fixtures/tricky_sample > fixtures/pytest-q-rA-tricky.log 2>&1
COLUMNS=160 $P -q fixtures/tricky_sample > fixtures/pytest-q-tricky.log 2>&1
$P -q --junitxml=fixtures/junit-tricky.xml fixtures/tricky_sample > /dev/null 2>&1
# An outer test that runs pytest -v itself (pytester) and fails, so a whole inner session
# sits in the captured output; and the same log cut right after the inner final line.
$P -v -p pytester fixtures/pytester_sample > fixtures/pytest-v-pytester.log 2>&1
n=$(grep -n "^=* 1 failed, 1 passed in" fixtures/pytest-v-pytester.log | head -n 1 | cut -d: -f1)
head -n "$n" fixtures/pytest-v-pytester.log > fixtures/pytest-v-pytester-cut.log

# The same outer test under -s: the inner session's banner is glued to the outer id.
$P -v -s -p pytester fixtures/pytester_sample > fixtures/pytest-v-s-pytester.log 2>&1
# Under -s a test prints a line shaped like the final line, with no session banner.
$P -v -s fixtures/printfinal_sample > fixtures/pytest-v-s-printfinal.log 2>&1
# A parameter id with a stray "]" before " - ", which only a verbose line can settle;
# -q -rA (no verbose lines), -rN (no summary after the tracebacks), -s (output after
# a spaced id) and --durations=0 with a setup slower than the call.
I=fixtures/ids_sample
COLUMNS=160 $P -v -rA --durations=0 $I > fixtures/pytest-v-rA-ids.log 2>&1
COLUMNS=160 $P -q -rA $I > fixtures/pytest-q-rA-ids.log 2>&1
COLUMNS=160 $P -v -rN $I > fixtures/pytest-v-rN-ids.log 2>&1
COLUMNS=160 $P -v -s $I > fixtures/pytest-v-s-ids.log 2>&1

# Replace the machine's checkout path and host name so fixtures are portable.
for f in fixtures/*.log fixtures/*.xml; do
  sed -i.bak -e "s#$ROOT#/work#g" -e "s#$HOME#/home/user#g" \
    -e "s#[^ '(]*/pytest-of-[^/]*/#/tmp/pytest-of-user/#g" -e 's/hostname="[^"]*"/hostname="localhost"/g' \
    -e 's/timestamp="[^"]*"/timestamp="2026-01-01T00:00:00"/g' "$f" && rm "$f.bak"
done
echo "fixtures regenerated"
