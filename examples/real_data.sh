#!/usr/bin/env bash
# Run the test suite of more-itertools (MIT) four ways and keep the logs, so that
# examples/real_data.py can check the parsers against each other on a real suite.
# Usage: bash examples/real_data.sh DATA_DIR
set -u
DATA="${1:?usage: real_data.sh DATA_DIR}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$DATA/logs/old"
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
# The same suite at an older release, run with that release's code, for a real diff.
OLD=v10.5.0
git fetch -q --depth 1 origin tag "$OLD"
[ -d "../more-itertools-$OLD" ] || git worktree add -q "../more-itertools-$OLD" "$OLD"
(cd "../more-itertools-$OLD" && PYTHONPATH=. "$ROOT/$PY" -m pytest -p no:cacheprovider --color=no \
  -v tests > ../logs/old/pytest-v.log 2>&1)
# A small JS suite, bytes.js (MIT), under the mocha installed in fixtures/node_sample
# (run "npm ci" there first). Its tests need no other package.
MOCHA="$REPO/fixtures/node_sample/node_modules/.bin/mocha"
if [ -x "$MOCHA" ]; then
  mkdir -p ../logs/js
  [ -d ../bytes.js ] || git clone -q --depth 1 https://github.com/visionmedia/bytes.js.git ../bytes.js
  (cd ../bytes.js && git log -1 --format='bytes.js commit %H' >> ../logs/SOURCE \
    && NO_COLOR=1 "$MOCHA" --check-leaks --reporter spec > ../logs/js/mocha-spec.log 2>&1
    "$MOCHA" --check-leaks --reporter tap > ../logs/js/mocha-tap.log 2>&1)
fi
for f in ../logs/*.log ../logs/*.xml ../logs/old/*.log ../logs/js/*.log; do
  sed -i.bak -e "s#$ROOT-$OLD#/work#g" -e "s#$ROOT#/work#g" -e "s#$HOME#/home/user#g" -e 's/hostname="[^"]*"/hostname="localhost"/g' "$f" && rm "$f.bak"
done
ls -l ../logs
