#!/usr/bin/env bash
# Run the test suite of more-itertools (MIT) four ways and keep the logs, so that
# examples/real_data.py can check the parsers against each other on a real suite.
# Usage: bash examples/real_data.sh DATA_DIR
set -u
DATA="${1:?usage: real_data.sh DATA_DIR}"
mkdir -p "$DATA/logs"
cd "$DATA"
[ -d more-itertools ] || git clone -q --depth 1 https://github.com/more-itertools/more-itertools.git
cd more-itertools
git log -1 --format='more-itertools commit %H' > ../logs/SOURCE
[ -x .venv/bin/python ] || uv venv -q --python 3.12 .venv
uv pip install -q --python .venv/bin/python -e . pytest
PY=.venv/bin/python
ROOT="$(pwd)"
$PY -m pytest -p no:cacheprovider --color=no -v tests > ../logs/pytest-v.log 2>&1
$PY -m pytest -p no:cacheprovider --color=no -v -rA --durations=0 \
  --junitxml=../logs/junit.xml tests > ../logs/pytest-rA.log 2>&1
$PY -m pytest -p no:cacheprovider --color=yes -v tests > ../logs/pytest-v-color.log 2>&1
$PY -m unittest -v tests.test_more tests.test_recipes > ../logs/unittest-v.log 2>&1
for f in ../logs/*.log ../logs/*.xml; do
  sed -i.bak -e "s#$ROOT#/work#g" -e 's/hostname="[^"]*"/hostname="localhost"/g' "$f" && rm "$f.bak"
done
ls -l ../logs
