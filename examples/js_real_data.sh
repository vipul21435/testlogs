#!/usr/bin/env bash
# Run the test suites of two small public JS/TS libraries with several reporters and
# keep the logs, so that examples/js_real_data.py can check testlogs against each
# runner's own summary line and JSON report.
#   ms  (vercel/ms, MIT), jest 30 with ts-jest
#   ufo (unjs/ufo, MIT), vitest 4
# Usage: bash examples/js_real_data.sh DATA_DIR
# Each library gets DATA_DIR/<name>/ with a package.json that installs only its test
# runner (npm, pinned versions) and the clone in DATA_DIR/<name>/repo, so that node
# finds the runner by walking up from the clone. The library's own lint, build and
# release tools are not installed.
# Then one test in each suite is made to fail by a one-line sed edit, the suite is run
# again, and the edit is reverted with "git checkout".
set -euo pipefail
DATA="${1:?usage: js_real_data.sh DATA_DIR}"
mkdir -p "$DATA/logs"
DATA="$(cd "$DATA" && pwd)"
LOGS="$DATA/logs"
export NO_COLOR=1 FORCE_COLOR=0 CI=1
MS_COMMIT=4ff48cec099f0514c3e9bbca18706c9c21122bfb
UFO_COMMIT=f06c800d0c59f2a4a1b9ba65eb6cb61a84419be6

setup() {  # name url commit npm-packages...
  local name=$1 url=$2 commit=$3
  shift 3
  mkdir -p "$DATA/$name"
  cd "$DATA/$name"
  [ -f package.json ] || printf '{"name":"%s-runner","private":true}\n' "$name" > package.json
  npm install -s --ignore-scripts --no-audit --no-fund "$@"
  [ -d repo ] || git clone -q "$url" repo
  cd repo
  git fetch -q origin "$commit" 2>/dev/null || true
  git checkout -q "$commit"
  git log -1 --format="$name commit %H" >> "$LOGS/SOURCE"
}

: > "$LOGS/SOURCE"

# ms: jest. --env node is the package's own test:nodejs script; --runInBand keeps the
# order of the files stable. The config turns coverage on, so the table is in the logs.
setup ms https://github.com/vercel/ms.git "$MS_COMMIT" \
  jest@30.0.5 ts-jest@29.4.0 @jest/globals@30.0.5 typescript@5.8.3 ts-node@10.9.2
J="../node_modules/.bin/jest --env node --runInBand"
$J > "$LOGS/ms-jest-default.log" 2>&1 || true
$J --verbose > "$LOGS/ms-jest-verbose.log" 2>&1 || true
$J --json --outputFile="$LOGS/ms-jest.json" > /dev/null 2>&1 || true
# One test made to fail: ms('100') is expected to be 101.
sed -i.bak "s/expect(ms('100')).toBe(100);/expect(ms('100')).toBe(101);/" src/index.test.ts
rm src/index.test.ts.bak
git diff --quiet && { echo "the one-line edit did not apply" >&2; exit 1; }
$J --verbose > "$LOGS/ms-jest-verbose-broken.log" 2>&1 || true
$J --json --outputFile="$LOGS/ms-jest-broken.json" > /dev/null 2>&1 || true
git checkout -q -- src/index.test.ts
git diff --quiet

# ufo: vitest. Without --typecheck, which needs typescript; that part of the package's
# test script is a type check, not a test.
setup ufo https://github.com/unjs/ufo.git "$UFO_COMMIT" vitest@4.1.5
V="../node_modules/.bin/vitest run"
$V > "$LOGS/ufo-vitest-default.log" 2>&1 || true
$V --reporter=verbose > "$LOGS/ufo-vitest-verbose.log" 2>&1 || true
$V --reporter=tap > "$LOGS/ufo-vitest-tap.log" 2>&1 || true
$V --reporter=tap-flat > "$LOGS/ufo-vitest-tap-flat.log" 2>&1 || true
$V --reporter=junit > "$LOGS/ufo-vitest-junit.xml" 2>/dev/null || true
$V --reporter=json --outputFile="$LOGS/ufo-vitest.json" > /dev/null 2>&1 || true
# One test made to fail: "/foo != /bar" now expects isSamePath to say true.
sed -i.bak '22s/toBe(false)/toBe(true)/' test/is-same.test.ts
rm test/is-same.test.ts.bak
git diff --quiet && { echo "the one-line edit did not apply" >&2; exit 1; }
$V --reporter=verbose > "$LOGS/ufo-vitest-verbose-broken.log" 2>&1 || true
$V --reporter=tap > "$LOGS/ufo-vitest-tap-broken.log" 2>&1 || true
$V --reporter=json --outputFile="$LOGS/ufo-vitest-broken.json" > /dev/null 2>&1 || true
git checkout -q -- test/is-same.test.ts
git diff --quiet

# Neutral paths and host names in every log.
for f in "$LOGS"/*.log "$LOGS"/*.json "$LOGS"/*.xml; do
  sed -i.bak -e "s#$DATA#/work#g" -e "s#$HOME#/home/user#g" \
    -e 's/hostname="[^"]*"/hostname="localhost"/g' "$f" && rm "$f.bak"
done
{ node --version; ../node_modules/.bin/vitest --version; "$DATA/ms/node_modules/.bin/jest" --version; } \
  > "$LOGS/VERSIONS"
ls -l "$LOGS"
