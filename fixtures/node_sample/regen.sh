#!/usr/bin/env bash
# Regenerate the node runner fixtures by really running the sample suites.
# Run from the repo root after "npm install" in fixtures/node_sample:
#   bash fixtures/node_sample/regen.sh
set -u
cd "$(dirname "$0")"
OUT=..
export NO_COLOR=1 CI=1 FORCE_COLOR=0
J="npx jest --config jest.config.json"
$J > $OUT/jest-default.log 2>&1
$J --verbose > $OUT/jest-verbose.log 2>&1
$J --json --outputFile=$OUT/jest-report.json > /dev/null 2>&1
V="npx vitest run --config vitest.config.mjs"
$V > $OUT/vitest-default.log 2>&1
$V --reporter=verbose > $OUT/vitest-verbose.log 2>&1
$V --reporter=json --outputFile=$OUT/vitest-report.json > /dev/null 2>&1
M="npx mocha mocha/maths.spec.js mocha/strings.spec.js"
$M --reporter spec > $OUT/mocha-spec.log 2>&1
$M --reporter tap > $OUT/mocha-tap.log 2>&1
N="node --test"
$N --test-reporter=spec nodetest/maths.test.mjs nodetest/strings.test.mjs > $OUT/nodetest-spec.log 2>&1
$N --test-reporter=tap nodetest/maths.test.mjs nodetest/strings.test.mjs > $OUT/nodetest-tap.log 2>&1
# Names holding "#" and "\", which TAP 14 escapes as "\#" and "\\".
$N --test-reporter=tap nodetest/escapes.test.mjs > $OUT/nodetest-tap-escapes.log 2>&1
$N --test-reporter=spec nodetest/escapes.test.mjs > $OUT/nodetest-spec-escapes.log 2>&1
# A colour run to exercise ANSI stripping on a node reporter.
FORCE_COLOR=1 npx jest --config jest.config.json --verbose --colors > $OUT/jest-verbose-color.log 2>&1
# Replace the checkout path and timing noise so the fixtures are portable.
ROOT="$(cd .. && pwd)"
for f in $OUT/jest-*.log $OUT/jest-*.json $OUT/vitest-*.log $OUT/vitest-*.json $OUT/mocha-*.log $OUT/nodetest-*.log; do
  sed -i.bak -e "s#$ROOT#/work#g" "$f" && rm "$f.bak"
done
echo "node fixtures regenerated"
