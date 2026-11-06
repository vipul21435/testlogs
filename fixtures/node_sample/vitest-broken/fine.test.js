import { expect, test } from 'vitest';

test('adds', () => {
  expect(1 + 1).toBe(2);
});

test('fails', () => {
  expect(1).toBe(2);
});
