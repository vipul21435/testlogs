// Tests that print lines shaped like vitest's own result lines.
import { describe, expect, test } from 'vitest';

describe('printing', () => {
  test('prints a pass mark', () => {
    console.log('  ✓ fake passing line');
    expect(1).toBe(1);
  });

  test('prints a fail mark', () => {
    console.error('  × fake failing line');
    expect(1).toBe(1);
  });

  test('really fails', () => {
    console.log('  ✓ another fake line');
    expect(1).toBe(2);
  });
});
