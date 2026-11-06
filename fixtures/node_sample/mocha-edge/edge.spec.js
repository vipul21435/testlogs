// Output that mocha's spec reporter mixes into its tree: a line printed while the file
// loads, an indented line printed by a test, and a describe title that starts with "- ".
const assert = require('assert');

console.log('printed while the file loads');

describe('outer', function () {
  it('first', function () {});
  it('logs', function () {
    console.log('  indented log line');
  });
  it('fails', function () {
    assert.strictEqual(1, 2);
  });
  it('pending one');
  describe('- dash describe', function () {
    it('inside dash', function () {});
  });
  it('after the nested block', function () {});
});

describe('second', function () {
  it('adds', function () {
    assert.strictEqual(1 + 1, 2);
  });
});
