import { describe, test } from 'node:test';
import assert from 'node:assert';

const add = (a, b) => a + b;

describe('maths', () => {
  describe('add', () => {
    test('adds two numbers', () => {
      assert.strictEqual(add(1, 2), 3);
    });
    test('handles [brackets] and spaces (ünïcode)', () => {
      console.log('captured output in the middle of a run');
      assert.ok(Math.abs(add(0.1, 0.2) - 0.3) < 1e-9);
    });
    test('fails on purpose', () => {
      assert.strictEqual(add(2, 2), 5);
    });
  });
  test('skipped for now', { skip: true }, () => {});
  test('not written yet', { todo: true }, () => {});
  test('duplicate name', () => {});
  test('duplicate name', () => {});
});
