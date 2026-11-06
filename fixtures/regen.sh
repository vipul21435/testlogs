#!/usr/bin/env bash
# Regenerate the pytest fixtures by really running fixtures/pytest_sample with uv.
# Run from the repo root: bash fixtures/regen.sh
set -u
cd "$(dirname "$0")/.."
S=fixtures/pytest_sample
P="uv run --no-sync python -m pytest -p no:cacheprovider --color=no"

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
# Replace the machine's checkout path with a neutral one so fixtures are portable.
ROOT="$(pwd)"
for f in fixtures/*.log fixtures/*.xml; do
  sed -i.bak -e "s#$ROOT#/work#g" -e 's/hostname="[^"]*"/hostname="localhost"/g' "$f" && rm "$f.bak"
done
# unittest -v on its own sample (kept out of pytest_sample so the pytest logs stay the same).
uv run --no-sync python -m unittest -v fixtures.unittest_sample.test_unit > fixtures/unittest-v.log 2>&1
sed -i.bak -e "s#$ROOT#/work#g" fixtures/unittest-v.log && rm fixtures/unittest-v.log.bak
echo "fixtures regenerated"
