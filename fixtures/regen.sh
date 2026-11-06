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
# A truncated tail: the first 12 lines of the verbose log.
head -n 12 fixtures/pytest-v-after.log > fixtures/pytest-v-truncated.log

# unittest -v on its own sample (kept out of pytest_sample so the pytest logs stay the same).
$U fixtures.unittest_sample.test_unit > fixtures/unittest-v.log 2>&1

# subTest cases, under pytest (which reports subtests itself from version 9) and unittest.
T=fixtures/subtests_sample/test_subtests.py
$P -v $T > fixtures/subtests-pytest-v.log 2>&1
$P -v -rA $T > fixtures/subtests-pytest-rA.log 2>&1
$P -q --junitxml=fixtures/subtests-junit.xml $T > /dev/null 2>&1
$U fixtures.subtests_sample.test_subtests > fixtures/subtests-unittest-v.log 2>&1

# Replace the machine's checkout path and host name so fixtures are portable.
for f in fixtures/*.log fixtures/*.xml; do
  sed -i.bak -e "s#$ROOT#/work#g" -e 's/hostname="[^"]*"/hostname="localhost"/g' \
    -e 's/timestamp="[^"]*"/timestamp="2026-01-01T00:00:00"/g' "$f" && rm "$f.bak"
done
echo "fixtures regenerated"
