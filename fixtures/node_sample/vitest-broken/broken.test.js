// A test file that fails to load: it imports a module that does not exist.
import { test } from 'vitest';
import missing from './does-not-exist.js';

test('never runs', () => {
  missing();
});
