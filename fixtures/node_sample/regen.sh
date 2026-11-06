#!/usr/bin/env bash
# Regenerate the node runner fixtures by really running the sample suites.
# Run from the repo root after "npm ci" in fixtures/node_sample (package-lock.json pins
# the jest, vitest and mocha versions the fixtures were made with):
#   bash fixtures/node_sample/regen.sh
set -u
cd "$(dirname "$0")"
OUT=..
export NO_COLOR=1 CI=1 FORCE_COLOR=0
# --runInBand runs the test files one at a time, so the log order does not depend
# on which worker finishes first.
J="npx jest --config jest.config.json --runInBand"
$J > $OUT/jest-default.log 2>&1
$J --verbose > $OUT/jest-verbose.log 2>&1
$J --json --outputFile=$OUT/jest-report.json > /dev/null 2>&1
# A test file that fails to load, and a test whose name holds "›" (jest-edge/).
JE="npx jest --config jest-edge.config.json --runInBand"
$JE > $OUT/jest-default-edge.log 2>&1
$JE --verbose > $OUT/jest-verbose-edge.log 2>&1
$JE --json --outputFile=$OUT/jest-report-edge.json > /dev/null 2>&1
V="npx vitest run --config vitest.config.mjs"
$V > $OUT/vitest-default.log 2>&1
$V --reporter=verbose > $OUT/vitest-verbose.log 2>&1
$V --reporter=json --outputFile=$OUT/vitest-report.json > /dev/null 2>&1
# A test file that fails to load (it imports a missing module) beside a normal one.
VB="npx vitest run --config vitest-broken.config.mjs"
$VB > $OUT/vitest-default-broken.log 2>&1
$VB --reporter=verbose > $OUT/vitest-verbose-broken.log 2>&1
$VB --reporter=json --outputFile=$OUT/vitest-report-broken.json > /dev/null 2>&1
M="npx mocha mocha/maths.spec.js mocha/strings.spec.js"
$M --reporter spec > $OUT/mocha-spec.log 2>&1
$M --reporter tap > $OUT/mocha-tap.log 2>&1
# Output mixed into the spec tree (see mocha-edge/edge.spec.js), the same file run through
# "npm run", whose "> name@version script" banner comes first, and a run over a minute
# (slow.spec.js waits 61 s), which mocha's summary prints as "(1m)".
npx mocha mocha-edge/edge.spec.js --reporter spec > $OUT/mocha-spec-edge.log 2>&1
npm run mocha-edge > $OUT/mocha-spec-npm.log 2>&1
npx mocha mocha-edge/slow.spec.js mocha-edge/edge.spec.js --reporter spec > $OUT/mocha-spec-slow.log 2>&1
N="node --test"
$N --test-reporter=spec nodetest/maths.test.mjs nodetest/strings.test.mjs > $OUT/nodetest-spec.log 2>&1
$N --test-reporter=tap nodetest/maths.test.mjs nodetest/strings.test.mjs > $OUT/nodetest-tap.log 2>&1
# Names holding "#" and "\", which TAP 14 escapes as "\#" and "\\".
$N --test-reporter=tap nodetest/escapes.test.mjs > $OUT/nodetest-tap-escapes.log 2>&1
$N --test-reporter=spec nodetest/escapes.test.mjs > $OUT/nodetest-spec-escapes.log 2>&1
# A test that prints a spec-shaped line, and a test with subtests.
$N --test-reporter=spec nodetest/edge.test.mjs > $OUT/nodetest-spec-edge.log 2>&1
$N --test-reporter=tap nodetest/edge.test.mjs > $OUT/nodetest-tap-edge.log 2>&1
# A colour run to exercise ANSI stripping on a node reporter.
FORCE_COLOR=1 $J --verbose --colors > $OUT/jest-verbose-color.log 2>&1
# Replace the checkout path and timing noise so the fixtures are portable.
ROOT="$(cd .. && pwd)"
for f in $OUT/jest-*.log $OUT/jest-*.json $OUT/vitest-*.log $OUT/vitest-*.json $OUT/mocha-*.log $OUT/nodetest-*.log; do
  sed -i.bak -e "s#$ROOT#/work#g" "$f" && rm "$f.bak"
done
echo "node fixtures regenerated"
