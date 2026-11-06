const assert = require('node:assert');

it('trims whitespace', function () {
  assert.strictEqual('  a  '.trim(), 'a');
});
it('throws on purpose', function () {
  throw new Error('boom');
});
