const assert = require('node:assert');

const add = (a, b) => a + b;

describe('maths', function () {
  describe('add', function () {
    it('adds two numbers', function () {
      assert.strictEqual(add(1, 2), 3);
    });
    it('handles [brackets] and spaces (ünïcode)', function () {
      console.log('captured output in the middle of a run');
      assert.ok(Math.abs(add(0.1, 0.2) - 0.3) < 1e-9);
    });
    it('fails on purpose', function () {
      assert.strictEqual(add(2, 2), 5);
    });
  });
  it.skip('skipped for now', function () {});
  it('not written yet');
  it('duplicate name', function () {});
  it('duplicate name', function () {});
});
