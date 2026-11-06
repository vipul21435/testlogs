// A test that prints a line shaped like a passing test, at a test's own indent.
const assert = require('assert');

describe('Outer', function () {
  it('prints a check mark', function () {
    console.log('    ✓ not a test');
    assert.ok(true);
  });

  it('plain', function () {
    assert.strictEqual(1 + 1, 2);
  });
});
