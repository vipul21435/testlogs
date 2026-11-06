// A test that prints a line shaped like a spec result, and a test with subtests,
// which node counts as a test but prints like a describe block.
import { describe, it, test } from 'node:test';
import assert from 'node:assert';

describe('outer', () => {
  it('prints', () => {
    console.log('  ✔ printed result line (1ms)');
  });
  it('fails', () => {
    assert.strictEqual(1, 2);
  });
});

test('parent with subtests', async (t) => {
  await t.test('sub a', () => {});
  await t.test('sub b', () => {});
});
