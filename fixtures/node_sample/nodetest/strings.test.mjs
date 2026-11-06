import { test } from 'node:test';
import assert from 'node:assert';

test('trims whitespace', () => {
  assert.strictEqual('  a  '.trim(), 'a');
});
test('throws on purpose', () => {
  throw new Error('boom');
});
