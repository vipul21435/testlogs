import { describe, test } from 'node:test';
import assert from 'node:assert';

describe('outer', () => {
  test('plain', () => {});
  test('issue #42 works', () => {});
  test('back\\slash # and hash', () => {});
  test('slow', async () => {
    await new Promise((resolve) => setTimeout(resolve, 20));
  });
});
test('top level #7', () => {
  assert.ok(true);
});
