import { describe, test, expect } from 'vitest';

const add = (a, b) => a + b;

describe('maths', () => {
  describe('add', () => {
    test('adds two numbers', () => {
      expect(add(1, 2)).toBe(3);
    });
    test('handles [brackets] and spaces (ünïcode)', () => {
      console.log('captured output in the middle of a run');
      expect(add(0.1, 0.2)).toBeCloseTo(0.3);
    });
    test('fails on purpose', () => {
      expect(add(2, 2)).toBe(5);
    });
  });
  test.skip('skipped for now', () => {});
  test.todo('not written yet');
  test('duplicate name', () => {});
  test('duplicate name', () => {});
});
